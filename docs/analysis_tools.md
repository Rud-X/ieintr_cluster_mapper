# Analysis Tools

Two CLI tools for post-extraction analysis: stream normalization and carbon accounting.

Both live in `analysis/` and accept an optional `--db <path>` argument (default: `industrial_cluster.db`).

---

## Stream Normalization (`normalize_streams.py`)

Per-company normalization of flow rates relative to a single reference stream. When a reference is set, all `norm_flow_kton_per_year` values for that company are computed as `flow_kton_per_year / ref_flow`, making the reference stream's value `1.0` and scaling all others proportionally.

This is **independent** of `scaling_factor` (which is display-only and never written to the DB). Normalization writes to the DB; it never modifies raw `flow_kton_per_year`.

### Schema affected

- `companies.normalize_stream_id` — FK to the reference stream (`output` direction, same company, `flow > 0`). `NULL` = disabled.
- `streams.norm_flow_kton_per_year` — computed normalized value. `NULL` when no reference is set.

Both columns added by `migrations/migrate_add_normalization.py`.

### CLI

```bash
# List valid output streams for a company (current reference marked with *)
python analysis/normalize_streams.py list <company_id>

# Set the reference stream for a company
python analysis/normalize_streams.py set <company_id> <stream_id>

# Clear the reference stream for a company
python analysis/normalize_streams.py clear <company_id>

# Recalculate norm_flow_kton_per_year for all companies that have a reference set
python analysis/normalize_streams.py normalize
```

`set` validates:
- `company_id` exists in `companies`
- `stream_id` exists in `streams`
- Stream belongs to the specified company
- Stream `direction = 'output'`
- Stream `flow_kton_per_year > 0`

`normalize` applies the same validation at run time and skips (with a warning) any company that fails.

### Typical workflow

```bash
python analysis/normalize_streams.py list C001       # find a valid reference stream
python analysis/normalize_streams.py set C001 S007   # set it
python analysis/normalize_streams.py normalize       # compute norm_flow_kton_per_year
```

---

## Carbon Accounting (`carbon.py`)

Per-component and per-stream carbon content tracking for carbon accounting across the cluster.

### Schema affected

- `components.carbon_weight_pct` — weight fraction of carbon (0–1). Computed as `(carbon_atoms × 12.011) / molecular_weight`. NULL if data is insufficient. Can be manually overridden.
- `components.carbon_weight_pct_manual` — `1` when manually set; prevents `recalculate` from overwriting.
- `stream_composition.carbon_fraction` — `fraction × carbon_weight_pct` for non-trace rows. NULL when component has no `carbon_weight_pct` or `is_trace = 1`.
- `streams.carbon_pct` — sum of `carbon_fraction` across non-trace, non-unknown composition rows. Partial sums accepted.
- `streams.carbon_pct_complete` — `1` if all non-trace, non-unknown components have `carbon_weight_pct`; `0` if any are missing; NULL if no composition rows.

All columns added by `migrations/migrate_add_carbon.py`. Values computed by `carbon.py recalculate`.

### CLI

```bash
# Summary of coverage across all components and streams
python analysis/carbon.py status

# Full three-layer recalculation (idempotent):
#   1. carbon_weight_pct per component
#   2. carbon_fraction per stream_composition row
#   3. carbon_pct + carbon_pct_complete per stream
python analysis/carbon.py recalculate

# List components with NULL carbon_weight_pct, sorted by stream impact
python analysis/carbon.py list-gaps

# Full detail for a single component
python analysis/carbon.py show <component_id>

# Update molecular data or manually override carbon_weight_pct
python analysis/carbon.py set-component <component_id> \
    [--carbon-atoms INT] \
    [--molecular-weight FLOAT] \
    [--carbon-pct FLOAT] \
    [--clear-override]
```

`set-component` automatically cascades: recomputes `carbon_weight_pct` (unless overridden), then updates `stream_composition.carbon_fraction` and `streams.carbon_pct` for all affected streams.

### Edge cases

| Situation | Behaviour |
|---|---|
| `carbon_atoms = 0` (e.g. H₂O, N₂) | `carbon_weight_pct = 0.0` — carbon-free, not unknown |
| Trace rows (`is_trace = 1`) | `carbon_fraction = NULL`; excluded from stream sum |
| Reserved `unknown` component (CM227) | Excluded from `carbon_pct` sum |
| Partial coverage | `carbon_pct` is a partial sum; `carbon_pct_complete = 0` flags this |
