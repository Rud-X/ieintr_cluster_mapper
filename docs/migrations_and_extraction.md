# Migrations and Extraction

All scripts that touch the database schema or populate it from raw data.

---

## Source files

### `data/raw_streams_data.csv` — primary input

Delimiter: `;`

| Column | Description |
|---|---|
| `company` | Company name |
| `stream_type` | One of: `raw`, `product`, `waste` |
| `stream_name` | Name of the material/stream |
| `composition` | Free-text composition string |
| `kiloton/year` | Numeric flow rate in kton/year |
| `Temperature ©` | Operating temperature in °C. Header has a copyright-symbol encoding artefact; `extract.py` matches any header containing `"temp"` (case-insensitive). |
| `pressure (bar)` | Operating pressure in bar |

`stream_type` mapping during extraction:

| CSV value | DB `stream_type` | DB `direction` |
|---|---|---|
| `raw` | `raw_material` | `input` |
| `product` | `product` | `output` |
| `waste` | `waste` | `output` |

### `data/raw_materials_nomenclature.csv` — reference input

Delimiter: `;` — 226 known materials. Pre-loaded into `components` before stream extraction.

| Column | Maps to |
|---|---|
| `Chemical` | `components.name` |
| `Abbreviation` | `components.aliases` |
| `CAS Number` | `components.cas_number` |
| `Molecular weight` | `components.molecular_weight` |
| `Carbon Atoms` | `components.carbon_atoms` |

---

## Extraction pipeline (`migrations/extract.py`)

**Stable — do not modify.**

```
data/raw_materials_nomenclature.csv
    │
    └─► Load known components → INSERT into components

data/raw_streams_data.csv
    │
    ├─► Extract distinct company names → INSERT into companies
    │       (sector and location left NULL for manual fill)
    │
    └─► For each row:
            Map stream_type; derive direction
            INSERT into streams (incl. temperature_c, pressure_bar)
            Parse composition string:
                For each (component_name, fraction):
                    Normalize: strip whitespace, handle European commas
                    Convert units: % → decimal, ppm → decimal, "trace" → 0
                    Look up component_name in components.name + aliases
                    If found → use existing component_id
                    If not found → INSERT into components with needs_review = 1
                Warn if non-trace fractions don't sum to ~1.0 (±0.02)
                Record remainder as "unknown" component
                INSERT into stream_composition

Output: industrial_cluster.db
```

### Composition string parser

Handles all formats observed in real data:

| Format | Example |
|---|---|
| Name then `%` in parens | `Methane (93%), Ethane (2.5%)` |
| `%` before name | `23.13% O2, 75.27% N2` |
| Name then `%` no parens | `CH3OH 0,018 %, DME 99,98%` |
| ppm values | `H2(666 ppm), Ar (2.41 ppm)` |
| Trace | `CO(trace)` |
| Decimal fractions | `SiO2: 0.6, CaO: 0.2` |

**Unit conversion:**
- `%` → divide by 100
- `ppm` → divide by 1,000,000
- `trace` → `fraction = 0`, `is_trace = 1`
- Decimal < 1, no unit → use as-is

**European decimal comma handling:** commas within numbers (e.g. `0,018`) are detected and converted to dots before numeric parsing. Heuristic: if a comma has fewer than 3 digits after it, treat it as a decimal separator. Both formats can appear in the same CSV.

**Fraction-sum validation:** sum all non-trace fractions per stream. If outside 1.0 ±0.02, log a warning and insert the remainder as the `"unknown"` component.

---

## Migration scripts

Each migration adds columns to (or evolves) an existing database. `migrations/run_migration.py` runs the full pipeline in order on a fresh `extract.py` output:

| Step | Script | Entry point |
|---|---|---|
| 1 | `extract.py` | `main()` |
| 2 | `migrate_add_company_columns.py` | `migrate()` |
| 3 | `migrate_add_normalization.py` | `migrate()` |
| 4 | `migrate_add_carbon.py` | `migrate()` |
| 5 | `migrate_add_normalize_setpoint.py` | `migrate()` |
| 6 | `migrate_add_external_nodes.py` | `migrate()` |
| 7 | `seed_manual_companies.py` | `apply()` |
| 8 | `correct_components.py` | `apply()` |

```bash
python migrations/run_migration.py            # run all 8 steps
python migrations/run_migration.py --dry-run  # steps 1–7 normally, preview step 8
```

> **Not in the pipeline.** Two further schema migrations exist but are **not** invoked by `run_migration.py`; run them standalone after a rebuild if the web app graph view or manual scaling factors are needed:
> - `migrate_add_graph_layout.py` — adds `companies.graph_x`, `companies.graph_y` (entry point `run()`).
> - `migrate_add_scaling_factor_manual.py` — adds `companies.scaling_factor_manual` (entry point `migrate()`).

All steps are idempotent (safe to re-run on an existing schema).

### `migrations/migrate_add_company_columns.py`

Adds `scaling_factor` and `included` to the `companies` table.

| Column | Default |
|---|---|
| `scaling_factor` | `1.0` |
| `included` | `1` |

### `migrations/migrate_add_normalization.py`

Adds two columns to support per-company stream normalization.

