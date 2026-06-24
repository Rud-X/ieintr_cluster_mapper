# Folder Structure

```
project/
│
├── docs/                                    ← project documentation
│   ├── data_model.md                        ← tables, columns, ER diagram
│   ├── migrations_and_extraction.md         ← extract.py pipeline, composition parser, migration scripts
│   ├── analysis_tools.md                    ← carbon.py and normalize_streams.py CLIs
│   ├── cluster_cli.md                       ← interactive TUI menu (cluster_cli.py)
│   ├── webapp.md                            ← FastAPI backend + React frontend
│   └── folder_structure.md                  ← this file
│
├── data/                                    ← raw input files (do not modify)
│   ├── raw_streams_data.csv                 ← manually copied stream data; primary input to extract.py
│   └── raw_materials_nomenclature.csv       ← 226-material reference list; pre-loaded into components
│
├── migrations/                              ← scripts that create or evolve the DB schema
│   ├── run_migration.py                     ← runs the full 8-step migration pipeline in order
│   ├── extract.py                           ← CSV → SQLite pipeline (stable; do not modify)
│   ├── migrate_add_company_columns.py       ← adds scaling_factor + included to companies
│   ├── migrate_add_normalization.py         ← adds normalize_stream_id + norm_flow_kton_per_year
│   ├── migrate_add_carbon.py                ← adds carbon_weight_pct, carbon_fraction, carbon_pct, etc.
│   ├── migrate_add_normalize_setpoint.py    ← adds normalize_setpoint to companies
│   ├── migrate_add_external_nodes.py        ← adds node_type / flow_type; relaxes flow stream-FK NOT NULL
│   ├── seed_manual_companies.py             ← re-applies external nodes + company metadata after extraction
│   ├── correct_components.py                ← resolve needs_review=1 stubs: merge duplicates, enrich, flag
│   ├── migrate_add_graph_layout.py          ← adds graph_x/graph_y (NOT in run_migration; run standalone)
│   └── migrate_add_scaling_factor_manual.py ← adds scaling_factor_manual (NOT in run_migration; run standalone)
│
├── analysis/                                ← CLI/TUI tools for post-extraction analysis
│   ├── cluster_cli.py                       ← interactive TUI orchestrator (entry point)
│   ├── manage_companies.py                  ← pure DB logic: company/stream/flow queries and mutations
│   ├── manage_companies_tui.py              ← TUI for Manage Companies
│   ├── manage_flows_tui.py                  ← TUI for Manage Flows
│   ├── carbon_tui.py                        ← TUI for carbon browsing + Manage Streams / Manage Components
│   ├── explore.py                           ← read-only DB exploration (backs the Explore menu)
│   ├── carbon.py                            ← carbon accounting backend + CLI
│   └── normalize_streams.py                 ← stream normalization / scaling backend + CLI
│
├── api/                                     ← FastAPI backend (see webapp.md)
│   ├── deps.py                              ← shared dependencies; DB path resolution
│   ├── models.py                            ← Pydantic response models
│   └── routes/                              ← routers: companies, flows, streams, components,
│                                                       carbon, graph, normalization
│
├── frontend/                                ← React + Vite web interface (see webapp.md)
│   ├── src/                                 ← components, hooks, lib (API client, theme)
│   ├── dist/                                ← built production bundle (served by server.py if present)
│   ├── package.json / vite.config.js        ← build + dev-server config
│   └── README.md                            ← frontend-specific notes
│
├── reference/                               ← archived artifacts; read-only
│   └── version1_industrial_cluster.db       ← database snapshot from v1 of the project
│
├── data_exploration/                        ← Jupyter notebooks + per-chapter analysis scripts
│   ├── data_exploration.ipynb               ← ad-hoc inspection notebook
│   ├── ch4/                                 ← mass/carbon balance, streams, sankey, flow compatibility
│   ├── ch6/                                 ← energy/material KPI notebooks + spreadsheets
│   └── export/                              ← generated CSV exports
│
├── server.py                                ← FastAPI entry point (serves API + built frontend)
├── dev.sh                                   ← starts backend + Vite dev server together
├── industrial_cluster.db                    ← live working database (git-ignored)
├── industrial_cluster_*.db                  ← chapter/scenario database snapshots (ch6_7, *_ch4, etc.)
├── README.md                                ← project overview, prerequisites, run instructions
└── CLAUDE.md                                ← guidance for Claude Code (commands + architecture)
```

## Notes

- **`migrations/` run order (8 steps):** `extract.py` → `migrate_add_company_columns.py` → `migrate_add_normalization.py` → `migrate_add_carbon.py` → `migrate_add_normalize_setpoint.py` → `migrate_add_external_nodes.py` → `seed_manual_companies.py` → `correct_components.py`. All steps are idempotent. Use `migrations/run_migration.py` to run the whole pipeline. `migrate_add_graph_layout.py` and `migrate_add_scaling_factor_manual.py` are **not** part of this pipeline — run them standalone if their columns are needed.
- **`analysis/` tools** require a populated database; run migrations first. `cluster_cli.py` is the interactive front door; `carbon.py` and `normalize_streams.py` are also usable as standalone CLIs.
- **Web app:** `./dev.sh` runs `server.py` (FastAPI, port 8000) and the Vite dev server (port 5173) together. In production `server.py` serves the built bundle from `frontend/dist/`. See `webapp.md`.
- **Databases:** `industrial_cluster.db` is the live working database (git-ignored). Other `industrial_cluster_*.db` files are committed chapter/scenario snapshots; pass them with `--db`. The `reference/` copy is a read-only snapshot and must not be overwritten.
- **`data/`** files are the source of truth for stream content; do not edit them after extraction unless re-running `extract.py` from scratch.
