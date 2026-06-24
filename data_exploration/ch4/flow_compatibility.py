#!/usr/bin/env python3
"""
Flow compatibility explorer for industrial cluster material streams.

Compares the streams on both sides of each proposed symbiosis flow,
showing flow rate and composition differences as tables and/or charts.

Usage:
  python data_exploration/flow_compatibility.py --help
"""

import csv
import io
import sqlite3
import argparse
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # non-interactive backend, no display needed
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# --------------------------------------------------------------------------- #
# Colors
# --------------------------------------------------------------------------- #

COLOR_A = "#4e79a7"  # Stream A (from / output)
COLOR_B = "#f28e2b"  # Stream B (to / input)

EXPORT_DIR = Path(__file__).parent / "../export"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def parse_args():
    p = argparse.ArgumentParser(
        description="Compare streams on both sides of industrial symbiosis flows.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Print comparison tables for all flows
  python data_exploration/flow_compatibility.py

  # List all flows with company and stream names
  python data_exploration/flow_compatibility.py --list-flows

  # Interactively select flows to compare
  python data_exploration/flow_compatibility.py --select

  # Compare specific flows and open visualization
  python data_exploration/flow_compatibility.py --flow FL001 FL002 --visual

  # Flow-rate-only comparison, save tables to text or CSV
  python data_exploration/flow_compatibility.py --flow-rate-only --save-text report.txt
  python data_exploration/flow_compatibility.py --flow-rate-only --save-csv report.csv

  # Save visualization as HTML or PNG
  python data_exploration/flow_compatibility.py --save-visual flows.html
  python data_exploration/flow_compatibility.py --save-png flows.png
""",
    )
    p.add_argument(
        "--db",
        default="industrial_cluster.db",
        help="SQLite database path (default: industrial_cluster.db)",
    )
    p.add_argument(
        "--flow",
        nargs="+",
        metavar="FLOW_ID",
        dest="flows",
        help="Flow ID(s) to compare (default: all flows)",
    )
    p.add_argument(
        "--save-text",
        nargs="?",
        const="",
        metavar="PATH",
        help="Save comparison tables as plain text (default: data_exploration/export/)",
    )
    p.add_argument(
        "--save-csv",
        nargs="?",
        const="",
        metavar="PATH",
        help="Save comparison tables as CSV (default: data_exploration/export/)",
    )
    p.add_argument(
        "--visual", action="store_true", help="Open visualization in browser"
    )
    p.add_argument(
        "--save-visual",
        nargs="?",
        const="",
        metavar="PATH",
        help="Save visualization as HTML (default: data_exploration/export/)",
    )
    p.add_argument(
        "--save-png",
        nargs="?",
        const="",
        metavar="PATH",
        help="Save visualization as PNG (default: data_exploration/export/, requires kaleido)",
    )
    p.add_argument(
        "--flow-rate-only",
        action="store_true",
        help="Compare only total flow rates, skip composition breakdown",
    )
    p.add_argument(
        "--list-flows",
        action="store_true",
        help="Print all flows with company/stream names, then exit",
    )
    p.add_argument(
        "--select",
        action="store_true",
        help="Show a numbered flow list and prompt for selection",
    )
    return p.parse_args()


# --------------------------------------------------------------------------- #
# Database helpers
# --------------------------------------------------------------------------- #


def _placeholders(ids):
    return ",".join("?" * len(ids))


_FLOW_SELECT = """
    SELECT f.flow_id,
           f.from_stream_id, f.to_stream_id,
           f.flow_kton_per_year, f.status, f.flow_type,
           COALESCE(sa.stream_name, '—') AS from_stream_name,
           COALESCE(sb.stream_name, '—') AS to_stream_name,
           COALESCE(ca.name, '—') AS from_company,
           COALESCE(cb.name, '—') AS to_company,
           COALESCE(sa.norm_flow_kton_per_year, sa.flow_kton_per_year, 0.0) AS from_flow_kton,
           COALESCE(sb.norm_flow_kton_per_year, sb.flow_kton_per_year, 0.0) AS to_flow_kton
    FROM flows f
    LEFT JOIN streams sa ON sa.stream_id = f.from_stream_id
    LEFT JOIN streams sb ON sb.stream_id = f.to_stream_id
    LEFT JOIN companies ca ON ca.company_id = f.from_company_id
    LEFT JOIN companies cb ON cb.company_id = f.to_company_id
"""


def _row_to_flow(r):
    return {
        "flow_id": r[0],
        "from_stream_id": r[1],
        "to_stream_id": r[2],
        "flow_kton_per_year": r[3],
        "status": r[4],
        "flow_type": r[5],
        "from_stream_name": r[6],
        "to_stream_name": r[7],
        "from_company": r[8],
        "to_company": r[9],
        "from_flow_kton": r[10],
        "to_flow_kton": r[11],
    }


def list_flows(conn):
    """Return all flows joined with stream and company names."""
    rows = conn.execute(_FLOW_SELECT + " ORDER BY f.flow_id").fetchall()
    return [_row_to_flow(r) for r in rows]


def load_flows(conn, flow_ids=None):
    """Load flows, optionally filtered to specific flow_ids."""
    if flow_ids:
        ph = _placeholders(flow_ids)
        rows = conn.execute(
            _FLOW_SELECT + f" WHERE f.flow_id IN ({ph}) ORDER BY f.flow_id",
            list(flow_ids),
        ).fetchall()
    else:
        rows = conn.execute(_FLOW_SELECT + " ORDER BY f.flow_id").fetchall()
    return [_row_to_flow(r) for r in rows]


def load_compositions(conn, stream_ids):
    """Return {stream_id: [{component_name, fraction, is_trace}]} sorted non-trace first."""
    if not stream_ids:
        return {}
    ph = _placeholders(stream_ids)
    rows = conn.execute(
        f"""
        SELECT sc.stream_id, c.name, sc.fraction, sc.is_trace
        FROM stream_composition sc
        JOIN components c ON c.component_id = sc.component_id
        WHERE sc.stream_id IN ({ph})
        ORDER BY sc.is_trace ASC, sc.fraction DESC
        """,
        list(stream_ids),
    ).fetchall()
    result = defaultdict(list)
    for r in rows:
        result[r[0]].append(
            {"component_name": r[1], "fraction": r[2], "is_trace": bool(r[3])}
        )
    return dict(result)


# --------------------------------------------------------------------------- #
# Comparison rows
# --------------------------------------------------------------------------- #


def build_comparison_rows(flow, comp_a, comp_b, flow_rate_only=False):
    """
    Build list of row dicts for a single flow comparison.
    Each row: {measure, val_a, val_b, diff, rel_diff, is_trace}
    """

    def _rel(diff, denom):
        return f"{diff / denom * 100:+.1f}%" if denom != 0 else "—"

    rows = []

    a = flow["from_flow_kton"] or 0.0
    b = flow["to_flow_kton"] or 0.0
    diff = a - b
    rows.append(
        {
            "measure": "Total flow (kton/yr)",
            "val_a": a,
            "val_b": b,
            "diff": diff,
            "rel_diff": _rel(diff, a),
            "is_trace": False,
        }
    )

    if flow_rate_only or flow["from_stream_id"] is None or flow["to_stream_id"] is None:
        return rows

    # Merge components from both streams
    merged = {}
    for entry in comp_a or []:
        n = entry["component_name"]
        merged[n] = {
            "frac_a": entry["fraction"],
            "frac_b": 0.0,
            "is_trace": entry["is_trace"],
        }
    for entry in comp_b or []:
        n = entry["component_name"]
        if n in merged:
            merged[n]["frac_b"] = entry["fraction"]
            merged[n]["is_trace"] = merged[n]["is_trace"] and entry["is_trace"]
        else:
            merged[n] = {
                "frac_a": 0.0,
                "frac_b": entry["fraction"],
                "is_trace": entry["is_trace"],
            }

    non_trace = sorted(
        [(n, v) for n, v in merged.items() if not v["is_trace"]],
        key=lambda x: -x[1]["frac_a"],
    )
    trace = sorted(
        [(n, v) for n, v in merged.items() if v["is_trace"]],
        key=lambda x: -x[1]["frac_a"],
    )

    for name, v in non_trace + trace:
        fa, fb = v["frac_a"], v["frac_b"]
        diff = fa - fb
        label = f"~{name} (trace)" if v["is_trace"] else f"{name}"
        rows.append(
            {
                "measure": label,
                "val_a": fa,
                "val_b": fb,
                "diff": diff,
                "rel_diff": _rel(diff, fa),
                "is_trace": v["is_trace"],
            }
        )

    return rows


# --------------------------------------------------------------------------- #
# Table formatting
# --------------------------------------------------------------------------- #


def format_table(flow, rows):
    """Return a formatted ASCII table string for one flow comparison."""
    header_a = f"{flow['from_company']} / {flow['from_stream_name']}"
    header_b = f"{flow['to_company']} / {flow['to_stream_name']}"

    W = [
        max(30, max(len(r["measure"]) for r in rows) + 2),
        max(20, len(header_a) + 2),
        max(20, len(header_b) + 2),
        12,
        14,
    ]

    def _cell(val, is_total):
        return f"{val:.3f}" if is_total else f"{val:.4f}"

    def _row(cells):
        return "│ " + " │ ".join(str(c).ljust(w) for c, w in zip(cells, W)) + " │"

    sep = "─" * (sum(W) + len(W) * 3 + 1)
    thick = "═" * len(sep)

    lines = [
        "",
        f"Flow {flow['flow_id']}  │  {flow['from_company']} → {flow['to_company']}"
        f"  [status: {flow['status']}]",
        thick,
        _row(["Measure", header_a, header_b, "Difference", "Rel. Diff"]),
        sep,
    ]
    for r in rows:
        is_total = r["measure"].startswith("Total")
        lines.append(
            _row(
                [
                    r["measure"],
                    _cell(r["val_a"], is_total),
                    _cell(r["val_b"], is_total),
                    _cell(r["diff"], is_total),
                    r["rel_diff"],
                ]
            )
        )
    lines.append(thick)
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CSV formatting
# --------------------------------------------------------------------------- #


def format_csv(flows_data):
    """Return CSV string with all flows. Each flow is preceded by a header row."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    cols = [
        "flow_id",
        "from_company",
        "from_stream",
        "to_company",
        "to_stream",
        "status",
        "measure",
        "stream_a",
        "stream_b",
        "difference",
        "rel_diff",
    ]
    writer.writerow(cols)
    for flow, rows in flows_data:
        for r in rows:
            writer.writerow(
                [
                    flow["flow_id"],
                    flow["from_company"],
                    flow["from_stream_name"],
                    flow["to_company"],
                    flow["to_stream_name"],
                    flow["status"],
                    r["measure"],
                    r["val_a"],
                    r["val_b"],
                    r["diff"],
                    r["rel_diff"],
                ]
            )
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Flow listing and interactive selection
# --------------------------------------------------------------------------- #


