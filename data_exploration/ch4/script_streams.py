"""
Stream inventory script for industrial cluster companies.

Lists all streams grouped by type (raw_material, product, waste) with
normalized flow and carbon mass percentage.

Usage:
    python script_streams.py all
    python script_streams.py all_included
    python script_streams.py <company_id>
    python script_streams.py all output=csv
    python script_streams.py all --only-water
    python script_streams.py all --exclude-water
    python script_streams.py all --db /path/to/db.sqlite
"""

import sys
from pathlib import Path
from datetime import datetime

import duckdb
import pandas as pd

SCRIPT_DIR = Path(__file__).parent
DEFAULT_DB = SCRIPT_DIR.parent / "../industrial_cluster.db"

STREAM_TYPE_LABELS = {
    "raw_material": "RAW MATERIALS (input)",
    "product": "PRODUCTS (output)",
    "waste": "WASTE (output)",
}

DISPLAY_COLS = [
    "company_id",
    "company_name",
    "stream_id",
    "stream_name",
    "flow_kton_per_year",
    "norm_flow_kton_per_year",
    "carbon_pct_%",
    "carbon_pct_complete",
]


def get_connection(db_path: Path) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"ATTACH '{db_path}' AS db (TYPE SQLITE)")
    return con


def get_all_company_ids(con) -> list[str]:
    rows = con.execute(
        "SELECT company_id FROM db.companies ORDER BY company_id"
    ).fetchall()
    return [r[0] for r in rows]


def get_included_company_ids(con) -> list[str]:
    rows = con.execute(
        "SELECT company_id FROM db.companies WHERE included = 1 ORDER BY company_id"
    ).fetchall()
    return [r[0] for r in rows]


def company_exists(con, company_id: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM db.companies WHERE company_id = $id", {"id": company_id}
    ).fetchone()
    return row is not None


def get_streams(con, company_ids: list[str]) -> pd.DataFrame:
    id_list = ", ".join(f"'{cid}'" for cid in company_ids)
    return con.execute(f"""
        WITH water_frac AS (
            SELECT sc.stream_id, sc.fraction AS wf
            FROM db.stream_composition sc
            WHERE sc.component_id = 'CM226'
        ),
        max_frac AS (
            SELECT stream_id, MAX(fraction) AS mf
            FROM db.stream_composition
            GROUP BY stream_id
        ),
        water_majority AS (
            SELECT wf.stream_id
            FROM water_frac wf
            JOIN max_frac mf ON wf.stream_id = mf.stream_id
            WHERE wf.wf >= mf.mf
        )
        SELECT
            s.company_id,
            c.name                                          AS company_name,
            s.stream_id,
            s.stream_name,
            s.stream_type,
            s.direction,
            ROUND(s.flow_kton_per_year, 3)                 AS flow_kton_per_year,
            ROUND(s.norm_flow_kton_per_year, 3)            AS norm_flow_kton_per_year,
            ROUND(s.carbon_pct * 100, 2)                   AS "carbon_pct_%",
            s.carbon_pct_complete,
            CASE WHEN wm.stream_id IS NOT NULL THEN 1 ELSE 0 END AS is_water_majority
        FROM db.streams s
        JOIN db.companies c ON s.company_id = c.company_id
        LEFT JOIN water_majority wm ON s.stream_id = wm.stream_id
        WHERE s.company_id IN ({id_list})
        ORDER BY
            s.company_id,
            CASE s.direction   WHEN 'input'  THEN 0 ELSE 1 END,
            CASE s.stream_type
                WHEN 'raw_material' THEN 0
                WHEN 'product'      THEN 1
                WHEN 'waste'        THEN 2
                ELSE 3
            END,
            s.flow_kton_per_year DESC
    """).df()


def print_streams(df: pd.DataFrame, multi_company: bool):
    cols = (
        DISPLAY_COLS
        if multi_company
        else [c for c in DISPLAY_COLS if c not in ("company_id", "company_name")]
    )

    for stream_type, label in STREAM_TYPE_LABELS.items():
        group = df[df["stream_type"] == stream_type][cols]
        if group.empty:
            continue
        print(f"\n── {label} ──")
        print(group.to_string(index=False))

    print()


def export_csv(df: pd.DataFrame, export_dir: Path):
    export_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = export_dir / f"{ts}_streams.csv"
    out = df.drop(columns=["direction", "is_water_majority"], errors="ignore")
    out.to_csv(path, index=False)
    print(f"Exported: {path}")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    db_path = DEFAULT_DB
    to_csv = False
    only_water = False
    exclude_water = False
    positional = []

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--db":
            db_path = Path(args[i + 1])
            i += 2
        elif a.startswith("--db="):
            db_path = Path(a.split("=", 1)[1])
            i += 1
        elif a == "output=csv":
            to_csv = True
            i += 1
        elif a == "--only-water":
            only_water = True
            i += 1
        elif a == "--exclude-water":
            exclude_water = True
            i += 1
        else:
            positional.append(a)
            i += 1

    if only_water and exclude_water:
        print("Error: --only-water and --exclude-water are mutually exclusive.")
        sys.exit(1)

    if not positional:
        print("Error: missing target (all / all_included / <company_id>)")
        sys.exit(1)

    target = positional[0]
    con = get_connection(db_path)

    if target == "all":
        company_ids = get_all_company_ids(con)
        multi = True
    elif target == "all_included":
        company_ids = get_included_company_ids(con)
        multi = True
    else:
        if not company_exists(con, target):
            print(f"Company '{target}' not found.")
            sys.exit(1)
        company_ids = [target]
        multi = False

    if not company_ids:
        print("No companies found.")
        sys.exit(0)

    df = get_streams(con, company_ids)

    if only_water:
        df = df[df["is_water_majority"] == 1]
    elif exclude_water:
        df = df[df["is_water_majority"] == 0]

    if df.empty:
        print("No streams match the given filters.")
        sys.exit(0)

    print_streams(df, multi_company=multi)

    if to_csv:
        export_csv(df, SCRIPT_DIR / "export")


if __name__ == "__main__":
    main()
