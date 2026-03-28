"""
normalize_streams.py

Recalculates norm_flow_kton_per_year for all companies.
  - If normalize_stream_id is NULL: sets norm_flow_kton_per_year = NULL for all company streams.
  - If set: validates the reference stream and divides all company stream flows by ref_flow.

Safe to re-run at any time (idempotent).
"""

import sqlite3
import sys

DB_PATH = "industrial_cluster.db"


def normalize(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT company_id, name, normalize_stream_id, normalize_setpoint FROM companies")
    companies = cur.fetchall()

    count_normalized = 0
    count_skipped = 0
    errors = []

    for company in companies:
        company_id = company["company_id"]
        company_name = company["name"]
        ref_stream_id = company["normalize_stream_id"]

        if ref_stream_id is None:
            cur.execute(
                "UPDATE streams SET norm_flow_kton_per_year = flow_kton_per_year WHERE company_id = ?",
                (company_id,),
            )
            cur.execute(
                "UPDATE companies SET scaling_factor = 1.0 WHERE company_id = ?",
                (company_id,),
            )
            count_skipped += 1
            continue

        # Validate reference stream
        cur.execute(
            "SELECT stream_id, company_id, direction, flow_kton_per_year FROM streams WHERE stream_id = ?",
            (ref_stream_id,),
        )
        ref_stream = cur.fetchone()

        if ref_stream is None:
            errors.append(f"  {company_name}: reference stream '{ref_stream_id}' not found in streams")
            continue

        if ref_stream["company_id"] != company_id:
            errors.append(
                f"  {company_name}: reference stream '{ref_stream_id}' belongs to a different company"
            )
            continue

        if ref_stream["direction"] != "output":
            errors.append(
                f"  {company_name}: reference stream '{ref_stream_id}' has direction='{ref_stream['direction']}' (must be 'output')"
            )
            continue

        ref_flow = ref_stream["flow_kton_per_year"]
        if ref_flow is None or ref_flow <= 0:
            errors.append(
                f"  {company_name}: reference stream '{ref_stream_id}' has invalid flow={ref_flow} (must be > 0)"
            )
            continue

        setpoint = company["normalize_setpoint"] if company["normalize_setpoint"] is not None else 1.0
        cur.execute(
            "UPDATE streams SET norm_flow_kton_per_year = flow_kton_per_year / ? * ? WHERE company_id = ?",
            (ref_flow, setpoint, company_id),
        )
        cur.execute(
            "UPDATE companies SET scaling_factor = ? WHERE company_id = ?",
            (setpoint / ref_flow, company_id),
        )
        count_normalized += 1

    conn.commit()
    conn.close()

    print(f"Normalization complete.")
    print(f"  Normalized:  {count_normalized} companies")
    print(f"  Skipped:     {count_skipped} companies (no reference stream set)")
    if errors:
        print(f"  Warnings ({len(errors)}):")
        for msg in errors:
            print(msg)


def list_candidates(company_id: str, db_path: str = DB_PATH) -> None:
    """Print valid reference streams (output-direction, flow > 0) for a company."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT company_id, name, normalize_stream_id FROM companies WHERE company_id = ?", (company_id,))
    company = cur.fetchone()
    if company is None:
        print(f"Error: company '{company_id}' not found.")
        conn.close()
        return

    cur.execute(
        "SELECT stream_id, stream_name, flow_kton_per_year, composition_raw FROM streams"
        " WHERE company_id = ? AND direction = 'output' AND flow_kton_per_year > 0"
        " ORDER BY flow_kton_per_year DESC",
        (company_id,),
    )
    streams = cur.fetchall()
    conn.close()

    current = company["normalize_stream_id"]
    print(f"Valid reference streams for {company['name']} ({company_id}):")
    if not streams:
        print("  (none)")
    for s in streams:
        marker = "  * " if s["stream_id"] == current else "    "
        print(f"{marker}{s['stream_id']}  {s['flow_kton_per_year']:.4f} kton/yr  {s['stream_name']}")
        print(f"       {s['composition_raw']}")
    if current:
        print(f"Current reference: {current}")
    else:
        print("Current reference: (none)")


def set_reference(company_id: str, stream_id: str, db_path: str = DB_PATH) -> bool:
    """
    Set the normalization reference stream for a company.

    Validates:
    - company_id exists
    - stream_id exists in streams
    - stream belongs to company_id
    - stream direction is 'output'
    - stream flow_kton_per_year > 0

    Returns True on success, False on validation failure.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT company_id, name FROM companies WHERE company_id = ?", (company_id,))
    company = cur.fetchone()
    if company is None:
        print(f"Error: company '{company_id}' not found.")
        conn.close()
        return False

    cur.execute(
        "SELECT stream_id, company_id, direction, flow_kton_per_year FROM streams WHERE stream_id = ?",
        (stream_id,),
    )
    stream = cur.fetchone()
    if stream is None:
        print(f"Error: stream '{stream_id}' not found.")
        conn.close()
        return False

    if stream["company_id"] != company_id:
        print(f"Error: stream '{stream_id}' belongs to company '{stream['company_id']}', not '{company_id}'.")
        conn.close()
        return False

    if stream["direction"] != "output":
        print(f"Error: stream '{stream_id}' has direction='{stream['direction']}' (must be 'output').")
        conn.close()
        return False

    flow = stream["flow_kton_per_year"]
    if flow is None or flow <= 0:
        print(f"Error: stream '{stream_id}' has flow={flow} (must be > 0).")
        conn.close()
        return False

    cur.execute("UPDATE companies SET normalize_stream_id = ? WHERE company_id = ?", (stream_id, company_id))
    conn.commit()
    conn.close()

    print(f"Set reference stream for {company['name']} ({company_id}): {stream_id} ({flow:.4f} kton/yr)")
    print("Run normalize_streams.py to recalculate norm_flow_kton_per_year.")
    return True


def clear_reference(company_id: str, db_path: str = DB_PATH) -> bool:
    """
    Clear the normalization reference stream for a company.
    Returns True on success, False if company not found.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT company_id, name, normalize_stream_id FROM companies WHERE company_id = ?", (company_id,))
    company = cur.fetchone()
    if company is None:
        print(f"Error: company '{company_id}' not found.")
        conn.close()
        return False

    cur.execute("UPDATE companies SET normalize_stream_id = NULL WHERE company_id = ?", (company_id,))
    conn.commit()
    conn.close()

    prev = company["normalize_stream_id"]
    if prev:
        print(f"Cleared reference stream for {company['name']} ({company_id}) (was: {prev}).")
    else:
        print(f"{company['name']} ({company_id}) had no reference stream set.")
    print("Run normalize_streams.py to recalculate norm_flow_kton_per_year.")
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage stream normalization.")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("normalize", help="Recalculate norm_flow_kton_per_year for all companies.")

    p_set = sub.add_parser("set", help="Set the reference stream for a company.")
    p_set.add_argument("company_id")
    p_set.add_argument("stream_id")

    p_clear = sub.add_parser("clear", help="Clear the reference stream for a company.")
    p_clear.add_argument("company_id")

    p_list = sub.add_parser("list", help="List valid reference streams for a company.")
    p_list.add_argument("company_id")

    parser.add_argument("--db", default=DB_PATH)
    args = parser.parse_args()

    if args.command == "normalize" or args.command is None:
        normalize(args.db)
    elif args.command == "set":
        set_reference(args.company_id, args.stream_id, args.db)
    elif args.command == "clear":
        clear_reference(args.company_id, args.db)
    elif args.command == "list":
        list_candidates(args.company_id, args.db)
