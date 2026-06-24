"""
Mass balance script for industrial cluster companies.

Closure: Calculated as (1 - abs(gap) / total_in) * 100, where gap is total_in - total_out.

Usage:
    python script_mass_balance.py <company_id>
    python script_mass_balance.py all_included
    python script_mass_balance.py <company_id> output=csv
    python script_mass_balance.py all_included output=csv
    python script_mass_balance.py <company_id> --db /path/to/db.sqlite
"""

import sys
import os
from pathlib import Path
from datetime import datetime

import duckdb
import pandas as pd

SCRIPT_DIR = Path(__file__).parent
DEFAULT_DB = SCRIPT_DIR.parent / "../industrial_cluster.db"


def get_connection(db_path: Path) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"ATTACH '{db_path}' AS db (TYPE SQLITE)")
    return con


def get_included_companies(con) -> list[tuple]:
    rows = con.execute("""
        SELECT c.company_id, c.name, c.normalize_stream_id, s.stream_name, c.normalize_setpoint, c.scaling_factor
        FROM db.companies c
        LEFT JOIN db.streams s ON c.normalize_stream_id = s.stream_id
        WHERE c.included = 1
        ORDER BY c.company_id
    """).fetchall()
    return rows


def get_company_info(con, company_id: str) -> tuple:
    return con.execute(
        """
        SELECT c.name, c.normalize_stream_id, s.stream_name, c.normalize_setpoint, c.scaling_factor
        FROM db.companies c
        LEFT JOIN db.streams s ON c.normalize_stream_id = s.stream_id
        WHERE c.company_id = $id
    """,
        {"id": company_id},
    ).fetchone()


def get_totals(con, company_id: str) -> pd.DataFrame:
    return con.execute(
        """
        SELECT * FROM (
            SELECT
                direction,
                stream_type,
                COUNT(*)                                            AS stream_count,
                ROUND(SUM(flow_kton_per_year), 3)                  AS total_flow_kton_per_year,
                ROUND(SUM(norm_flow_kton_per_year), 3)             AS total_norm_flow,
                ROUND(SUM(flow_kton_per_year * carbon_pct), 3)     AS total_carbon_flow_kton_per_year
            FROM db.streams
            WHERE company_id = $company_id
              AND flow_kton_per_year IS NOT NULL
            GROUP BY direction, stream_type

            UNION ALL

            SELECT
                direction,
                'TOTAL'                                             AS stream_type,
                COUNT(*)                                            AS stream_count,
                ROUND(SUM(flow_kton_per_year), 3)                  AS total_flow_kton_per_year,
                ROUND(SUM(norm_flow_kton_per_year), 3)             AS total_norm_flow,
                ROUND(SUM(flow_kton_per_year * carbon_pct), 3)     AS total_carbon_flow_kton_per_year
            FROM db.streams
            WHERE company_id = $company_id
              AND flow_kton_per_year IS NOT NULL
            GROUP BY direction
        )
        ORDER BY
            CASE direction   WHEN 'input' THEN 0 ELSE 1 END,
            CASE stream_type WHEN 'TOTAL' THEN 99 ELSE 0 END
    """,
        {"company_id": company_id},
    ).df()


def get_streams(con, company_id: str) -> pd.DataFrame:
    return con.execute(
        """
        SELECT
            s.stream_id,
            s.stream_name,
            s.stream_type,
            s.direction,
            s.flow_kton_per_year,
            s.norm_flow_kton_per_year,
            ROUND(s.carbon_pct * 100, 2)                        AS carbon_pct_display,
            s.carbon_pct_complete,
            ROUND(s.flow_kton_per_year * s.carbon_pct, 3)       AS carbon_flow_kton_per_year,
            s.temperature_c,
            s.pressure_bar,
            s.notes
        FROM db.streams s
        WHERE s.company_id = $company_id
        ORDER BY
            CASE s.direction  WHEN 'input' THEN 0 ELSE 1 END,
            CASE s.stream_type
                WHEN 'raw_material' THEN 0
                WHEN 'product'      THEN 1
                WHEN 'waste'        THEN 2
                ELSE 3
            END,
            s.flow_kton_per_year DESC
    """,
        {"company_id": company_id},
    ).df()


def compute_balance(df_totals: pd.DataFrame) -> dict:
    totals = df_totals[df_totals["stream_type"] == "TOTAL"].set_index("direction")
    total_in = (
        totals.loc["input", "total_flow_kton_per_year"]
        if "input" in totals.index
        else 0.0
    )
    total_out = (
        totals.loc["output", "total_flow_kton_per_year"]
        if "output" in totals.index
        else 0.0
    )
    gap = total_in - total_out
    closure = (1 - abs(gap) / total_in) * 100 if total_in else float("nan")
    carbon_in = (
        totals.loc["input", "total_carbon_flow_kton_per_year"]
        if "input" in totals.index
        else 0.0
    )
    carbon_out = (
        totals.loc["output", "total_carbon_flow_kton_per_year"]
        if "output" in totals.index
        else 0.0
    )
    carbon_gap = carbon_in - carbon_out
    carbon_closure = (
        (1 - abs(carbon_gap) / carbon_in) * 100 if carbon_in else float("nan")
    )
    return dict(
        total_in=total_in,
        total_out=total_out,
        gap=gap,
        closure=closure,
        carbon_in=carbon_in,
        carbon_out=carbon_out,
        carbon_gap=carbon_gap,
        carbon_closure=carbon_closure,
    )