def print_flow_list(flows):
    """Print a numbered table of all flows."""
    if not flows:
        print("No flows in database.")
        return

    W_N = max(2, len(str(len(flows))))
    W_ID = max(len("Flow ID"), max(len(f["flow_id"]) for f in flows))
    W_FROM = max(
        len("From Company → Stream"),
        max(len(f"{f['from_company']} → {f['from_stream_name']}") for f in flows),
    )
    W_TO = max(
        len("To Company → Stream"),
        max(len(f"{f['to_company']} → {f['to_stream_name']}") for f in flows),
    )
    W_ST = max(len("Status"), max(len(f["status"]) for f in flows))

    def _row(n, fid, frm, to, status):
        return (
            f"  {str(n).rjust(W_N)}  {fid.ljust(W_ID)}  "
            f"{frm.ljust(W_FROM)}  {to.ljust(W_TO)}  {status}"
        )

    sep = "  " + "─" * (W_N + 2 + W_ID + 2 + W_FROM + 2 + W_TO + 2 + W_ST)
    print(
        _row("#", "Flow ID", "From Company → Stream", "To Company → Stream", "Status")
    )
    print(sep)
    for i, f in enumerate(flows, 1):
        print(
            _row(
                i,
                f["flow_id"],
                f"{f['from_company']} → {f['from_stream_name']}",
                f"{f['to_company']} → {f['to_stream_name']}",
                f["status"],
            )
        )


