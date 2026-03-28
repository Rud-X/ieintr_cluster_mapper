# Data Model

Five tables in total. Companies and streams capture what each company independently consumes and produces. Flows are populated only after matching analysis identifies candidate connections.

---

## Entity Relationship

```mermaid
erDiagram
    companies {
        TEXT company_id PK
        TEXT name
        TEXT sector
        TEXT location
        TEXT node_type
        REAL scaling_factor
        INTEGER included
        TEXT normalize_stream_id FK
    }

    streams {
        TEXT stream_id PK
        TEXT company_id FK
        TEXT stream_name
        TEXT stream_type
        TEXT direction
        REAL flow_kton_per_year
        REAL norm_flow_kton_per_year
        REAL temperature_c
        REAL pressure_bar
        TEXT composition_raw
        REAL carbon_pct
        INTEGER carbon_pct_complete
        TEXT notes
    }

    components {
        TEXT component_id PK
        TEXT name
        TEXT aliases
        TEXT category
        TEXT cas_number
        REAL molecular_weight
        INTEGER carbon_atoms
        REAL carbon_weight_pct
        INTEGER carbon_weight_pct_manual
        INTEGER hazardous
        INTEGER needs_review
        TEXT notes
    }

    stream_composition {
        TEXT composition_id PK
        TEXT stream_id FK
        TEXT component_id FK
        REAL fraction
        INTEGER is_trace
        REAL carbon_fraction
    }

    flows {
        TEXT flow_id PK
        TEXT from_company_id FK
        TEXT to_company_id FK
        TEXT from_stream_id FK
        TEXT to_stream_id FK
        REAL flow_kton_per_year
        TEXT flow_type
        TEXT status
        TEXT notes
    }

    companies ||--o{ streams : "has"
    streams ||--o{ stream_composition : "contains"
    components ||--o{ stream_composition : "identified in"
    companies ||--o{ flows : "supplies (from)"
    companies ||--o{ flows : "receives (to)"
    streams ||--o{ flows : "output stream"
    streams ||--o{ flows : "input stream"
```

---

## `companies` — Graph nodes

One row per company **or external node**. Real companies are auto-generated from distinct values in `raw_streams_data.csv` during extraction; external nodes are added manually via the TUI. `sector` and `location` are filled manually afterward.

| Column | Type | Description |
|---|---|---|
| `company_id` | TEXT (PK) | e.g. `C001` |
| `name` | TEXT | Company or node name |
| `sector` | TEXT | Industry sector — filled manually |
| `location` | TEXT | Zone or address — filled manually |
| `node_type` | TEXT | `'company'` (default), `'import_source'`, `'export_sink'`, or `'waste_facility'`. See **External Nodes** below. Added by `migrate_add_external_nodes.py`. |
| `scaling_factor` | REAL | Display multiplier (0.1–5.0, default 1.0). Applied client-side to kton/year display only; raw DB values are never modified. Added by `migrate_add_company_columns.py`. |
| `included` | INTEGER | `1` = visible in cluster analysis, `0` = excluded. Added by `migrate_add_company_columns.py`. |
| `normalize_stream_id` | TEXT (FK → streams) | Reference stream for per-company normalization. Must be an `output`-direction stream of this company with `flow > 0`. `NULL` = normalization disabled. Added by `migrate_add_normalization.py`. |

---

## `components` — Material/component reference table

Centralizes component identity so that `"SiO2"` and `"silicon dioxide"` resolve to the same row. Pre-populated from `raw_materials_nomenclature.csv`; extended during stream extraction.

| Column | Type | Description |
|---|---|---|
| `component_id` | TEXT (PK) | e.g. `CM001` |
| `name` | TEXT | Canonical name, e.g. `SiO2`, `Fe`, `limestone` |
| `aliases` | TEXT | Comma-separated alternative names / synonyms |
| `category` | TEXT | One of: `oxide`, `metal`, `carbonate`, `sulfate`, `organic`, `named_material`, `other` |
| `cas_number` | TEXT | CAS registry number where applicable |
| `molecular_weight` | REAL | g/mol (NULL for named materials) |
| `carbon_atoms` | INTEGER | Number of carbon atoms (from nomenclature CSV; NULL if unknown) |
| `carbon_weight_pct` | REAL | Carbon weight fraction (0–1). Computed as `(carbon_atoms × 12.011) / molecular_weight`. Can be overridden manually via `carbon.py set-component`. NULL when data is insufficient and no override is set. Added by `migrate_add_carbon.py`. |
| `carbon_weight_pct_manual` | INTEGER | `1` if manually set; prevents `carbon.py recalculate` from overwriting. Added by `migrate_add_carbon.py`. |
| `hazardous` | INTEGER | `1` = hazardous, `0` = not, NULL = unknown |
| `needs_review` | INTEGER | `1` if auto-added during extraction and not yet verified |
| `notes` | TEXT | Optional regulatory or handling notes |

> **Reserved entry:** CM227 is the `"unknown"` component — used to absorb unaccounted composition fractions. It is excluded from `carbon_pct` sums.

> **Lookup during extraction:** the parser resolves component names against both `name` and `aliases`. Unrecognized components are inserted with `needs_review = 1`.

---

## `streams` — Material streams per company

