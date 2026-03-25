"""
migrate_add_normalization.py

Idempotently adds normalization columns:
  - companies.normalize_stream_id  (TEXT, NULL)
  - streams.norm_flow_kton_per_year (REAL, NULL)
"""

import sqlite3
import sys

DB_PATH = "industrial_cluster.db"


def migrate(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    added = []

    # --- companies table ---
    cur.execute("PRAGMA table_info(companies)")
    companies_columns = {row[1] for row in cur.fetchall()}

    if "normalize_stream_id" not in companies_columns:
        cur.execute("ALTER TABLE companies ADD COLUMN normalize_stream_id TEXT DEFAULT NULL")
        added.append("companies.normalize_stream_id TEXT DEFAULT NULL")
    else:
        print("  normalize_stream_id already exists in companies — skipping")

    # --- streams table ---
    cur.execute("PRAGMA table_info(streams)")
    streams_columns = {row[1] for row in cur.fetchall()}

    if "norm_flow_kton_per_year" not in streams_columns:
        cur.execute("ALTER TABLE streams ADD COLUMN norm_flow_kton_per_year REAL DEFAULT NULL")
        added.append("streams.norm_flow_kton_per_year REAL DEFAULT NULL")
    else:
        print("  norm_flow_kton_per_year already exists in streams — skipping")

    conn.commit()

    if added:
        print(f"Added columns: {', '.join(added)}")

    # Verify
    cur.execute("SELECT company_id, name, normalize_stream_id FROM companies")
    rows = cur.fetchall()
    print(f"\nVerification — {len(rows)} companies:")
    for row in rows:
        print(f"  {row[0]}  {row[1]:<40}  normalize_stream_id={row[2]}")

    conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    migrate(db)
