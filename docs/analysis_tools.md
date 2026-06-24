# Analysis Tools

Two scriptable CLI tools for post-extraction analysis: stream normalization and carbon accounting.

Both live in `analysis/` and accept an optional `--db <path>` argument (default: `industrial_cluster.db`).

> For the interactive arrow-key menus that wrap these (plus company/flow/stream/component management), see `cluster_cli.md`. For the browser-based interface, see `webapp.md`.

---

## Stream Normalization (`normalize_streams.py`)

Per-company scaling of flow rates. `normalize` writes `norm_flow_kton_per_year` for **every** company stream and writes the company's `scaling_factor` (it never modifies raw `flow_kton_per_year`). Each company resolves to one of three modes:

| Mode | Condition | `norm_flow` | `scaling_factor` written |
|---|---|---|---|
| **Manual factor** | `scaling_factor_manual = 1` | `flow × scaling_factor` | (left as the stored value) |
| **Reference stream** | `normalize_stream_id` set | `flow / ref_flow × setpoint` | `setpoint / ref_flow` |
| **None** | neither set | `flow` (unchanged) | `1.0` |

The reference stream is scaled to `normalize_setpoint` (default 1.0); all other streams of that company scale proportionally.

### Schema affected

- `companies.normalize_stream_id` — FK to the reference stream (same company, `flow > 0`). `NULL` = no reference.
- `companies.normalize_setpoint` — target value the reference stream is scaled to (default 1.0).
- `companies.scaling_factor` — multiplier written by `normalize` (or set manually). Used as `norm_flow = flow × scaling_factor`.
- `companies.scaling_factor_manual` — `1` = use the stored `scaling_factor` directly instead of recomputing it.
- `streams.norm_flow_kton_per_year` — computed normalized value (written for all streams).

Columns added by `migrate_add_normalization.py`, `migrate_add_normalize_setpoint.py`, and `migrate_add_scaling_factor_manual.py`.

### CLI

```bash
# List candidate reference streams for a company (any direction, flow > 0; current marked with *)
python analysis/normalize_streams.py list <company_id>

# Set / clear the reference stream for a company
python analysis/normalize_streams.py set <company_id> <stream_id>
python analysis/normalize_streams.py clear <company_id>

# Set / clear a manual scaling factor (bypasses the reference-stream formula;
# set also clears normalize_stream_id and immediately recalculates)
python analysis/normalize_streams.py set-custom-factor <company_id> <value>
python analysis/normalize_streams.py clear-custom-factor <company_id>

# Recalculate norm_flow_kton_per_year + scaling_factor for all companies
python analysis/normalize_streams.py normalize
```

`set` validates that `company_id` and `stream_id` exist, the stream belongs to the company, and `flow_kton_per_year > 0`. (Direction is **not** restricted — a reference stream may be an input or an output.) `set-custom-factor` requires `value > 0`. `normalize` re-applies validation at run time and skips (with a warning) any company that fails.

### Typical workflow

```bash
python analysis/normalize_streams.py list C001       # find a candidate reference stream
python analysis/normalize_streams.py set C001 S007   # set it
python analysis/normalize_streams.py normalize       # compute norm_flow + scaling_factor
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
