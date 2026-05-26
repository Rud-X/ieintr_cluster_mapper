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

  # Exclude a dominant component (fold into 'Other')
  python data_exploration/sankey.py --top-n 5 --exclude-component CM001

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
    p.add_argument("--exclude-component", action="append", default=[],
                   metavar="ID", dest="exclude_components",
                   help="Never show this component individually; fold into 'Other' (repeatable; component mode only)")
    p.add_argument("--hide-component", action="append", default=[],
                   metavar="ID", dest="hide_components",
                   help="Remove this component from the plot entirely; its flow is not shown (repeatable; component mode only)")
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
      streams            : {stream_id: {stream_id, company_id, stream_name, stream_type, direction, flow_kton}}
      flows_by_from      : {from_stream_id: [flow_dict, ...]}
      flows_by_to        : {to_stream_id:   [flow_dict, ...]}
      sender_stream_flows: {stream_id: flow_kton}  — from_stream flowrates for internal flows
      receiver_stream_flows: {stream_id: flow_kton} — to_stream flowrates for internal flows
      company_node_types : {company_id: node_type}  — for all companies seen in flows
      composition        : {stream_id: [{component_id, name, fraction}, ...]}
    """
    ph = _placeholders(company_ids)

    # --- streams (positive flow only, scaled by company scaling_factor) ---
    streams = {}
    for row in conn.execute(
        f"""
        SELECT s.stream_id, s.company_id, s.stream_name, s.stream_type, s.direction,
               s.flow_kton_per_year * COALESCE(c.scaling_factor, 1.0)
        FROM streams s
        JOIN companies c ON c.company_id = s.company_id
        WHERE s.company_id IN ({ph}) AND s.flow_kton_per_year > 0
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

    # --- node_type for every company seen in flows ---
    all_flow_company_ids = set()
    for fl in list(flows_by_from.values()) + list(flows_by_to.values()):
        for f in fl:
            all_flow_company_ids.add(f["from_company_id"])
            all_flow_company_ids.add(f["to_company_id"])
    company_node_types = {}
    if all_flow_company_ids:
        nt_ph = _placeholders(list(all_flow_company_ids))
        for row in conn.execute(
            f"SELECT company_id, node_type FROM companies WHERE company_id IN ({nt_ph}) AND included=1",
            list(all_flow_company_ids),
        ):
            company_node_types[row[0]] = row[1]

    # --- sender and receiver stream flowrates for internal flows ---
    # Sender streams may belong to companies outside the selected set.
    # Receiver streams are always in our selected set, but fetching them here
    # keeps the sizing logic self-contained.
    sender_stream_flows = {}   # {from_stream_id: flow_kton_per_year}
    receiver_stream_flows = {} # {to_stream_id:   flow_kton_per_year}

    internal_from_ids = [
        f["from_stream_id"]
        for fl in flows_by_to.values()
        for f in fl
        if f["flow_type"] == "internal" and f["from_stream_id"]
    ]
    internal_to_ids = [
        f["to_stream_id"]
        for fl in flows_by_from.values()
        for f in fl
        if f["flow_type"] == "internal" and f["to_stream_id"]
    ]

    all_extra_ids = list(set(internal_from_ids + internal_to_ids))
    if all_extra_ids:
        ex_ph = _placeholders(all_extra_ids)
        for row in conn.execute(
            f"""
            SELECT s.stream_id, s.flow_kton_per_year * COALESCE(c.scaling_factor, 1.0)
            FROM streams s
            JOIN companies c ON c.company_id = s.company_id
            WHERE s.stream_id IN ({ex_ph})
            """,
            all_extra_ids,
        ):
            if row[0] in internal_from_ids:
                sender_stream_flows[row[0]] = row[1]
            if row[0] in internal_to_ids:
                receiver_stream_flows[row[0]] = row[1]

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

    return streams, flows_by_from, flows_by_to, sender_stream_flows, receiver_stream_flows, company_node_types, composition


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
                    sender_stream_flows, receiver_stream_flows, company_node_types,
                    show_products_wastes, conn):
    """
    Produce a flat list of raw links. Each link carries:
      src_col/tgt_col  : 'left' | 'center' | 'center_right' | 'right'
      src_label/tgt_label : display name of the node
      stream_id, stream_name, stream_type, flow_kton, passthrough

    Flow sizing rule for internal flows:
      flow_size = min(sender_output_kton, receiver_input_kton)

      Receiver side:  flow_size from the sender node; any deficit from Import.
      Sender side:    flow_size to the receiver node; any surplus to Export.

    Named nodes for IMP/EXP/WMF:
      import_source  → named left node  (instead of generic "Import")
      export_sink    → named right node (instead of generic "Export")
      waste_facility → named right node (instead of generic "Export")
    """
    # Resolve names for all non-center companies that appear in any flow
    external_ids = set()
    for sid in streams:
        for f in flows_by_to.get(sid, []):
            if f["from_company_id"] not in company_names:
                external_ids.add(f["from_company_id"])
        for f in flows_by_from.get(sid, []):
            if f["to_company_id"] not in company_names:
                external_ids.add(f["to_company_id"])
    all_names = dict(company_names)
    if external_ids:
        all_names.update(fetch_company_names(conn, list(external_ids)))

    links = []

    for sid, s in streams.items():
        cname = company_names[s["company_id"]]

        if s["direction"] == "input":
            flow_list = flows_by_to.get(sid, [])
            if not flow_list:
                # No flow at all → entire input comes from Import
                links.append(_make_link("left", "Import", "center", cname, s))
            else:
                total_covered = 0.0
                for f in flow_list:
                    from_cid = f["from_company_id"]
                    if f["flow_type"] == "internal" or from_cid in company_names:
                        # Sender is a center company (internal flow or promoted WMF/etc.)
                        sender_kton = (
                            sender_stream_flows.get(f["from_stream_id"])
                            or streams.get(f["from_stream_id"], {}).get("flow_kton")
                            or f["flow_kton"]
                        )
                        # Flow is capped at the smaller of the two connected streams
                        flow_size = min(sender_kton, s["flow_kton"])
                        from_name = all_names.get(from_cid, from_cid)
                        links.append(_make_link("left", from_name, "center", cname, s, flow_size))
                        total_covered += flow_size
                    else:
                        # Non-center sender: named node for import_source, else "Import"
                        ntype = company_node_types.get(from_cid, "company")
                        src_label = (
                            all_names.get(from_cid, "Import")
                            if ntype == "import_source" else "Import"
                        )
                        links.append(_make_link("left", src_label, "center", cname, s, f["flow_kton"]))
                        total_covered += f["flow_kton"]

                # Remaining input not covered by any sender/import flow → comes from Import
                remainder = s["flow_kton"] - total_covered
                if remainder > 1e-6:
                    links.append(_make_link("left", "Import", "center", cname, s, remainder))

        else:  # output
            flow_list = flows_by_from.get(sid, [])

            def _right_label(f):
                """Destination label on the right side for a given flow."""
                if f["flow_type"] == "internal":
                    return all_names.get(f["to_company_id"], f["to_company_id"])
                ntype = company_node_types.get(f["to_company_id"], "company")
                if ntype in ("export_sink", "waste_facility"):
                    return all_names.get(f["to_company_id"], "Export")
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
                total_sent = 0.0
                for f in flow_list:
                    rlabel = _right_label(f)
                    if f["flow_type"] == "internal":
                        receiver_kton = receiver_stream_flows.get(f["to_stream_id"], s["flow_kton"])
                        # Flow is capped at the smaller of the two connected streams
                        kton = min(s["flow_kton"], receiver_kton)
                    else:
                        kton = s["flow_kton"]
                    total_sent += kton
                    if show_products_wastes:
                        sub = _sub_label(cname, s["stream_type"])
                        links.append(_make_link("center", cname, "center_right", sub, s, kton))
                        links.append(_make_link("center_right", sub, "right", rlabel, s, kton, passthrough=True))
                    else:
                        links.append(_make_link("center", cname, "right", rlabel, s, kton))

                    # If the receiver is a center company but has no input stream (to_stream_id is
                    # None), it cannot generate its own left-side link — do it here from the sender.
                    if f["to_stream_id"] is None and f["to_company_id"] in company_names:
                        links.append(_make_link("left", cname, "center", rlabel, s, kton))

                # Any sender output not absorbed by receivers → goes to Export
                surplus = s["flow_kton"] - total_sent
                if surplus > 1e-6:
                    if show_products_wastes:
                        sub = _sub_label(cname, s["stream_type"])
                        links.append(_make_link("center", cname, "center_right", sub, s, surplus))
                        links.append(_make_link("center_right", sub, "right", "Export", s, surplus, passthrough=True))
                    else:
                        links.append(_make_link("center", cname, "right", "Export", s, surplus))

    return links


