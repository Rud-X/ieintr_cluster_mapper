"""
match_candidates.py — Industrial Symbiosis Matching Pipeline

Reads industrial_cluster.db, computes candidate matches between
output streams and input streams based on shared components,
scores each candidate, and exports a single JSON file for the
React visualization frontend.

Usage:
    python match_candidates.py [--db industrial_cluster.db] [--out frontend_data.json]

Scoring algorithm:
    For each (output_stream, input_stream) pair across different companies:
    1. component_overlap — Jaccard index of non-trace component sets
    2. fraction_similarity — 1 - mean |frac_out - frac_in| for shared components
    3. flow_compatibility — min(available, required) / max(available, required)
    4. temperature_proximity — 1 / (1 + |T_out - T_in| / 100) if both known, else 0.5
    5. pressure_proximity — 1 / (1 + |P_out - P_in| / 10) if both known, else 0.5

    composite_score = weighted average:
        component_overlap     × 0.35
        fraction_similarity   × 0.25
        flow_compatibility    × 0.20
        temperature_proximity × 0.10
        pressure_proximity    × 0.10

    Candidates with composite_score < 0.15 are discarded.
"""

import sqlite3
import json
import argparse
import sys
from collections import defaultdict


def load_companies(cur):
    """Load all companies."""
    cur.execute("SELECT company_id, name, sector, location FROM companies")
    return [
        {
            "company_id": r[0],
            "name": r[1],
            "sector": r[2],
            "location": r[3],
        }
        for r in cur.fetchall()
    ]


def load_streams_with_composition(cur):
    """Load all streams with their composition details."""
    cur.execute("""
        SELECT s.stream_id, s.company_id, s.stream_name, s.stream_type,
               s.direction, s.flow_kton_per_year, s.temperature_c,
               s.pressure_bar, s.composition_raw, s.notes
        FROM streams s
        ORDER BY s.company_id, s.direction, s.stream_name
    """)
    streams = {}
    for r in cur.fetchall():
        sid = r[0]
        streams[sid] = {
            "stream_id": sid,
            "company_id": r[1],
            "stream_name": r[2],
            "stream_type": r[3],
            "direction": r[4],
            "flow_kton_per_year": r[5],
            "temperature_c": r[6],
            "pressure_bar": r[7],
            "composition_raw": r[8],
            "notes": r[9],
            "components": [],
        }

    # Load compositions
    cur.execute("""
        SELECT sc.stream_id, sc.component_id, c.name, c.category,
               c.cas_number, c.hazardous, sc.fraction, sc.is_trace
        FROM stream_composition sc
        JOIN components c ON sc.component_id = c.component_id
        ORDER BY sc.stream_id, sc.fraction DESC
    """)
    for r in cur.fetchall():
        sid = r[0]
        if sid in streams:
            streams[sid]["components"].append({
                "component_id": r[1],
                "name": r[2],
                "category": r[3],
                "cas_number": r[4],
                "hazardous": r[5],
                "fraction": r[6],
                "is_trace": r[7],
            })

    return streams


def load_components(cur):
    """Load the full components table for reference."""
    cur.execute("""
        SELECT component_id, name, aliases, category, cas_number,
               molecular_weight, carbon_atoms, hazardous, needs_review, notes
        FROM components
    """)
    return [
        {
            "component_id": r[0],
            "name": r[1],
            "aliases": r[2],
            "category": r[3],
            "cas_number": r[4],
            "molecular_weight": r[5],
            "carbon_atoms": r[6],
            "hazardous": r[7],
            "needs_review": r[8],
            "notes": r[9],
        }
        for r in cur.fetchall()
    ]


