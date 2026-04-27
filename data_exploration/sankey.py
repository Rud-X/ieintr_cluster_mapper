#!/usr/bin/env python3
"""
Sankey diagram for industrial cluster material flows.

Nodes (left → right):
  Left:         "Import" + company nodes supplying selected companies via internal flows
  Center:       selected companies
  Center-right: (optional) per-company Products / Wastes nodes
  Right:        "Export" + company nodes receiving from selected companies via internal flows

Usage:
  python data_exploration/sankey.py --help
"""

import sqlite3
import argparse
from collections import defaultdict
import plotly.graph_objects as go

# --------------------------------------------------------------------------- #
# Color palette
# --------------------------------------------------------------------------- #

PALETTE = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
    "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#17becf",
    "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
    "#f7b6d2", "#c49c94", "#dbdb8d", "#9edae5", "#ad494a",
]
OTHER_COLOR = "#cccccc"
UNKNOWN_COLOR = "#aaaaaa"

# Sentinel keys used for special link groups
_OTHER = "__other__"
_UNKNOWN = "__unknown__"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def parse_args():
    p = argparse.ArgumentParser(
        description="Generate a Sankey diagram of industrial cluster material flows.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # All included companies, component mode (top 5)
  python data_exploration/sankey.py

  # Specific companies, stream mode
  python data_exploration/sankey.py --companies C002 C003 --mode stream

  # Top 3 components + always show CM111
  python data_exploration/sankey.py --top-n 3 --include-component CM111

  # Products / wastes split, save to file
  python data_exploration/sankey.py --show-products-wastes --output sankey.html
""",
    )
    p.add_argument("--db", default="industrial_cluster.db",
                   help="SQLite database path (default: industrial_cluster.db)")
    p.add_argument("--companies", nargs="+", metavar="ID",
                   help="Company IDs to show (default: all with included=1)")
    p.add_argument("--mode", choices=["component", "stream"], default="component",
                   help="Color links by component (default) or by stream")
    p.add_argument("--top-n", type=int, default=5, dest="top_n",
                   help="Top N components before grouping the rest as 'Other' (component mode, default: 5)")
    p.add_argument("--include-component", action="append", default=[],
                   metavar="ID", dest="include_components",
                   help="Always show this component individually (repeatable; component mode only)")
    p.add_argument("--show-products-wastes", action="store_true",
                   help="Add a 4th node column that splits each company's outputs into Products and Wastes")
    p.add_argument("--output", metavar="PATH",
                   help="Save diagram as HTML file instead of opening in browser")
    return p.parse_args()


# --------------------------------------------------------------------------- #
# Database helpers
# --------------------------------------------------------------------------- #

def _placeholders(ids):
    return ",".join("?" * len(ids))


def fetch_company_names(conn, company_ids):
    """Return {company_id: name} for the given ids."""
    ph = _placeholders(company_ids)
    return dict(conn.execute(
        f"SELECT company_id, name FROM companies WHERE company_id IN ({ph})",
        company_ids,
    ))


def load_data(conn, company_ids):
    """
    Returns:
      streams    : {stream_id: {stream_id, company_id, stream_name, stream_type, direction, flow_kton}}
      flows_by_from : {from_stream_id: [flow_dict, ...]}
      flows_by_to   : {to_stream_id:   [flow_dict, ...]}
      composition   : {stream_id: [{component_id, name, fraction}, ...]}
                      includes CM227 ("unknown") rows
    """
    ph = _placeholders(company_ids)

    # --- streams (positive flow only) ---
    streams = {}
    for row in conn.execute(
        f"""
        SELECT stream_id, company_id, stream_name, stream_type, direction, flow_kton_per_year
        FROM streams
        WHERE company_id IN ({ph}) AND flow_kton_per_year > 0
        """,
        company_ids,
    ):
        streams[row[0]] = {
            "stream_id": row[0], "company_id": row[1], "stream_name": row[2],
            "stream_type": row[3], "direction": row[4], "flow_kton": row[5],
        }

    stream_ids = list(streams.keys())

    # --- flows touching these streams ---
    flows_by_from = defaultdict(list)
    flows_by_to = defaultdict(list)
    if stream_ids:
        in_ph = _placeholders(stream_ids)
        for row in conn.execute(
            f"""
            SELECT from_company_id, to_company_id, from_stream_id, to_stream_id,
                   flow_kton_per_year, flow_type
            FROM flows
            WHERE from_stream_id IN ({in_ph}) OR to_stream_id IN ({in_ph})
            """,
            stream_ids + stream_ids,
        ):
            flow = {
                "from_company_id": row[0], "to_company_id": row[1],
                "from_stream_id": row[2], "to_stream_id": row[3],
                "flow_kton": row[4], "flow_type": row[5],
            }
            if row[2]:
                flows_by_from[row[2]].append(flow)
            if row[3]:
                flows_by_to[row[3]].append(flow)

    # --- composition (all non-trace components, including CM227) ---
    composition = defaultdict(list)
    if stream_ids:
        in_ph = _placeholders(stream_ids)
        for row in conn.execute(
            f"""
            SELECT sc.stream_id, sc.component_id, c.name, sc.fraction
            FROM stream_composition sc
            JOIN components c ON c.component_id = sc.component_id
            WHERE sc.stream_id IN ({in_ph}) AND sc.is_trace = 0
            """,
            stream_ids,
        ):
            composition[row[0]].append({
                "component_id": row[1], "name": row[2], "fraction": row[3],
            })

    return streams, flows_by_from, flows_by_to, composition


# --------------------------------------------------------------------------- #
# Raw link building
# --------------------------------------------------------------------------- #

def _make_link(src_col, src_label, tgt_col, tgt_label, stream, flow_kton=None, passthrough=False):
    return {
        "src_col": src_col, "src_label": src_label,
        "tgt_col": tgt_col, "tgt_label": tgt_label,
        "stream_id": stream["stream_id"],
        "stream_name": stream["stream_name"],
        "stream_type": stream["stream_type"],
        "flow_kton": flow_kton if flow_kton is not None else stream["flow_kton"],
        "passthrough": passthrough,  # True for center_right→right legs
    }


def build_raw_links(company_ids, company_names, streams, flows_by_from, flows_by_to,
                    show_products_wastes, conn):
    """
    Produce a flat list of raw links. Each link carries:
      src_col/tgt_col  : 'left' | 'center' | 'center_right' | 'right'
      src_label/tgt_label : display name of the node
      stream_id, stream_name, stream_type, flow_kton, passthrough
    """
    # Resolve names for companies not in our selection (needed for internal flow nodes)
    external_ids = set()
    for sid, s in streams.items():
        for f in flows_by_to.get(sid, []):
            if f["flow_type"] == "internal" and f["from_company_id"] not in company_names:
                external_ids.add(f["from_company_id"])
        for f in flows_by_from.get(sid, []):
            if f["flow_type"] == "internal" and f["to_company_id"] not in company_names:
                external_ids.add(f["to_company_id"])
    all_names = dict(company_names)
    if external_ids:
        all_names.update(fetch_company_names(conn, list(external_ids)))

    links = []

    for sid, s in streams.items():
        cname = company_names[s["company_id"]]

        if s["direction"] == "input":
            if sid not in flows_by_to:
                # No flow → comes from Import
                links.append(_make_link("left", "Import", "center", cname, s))
            else:
                for f in flows_by_to[sid]:
                    if f["flow_type"] == "internal":
                        from_name = all_names.get(f["from_company_id"], f["from_company_id"])
                        links.append(_make_link("left", from_name, "center", cname, s, f["flow_kton"]))
                    else:
                        # import-type flow recorded in flows table
                        links.append(_make_link("left", "Import", "center", cname, s, f["flow_kton"]))

        else:  # output
            flow_list = flows_by_from.get(sid, [])

            def _right_label(f):
                """Destination label on the right side for a given flow."""
                if f["flow_type"] == "internal":
                    return all_names.get(f["to_company_id"], f["to_company_id"])
                return "Export"

            if not flow_list:
                # No flow → goes to Export (possibly via products/wastes node)
                if show_products_wastes:
                    sub = _sub_label(cname, s["stream_type"])
                    links.append(_make_link("center", cname, "center_right", sub, s))
                    links.append(_make_link("center_right", sub, "right", "Export", s, passthrough=True))
                else:
                    links.append(_make_link("center", cname, "right", "Export", s))
            else:
                for f in flow_list:
                    rlabel = _right_label(f)
                    if show_products_wastes:
                        sub = _sub_label(cname, s["stream_type"])
                        links.append(_make_link("center", cname, "center_right", sub, s, f["flow_kton"]))
                        links.append(_make_link("center_right", sub, "right", rlabel, s, f["flow_kton"], passthrough=True))
                    else:
                        links.append(_make_link("center", cname, "right", rlabel, s, f["flow_kton"]))

    return links


def _sub_label(company_name, stream_type):
    suffix = "Products" if stream_type == "product" else "Wastes"
    return f"{company_name} | {suffix}"


# --------------------------------------------------------------------------- #
# Link expansion (component / stream mode)
# --------------------------------------------------------------------------- #

def expand_by_component(raw_links, composition, top_n, include_component_ids):
    """
    Split each raw link into per-component sub-links.

    Returns:
      expanded          : list of link dicts with color_key, color_label, flow_kton
      ordered_color_keys: color keys in display order (top components first)
      key_to_label      : {color_key: display label}
    """
    include_set = set(include_component_ids)

    # Compute total kton per component (from non-passthrough links only, to avoid double-counting)
    totals = defaultdict(float)
    names_map = {}  # component_id → display name
    for lnk in raw_links:
        if lnk["passthrough"]:
            continue
        for comp in composition.get(lnk["stream_id"], []):
            kton = lnk["flow_kton"] * comp["fraction"]
            totals[comp["component_id"]] += kton
            names_map[comp["component_id"]] = comp["name"]

    # Determine top-N set (excluding already force-included)
    ranked = sorted(
        [(cid, tot) for cid, tot in totals.items() if cid not in include_set and cid != "CM227"],
        key=lambda x: -x[1],
    )
    top_ids = include_set | {cid for cid, _ in ranked[:top_n]}

    # Build ordered color keys: force-included first, then top-N by rank, then Other, Unknown
    ordered_keys = list(include_set)
    for cid, _ in ranked[:top_n]:
        if cid not in ordered_keys:
            ordered_keys.append(cid)
    ordered_keys += [_OTHER, _UNKNOWN]

    key_to_label = {cid: names_map.get(cid, cid) for cid in top_ids}
    key_to_label[_OTHER] = "Other"
    key_to_label[_UNKNOWN] = "Unknown"

    # Expand links
    expanded = []
    for lnk in raw_links:
        comps = composition.get(lnk["stream_id"])
        if not comps:
            expanded.append({**lnk, "color_key": _UNKNOWN, "color_label": "Unknown"})
            continue

        other_kton = 0.0
        unknown_kton = 0.0
        for comp in comps:
            kton = lnk["flow_kton"] * comp["fraction"]
            if comp["component_id"] == "CM227":
                unknown_kton += kton
            elif comp["component_id"] in top_ids:
                expanded.append({
                    **lnk,
                    "flow_kton": kton,
                    "color_key": comp["component_id"],
                    "color_label": names_map.get(comp["component_id"], comp["component_id"]),
                })
            else:
                other_kton += kton

        if other_kton > 0:
            expanded.append({**lnk, "flow_kton": other_kton, "color_key": _OTHER, "color_label": "Other"})
        if unknown_kton > 0:
            expanded.append({**lnk, "flow_kton": unknown_kton, "color_key": _UNKNOWN, "color_label": "Unknown"})

    return expanded, ordered_keys, key_to_label


def expand_by_stream(raw_links):
    """One link per stream — no grouping."""
    expanded = []
    seen_keys = []
    seen_set = set()
    for lnk in raw_links:
        key = lnk["stream_id"]
        expanded.append({**lnk, "color_key": key, "color_label": lnk["stream_name"]})
        if key not in seen_set:
            seen_keys.append(key)
            seen_set.add(key)

    key_to_label = {lnk["stream_id"]: lnk["stream_name"] for lnk in raw_links}
    return expanded, seen_keys, key_to_label


# --------------------------------------------------------------------------- #
# Color assignment
# --------------------------------------------------------------------------- #

def assign_colors(ordered_keys):
    """Map color_key → hex color string."""
    colors = {}
    palette_idx = 0
    for key in ordered_keys:
        if key == _OTHER:
            colors[key] = OTHER_COLOR
        elif key == _UNKNOWN:
            colors[key] = UNKNOWN_COLOR
        else:
            colors[key] = PALETTE[palette_idx % len(PALETTE)]
            palette_idx += 1
    return colors


def _rgba(hex_color, alpha=0.6):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# --------------------------------------------------------------------------- #
# Plotly Sankey assembly
# --------------------------------------------------------------------------- #

COL_X = {"left": 0.01, "center": 0.4, "center_right": 0.65, "right": 0.99}


def build_sankey_data(expanded_links, colors):
    """
    Build node labels/positions and link arrays for go.Sankey.

    Returns:
      node_labels, node_x, node_y,
      sources, targets, values, link_colors, link_labels
    """
    # Node registry: (col, label) → index
    node_keys = []  # list of (col, label)
    node_index = {}

    def get_node(col, label):
        key = (col, label)
        if key not in node_index:
            node_index[key] = len(node_keys)
            node_keys.append(key)
        return node_index[key]

    # Reserve Import and Export as first nodes in their columns
    get_node("left", "Import")
    get_node("right", "Export")

    # Build links
    sources, targets, values, link_colors, link_labels = [], [], [], [], []
    for lnk in expanded_links:
        if lnk["flow_kton"] <= 1e-6:
            continue
        src = get_node(lnk["src_col"], lnk["src_label"])
        tgt = get_node(lnk["tgt_col"], lnk["tgt_label"])
        color = colors.get(lnk["color_key"], OTHER_COLOR)
        sources.append(src)
        targets.append(tgt)
        values.append(round(lnk["flow_kton"], 4))
        link_colors.append(_rgba(color))
        link_labels.append(
            f"{lnk['color_label']}<br>{lnk['flow_kton']:.2f} kt/y"
            f"<br>{lnk['src_label']} → {lnk['tgt_label']}"
        )

    # Group nodes by column for y-position calculation
    col_nodes = defaultdict(list)
    for i, (col, _) in enumerate(node_keys):
        col_nodes[col].append(i)

    node_x, node_y, node_labels = [], [], []
    for i, (col, label) in enumerate(node_keys):
        node_x.append(COL_X.get(col, 0.5))
        col_list = col_nodes[col]
        pos = col_list.index(i)
        n = len(col_list)
        node_y.append(0.05 if n == 1 else 0.05 + 0.9 * pos / (n - 1))
        node_labels.append(label)

    return node_labels, node_x, node_y, sources, targets, values, link_colors, link_labels


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

def render(node_labels, node_x, node_y, sources, targets, values,
           link_colors, link_labels, key_to_label, colors, output=None):
    """Create and display (or save) the Sankey figure."""

    # Node hover text: total throughput
    node_throughput = defaultdict(float)
    for i, src in enumerate(sources):
        node_throughput[src] += values[i]
        node_throughput[targets[i]] += values[i]
    node_hover = [
        f"{label}<br>{node_throughput.get(i, 0):.2f} kt/y total"
        for i, label in enumerate(node_labels)
    ]

    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=20,
            thickness=25,
            line=dict(color="black", width=0.5),
            label=node_labels,
            customdata=node_hover,
            hovertemplate="%{customdata}<extra></extra>",
            x=node_x,
            y=node_y,
            color="rgba(120,120,120,0.3)",
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors,
            label=link_labels,
            hovertemplate="%{label}<extra></extra>",
        ),
    )])

    # Legend via annotations
    legend_lines = ["<b>Legend</b>"]
    seen_keys = []
    seen_set = set()
    for key, label in key_to_label.items():
        if key not in seen_set:
            seen_keys.append((key, label))
            seen_set.add(key)

    annotations = []
    for i, (key, label) in enumerate(seen_keys):
        color = colors.get(key, OTHER_COLOR)
        annotations.append(dict(
            x=1.01, y=1.0 - i * 0.045,
            xref="paper", yref="paper",
            xanchor="left", yanchor="top",
            text=f"<span style='color:{color}'>■</span> {label}",
            showarrow=False,
            font=dict(size=11),
        ))

    fig.update_layout(
        title_text="Industrial Cluster — Material Flow Sankey",
        font_size=12,
        height=700,
        margin=dict(r=220),
        annotations=annotations,
    )

    if output:
        fig.write_html(output)
        print(f"Saved to {output}")
    else:
        fig.show()


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main():
    args = parse_args()

    conn = sqlite3.connect(args.db)

    # Resolve company IDs
    if args.companies:
        company_ids = args.companies
    else:
        company_ids = [
            row[0] for row in conn.execute(
                "SELECT company_id FROM companies WHERE included=1 AND node_type='company' ORDER BY company_id"
            )
        ]

    if not company_ids:
        print("No companies found. Use --companies or set included=1 in the database.")
        conn.close()
        return

    company_names = fetch_company_names(conn, company_ids)
    unknown_ids = [cid for cid in company_ids if cid not in company_names]
    if unknown_ids:
        print(f"Warning: unknown company IDs: {', '.join(unknown_ids)}")
        company_ids = [cid for cid in company_ids if cid in company_names]

    print(f"Companies: {', '.join(company_names[cid] for cid in company_ids)}")

    streams, flows_by_from, flows_by_to, composition = load_data(conn, company_ids)
    print(f"Streams loaded: {len(streams)}  |  Flows loaded: {sum(len(v) for v in flows_by_from.values())}")

    raw_links = build_raw_links(
        company_ids, company_names, streams,
        flows_by_from, flows_by_to,
        args.show_products_wastes, conn,
    )

    if args.mode == "component":
        expanded, ordered_keys, key_to_label = expand_by_component(
            raw_links, composition, args.top_n, args.include_components
        )
    else:
        expanded, ordered_keys, key_to_label = expand_by_stream(raw_links)

    colors = assign_colors(ordered_keys)

    node_labels, node_x, node_y, sources, targets, values, link_colors, link_labels = \
        build_sankey_data(expanded, colors)

    if not sources:
        print("No links to display.")
        conn.close()
        return

    render(
        node_labels, node_x, node_y,
        sources, targets, values, link_colors, link_labels,
        key_to_label, colors,
        args.output,
    )

    conn.close()


if __name__ == "__main__":
    main()