def _sub_label(company_name, stream_type):
    suffix = "Products" if stream_type == "products" else "Wastes"
    return f"{company_name} | {suffix}"


# --------------------------------------------------------------------------- #
# Link expansion (component / stream mode)
# --------------------------------------------------------------------------- #

def expand_by_component(raw_links, composition, top_n, include_component_ids,
                        exclude_component_ids=(), hide_component_ids=()):
    """
    Split each raw link into per-component sub-links.

    Returns:
      expanded          : list of link dicts with color_key, color_label, flow_kton
      ordered_color_keys: color keys in display order (top components first)
      key_to_label      : {color_key: display label}
    """
    include_set = set(include_component_ids)
    exclude_set = set(exclude_component_ids)
    hide_set = set(hide_component_ids)

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

    # Determine top-N set (excluding already force-included, force-excluded, and hidden)
    ranked = sorted(
        [(cid, tot) for cid, tot in totals.items()
         if cid not in include_set and cid not in exclude_set and cid not in hide_set and cid != "CM227"],
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
            elif comp["component_id"] in hide_set:
                pass  # drop entirely — not shown anywhere
            elif comp["component_id"] in exclude_set:
                other_kton += kton
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


def aggregate_links(expanded):
    """
    Merge component-mode links that share the same endpoints and color_key.
    Multiple streams carrying the same component between the same two nodes
    are collapsed into one band with summed flow_kton.
    """
    merged = {}
    for lnk in expanded:
        key = (lnk["src_col"], lnk["src_label"], lnk["tgt_col"], lnk["tgt_label"], lnk["color_key"])
        if key in merged:
            merged[key]["flow_kton"] += lnk["flow_kton"]
        else:
            merged[key] = dict(lnk)
    return list(merged.values())


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


def build_sankey_data(expanded_links, colors, center_company_names):
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

    node_x, node_y, node_labels, node_colors = [], [], [], []
    for i, (col, label) in enumerate(node_keys):
        node_x.append(COL_X.get(col, 0.5))
        col_list = col_nodes[col]
        pos = col_list.index(i)
        n = len(col_list)
        node_y.append(0.05 if n == 1 else 0.05 + 0.9 * pos / (n - 1))
        # center_right nodes: display only "Products" or "Wastes", not the company prefix
        if col == "center_right" and " | " in label:
            node_labels.append(label.split(" | ", 1)[1])
        else:
            node_labels.append(label)
        node_colors.append(_node_color(col, label, center_company_names))

    return node_labels, node_x, node_y, node_colors, sources, targets, values, link_colors, link_labels


def _node_color(col, label, center_names):
    if col == "center":
        return "rgba(173,216,230,0.8)"   # light blue — company nodes
    if col == "center_right":
        if label.endswith("| Products"):
            return "rgba(148,103,189,0.8)"  # purple — product sub-nodes
        return "rgba(100,100,100,0.8)"       # dark grey — waste sub-nodes
    if col in ("left", "right") and label in center_names:
        return "rgba(173,216,230,0.8)"   # light blue — regular company sidebar nodes only
    return "rgba(120,120,120,0.3)"           # default grey — Import/Export/IMP/EXP/WMF nodes


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

def render(node_labels, node_x, node_y, node_colors, sources, targets, values,
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
            color=node_colors,
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

    # Promote waste_facility companies that have output streams to center companies
    if company_ids:
        ph = _placeholders(company_ids)
        wmf_center = [
            row[0] for row in conn.execute(
                f"""
                SELECT DISTINCT c.company_id
                FROM flows f
                JOIN streams s ON s.stream_id = f.from_stream_id
                JOIN companies c ON c.company_id = f.to_company_id
                WHERE s.company_id IN ({ph})
                  AND c.node_type = 'waste_facility' AND c.included = 1
                  AND EXISTS (
                      SELECT 1 FROM streams s2
                      WHERE s2.company_id = c.company_id AND s2.direction = 'output'
                  )
                """,
                company_ids,
            )
        ]
        for cid in wmf_center:
            if cid not in company_ids:
                company_ids.append(cid)
        if wmf_center:
            company_names = fetch_company_names(conn, company_ids)

    # Names of center companies — used to colour sidebar nodes correctly
    center_company_names = set(company_names.values())

    print(f"Companies: {', '.join(company_names[cid] for cid in company_ids)}")

    streams, flows_by_from, flows_by_to, sender_stream_flows, receiver_stream_flows, \
        company_node_types, composition = load_data(conn, company_ids)
    print(f"Streams loaded: {len(streams)}  |  Flows loaded: {sum(len(v) for v in flows_by_from.values())}")

    raw_links = build_raw_links(
        company_ids, company_names, streams,
        flows_by_from, flows_by_to,
        sender_stream_flows, receiver_stream_flows, company_node_types,
        args.show_products_wastes, conn,
    )

    if args.mode == "component":
        expanded, ordered_keys, key_to_label = expand_by_component(
            raw_links, composition, args.top_n, args.include_components,
            args.exclude_components, args.hide_components,
        )
        expanded = aggregate_links(expanded)
    else:
        expanded, ordered_keys, key_to_label = expand_by_stream(raw_links)

    colors = assign_colors(ordered_keys)

    node_labels, node_x, node_y, node_colors, sources, targets, values, link_colors, link_labels = \
        build_sankey_data(expanded, colors, center_company_names)

    if not sources:
        print("No links to display.")
        conn.close()
        return

    render(
        node_labels, node_x, node_y, node_colors,
        sources, targets, values, link_colors, link_labels,
        key_to_label, colors,
        args.output,
    )

    conn.close()


if __name__ == "__main__":
    main()
