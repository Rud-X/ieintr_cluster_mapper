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
│   ├── extract.py                           ← CSV → SQLite pipeline (stable; do not modify)
│   ├── migrate_add_company_columns.py       ← adds scaling_factor + included to companies
│   ├── migrate_add_normalization.py         ← adds normalize_stream_id + norm_flow_kton_per_year
│   └── migrate_add_carbon.py               ← adds carbon_weight_pct, carbon_fraction, carbon_pct, etc.
│
├── analysis/                                ← CLI tools for post-extraction analysis
│   ├── normalize_streams.py                 ← set/clear reference streams; recalculate norm_flow
│   └── carbon.py                            ← status, recalculate, set-component, show, list-gaps
│
├── reference/                               ← archived artifacts; read-only
│   └── version1_industrial_cluster.db       ← database snapshot from v1 of the project
│
├── industrial_cluster.db                    ← live output database (git-ignored)
├── industrial_cluster_spec_V2.md            ← top-level spec (index into docs/)
├── data_exploration.ipynb                   ← loads all tables into pandas for quick inspection
├── component_review_analysis.md             ← pre-change analysis of needs_review=1 components
└── claude_code_handoff.md                   ← context document for Claude Code sessions
```

## Notes

- **`migrations/` run order:** `extract.py` → `migrate_add_company_columns.py` → `migrate_add_normalization.py` → `migrate_add_carbon.py`. Each migration is idempotent (safe to re-run on an existing schema).
- **`analysis/` tools** require a populated database; run migrations first.
- **`industrial_cluster.db`** is the live working database. The `reference/` copy is a read-only snapshot and should not be overwritten.
- **`data/`** files are the source of truth for stream content; do not edit them after extraction unless re-running `extract.py` from scratch.
