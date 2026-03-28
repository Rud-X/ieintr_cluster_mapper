"""
migrate_add_external_nodes.py

Adds support for external nodes (import sources, export sinks, waste management
facilities) to the industrial cluster database.

Changes:
  1. companies: add node_type column (TEXT NOT NULL DEFAULT 'company')
     Valid values: 'company', 'import_source', 'export_sink', 'waste_facility'
  2. flows: add flow_type column (TEXT NOT NULL DEFAULT 'internal')
     Valid values: 'internal', 'import', 'export', 'waste_to_wmf'
  3. flows: drop NOT NULL constraint on from_stream_id and to_stream_id
     Required for import flows (no from_stream) and export/WMF flows (no to_stream)

All changes are idempotent.
"""

import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).parent.parent / "industrial_cluster.db"


def migrate(db_path: str = str(DEFAULT_DB)) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # -------------------------------------------------------------------
    # 1. Add node_type to companies
    # -------------------------------------------------------------------
    cur.execute("PRAGMA table_info(companies)")
    companies_cols = {row[1] for row in cur.fetchall()}

    if "node_type" not in companies_cols:
        cur.execute(
            "ALTER TABLE companies ADD COLUMN node_type TEXT NOT NULL DEFAULT 'company'"
        )
        print("  companies.node_type added.")
    else:
        print("  companies.node_type already present — skipped.")

    # -------------------------------------------------------------------
    # 2. Add flow_type to flows, and check stream FK nullability
    # -------------------------------------------------------------------
    cur.execute("PRAGMA table_info(flows)")
    flows_info = cur.fetchall()
    # rows: (cid, name, type, notnull, dflt_value, pk)
    flows_cols = {row[1] for row in flows_info}
    stream_cols_notnull = {
        row[1]: row[3] for row in flows_info
        if row[1] in ("from_stream_id", "to_stream_id")
    }

    needs_flow_type = "flow_type" not in flows_cols
    needs_recreation = any(v == 1 for v in stream_cols_notnull.values())

    if needs_recreation:
        # Recreate the flows table to:
        #   a) drop NOT NULL on from_stream_id / to_stream_id
        #   b) add flow_type column (if not already there via a previous partial run)
        print("  Recreating flows table to relax NOT NULL on stream FK columns...")
        cur.execute("""
            CREATE TABLE flows_new (
                flow_id             TEXT PRIMARY KEY,
                from_company_id     TEXT NOT NULL REFERENCES companies(company_id),
                to_company_id       TEXT NOT NULL REFERENCES companies(company_id),
                from_stream_id      TEXT REFERENCES streams(stream_id),
                to_stream_id        TEXT REFERENCES streams(stream_id),
                flow_kton_per_year  REAL,
                flow_type           TEXT NOT NULL DEFAULT 'internal',
                status              TEXT NOT NULL DEFAULT 'candidate',
                notes               TEXT
            )
        """)
        # Copy existing data; supply 'internal' for flow_type if column doesn't exist yet
        if needs_flow_type:
            cur.execute("""
                INSERT INTO flows_new
                    (flow_id, from_company_id, to_company_id, from_stream_id, to_stream_id,
                     flow_kton_per_year, flow_type, status, notes)
                SELECT flow_id, from_company_id, to_company_id, from_stream_id, to_stream_id,
                       flow_kton_per_year, 'internal', status, notes
                FROM flows
            """)
        else:
            cur.execute("""
                INSERT INTO flows_new
                    (flow_id, from_company_id, to_company_id, from_stream_id, to_stream_id,
                     flow_kton_per_year, flow_type, status, notes)
                SELECT flow_id, from_company_id, to_company_id, from_stream_id, to_stream_id,
                       flow_kton_per_year, flow_type, status, notes
                FROM flows
            """)
        cur.execute("DROP TABLE flows")
        cur.execute("ALTER TABLE flows_new RENAME TO flows")
        print("  flows table recreated (nullable stream FKs, flow_type added).")

    elif needs_flow_type:
        cur.execute(
            "ALTER TABLE flows ADD COLUMN flow_type TEXT NOT NULL DEFAULT 'internal'"
        )
        print("  flows.flow_type added.")

    else:
        print("  flows already up to date — skipped.")

    conn.commit()
    conn.close()
    print("  Done.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Add external node support.")
    parser.add_argument("--db", default=str(DEFAULT_DB), metavar="PATH")
    args = parser.parse_args()
    migrate(args.db)
