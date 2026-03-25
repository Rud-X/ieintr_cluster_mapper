"""
migrate_add_carbon.py

Idempotently adds carbon-weight columns:
  - components.carbon_weight_pct         (REAL, NULL)
  - components.carbon_weight_pct_manual  (INTEGER, NULL)
  - stream_composition.carbon_fraction   (REAL, NULL)
  - streams.carbon_pct                   (REAL, NULL)
  - streams.carbon_pct_complete          (INTEGER, NULL)
"""

import sqlite3
import sys

DB_PATH = "industrial_cluster.db"


def migrate(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    added = []

    # --- components table ---
    cur.execute("PRAGMA table_info(components)")
    components_columns = {row[1] for row in cur.fetchall()}

    if "carbon_weight_pct" not in components_columns:
        cur.execute("ALTER TABLE components ADD COLUMN carbon_weight_pct REAL DEFAULT NULL")
        added.append("components.carbon_weight_pct REAL DEFAULT NULL")
    else:
        print("  carbon_weight_pct already exists in components — skipping")

    if "carbon_weight_pct_manual" not in components_columns:
        cur.execute("ALTER TABLE components ADD COLUMN carbon_weight_pct_manual INTEGER DEFAULT NULL")
        added.append("components.carbon_weight_pct_manual INTEGER DEFAULT NULL")
    else:
        print("  carbon_weight_pct_manual already exists in components — skipping")

    # --- stream_composition table ---
    cur.execute("PRAGMA table_info(stream_composition)")
    sc_columns = {row[1] for row in cur.fetchall()}

    if "carbon_fraction" not in sc_columns:
        cur.execute("ALTER TABLE stream_composition ADD COLUMN carbon_fraction REAL DEFAULT NULL")
        added.append("stream_composition.carbon_fraction REAL DEFAULT NULL")
    else:
        print("  carbon_fraction already exists in stream_composition — skipping")

    # --- streams table ---
    cur.execute("PRAGMA table_info(streams)")
    streams_columns = {row[1] for row in cur.fetchall()}

    if "carbon_pct" not in streams_columns:
        cur.execute("ALTER TABLE streams ADD COLUMN carbon_pct REAL DEFAULT NULL")
        added.append("streams.carbon_pct REAL DEFAULT NULL")
    else:
        print("  carbon_pct already exists in streams — skipping")

    if "carbon_pct_complete" not in streams_columns:
        cur.execute("ALTER TABLE streams ADD COLUMN carbon_pct_complete INTEGER DEFAULT NULL")
        added.append("streams.carbon_pct_complete INTEGER DEFAULT NULL")
    else:
        print("  carbon_pct_complete already exists in streams — skipping")

    conn.commit()

    if added:
        print("Added columns:")
        for col in added:
            print(f"  {col}")

    conn.close()
    print("\nMigration complete. Run 'python carbon.py recalculate' to populate values.")


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    migrate(db)
