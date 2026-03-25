"""
carbon.py

CLI tool for carbon weight percentage tracking.

Subcommands:
  status           — summary of coverage across components and streams
  recalculate      — full three-layer recalculation (idempotent)
  set-component    — update molecular data / manually override carbon_weight_pct
  show             — display full detail for a single component
  list-gaps        — list components with NULL carbon_weight_pct, sorted by stream impact

All subcommands accept --db <path> (default: industrial_cluster.db).
"""

import argparse
import sqlite3
import sys

DB_PATH = "industrial_cluster.db"
UNKNOWN_NAME = "unknown"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_unknown_component_id(cur: sqlite3.Cursor) -> str | None:
    cur.execute("SELECT component_id FROM components WHERE name = ?", (UNKNOWN_NAME,))
    row = cur.fetchone()
    return row["component_id"] if row else None


# ---------------------------------------------------------------------------
# recalculate
# ---------------------------------------------------------------------------

def recalculate(db_path: str = DB_PATH) -> None:
    conn = connect(db_path)
    cur = conn.cursor()

    unknown_id = get_unknown_component_id(cur)

    # 1. Components layer — formula-based, skip manual overrides
    cur.execute("""
        SELECT component_id, name, carbon_atoms, molecular_weight, carbon_weight_pct_manual
        FROM components
    """)
    components = cur.fetchall()

    comp_updated = 0
    comp_skipped_manual = 0
    comp_warned = 0

    for c in components:
        cid = c["component_id"]
        if c["carbon_weight_pct_manual"] == 1:
            comp_skipped_manual += 1
            continue

        ca = c["carbon_atoms"]
        mw = c["molecular_weight"]

        if ca is not None and mw is not None and mw > 0:
            pct = (ca * 12.011) / mw
            cur.execute(
                "UPDATE components SET carbon_weight_pct = ? WHERE component_id = ?",
                (pct, cid),
            )
            comp_updated += 1
        else:
            # Set NULL for components without sufficient data
            cur.execute(
                "UPDATE components SET carbon_weight_pct = NULL WHERE component_id = ?",
                (cid,),
            )
            if ca is None or mw is None:
                comp_warned += 1

    # 2. Stream composition layer
    # For non-trace rows: carbon_fraction = fraction * carbon_weight_pct (if available)
    cur.execute("""
        UPDATE stream_composition
        SET carbon_fraction = (
            SELECT sc.fraction * c.carbon_weight_pct
            FROM stream_composition sc
            JOIN components c ON sc.component_id = c.component_id
            WHERE sc.composition_id = stream_composition.composition_id
              AND c.carbon_weight_pct IS NOT NULL
              AND sc.is_trace = 0
        )
        WHERE is_trace = 0
    """)

    # Set NULL for non-trace rows where component has no carbon data
    cur.execute("""
        UPDATE stream_composition
        SET carbon_fraction = NULL
        WHERE is_trace = 0
          AND component_id IN (
              SELECT component_id FROM components WHERE carbon_weight_pct IS NULL
          )
    """)

    # Trace rows always NULL
    cur.execute("UPDATE stream_composition SET carbon_fraction = NULL WHERE is_trace = 1")

    cur.execute("SELECT changes()")
    sc_total = cur.fetchone()[0]

    # 3. Streams layer — carbon_pct (partial sums are acceptable)
    unknown_filter = f"AND sc.component_id != '{unknown_id}'" if unknown_id else ""

    cur.execute(f"""
        UPDATE streams
        SET carbon_pct = (
            SELECT CASE
                WHEN SUM(CASE WHEN sc.carbon_fraction IS NOT NULL THEN 1 ELSE 0 END) > 0
                    THEN SUM(COALESCE(sc.carbon_fraction, 0))
                ELSE NULL
            END
            FROM stream_composition sc
            JOIN components c ON sc.component_id = c.component_id
            WHERE sc.stream_id = streams.stream_id
              AND sc.is_trace = 0
              {unknown_filter}
        )
    """)

    # 4. carbon_pct_complete flag
    cur.execute(f"""
        UPDATE streams
        SET carbon_pct_complete = (
            SELECT CASE
                WHEN COUNT(*) = 0 THEN NULL
                WHEN SUM(CASE WHEN c.carbon_weight_pct IS NULL THEN 1 ELSE 0 END) = 0 THEN 1
                ELSE 0
            END
            FROM stream_composition sc
            JOIN components c ON sc.component_id = c.component_id
            WHERE sc.stream_id = streams.stream_id
              AND sc.is_trace = 0
              {unknown_filter}
        )
    """)

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM streams WHERE carbon_pct IS NOT NULL")
    streams_with_pct = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM streams")
    total_streams = cur.fetchone()[0]

    conn.close()

    print("Recalculation complete.")
    print(f"  Components updated (formula):  {comp_updated}")
    print(f"  Components skipped (manual):   {comp_skipped_manual}")
    if comp_warned:
        print(f"  Components with NULL carbon_weight_pct (missing data): {comp_warned}")
    print(f"  Streams with carbon_pct set:   {streams_with_pct} / {total_streams}")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def status(db_path: str = DB_PATH) -> None:
    conn = connect(db_path)
    cur = conn.cursor()

    # Components summary
    cur.execute("SELECT COUNT(*) FROM components")
    total_comp = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM components WHERE carbon_weight_pct IS NOT NULL AND carbon_weight_pct_manual = 1")
    manual_comp = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM components
        WHERE carbon_weight_pct IS NOT NULL
          AND (carbon_weight_pct_manual IS NULL OR carbon_weight_pct_manual = 0)
    """)
    formula_comp = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM components WHERE carbon_weight_pct IS NULL")
    null_comp = cur.fetchone()[0]

    print("=== Components ===")
    print(f"  Total:            {total_comp}")
    print(f"  carbon_weight_pct set (formula): {formula_comp}")
    print(f"  carbon_weight_pct set (manual):  {manual_comp}")
    print(f"  carbon_weight_pct NULL:          {null_comp}")

    # Actionable gaps: NULL and needs_review = 0
    cur.execute("""
        SELECT component_id, name, carbon_atoms, molecular_weight
        FROM components
        WHERE carbon_weight_pct IS NULL AND needs_review = 0
        ORDER BY component_id
    """)
    actionable = cur.fetchall()

    if actionable:
        print(f"\n  Actionable gaps (NULL, needs_review=0): {len(actionable)}")
        for c in actionable:
            print(f"    {c['component_id']}  {c['name']:<40}  "
                  f"C={c['carbon_atoms']}  MW={c['molecular_weight']}")
    else:
        print("\n  No actionable gaps (all NULL components have needs_review=1).")

    # Streams summary
    cur.execute("SELECT COUNT(*) FROM streams")
    total_streams = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM streams WHERE carbon_pct IS NOT NULL")
    streams_with = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM streams WHERE carbon_pct IS NULL")
    streams_null = cur.fetchone()[0]

    print(f"\n=== Streams ===")
    print(f"  Total:            {total_streams}")
    print(f"  carbon_pct set:   {streams_with}")
    print(f"  carbon_pct NULL:  {streams_null}")

    if streams_null > 0:
        print(f"\n  Streams with NULL carbon_pct (grouped by company):")
        cur.execute("""
            SELECT s.stream_id, s.stream_name, s.company_id,
                   co.name AS company_name,
                   GROUP_CONCAT(
                       CASE WHEN c.carbon_weight_pct IS NULL THEN c.name ELSE NULL END, ', '
                   ) AS missing_components
            FROM streams s
            JOIN companies co ON s.company_id = co.company_id
            LEFT JOIN stream_composition sc ON s.stream_id = sc.stream_id AND sc.is_trace = 0
            LEFT JOIN components c ON sc.component_id = c.component_id
            WHERE s.carbon_pct IS NULL
            GROUP BY s.stream_id
            ORDER BY co.name, s.stream_id
        """)
        null_streams = cur.fetchall()

        current_company = None
        for row in null_streams:
            if row["company_name"] != current_company:
                current_company = row["company_name"]
                print(f"\n    {current_company} ({row['company_id']}):")
            missing = row["missing_components"] or "(no composition data)"
            print(f"      {row['stream_id']}  {row['stream_name']}")
            print(f"        missing: {missing}")

    conn.close()


# ---------------------------------------------------------------------------
# set-component
# ---------------------------------------------------------------------------

def set_component(
    component_id: str,
    carbon_atoms: int | None = None,
    molecular_weight: float | None = None,
    carbon_pct: float | None = None,
    clear_override: bool = False,
    db_path: str = DB_PATH,
) -> None:
    conn = connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT * FROM components WHERE component_id = ?", (component_id,))
    comp = cur.fetchone()
    if comp is None:
        print(f"Error: component '{component_id}' not found.")
        conn.close()
        return

    updates = {}

    if carbon_atoms is not None:
        updates["carbon_atoms"] = carbon_atoms

    if molecular_weight is not None:
        updates["molecular_weight"] = molecular_weight

    if carbon_pct is not None:
        if not (0.0 <= carbon_pct <= 1.0):
            print(f"Error: --carbon-pct must be in range 0.0–1.0 (got {carbon_pct}).")
            conn.close()
            return
        updates["carbon_weight_pct"] = carbon_pct
        updates["carbon_weight_pct_manual"] = 1

    if clear_override:
        updates["carbon_weight_pct_manual"] = 0

    if not updates:
        print("No changes specified. Use --carbon-atoms, --molecular-weight, --carbon-pct, or --clear-override.")
        conn.close()
        return

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [component_id]
    cur.execute(f"UPDATE components SET {set_clause} WHERE component_id = ?", values)

    # Cascade: recompute carbon_weight_pct if not manually overridden
    cur.execute(
        "SELECT carbon_atoms, molecular_weight, carbon_weight_pct_manual FROM components WHERE component_id = ?",
        (component_id,),
    )
    updated = cur.fetchone()
    is_manual = updated["carbon_weight_pct_manual"] == 1

    if not is_manual:
        ca = updated["carbon_atoms"]
        mw = updated["molecular_weight"]
        if ca is not None and mw is not None and mw > 0:
            new_pct = (ca * 12.011) / mw
            cur.execute(
                "UPDATE components SET carbon_weight_pct = ? WHERE component_id = ?",
                (new_pct, component_id),
            )
        else:
            cur.execute(
                "UPDATE components SET carbon_weight_pct = NULL WHERE component_id = ?",
                (component_id,),
            )

    # Cascade: stream_composition rows for this component
    cur.execute(
        "SELECT carbon_weight_pct FROM components WHERE component_id = ?",
        (component_id,),
    )
    final_pct = cur.fetchone()["carbon_weight_pct"]

    if final_pct is not None:
        cur.execute("""
            UPDATE stream_composition
            SET carbon_fraction = fraction * ?
            WHERE component_id = ? AND is_trace = 0
        """, (final_pct, component_id))
    else:
        cur.execute("""
            UPDATE stream_composition
            SET carbon_fraction = NULL
            WHERE component_id = ?
        """, (component_id,))

    # Cascade: streams containing this component
    cur.execute(
        "SELECT DISTINCT stream_id FROM stream_composition WHERE component_id = ?",
        (component_id,),
    )
    affected_streams = [row["stream_id"] for row in cur.fetchall()]

    unknown_id = get_unknown_component_id(cur)
    unknown_filter = f"AND sc.component_id != '{unknown_id}'" if unknown_id else ""

    for sid in affected_streams:
        cur.execute(f"""
            UPDATE streams
            SET carbon_pct = (
                SELECT CASE
                    WHEN SUM(CASE WHEN sc.carbon_fraction IS NOT NULL THEN 1 ELSE 0 END) > 0
                        THEN SUM(COALESCE(sc.carbon_fraction, 0))
                    ELSE NULL
                END
                FROM stream_composition sc
                JOIN components c ON sc.component_id = c.component_id
                WHERE sc.stream_id = ?
                  AND sc.is_trace = 0
                  {unknown_filter}
            ),
            carbon_pct_complete = (
                SELECT CASE
                    WHEN COUNT(*) = 0 THEN NULL
                    WHEN SUM(CASE WHEN c.carbon_weight_pct IS NULL THEN 1 ELSE 0 END) = 0 THEN 1
                    ELSE 0
                END
                FROM stream_composition sc
                JOIN components c ON sc.component_id = c.component_id
                WHERE sc.stream_id = ?
                  AND sc.is_trace = 0
                  {unknown_filter}
            )
            WHERE stream_id = ?
        """, (sid, sid, sid))

    conn.commit()

    print(f"Updated {comp['name']} ({component_id}):")
    for k, v in updates.items():
        print(f"  {k} = {v}")
    if not is_manual and "carbon_atoms" in updates or "molecular_weight" in updates:
        cur2 = conn.cursor()
        cur2.execute("SELECT carbon_weight_pct FROM components WHERE component_id = ?", (component_id,))
        row = cur2.fetchone()
        if row:
            print(f"  carbon_weight_pct (recomputed) = {row['carbon_weight_pct']}")

    print(f"  Cascaded to {len(affected_streams)} stream(s).")
    conn.close()


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------

def show(component_id: str, db_path: str = DB_PATH) -> None:
    conn = connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT * FROM components WHERE component_id = ?", (component_id,))
    comp = cur.fetchone()
    if comp is None:
        print(f"Error: component '{component_id}' not found.")
        conn.close()
        return

    print(f"=== {comp['name']} ({component_id}) ===")
    print(f"  aliases:               {comp['aliases']}")
    print(f"  category:              {comp['category']}")
    print(f"  cas_number:            {comp['cas_number']}")
    print(f"  molecular_weight:      {comp['molecular_weight']}")
    print(f"  carbon_atoms:          {comp['carbon_atoms']}")
    print(f"  hazardous:             {comp['hazardous']}")
    print(f"  needs_review:          {comp['needs_review']}")
    manual_flag = " (manual override)" if comp["carbon_weight_pct_manual"] == 1 else ""
    print(f"  carbon_weight_pct:     {comp['carbon_weight_pct']}{manual_flag}")
    print(f"  notes:                 {comp['notes']}")

    cur.execute("""
        SELECT sc.composition_id, sc.stream_id, s.stream_name, co.company_id, co.name AS company_name,
               sc.fraction, sc.carbon_fraction, sc.is_trace
        FROM stream_composition sc
        JOIN streams s ON sc.stream_id = s.stream_id
        JOIN companies co ON s.company_id = co.company_id
        WHERE sc.component_id = ?
        ORDER BY co.company_id, s.stream_id
    """, (component_id,))
    rows = cur.fetchall()
    conn.close()

    print(f"\n  Appears in {len(rows)} stream composition row(s):")
    if rows:
        print(f"  {'stream_id':<8}  {'stream_name':<35}  {'company':<8}  {'fraction':>10}  {'carbon_frac':>12}  trace")
        print(f"  {'-'*8}  {'-'*35}  {'-'*8}  {'-'*10}  {'-'*12}  -----")
        for r in rows:
            frac = f"{r['fraction']:.4f}" if r["fraction"] is not None else "NULL"
            cfrac = f"{r['carbon_fraction']:.6f}" if r["carbon_fraction"] is not None else "NULL"
            trace = "yes" if r["is_trace"] else "no"
            print(f"  {r['stream_id']:<8}  {r['stream_name']:<35}  {r['company_id']:<8}  "
                  f"{frac:>10}  {cfrac:>12}  {trace}")


# ---------------------------------------------------------------------------
# list-gaps
# ---------------------------------------------------------------------------

def list_gaps(db_path: str = DB_PATH) -> None:
    conn = connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        SELECT c.component_id, c.name, c.carbon_atoms, c.molecular_weight, c.needs_review,
               COUNT(DISTINCT sc.stream_id) AS stream_count
        FROM components c
        LEFT JOIN stream_composition sc ON c.component_id = sc.component_id AND sc.is_trace = 0
        WHERE c.carbon_weight_pct IS NULL
        GROUP BY c.component_id
        ORDER BY stream_count DESC, c.component_id
    """)
    gaps = cur.fetchall()
    conn.close()

    if not gaps:
        print("No components with NULL carbon_weight_pct.")
        return

    print(f"Components with NULL carbon_weight_pct ({len(gaps)} total), sorted by stream impact:")
    print(f"{'component_id':<14}  {'name':<40}  {'C_atoms':>7}  {'MW':>10}  {'streams':>7}  review")
    print(f"{'-'*14}  {'-'*40}  {'-'*7}  {'-'*10}  {'-'*7}  ------")
    for g in gaps:
        ca = str(g["carbon_atoms"]) if g["carbon_atoms"] is not None else "NULL"
        mw = f"{g['molecular_weight']:.3f}" if g["molecular_weight"] is not None else "NULL"
        review = "yes" if g["needs_review"] else "no"
        print(f"  {g['component_id']:<12}  {g['name']:<40}  {ca:>7}  {mw:>10}  {g['stream_count']:>7}  {review}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Carbon weight percentage tracking for industrial cluster DB."
    )
    parser.add_argument("--db", default=DB_PATH, help="Path to SQLite database.")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Summary of carbon_weight_pct coverage.")
    sub.add_parser("recalculate", help="Full three-layer recalculation (idempotent).")
    sub.add_parser("list-gaps", help="List components with NULL carbon_weight_pct by stream impact.")

    p_show = sub.add_parser("show", help="Full detail for a single component.")
    p_show.add_argument("component_id")

    p_set = sub.add_parser("set-component", help="Update molecular data or manually override carbon_weight_pct.")
    p_set.add_argument("component_id")
    p_set.add_argument("--carbon-atoms", type=int, metavar="INT")
    p_set.add_argument("--molecular-weight", type=float, metavar="FLOAT")
    p_set.add_argument("--carbon-pct", type=float, metavar="FLOAT", help="Manual override (0–1 scale).")
    p_set.add_argument("--clear-override", action="store_true", help="Remove manual override flag.")

    args = parser.parse_args()

    if args.command == "status":
        status(args.db)
    elif args.command == "recalculate":
        recalculate(args.db)
    elif args.command == "list-gaps":
        list_gaps(args.db)
    elif args.command == "show":
        show(args.component_id, args.db)
    elif args.command == "set-component":
        set_component(
            component_id=args.component_id,
            carbon_atoms=args.carbon_atoms,
            molecular_weight=args.molecular_weight,
            carbon_pct=args.carbon_pct,
            clear_override=args.clear_override,
            db_path=args.db,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
