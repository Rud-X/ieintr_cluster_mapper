# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Extract material flow data from an Excel-derived CSV and organize it into a SQLite database for **industrial symbiosis matching** — identifying which companies could exchange waste/byproduct streams. Companies are not yet connected; the `flows` table starts empty and is only populated after matching analysis.

## Common Commands

### Build the database from scratch

Run migrations in this exact order (each is idempotent):

```bash
python migrations/extract.py
python migrations/migrate_add_company_columns.py
python migrations/migrate_add_normalization.py
python migrations/migrate_add_carbon.py
```

### Analysis tools

```bash
# Carbon accounting
python analysis/carbon.py status
python analysis/carbon.py recalculate
python analysis/carbon.py list-gaps
python analysis/carbon.py show <component_id>
python analysis/carbon.py set-component <component_id> [--carbon-atoms INT] [--molecular-weight FLOAT] [--carbon-pct FLOAT] [--clear-override]

# Stream normalization
python analysis/normalize_streams.py list <company_id>
python analysis/normalize_streams.py set <company_id> <stream_id>
python analysis/normalize_streams.py normalize
```

All tools accept `--db <path>` (default: `industrial_cluster.db`).

### Data exploration

```bash
jupyter notebook data_exploration/data_exploration.ipynb
```

## Architecture

### Database (`industrial_cluster.db`)

Five tables:

- **`companies`** — graph nodes. One row per company. `included=0` hides from analysis. `scaling_factor` is display-only (never modifies DB values). `normalize_stream_id` points to the reference output stream for normalization.
- **`streams`** — what each company independently consumes (`direction=input`) or produces (`direction=output`). Contains `flow_kton_per_year`, normalized values, and computed `carbon_pct`.
- **`components`** — reference table resolving aliases (e.g. "SiO2" and "silicon dioxide" → same row). CM227 is the reserved `"unknown"` component used for unaccounted composition remainder.
- **`stream_composition`** — junction table linking streams to components with `fraction` (decimal 0–1) and computed `carbon_fraction`.
- **`flows`** — graph edges representing proposed/confirmed symbiosis connections. Starts empty; populated by matching analysis.

### Pipeline flow

```
data/raw_materials_nomenclature.csv  ─┐
data/raw_streams_data.csv            ─┴─► migrations/extract.py ─► industrial_cluster.db
                                                                         │
                                         migrations/migrate_add_*.py ───┘ (add columns)
                                                                         │
                                         analysis/carbon.py recalculate  │ (compute values)
                                         analysis/normalize_streams.py normalize
```

### Key design rules

- `migrations/extract.py` is **stable — do not modify**.
- `data/` files are **source of truth** — do not edit after extraction unless re-running from scratch.
- `reference/version1_industrial_cluster.db` is a **read-only snapshot** — never overwrite it.
- Raw `flow_kton_per_year` values are **never modified** by analysis tools; normalization and scaling always write to separate columns.
- `carbon_weight_pct_manual=1` protects a component's carbon value from being overwritten by `recalculate`.

## Documentation

Full specs are in `docs/`:

| File | Contents |
|---|---|
| `docs/data_model.md` | Full schema with all columns, ER diagram |
| `docs/migrations_and_extraction.md` | CSV formats, composition string parser, migration details |
| `docs/analysis_tools.md` | Full CLI reference for `carbon.py` and `normalize_streams.py` |
| `docs/folder_structure.md` | Annotated directory tree |
