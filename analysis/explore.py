"""
explore.py

Read-only data exploration functions for the industrial cluster database.
Intended to be called from cluster_cli.py (Explore module).

Functions:
  summary(db_path)              — row counts and coverage stats for all tables
  list_companies(db_path)       — aligned table of all companies with stream counts
  show_company(company_id, db_path) — full dump of a company's streams and compositions
  drill_down(db_path)           — interactive three-level navigator
"""

import sqlite3

import questionary

DB_PATH = "industrial_cluster.db"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------

def summary(db_path: str = DB_PATH) -> None:
    """Print a one-shot stats overview of the database."""
    conn = connect(db_path)
    cur = conn.cursor()

    def count(query):
        cur.execute(query)
        return cur.fetchone()[0]

    companies_total    = count("SELECT COUNT(*) FROM companies")
    companies_included = count("SELECT COUNT(*) FROM companies WHERE included=1")
    streams_total      = count("SELECT COUNT(*) FROM streams")
    components_ok      = count("SELECT COUNT(*) FROM components WHERE needs_review=0")
    components_total   = count("SELECT COUNT(*) FROM components")
    sc_total           = count("SELECT COUNT(*) FROM stream_composition")
    flows_total        = count("SELECT COUNT(*) FROM flows")
    carbon_gaps        = count("SELECT COUNT(*) FROM streams WHERE carbon_pct_complete=0")
    carbon_null        = count("SELECT COUNT(*) FROM streams WHERE carbon_pct IS NULL")

    print("=== Database Summary ===")
    print(f"  Companies        : {companies_total}  ({companies_included} included, "
          f"{companies_total - companies_included} excluded)")
    print(f"  Streams          : {streams_total}")
    print(f"  Components       : {components_total}  ({components_ok} resolved, "
          f"{components_total - components_ok} needs_review)")
    print(f"  Stream compos.   : {sc_total}")
    print()
    print("=== Carbon Coverage ===")
    print(f"  Streams with carbon_pct_complete=0 (gaps) : {carbon_gaps}")
    print(f"  Streams with carbon_pct IS NULL           : {carbon_null}")
    print()

    if flows_total == 0:
        print("=== Flows === (empty)")
    else:
        print(f"=== Flows === {flows_total} total")
        cur.execute("SELECT status, COUNT(*) AS n FROM flows GROUP BY status ORDER BY status")
        for row in cur.fetchall():
            print(f"  {row['status']:<12}: {row['n']}")

    conn.close()


# ---------------------------------------------------------------------------
# list_companies
# ---------------------------------------------------------------------------

def list_companies(db_path: str = DB_PATH) -> None:
    """Print all companies as an aligned table."""
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT c.company_id, c.name, c.sector, c.included,
               COUNT(s.stream_id) AS stream_count
        FROM companies c
        LEFT JOIN streams s ON s.company_id = c.company_id
        GROUP BY c.company_id
        ORDER BY c.company_id
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("No companies found.")
        return

    # Column widths
    id_w   = max(len("ID"),     max(len(r["company_id"]) for r in rows))
    name_w = max(len("Name"),   max(len(r["name"] or "") for r in rows))
    sec_w  = max(len("Sector"), max(len(r["sector"] or "") for r in rows))

    header = (f"{'ID':<{id_w}}  {'Name':<{name_w}}  {'Sector':<{sec_w}}  "
              f"{'Inc':>3}  {'#Streams':>8}")
    print(header)
    print("-" * len(header))
    for r in rows:
        print(f"{r['company_id']:<{id_w}}  "
              f"{(r['name'] or ''):<{name_w}}  "
              f"{(r['sector'] or ''):<{sec_w}}  "
              f"{'Y' if r['included'] else 'N':>3}  "
              f"{r['stream_count']:>8}")


# ---------------------------------------------------------------------------
# show_company
# ---------------------------------------------------------------------------