def compute_candidates(streams, min_score=0.15):
    """
    Find all (output, input) pairs across different companies
    that share at least one non-trace component, and score them.
    """
    # Index streams by direction
    outputs = {sid: s for sid, s in streams.items() if s["direction"] == "output"}
    inputs = {sid: s for sid, s in streams.items() if s["direction"] == "input"}

    # Build component → stream index for inputs (non-trace only)
    input_comp_index = defaultdict(set)
    for sid, s in inputs.items():
        for comp in s["components"]:
            if not comp["is_trace"]:
                input_comp_index[comp["component_id"]].add(sid)

    candidates = []

    for out_sid, out_stream in outputs.items():
        out_comps = {
            c["component_id"]: c for c in out_stream["components"] if not c["is_trace"]
        }
        if not out_comps:
            continue

        # Find input streams that share at least one component
        candidate_input_sids = set()
        for cid in out_comps:
            candidate_input_sids |= input_comp_index.get(cid, set())

        for in_sid in candidate_input_sids:
            in_stream = streams[in_sid]
            # Skip same company
            if out_stream["company_id"] == in_stream["company_id"]:
                continue

            in_comps = {
                c["component_id"]: c
                for c in in_stream["components"]
                if not c["is_trace"]
            }

            score_detail = score_pair(out_stream, in_stream, out_comps, in_comps)
            if score_detail["composite_score"] >= min_score:
                candidates.append({
                    "from_company_id": out_stream["company_id"],
                    "to_company_id": in_stream["company_id"],
                    "from_stream_id": out_sid,
                    "to_stream_id": in_sid,
                    "from_stream_name": out_stream["stream_name"],
                    "to_stream_name": in_stream["stream_name"],
                    "from_stream_type": out_stream["stream_type"],
                    "to_stream_type": in_stream["stream_type"],
                    **score_detail,
                })

    # Sort by composite score descending
    candidates.sort(key=lambda c: c["composite_score"], reverse=True)
    return candidates


def score_pair(out_stream, in_stream, out_comps, in_comps):
    """Score a single (output, input) stream pair."""
    out_cids = set(out_comps.keys())
    in_cids = set(in_comps.keys())
    shared = out_cids & in_cids
    union = out_cids | in_cids

    # 1. Component overlap (Jaccard)
    component_overlap = len(shared) / len(union) if union else 0

    # 2. Fraction similarity (for shared components)
    if shared:
        diffs = []
        for cid in shared:
            f_out = out_comps[cid]["fraction"] or 0
            f_in = in_comps[cid]["fraction"] or 0
            diffs.append(abs(f_out - f_in))
        fraction_similarity = 1 - (sum(diffs) / len(diffs))
    else:
        fraction_similarity = 0

    # 3. Flow compatibility
    flow_out = out_stream["flow_kton_per_year"] or 0
    flow_in = in_stream["flow_kton_per_year"] or 0
    if flow_out > 0 and flow_in > 0:
        flow_compatibility = min(flow_out, flow_in) / max(flow_out, flow_in)
    else:
        flow_compatibility = 0

    # 4. Temperature proximity
    t_out = out_stream["temperature_c"]
    t_in = in_stream["temperature_c"]
    if t_out is not None and t_in is not None:
        temperature_proximity = 1 / (1 + abs(t_out - t_in) / 100)
    else:
        temperature_proximity = 0.5  # neutral when unknown

    # 5. Pressure proximity
    p_out = out_stream["pressure_bar"]
    p_in = in_stream["pressure_bar"]
    if p_out is not None and p_in is not None:
        pressure_proximity = 1 / (1 + abs(p_out - p_in) / 10)
    else:
        pressure_proximity = 0.5  # neutral when unknown

    # Weighted composite
    composite = (
        component_overlap * 0.35
        + fraction_similarity * 0.25
        + flow_compatibility * 0.20
        + temperature_proximity * 0.10
        + pressure_proximity * 0.10
    )

    # Shared component names for display
    shared_components = [
        {
            "name": out_comps[cid]["name"],
            "hazardous": out_comps[cid]["hazardous"],
            "fraction_out": out_comps[cid]["fraction"],
            "fraction_in": in_comps[cid]["fraction"],
        }
        for cid in shared
    ]
    shared_components.sort(
        key=lambda x: (x["fraction_out"] or 0), reverse=True
    )

    # Hazardous flag if any shared component is hazardous
    has_hazardous = any(c["hazardous"] == 1 for c in shared_components)

    return {
        "composite_score": round(composite, 4),
        "component_overlap": round(component_overlap, 4),
        "fraction_similarity": round(fraction_similarity, 4),
        "flow_compatibility": round(flow_compatibility, 4),
        "temperature_proximity": round(temperature_proximity, 4),
        "pressure_proximity": round(pressure_proximity, 4),
        "shared_components": shared_components,
        "has_hazardous": has_hazardous,
        "available_flow_kton": out_stream["flow_kton_per_year"],
        "required_flow_kton": in_stream["flow_kton_per_year"],
    }


