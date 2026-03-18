"""
migrate_add_company_columns.py

Idempotently adds scaling_factor and included columns to the companies table.
"""

import sqlite3
import sys

DB_PATH = "industrial_cluster.db"


def migrate(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(companies)")
    existing_columns = {row[1] for row in cur.fetchall()}

    added = []

    if "scaling_factor" not in existing_columns:
        cur.execute("ALTER TABLE companies ADD COLUMN scaling_factor REAL DEFAULT 1.0")
        added.append("scaling_factor REAL DEFAULT 1.0")
    else:
        print("  scaling_factor already exists — skipping")

    if "included" not in existing_columns:
        cur.execute("ALTER TABLE companies ADD COLUMN included INTEGER DEFAULT 1")
        added.append("included INTEGER DEFAULT 1")
    else:
        print("  included already exists — skipping")

    conn.commit()

    if added:
        print(f"Added columns: {', '.join(added)}")

    # Verify
    cur.execute("SELECT company_id, name, scaling_factor, included FROM companies")
    rows = cur.fetchall()
    print(f"\nVerification — {len(rows)} companies:")
    for row in rows:
        print(f"  {row[0]}  {row[1]:<40}  scaling_factor={row[2]}  included={row[3]}")

    conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    migrate(db)