def show_company(company_id: str, db_path: str = DB_PATH) -> None:
    """Full one-shot dump of a company: metadata, streams, and compositions."""
    conn = connect(db_path)
    cur = conn.cursor()

    # Company metadata
    cur.execute("SELECT * FROM companies WHERE company_id = ?", (company_id,))
    company = cur.fetchone()
    if company is None:
        print(f"Company '{company_id}' not found.")
        conn.close()
        return

    print("=== Company ===")
    for key in company.keys():
        print(f"  {key:<30}: {company[key]}")
    print()

    # Streams
    cur.execute("""
        SELECT * FROM streams
        WHERE company_id = ?
        ORDER BY direction, stream_id
    """, (company_id,))
    streams = cur.fetchall()

    if not streams:
        print("  (no streams)")
        conn.close()
        return

    for s in streams:
        carbon_complete = s["carbon_pct_complete"]
        complete_tag = "" if carbon_complete else " [carbon gap]"
        print(f"  Stream {s['stream_id']}  [{s['direction']}]  {s['stream_name']}"
              f"  {s['stream_type'] or ''}  "
              f"{s['flow_kton_per_year']} kton/yr  "
              f"carbon_pct={s['carbon_pct']}  complete={carbon_complete}{complete_tag}")

        # Composition
        cur.execute("""
            SELECT sc.component_id, c.name, sc.fraction, sc.is_trace, sc.carbon_fraction
            FROM stream_composition sc
            JOIN components c ON c.component_id = sc.component_id
            WHERE sc.stream_id = ?
            ORDER BY sc.fraction DESC NULLS LAST
        """, (s["stream_id"],))
        comps = cur.fetchall()

        if not comps:
            print("    (no composition data)")
        else:
            for comp in comps:
                trace_tag = " [trace]" if comp["is_trace"] else ""
                print(f"    {comp['component_id']:<6}  {comp['name']:<30}  "
                      f"frac={comp['fraction']}  "
                      f"carbon_frac={comp['carbon_fraction']}{trace_tag}")
        print()

    conn.close()


# ---------------------------------------------------------------------------
# drill_down
# ---------------------------------------------------------------------------

def drill_down(db_path: str = DB_PATH) -> None:
    """Interactive three-level navigator: company → stream → composition."""
    conn = connect(db_path)
    cur = conn.cursor()

    # Level 1 — Company picker
    while True:
        cur.execute("SELECT company_id, name FROM companies ORDER BY company_id")
        companies = cur.fetchall()

        company_choices = [f"{r['company_id']:<6}  {r['name']}" for r in companies]
        company_choices.append("← Exit")

        choice = questionary.select("Select a company:", choices=company_choices).ask()
        if choice is None or choice == "← Exit":
            conn.close()
            return

        company_id = choice.split()[0]

        # Level 2 — Stream picker
        while True:
            cur.execute("""
                SELECT stream_id, stream_name, direction, flow_kton_per_year
                FROM streams
                WHERE company_id = ?
                ORDER BY direction, stream_id
            """, (company_id,))
            streams = cur.fetchall()

            stream_choices = [
                f"{s['stream_id']}  [{s['direction']}]  {s['stream_name']}  "
                f"({s['flow_kton_per_year']} kton/yr)"
                for s in streams
            ]
            stream_choices.append("← Back")

            choice = questionary.select(
                f"Company {company_id} — select a stream:",
                choices=stream_choices,
            ).ask()
            if choice is None or choice == "← Back":
                break

            stream_id = choice.split()[0]

            # Level 3 — Composition detail
            while True:
                cur.execute("SELECT * FROM streams WHERE stream_id = ?", (stream_id,))
                stream = cur.fetchone()

                print()
                print(f"  Stream  : {stream['stream_id']}  {stream['stream_name']}")
                print(f"  Company : {stream['company_id']}")
                print(f"  Dir     : {stream['direction']}  Type: {stream['stream_type']}")
                print(f"  Flow    : {stream['flow_kton_per_year']} kton/yr")
                print(f"  carbon_pct={stream['carbon_pct']}  "
                      f"complete={stream['carbon_pct_complete']}")
                print()

                cur.execute("""
                    SELECT sc.component_id, c.name, sc.fraction, sc.is_trace, sc.carbon_fraction
                    FROM stream_composition sc
                    JOIN components c ON c.component_id = sc.component_id
                    WHERE sc.stream_id = ?
                    ORDER BY sc.fraction DESC NULLS LAST
                """, (stream_id,))
                comps = cur.fetchall()

                if not comps:
                    print("  (no composition data)")
                else:
                    id_w   = max(len("Comp ID"),  max(len(c["component_id"]) for c in comps))
                    name_w = max(len("Name"),      max(len(c["name"] or "")  for c in comps))
                    header = (f"  {'Comp ID':<{id_w}}  {'Name':<{name_w}}  "
                              f"{'Fraction':>10}  {'Trace':>5}  {'C-frac':>10}")
                    print(header)
                    print("  " + "-" * (len(header) - 2))
                    for c in comps:
                        print(f"  {c['component_id']:<{id_w}}  "
                              f"{(c['name'] or ''):<{name_w}}  "
                              f"{str(c['fraction'] or ''):>10}  "
                              f"{'Y' if c['is_trace'] else 'N':>5}  "
                              f"{str(c['carbon_fraction'] or ''):>10}")
                print()

                nav = questionary.select(
                    "Stream detail",
                    choices=["← Back to streams"],
                ).ask()
                if nav is None or nav == "← Back to streams":
                    break

    conn.close()
