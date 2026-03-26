# Folder Structure

```
project/
│
├── docs/                                    ← project documentation
│   ├── data_model.md                        ← tables, columns, ER diagram
│   ├── analysis_tools.md                    ← carbon.py and normalize_streams.py
│   ├── migrations_and_extraction.md         ← extract.py pipeline, composition parser, migration scripts
│   └── folder_structure.md                  ← this file
│
├── data/                                    ← raw input files (do not modify)
│   ├── raw_streams_data.csv                 ← manually copied stream data; primary input to extract.py
│   └── raw_materials_nomenclature.csv       ← 226-material reference list; pre-loaded into components
│
├── migrations/                              ← scripts that create or evolve the DB schema
│   ├── run_migration.py                     ← runs the full 5-step migration pipeline in order
│   ├── extract.py                           ← CSV → SQLite pipeline (stable; do not modify)
│   ├── migrate_add_company_columns.py       ← adds scaling_factor + included to companies
│   ├── migrate_add_normalization.py         ← adds normalize_stream_id + norm_flow_kton_per_year
│   ├── migrate_add_carbon.py               ← adds carbon_weight_pct, carbon_fraction, carbon_pct, etc.
│   └── correct_components.py               ← resolve needs_review=1 stubs: merge duplicates, enrich new, flag ambiguous
│
├── analysis/                                ← CLI tools for post-extraction analysis
│   ├── normalize_streams.py                 ← set/clear reference streams; recalculate norm_flow
│   └── carbon.py                            ← status, recalculate, set-component, show, list-gaps
│
├── reference/                               ← archived artifacts; read-only
│   └── version1_industrial_cluster.db       ← database snapshot from v1 of the project
│
├── industrial_cluster.db                    ← live output database (git-ignored)
├── README.md                                ← project overview and documentation index
└── data_exploration/                        ← Jupyter notebooks for ad-hoc inspection
```

## Notes

- **`migrations/` run order:** `extract.py` → `migrate_add_company_columns.py` → `migrate_add_normalization.py` → `migrate_add_carbon.py` → `correct_components.py`. All steps are idempotent (safe to re-run on an existing schema). Use `migrations/run_migration.py` to run the full pipeline in one command.
- **`analysis/` tools** require a populated database; run migrations first.
- **`industrial_cluster.db`** is the live working database. The `reference/` copy is a read-only snapshot and should not be overwritten.
- **`data/`** files are the source of truth for stream content; do not edit them after extraction unless re-running `extract.py` from scratch.