def print_single(
    company_id: str,
    company_name: str,
    ref_stream_id,
    ref_stream_name,
    normalize_setpoint,
    scaling_factor,
    b: dict,
    df_streams: pd.DataFrame,
):
    print(f"\nCompany : {company_id}  {company_name}")
    print("─" * 40)
    print(f"Reference stream  : {ref_stream_id or 'None'}  {ref_stream_name or ''}")
    print(
        f"Normalize setpoint: {normalize_setpoint if normalize_setpoint is not None else 'None'}"
    )
    print(
        f"Scaling factor    : {scaling_factor if scaling_factor is not None else 'None'}"
    )
    print("─" * 40)
    print(f"Total input       : {b['total_in']:>10.3f}  kton/yr")
    print(f"Total output      : {b['total_out']:>10.3f}  kton/yr")
    print(f"Gap (in − out)    : {b['gap']:>10.3f}  kton/yr")
    print(f"Mass closure      : {b['closure']:>10.2f}  %")
    print("─" * 40)
    print(f"Carbon input      : {b['carbon_in']:>10.3f}  kton C/yr")
    print(f"Carbon output     : {b['carbon_out']:>10.3f}  kton C/yr")
    print(f"Carbon gap        : {b['carbon_gap']:>10.3f}  kton C/yr")
    print(f"Carbon closure    : {b['carbon_closure']:>10.2f}  %")
    print()
    print(df_streams.to_string(index=False))
    print()


def print_all_summary(rows: list[dict]):
    df = pd.DataFrame(rows)
    col_order = [
        "company_id",
        "company_name",
        "reference_stream_id",
        "reference_stream_name",
        "normalize_setpoint",
        "scaling_factor",
        "total_in",
        "total_out",
        "gap",
        "mass_closure_pct",
        "carbon_in",
        "carbon_out",
        "carbon_gap",
        "carbon_closure_pct",
    ]
    df = df[col_order]
    df = df.rename(
        columns={
            "mass_closure_pct": "mass_closure%",
            "carbon_closure_pct": "carbon_closure%",
        }
    )
    print()
    print(df.to_string(index=False))
    print()


def export_csv(df: pd.DataFrame, export_dir: Path):
    export_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = export_dir / f"{ts}_mass_balance.csv"
    df.to_csv(path, index=False)
    print(f"Exported: {path}")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    # Parse flags
    db_path = DEFAULT_DB
    to_csv = False
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
        else:
            positional.append(a)
            i += 1

    if not positional:
        print("Error: missing company_id or 'all_included'")
        sys.exit(1)

    target = positional[0]
    con = get_connection(db_path)

    if target == "all_included":
        companies = get_included_companies(con)
        if not companies:
            print("No included companies found.")
            sys.exit(0)

        summary_rows = []

        for (
            company_id,
            company_name,
            ref_sid,
            ref_sname,
            setpoint,
            scaling,
        ) in companies:
            df_totals = get_totals(con, company_id)
            b = compute_balance(df_totals)
            summary_rows.append(
                {
                    "company_id": company_id,
                    "company_name": company_name,
                    "reference_stream_id": ref_sid,
                    "reference_stream_name": ref_sname,
                    "normalize_setpoint": setpoint,
                    "scaling_factor": scaling,
                    **{
                        k: round(v, 3) if isinstance(v, float) else v
                        for k, v in b.items()
                        if k not in ("closure", "carbon_closure")
                    },
                    "mass_closure_pct": round(b["closure"], 2),
                    "carbon_closure_pct": round(b["carbon_closure"], 2),
                }
            )

        print_all_summary(summary_rows)

        if to_csv:
            df_summary = pd.DataFrame(summary_rows).rename(
                columns={"closure_pct": "closure%"}
            )
            export_csv(df_summary, SCRIPT_DIR / "export")

    else:
        company_id = target
        info = get_company_info(con, company_id)
        if info is None:
            print(f"Company '{company_id}' not found.")
            sys.exit(1)
        company_name, ref_sid, ref_sname, setpoint, scaling = info

        df_totals = get_totals(con, company_id)
        df_streams = get_streams(con, company_id)
        b = compute_balance(df_totals)

        print_single(
            company_id,
            company_name,
            ref_sid,
            ref_sname,
            setpoint,
            scaling,
            b,
            df_streams,
        )

        if to_csv:
            df_summary = pd.DataFrame(
                [
                    {
                        "company_id": company_id,
                        "company_name": company_name,
                        "reference_stream_id": ref_sid,
                        "reference_stream_name": ref_sname,
                        "normalize_setpoint": setpoint,
                        "scaling_factor": scaling,
                        **{
                            k: round(v, 3) if isinstance(v, float) else v
                            for k, v in b.items()
                            if k != "closure"
                        },
                        "mass_closure%": round(b["closure"], 2),
                        "carbon_closure%": round(b["carbon_closure"], 2),
                    }
                ]
            )
            export_csv(df_summary, SCRIPT_DIR / "export")


if __name__ == "__main__":
    main()