| Table | Column | Default |
|---|---|---|
| `companies` | `normalize_stream_id` | `NULL` |
| `streams` | `norm_flow_kton_per_year` | `NULL` |

Values are populated afterward by `analysis/normalize_streams.py`.

### `migrations/migrate_add_carbon.py`

Adds carbon tracking columns across three tables.

| Table | Column | Default |
|---|---|---|
| `components` | `carbon_weight_pct` | `NULL` |
| `components` | `carbon_weight_pct_manual` | `NULL` |
| `stream_composition` | `carbon_fraction` | `NULL` |
| `streams` | `carbon_pct` | `NULL` |
| `streams` | `carbon_pct_complete` | `NULL` |

Values are computed afterward by `analysis/carbon.py recalculate`.

### `migrations/migrate_add_normalize_setpoint.py`

Adds one column to support a normalization target value.

| Table | Column | Default |
|---|---|---|
| `companies` | `normalize_setpoint` | `1.0` |

With a reference stream set, `normalize_streams.py` scales the reference stream to `normalize_setpoint` (so `norm_flow = flow / ref_flow × setpoint`).

### `migrations/migrate_add_external_nodes.py`

Adds external-node support (import sources, export sinks, waste facilities):

1. `companies` — adds `node_type` (TEXT NOT NULL DEFAULT `'company'`; values `company`, `import_source`, `export_sink`, `waste_facility`).
2. `flows` — adds `flow_type` (TEXT NOT NULL DEFAULT `'internal'`; values `internal`, `import`, `export`, `waste_to_wmf`).
3. `flows` — **recreates the table** to drop the NOT NULL constraint on `from_stream_id` and `to_stream_id`, so import flows (no from-stream) and export/WMF flows (no to-stream) are representable. Existing rows are copied across. Idempotent: skips recreation if the FKs are already nullable.

See `data_model.md` → **External Nodes** for the resulting flow-type semantics.

### `migrations/correct_components.py`

Resolves components auto-inserted with `needs_review=1` during extraction. Any composition component not found in the reference nomenclature is inserted as a stub; this script applies documented corrections to clean them up.

Run via `run_migration.py` (step 8) or standalone:

```bash
python migrations/correct_components.py [--db PATH] [--dry-run]
```

`--dry-run` previews all changes without writing to the database.

#### Correction types

| Type | Effect |
|---|---|
| `Merge(src, into, reason)` | Redirects all `stream_composition` rows from `src` to `into`, appends `src` as an alias on `into`, deletes `src` component row. |
| `Enrich(name, reason, ...)` | Fills in `category`, `cas_number`, `molecular_weight`, `carbon_atoms` for a genuinely new component and sets `needs_review=0`. |
| `Flag(name, notes)` | Writes an explanatory note to `components.notes` and keeps `needs_review=1` for manual follow-up. |

All corrections are **idempotent**: `Merge` silently skips if `src` is already absent; `Enrich` and `Flag` are plain `UPDATE`s.

Lookups use the component **name** (`COLLATE NOCASE`), not the auto-generated `component_id`, so corrections survive a full re-extraction even if IDs shift.

#### Resolving a Flag

Once you have identified the correct resolution from source data:

1. Replace the `Flag(...)` entry in `CORRECTIONS` with a `Merge(...)` or `Enrich(...)`.
2. Add a `reason` explaining the decision.
3. Commit and re-run `python migrations/run_migration.py`.

---

### `migrations/seed_manual_companies.py` — manual company seeding (step 7)

Re-applies manually-managed company additions after every extraction. Runs before `correct_components.py`.

Run via `run_migration.py` (step 7) or standalone:

```bash
python migrations/seed_manual_companies.py [--db PATH] [--dry-run]
```

`--dry-run` previews all changes without writing to the database.

#### Seed types

| Type | Effect |
|---|---|
| `ExternalNode(name, node_type, sector, location)` | Inserts an external node if absent; skips if already present with the same `node_type`; warns if present with a different type. |
| `CompanyMeta(name, sector, location, included)` | Updates non-null metadata fields on a company matched by exact name. |

All seeds are **idempotent**: safe to re-run on an already-seeded database.

Lookups use the company **name** (case-sensitive exact match), not the auto-generated `company_id`.

#### Workflow for external nodes

Every external node (import source, export sink, waste facility) created via the TUI must also be declared in the `SEEDS` list to survive a full re-extraction:

1. Add the node via `+ Add External Node` in the TUI.
2. Add a matching `ExternalNode(...)` line to `SEEDS` in `seed_manual_companies.py`.
3. Commit the file — the node now persists across re-extractions.

When **deleting** an external node via the TUI:

1. Delete the node via the TUI (`Delete...` → type `"delete company"`).
2. Remove the corresponding `ExternalNode(...)` line from `SEEDS`.
3. Commit the file — the node will not reappear on the next re-extraction.

The TUI prints a reminder after every external node deletion.

#### Workflow for company metadata

Company `sector`, `location`, and `included` values set via the TUI are lost on re-extraction. Declare them as `CompanyMeta(...)` entries in `SEEDS` to preserve them:

```python
CompanyMeta("Hydrogen Plant",        sector="Energy",    location="Zone A"),
CompanyMeta("Solid Waste Management", included=0),
```
