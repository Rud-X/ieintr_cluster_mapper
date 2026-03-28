"""
migrate_add_normalize_setpoint.py

Idempotently adds normalize_setpoint column to the companies table.
"""

import sqlite3
import sys

DB_PATH = "industrial_cluster.db"


def migrate(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(companies)")
    existing_columns = {row[1] for row in cur.fetchall()}

    if "normalize_setpoint" not in existing_columns:
        cur.execute("ALTER TABLE companies ADD COLUMN normalize_setpoint REAL DEFAULT 1.0")
        print("Added column: normalize_setpoint REAL DEFAULT 1.0")
    else:
        print("  normalize_setpoint already exists — skipping")

    conn.commit()

    # Verify
    cur.execute("SELECT company_id, name, normalize_setpoint FROM companies")
    rows = cur.fetchall()
    print(f"\nVerification — {len(rows)} companies:")
    for row in rows:
        print(f"  {row[0]}  {row[1]:<40}  normalize_setpoint={row[2]}")

    conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    migrate(db)