One row per stream per company. `direction` is derived from `stream_type` and makes inflow/outflow queries straightforward without joins.

| Column | Type | Description |
|---|---|---|
| `stream_id` | TEXT (PK) | e.g. `S001` |
| `company_id` | TEXT (FK → companies) | Owning company |
| `stream_name` | TEXT | Name as in source data |
| `stream_type` | TEXT | `raw_material`, `product`, or `waste` |
| `direction` | TEXT | Derived: `input` (raw_material) or `output` (product, waste) |
| `flow_kton_per_year` | REAL | Flow rate in kton/year |
| `norm_flow_kton_per_year` | REAL | `flow_kton_per_year / ref_flow` where `ref_flow` is the company's reference stream. Reference stream's own value is always `1.0`. NULL when no reference set. Added by `migrate_add_normalization.py`. |
| `temperature_c` | REAL | Operating temperature in °C (NULL if not provided) |
| `pressure_bar` | REAL | Operating pressure in bar (NULL if not provided) |
| `composition_raw` | TEXT | Original composition string, preserved for reference |
| `carbon_pct` | REAL | Sum of `carbon_fraction` across all non-trace, non-unknown composition rows. Partial sums accepted. NULL when no eligible components have `carbon_weight_pct`. Added by `migrate_add_carbon.py`. |
| `carbon_pct_complete` | INTEGER | `1` if all non-trace, non-unknown components have `carbon_weight_pct`; `0` if any are missing; NULL if no composition rows. Added by `migrate_add_carbon.py`. |
| `notes` | TEXT | Optional |

---

## `stream_composition` — Junction: streams ↔ components

Each row is one component within one stream. Fractions are stored as decimals (0–1).

| Column | Type | Description |
|---|---|---|
| `composition_id` | TEXT (PK) | e.g. `CP001` |
| `stream_id` | TEXT (FK → streams) | The stream this component belongs to |
| `component_id` | TEXT (FK → components) | The resolved component |
| `fraction` | REAL | Decimal fraction, e.g. `0.60` for 60%. `0` for trace amounts. |
| `is_trace` | INTEGER | `1` if original value was `"trace"`, `0` otherwise |
| `carbon_fraction` | REAL | `fraction × carbon_weight_pct`. NULL when `carbon_weight_pct` is NULL or `is_trace = 1`. Added by `migrate_add_carbon.py`. |

> If non-trace fractions don't sum to 1.0 (±0.02 tolerance), the remainder is recorded as a row pointing to the `"unknown"` component and a warning is logged.

---

## `flows` — Graph edges (proposed/confirmed connections)

Starts **empty**. Populated after matching analysis identifies candidate industrial symbiosis links, or manually via the TUI.

Every flow has exactly **two node endpoints** (`from_company_id` and `to_company_id` are always non-null), preserving the graph invariant for network analysis. Stream references may be NULL when an endpoint is an external node.

| Column | Type | Description |
|---|---|---|
| `flow_id` | TEXT (PK) | e.g. `F001` |
| `from_company_id` | TEXT NOT NULL (FK → companies) | Source node — company or external node |
| `to_company_id` | TEXT NOT NULL (FK → companies) | Destination node — company or external node |
| `from_stream_id` | TEXT nullable (FK → streams) | Output stream being supplied. **NULL** when `from_company_id` is an `import_source`. |
| `to_stream_id` | TEXT nullable (FK → streams) | Input stream being satisfied. **NULL** when `to_company_id` is an `export_sink` or `waste_facility`. |
| `flow_kton_per_year` | REAL | Agreed or estimated quantity |
| `flow_type` | TEXT | `internal`, `import`, `export`, or `waste_to_wmf`. Auto-derived from node types. Added by `migrate_add_external_nodes.py`. |
| `status` | TEXT | `candidate`, `confirmed`, or `rejected` |
| `notes` | TEXT | Optional |

### Flow types

| `flow_type` | From node | To node | Stream NULLs |
|---|---|---|---|
| `internal` | `company` | `company` | Neither NULL |
| `import` | `import_source` | `company` | `from_stream_id` is NULL |
| `export` | `company` | `export_sink` | `to_stream_id` is NULL |
| `waste_to_wmf` | `company` | `waste_facility` | `to_stream_id` is NULL |

---

## External Nodes

External nodes use the same `companies` table but have `node_type != 'company'`. They represent cluster boundary entities:

| `node_type` | Role | Has streams? |
|---|---|---|
| `import_source` | Raw material supplier outside the cluster | Optional — can have output streams if needed |
| `export_sink` | Product buyer outside the cluster | Optional — can have input streams if needed |
| `waste_facility` | Material sink (WMF, landfill, etc.) — outflow not modelled by default | Optional — can have output streams if the WMF re-processes material |

External nodes appear in the graph and have named identities. They are created manually via `+ Add External Node` in the Manage Companies TUI.

**Graph invariant:** Every `flows` row always has two non-null company endpoints. Nulls appear only on the stream-reference side.

---

## Inflows / Outflows vs. Connections

| Concept | Table | Populated when |
|---|---|---|
| What a company consumes | `streams` (direction=`input`) | During extraction |
| What a company produces | `streams` (direction=`output`) | During extraction |
| Who exchanges with whom | `flows` | After matching analysis |
