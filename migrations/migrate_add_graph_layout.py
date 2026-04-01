"""
migrate_add_graph_layout.py

Adds graph_x and graph_y columns to the companies table.
These store the saved position of each company node in the web app graph view.

Idempotent: safe to re-run on an existing schema.
"""

import sqlite3
import sys

DB_PATH = "industrial_cluster.db"


def run(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(companies)")
    existing_columns = {row[1] for row in cur.fetchall()}

    added = []

    if "graph_x" not in existing_columns:
        cur.execute("ALTER TABLE companies ADD COLUMN graph_x REAL")
        added.append("graph_x")

    if "graph_y" not in existing_columns:
        cur.execute("ALTER TABLE companies ADD COLUMN graph_y REAL")
        added.append("graph_y")

    conn.commit()
    conn.close()

    if added:
        print(f"migrate_add_graph_layout: added columns {added}")
    else:
        print("migrate_add_graph_layout: columns already exist, nothing to do")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DB_PATH)
    args = parser.parse_args()
    run(args.db)