def load_existing_flows(cur):
    """Load any existing flow decisions."""
    cur.execute("""
        SELECT flow_id, from_company_id, to_company_id,
               from_stream_id, to_stream_id, flow_kton_per_year,
               status, notes
        FROM flows
    """)
    return [
        {
            "flow_id": r[0],
            "from_company_id": r[1],
            "to_company_id": r[2],
            "from_stream_id": r[3],
            "to_stream_id": r[4],
            "flow_kton_per_year": r[5],
            "status": r[6],
            "notes": r[7],
        }
        for r in cur.fetchall()
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Industrial Symbiosis Matching Pipeline"
    )
    parser.add_argument(
        "--db", default="industrial_cluster.db", help="Path to SQLite database"
    )
    parser.add_argument(
        "--out", default="frontend_data.json", help="Output JSON for frontend"
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.15,
        help="Minimum composite score threshold (default: 0.15)",
    )
    args = parser.parse_args()

    try:
        conn = sqlite3.connect(args.db)
    except Exception as e:
        print(f"Error opening database: {e}", file=sys.stderr)
        sys.exit(1)

    cur = conn.cursor()

    print("Loading companies...")
    companies = load_companies(cur)
    print(f"  {len(companies)} companies")

    print("Loading streams with compositions...")
    streams = load_streams_with_composition(cur)
    print(f"  {len(streams)} streams")

    print("Loading components reference...")
    components = load_components(cur)
    print(f"  {len(components)} components")

    print(f"Computing candidate matches (min score: {args.min_score})...")
    candidates = compute_candidates(streams, min_score=args.min_score)
    print(f"  {len(candidates)} candidates found")

    print("Loading existing flows...")
    flows = load_existing_flows(cur)
    print(f"  {len(flows)} existing flows")

    # Summary stats
    n_outputs = sum(1 for s in streams.values() if s["direction"] == "output")
    n_inputs = sum(1 for s in streams.values() if s["direction"] == "input")
    unique_pairs = len(
        set(
            (c["from_company_id"], c["to_company_id"])
            for c in candidates
        )
    )

    output = {
        "metadata": {
            "generated_by": "match_candidates.py",
            "database": args.db,
            "min_score_threshold": args.min_score,
            "total_companies": len(companies),
            "total_streams": len(streams),
            "total_output_streams": n_outputs,
            "total_input_streams": n_inputs,
            "total_candidates": len(candidates),
            "unique_company_pairs": unique_pairs,
            "total_components": len(components),
        },
        "companies": companies,
        "streams": list(streams.values()),
        "candidates": candidates,
        "flows": flows,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nExported to {args.out}")
    print(f"  Top 5 candidates:")
    for c in candidates[:5]:
        print(
            f"    {c['from_stream_name']} → {c['to_stream_name']} "
            f"(score: {c['composite_score']:.3f}, "
            f"shared: {len(c['shared_components'])} components)"
        )

    conn.close()


if __name__ == "__main__":
    main()
