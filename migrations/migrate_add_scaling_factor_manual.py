"""
migrate_add_scaling_factor_manual.py

Idempotently adds scaling_factor_manual column to the companies table.
When 1, normalize() uses the stored scaling_factor directly instead of
recomputing it from setpoint / ref_flow.
"""

import sqlite3
import sys

DB_PATH = "industrial_cluster.db"


def migrate(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(companies)")
    existing_columns = {row[1] for row in cur.fetchall()}

    if "scaling_factor_manual" not in existing_columns:
        cur.execute("ALTER TABLE companies ADD COLUMN scaling_factor_manual INTEGER DEFAULT 0")
        print("Added column: scaling_factor_manual INTEGER DEFAULT 0")
    else:
        print("  scaling_factor_manual already exists — skipping")

    conn.commit()

    # Verify
    cur.execute("SELECT company_id, name, scaling_factor_manual FROM companies")
    rows = cur.fetchall()
    print(f"\nVerification — {len(rows)} companies:")
    for row in rows:
        print(f"  {row[0]}  {row[1]:<40}  scaling_factor_manual={row[2]}")

    conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    migrate(db)