def select_flows(all_flows):
    """Show numbered flow list, prompt for selection, return selected flows."""
    print_flow_list(all_flows)
    if not all_flows:
        return []
    print()
    try:
        raw = input(
            "Enter flow number(s) to compare (e.g. 1, 1 3 5, or 'all') [all]: "
        ).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return []

    if not raw or raw.lower() == "all":
        return all_flows

    selected = []
    for token in raw.replace(",", " ").split():
        try:
            idx = int(token) - 1
            if 0 <= idx < len(all_flows):
                selected.append(all_flows[idx])
            else:
                print(f"Warning: {token} is out of range, skipping.")
        except ValueError:
            print(f"Warning: '{token}' is not a valid number, skipping.")
    return selected


# --------------------------------------------------------------------------- #
# Visualization
# --------------------------------------------------------------------------- #


def build_figure(flows_data, flow_rate_only=False):
    """Build a plotly Figure comparing streams for each flow.

    Layout per flow:
      flow_rate_only=False:  [A: actual kton/yr | B: relative %]  (row 1)
                             [C: component fractions — full width] (row 2)
      flow_rate_only=True:   [A: actual kton/yr | B: relative %]  (row 1 only)
    """
    n = len(flows_data)

    if flow_rate_only:
        n_rows = n
        specs = [[{}, {}]] * n
        titles = []
        for flow, _ in flows_data:
            base = f"Flow {flow['flow_id']}: {flow['from_company']} (A) → {flow['to_company']} (B)"
            titles += [
                f"{base}<br>Flow Rate (kton/yr)",
                f"{base}<br>Relative Flow Rate (% of A)",
            ]
    else:
        n_rows = n * 2
        specs = ([[{}, {}], [{"colspan": 2}, None]]) * n
        titles = []
        for flow, _ in flows_data:
            base = f"Flow {flow['flow_id']}: {flow['from_company']} (A) → {flow['to_company']} (B)"
            titles += [
                f"{base}<br>Flow Rate (kton/yr)",
                f"{base}<br>Relative Flow Rate (% of A)",
                f"{base}<br>Component Composition (fraction)",
                "",  # placeholder for the None cell in the colspan row
            ]

    fig = make_subplots(
        rows=n_rows,
        cols=2,
        specs=specs,
        subplot_titles=titles,
        vertical_spacing=max(0.04, 0.25 / n_rows),
        horizontal_spacing=0.1,
    )

    legend_shown = set()

    def _bar(name, color, x, y, hover_suffix, group, show_legend):
        return go.Bar(
            name=name,
            x=x,
            y=y,
            marker_color=color,
            showlegend=show_legend,
            legendgroup=group,
            hovertemplate=f"%{{x}}<br>{name}: %{{y:.3f}}{hover_suffix}<extra></extra>",
        )

    for i, (flow, rows) in enumerate(flows_data):
        row_ab = i * 2 + 1 if not flow_rate_only else i + 1
        row_c = i * 2 + 2  # only used when not flow_rate_only

        name_a = f"Stream A: {flow['from_stream_name']}"
        name_b = f"Stream B: {flow['to_stream_name']}"
        total_row = rows[0]
        val_a = total_row["val_a"]
        val_b = total_row["val_b"]
        rel_b = val_b / val_a * 100 if val_a else 0.0

        show_a = "A" not in legend_shown
        show_b = "B" not in legend_shown
        legend_shown.update(["A", "B"])

        # Plot A — actual flow rates
        fig.add_trace(
            _bar(name_a, COLOR_A, ["Flow Rate"], [val_a], " kton/yr", "A", show_a),
            row=row_ab,
            col=1,
        )
        fig.add_trace(
            _bar(name_b, COLOR_B, ["Flow Rate"], [val_b], " kton/yr", "B", show_b),
            row=row_ab,
            col=1,
        )

        # Plot B — relative (% of Stream A)
        fig.add_trace(
            _bar(name_a, COLOR_A, ["Flow Rate"], [100.0], "%", "A", False),
            row=row_ab,
            col=2,
        )
        fig.add_trace(
            _bar(name_b, COLOR_B, ["Flow Rate"], [rel_b], "%", "B", False),
            row=row_ab,
            col=2,
        )
        fig.add_hline(
            y=100, line_dash="dash", line_color="grey", line_width=1, row=row_ab, col=2
        )

        # Plot C — component fractions (full-width bottom row)
        if not flow_rate_only:
            comp_rows = rows[1:]
            if comp_rows:
                labels = [r["measure"] for r in comp_rows]
                vals_a = [r["val_a"] for r in comp_rows]
                vals_b = [r["val_b"] for r in comp_rows]
                fig.add_trace(
                    _bar(name_a, COLOR_A, labels, vals_a, "", "A", False),
                    row=row_c,
                    col=1,
                )
                fig.add_trace(
                    _bar(name_b, COLOR_B, labels, vals_b, "", "B", False),
                    row=row_c,
                    col=1,
                )
            else:
                fig.add_annotation(
                    text="No composition data",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                )

    fig.update_layout(
        title_text="Flow Compatibility — Stream Comparison",
        barmode="group",
        height=max(450, (300 if flow_rate_only else 500) * n),
        font_size=12,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


# --------------------------------------------------------------------------- #
# PNG export (matplotlib — no browser required)
# --------------------------------------------------------------------------- #


def save_png_matplotlib(flows_data, path, flow_rate_only=False):
    """Save PNG using matplotlib (no browser/kaleido needed).

    Layout per flow:
      [A: actual kton/yr | B: relative % of A]   ← top row
      [C: component fractions — full width     ]  ← bottom row (skipped if flow_rate_only)
    """
    from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec

    n = len(flows_data)
    row_height = 3.5
    comp_height = 0 if flow_rate_only else 3.5
    fig_h = n * (row_height + comp_height) + 1.2

    fig = plt.figure(figsize=(12, fig_h))
    fig.suptitle(
        "Flow Compatibility — Stream Comparison", fontsize=13, fontweight="bold"
    )

    outer_gs = GridSpec(n, 1, figure=fig, hspace=0.6, top=0.88, bottom=0.05)
    bar_width = 0.35

    for i, (flow, rows) in enumerate(flows_data):
        title = f"Flow {flow['flow_id']}: {flow['from_company']} (A) → {flow['to_company']} (B)"
        name_a = f"Stream A: {flow['from_stream_name']}"
        name_b = f"Stream B: {flow['to_stream_name']}"
        total_row = rows[0]
        val_a = total_row["val_a"]
        val_b = total_row["val_b"]
        rel_b = val_b / val_a * 100 if val_a else 0.0

        if flow_rate_only:
            inner_gs = GridSpecFromSubplotSpec(
                1, 2, subplot_spec=outer_gs[i], wspace=0.3
            )
            ax_a = fig.add_subplot(inner_gs[0, 0])
            ax_b = fig.add_subplot(inner_gs[0, 1])
        else:
            inner_gs = GridSpecFromSubplotSpec(
                2,
                2,
                subplot_spec=outer_gs[i],
                height_ratios=[row_height, comp_height],
                hspace=0.5,
                wspace=0.3,
            )
            ax_a = fig.add_subplot(inner_gs[0, 0])
            ax_b = fig.add_subplot(inner_gs[0, 1])
            ax_c = fig.add_subplot(inner_gs[1, :])

        # Plot A — actual flow rates
        ax_a.set_title(f"{title}\nFlow Rate (kton/yr)", fontsize=9, fontweight="bold")
        ax_a.bar(
            [-bar_width / 2], [val_a], width=bar_width, color=COLOR_A, label=name_a
        )
        ax_a.bar([bar_width / 2], [val_b], width=bar_width, color=COLOR_B, label=name_b)
        ax_a.set_xticks([0])
        ax_a.set_xticklabels(["Total Flow Rate"])
        ax_a.set_ylabel("kton/yr")
        ax_a.legend(fontsize=7)

        # Plot B — relative (% of Stream A)
        ax_b.set_title(
            f"{title}\nRelative Flow Rate (% of A)", fontsize=9, fontweight="bold"
        )
        ax_b.bar(
            [-bar_width / 2], [100.0], width=bar_width, color=COLOR_A, label=name_a
        )
        ax_b.bar([bar_width / 2], [rel_b], width=bar_width, color=COLOR_B, label=name_b)
        ax_b.axhline(100, color="grey", linestyle="--", linewidth=0.9, zorder=0)
        ax_b.set_xticks([0])
        ax_b.set_xticklabels(["Total Flow Rate"])
        ax_b.set_ylabel("% of Stream A")
        ax_b.legend(fontsize=7)

        # Plot C — component fractions, full width
        if not flow_rate_only:
            comp_rows = rows[1:]
            if comp_rows:
                labels = [r["measure"] for r in comp_rows]
                x = np.arange(len(labels))
                vals_a = [r["val_a"] for r in comp_rows]
                vals_b = [r["val_b"] for r in comp_rows]
                ax_c.bar(
                    x - bar_width / 2,
                    vals_a,
                    width=bar_width,
                    color=COLOR_A,
                    label=name_a,
                )
                ax_c.bar(
                    x + bar_width / 2,
                    vals_b,
                    width=bar_width,
                    color=COLOR_B,
                    label=name_b,
                )
                ax_c.set_title("Component Composition (fraction)", fontsize=9)
                ax_c.set_xticks(x)
                ax_c.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
                ax_c.set_ylabel("Fraction")
                ax_c.legend(fontsize=7)
            else:
                ax_c.text(
                    0.5,
                    0.5,
                    "No composition data",
                    ha="center",
                    va="center",
                    transform=ax_c.transAxes,
                    fontsize=10,
                    color="grey",
                )
                ax_c.axis("off")

    fig.savefig(str(path), dpi=150, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Export path helpers
# --------------------------------------------------------------------------- #


def _default_stem(flows_data):
    ids = [f["flow_id"] for f, _ in flows_data]
    name = "_".join(ids) if len(ids) <= 3 else "flows"
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{name}_{ts}"


def _resolve_path(arg, stem, suffix):
    """Return Path to write to. Empty string → auto-generate in EXPORT_DIR."""
    if arg:
        return Path(arg)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    return EXPORT_DIR / f"{stem}{suffix}"


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main():
    args = parse_args()
    conn = sqlite3.connect(args.db)

    all_flows = list_flows(conn)

    if args.list_flows:
        print_flow_list(all_flows)
        conn.close()
        return

    if args.select:
        selected = select_flows(all_flows)
        if not selected:
            print("No flows selected.")
            conn.close()
            return
        flow_ids = [f["flow_id"] for f in selected]
    elif args.flows:
        flow_ids = args.flows
    else:
        flow_ids = None

    flows = load_flows(conn, flow_ids)

    if not flows:
        print("No flows found.")
        conn.close()
        return

    stream_ids = list(
        {sid for f in flows for sid in (f["from_stream_id"], f["to_stream_id"]) if sid}
    )
    compositions = load_compositions(conn, stream_ids)

    flows_data = []
    for f in flows:
        comp_a = compositions.get(f["from_stream_id"], [])
        comp_b = compositions.get(f["to_stream_id"], [])
        rows = build_comparison_rows(f, comp_a, comp_b, args.flow_rate_only)
        flows_data.append((f, rows))

    table_text = "\n".join(format_table(f, rows) for f, rows in flows_data)
    print(table_text)

    stem = _default_stem(flows_data)

    if args.save_text is not None:
        path = _resolve_path(args.save_text, stem, ".txt")
        path.write_text(table_text + "\n")
        print(f"\nTables saved to {path}")

    if args.save_csv is not None:
        path = _resolve_path(args.save_csv, stem, ".csv")
        path.write_text(format_csv(flows_data), newline="")
        print(f"CSV saved to {path}")

    if args.save_png is not None:
        path = _resolve_path(args.save_png, stem, ".png")
        save_png_matplotlib(flows_data, path, args.flow_rate_only)
        print(f"PNG saved to {path}")

    needs_plotly = args.visual or args.save_visual is not None
    if needs_plotly:
        fig = build_figure(flows_data, args.flow_rate_only)
        if args.visual:
            fig.show()
        if args.save_visual is not None:
            path = _resolve_path(args.save_visual, stem, ".html")
            fig.write_html(str(path))
            print(f"Visualization saved to {path}")

    conn.close()


if __name__ == "__main__":
    main()
