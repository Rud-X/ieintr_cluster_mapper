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

Each migration adds columns to an existing database. Run them in order on a fresh `extract.py` output, or whenever the schema needs to be updated.

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
