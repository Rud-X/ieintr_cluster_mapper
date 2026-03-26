"""
run_migration.py — Build industrial_cluster.db from scratch.

Runs the full pipeline in the correct order:
  1. migrations/extract.py                  — CSV → SQLite (wipes and rebuilds)
  2. migrations/migrate_add_company_columns.py
  3. migrations/migrate_add_normalization.py
  4. migrations/migrate_add_carbon.py
  5. migrations/correct_components.py       — merge duplicates, enrich new entries,
                                             flag unresolved components

Usage:
  python migrations/run_migration.py [--db PATH] [--dry-run]

  --dry-run  Run steps 1–4 normally, then preview step 5 without writing changes.
             Useful for verifying corrections after modifying correct_components.py.
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_DB = PROJECT_ROOT / "industrial_cluster.db"

sys.path.insert(0, str(PROJECT_ROOT / "migrations"))

import extract
import migrate_add_company_columns
import migrate_add_normalization
import migrate_add_carbon
import correct_components


def _banner(step: int, total: int, label: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"Step {step}/{total}: {label}")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build industrial_cluster.db from scratch.")
    parser.add_argument("--db", default=str(DEFAULT_DB), metavar="PATH",
                        help="Output database path (default: %(default)s)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview step 5 (correct_components) without writing changes")
    args = parser.parse_args()
    db_path = Path(args.db).resolve()

    # Patch extract.py paths: the script was written when it lived in the project
    # root; now that it's in migrations/ the BASE_DIR resolves incorrectly.
    extract.BASE_DIR = PROJECT_ROOT
    extract.NOMENCLATURE_CSV = PROJECT_ROOT / "data" / "raw_materials_nomenclature.csv"
    extract.STREAMS_CSV = PROJECT_ROOT / "data" / "raw_streams_data.csv"
    extract.DB_PATH = db_path

    _banner(1, 5, "extract.py — CSV → SQLite")
    extract.main()

    _banner(2, 5, "migrate_add_company_columns")
    migrate_add_company_columns.migrate(str(db_path))

    _banner(3, 5, "migrate_add_normalization")
    migrate_add_normalization.migrate(str(db_path))

    _banner(4, 5, "migrate_add_carbon")
    migrate_add_carbon.migrate(str(db_path))

    _banner(5, 5, "correct_components — merge duplicates / enrich / flag")
    correct_components.apply(str(db_path), dry_run=args.dry_run)

    print(f"\nDone. Database written to: {db_path}")


if __name__ == "__main__":
    main()
