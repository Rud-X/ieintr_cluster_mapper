# Carbon Weight % Calculation — Implementation Brief

> Hand this file to Claude Code for implementation. Read `industrial_cluster_spec_V2.md` for full project context before starting.

---

## Overview

Add carbon weight percentage tracking across three layers of the data model:

1. **`components`** — what % of this component's molecular weight is carbon?
2. **`stream_composition`** — what carbon % does this component contribute to this stream?
3. **`streams`** — what is the stream's total carbon % by weight?

Implement via a migration script (`migrate_add_carbon.py`) and a CLI tool (`carbon.py`) following the same patterns as `migrate_add_normalization.py` and `normalize_streams.py`.

---

## Schema Changes (migration)

Create `migrate_add_carbon.py`. It adds three columns:

### `components.carbon_weight_pct`

| Column | Type | Description |
|---|---|---|
| `carbon_weight_pct` | REAL | Weight fraction of carbon in the component (0–1 scale, e.g. `0.75` = 75% carbon). Calculated as `(carbon_atoms × 12.011) / molecular_weight` when both values are present. Can also be set manually via CLI for named materials/mixtures. `NULL` when data is insufficient and no manual override has been set. |

### `stream_composition.carbon_fraction`

| Column | Type | Description |
|---|---|---|
| `carbon_fraction` | REAL | Carbon contribution of this component to the stream = `fraction × carbon_weight_pct`. `NULL` when the component's `carbon_weight_pct` is `NULL`. |

### `streams.carbon_pct`

| Column | Type | Description |
|---|---|---|
| `carbon_pct` | REAL | Total carbon weight % for the stream = sum of `carbon_fraction` across all non-trace, non-unknown composition rows. `NULL` when the stream has no composition data, or when all components lack `carbon_weight_pct`. |

The migration script should:
- Add the three columns with `ALTER TABLE` (safe to run repeatedly — check if column exists first, skip with a message if so)
- **Not** populate any values — that is the job of `carbon.py recalculate`
- Print a summary of what was added

---

## CLI Tool: `carbon.py`

All subcommands accept an optional `--db <path>` argument (default: `industrial_cluster.db`).

### Subcommands

#### `carbon.py status`

Print a summary report:
- Total components, how many have `carbon_weight_pct` set (formula-based vs manual), how many are `NULL`
- List components where `carbon_weight_pct` is `NULL` and `needs_review = 0` — these are the actionable gaps
- Total streams, how many have `carbon_pct` set, how many are `NULL`
- For streams with `NULL` carbon_pct: list them grouped by company, showing which components are missing data

#### `carbon.py recalculate`

Full three-layer recalculation in order:

1. **Components layer** — For every component where `carbon_atoms` and `molecular_weight` are both non-NULL **and** `carbon_weight_pct_manual` is not set (see below): compute `carbon_weight_pct = (carbon_atoms × 12.011) / molecular_weight`. Skip components with a manual override (preserve their value). Log warnings for components where either `carbon_atoms` or `molecular_weight` is NULL and no manual override exists.

2. **Stream composition layer** — For every `stream_composition` row: if the linked component has a non-NULL `carbon_weight_pct` and the row is not trace (`is_trace = 0`), compute `carbon_fraction = fraction × carbon_weight_pct`. Otherwise set `carbon_fraction = NULL`.

3. **Streams layer** — For every stream: sum `carbon_fraction` across all composition rows, **excluding** trace rows (`is_trace = 1`) and rows where `component_id` points to the reserved `"unknown"` component. If the sum includes at least one non-NULL `carbon_fraction`, set `carbon_pct` to that sum. If all relevant rows have `NULL` carbon_fraction, set `carbon_pct = NULL`.

Print a summary at the end: how many components/composition rows/streams were updated, how many skipped.

**Important:** `recalculate` must be safe to run repeatedly (idempotent). Running it twice should produce the same result.

#### `carbon.py set-component <component_id> [options]`

Update molecular data and/or manually override carbon weight % for a specific component. Options:

| Flag | Description |
|---|---|
| `--carbon-atoms <int>` | Set `carbon_atoms` value |
| `--molecular-weight <float>` | Set `molecular_weight` value |
| `--carbon-pct <float>` | Manually set `carbon_weight_pct` (0–1 scale). Sets a flag so `recalculate` does not overwrite it. |
| `--clear-override` | Remove the manual override flag, allowing `recalculate` to recompute from formula |

Validation:
- `component_id` must exist in `components`
- `--carbon-pct` must be in range 0.0–1.0
- `--carbon-atoms` must be a non-negative integer
- `--molecular-weight` must be positive

After updating the component, **automatically run a cascading recalculation** for this component only:
1. Recompute `carbon_weight_pct` if not manually overridden (i.e., if `--carbon-atoms` or `--molecular-weight` was changed but not `--carbon-pct`)
2. Update all `stream_composition.carbon_fraction` rows referencing this component
3. Update `streams.carbon_pct` for all streams that contain this component

This auto-cascade ensures the DB is always consistent after a `set-component` call. The `recalculate` subcommand exists for bulk recomputation (e.g., after migration or bulk data changes).

#### `carbon.py show <component_id>`

Display full detail for a single component:
- All component fields including `carbon_weight_pct` and whether it's a manual override
- All streams containing this component (stream_id, stream_name, company, fraction, carbon_fraction)

#### `carbon.py list-gaps`

List components where `carbon_weight_pct` is NULL, sorted by how many streams they appear in (most impactful gaps first). For each, show:
- `component_id`, `name`, `carbon_atoms` (if any), `molecular_weight` (if any)
- Number of streams affected
- Whether `needs_review = 1`

This helps prioritize which components to fix with `set-component`.

---

## Manual Override Mechanism

To track whether a `carbon_weight_pct` value was set manually (and should not be overwritten by `recalculate`), add a column in the migration:

| Column | Type | Description |
|---|---|---|
| `components.carbon_weight_pct_manual` | INTEGER | `1` if `carbon_weight_pct` was manually set via CLI, `0` or `NULL` otherwise. When `1`, `recalculate` preserves the existing `carbon_weight_pct` value. |

---

## Edge Cases and Warnings

- **Components with `carbon_atoms = 0`** (e.g., `H2O`, `SiO2`, `N2`): `carbon_weight_pct` should compute to `0.0`, which is correct — these are carbon-free. This is distinct from `NULL` (unknown).
- **Components with `carbon_atoms` but no `molecular_weight`** (or vice versa): `carbon_weight_pct = NULL`, log a warning during `recalculate`.
- **The reserved `"unknown"` component**: excluded from stream-level `carbon_pct` sum (same treatment as trace). Identify it by name = `"unknown"` or however it is stored in the DB — check the actual data.
- **Trace composition rows** (`is_trace = 1`): `carbon_fraction` set to `NULL`, excluded from stream-level sum.
- **Streams with partial coverage**: If a stream has 5 components but only 3 have `carbon_weight_pct`, the `carbon_pct` will be an undercount. This is acceptable — the `status` and `list-gaps` commands make the gaps visible. Do **not** set `carbon_pct = NULL` just because some components are missing; compute the partial sum so the data is still useful. Add a `streams.carbon_pct_complete` column (INTEGER, `1` if all non-trace non-unknown components have `carbon_weight_pct`, `0` otherwise) so consumers can distinguish complete vs partial values.

---

## Additional Migration Column

Add to the `streams` table alongside `carbon_pct`:

| Column | Type | Description |
|---|---|---|
| `carbon_pct_complete` | INTEGER | `1` if all non-trace, non-unknown composition rows for this stream have non-NULL `carbon_weight_pct` on their component. `0` if any are missing. `NULL` if the stream has no composition rows. Recalculated by `carbon.py recalculate`. |

---

## File Structure

```
project/
├── migrate_add_carbon.py          ← NEW: adds carbon columns to components, stream_composition, streams
├── carbon.py                      ← NEW: CLI tool (status, recalculate, set-component, show, list-gaps)
├── ...existing files...
```

---

## Recalculation SQL Reference

These are the core computations for reference. The actual implementation should use parameterized queries.

```sql
-- 1. Component-level: formula-based carbon_weight_pct (skip manual overrides)
UPDATE components
SET carbon_weight_pct = (carbon_atoms * 12.011) / molecular_weight
WHERE carbon_atoms IS NOT NULL
  AND molecular_weight IS NOT NULL
  AND molecular_weight > 0
  AND (carbon_weight_pct_manual IS NULL OR carbon_weight_pct_manual = 0);

-- 2. Stream composition-level: carbon_fraction
UPDATE stream_composition
SET carbon_fraction = (
    SELECT sc.fraction * c.carbon_weight_pct
    FROM stream_composition sc2
    JOIN components c ON sc2.component_id = c.component_id
    WHERE sc2.composition_id = stream_composition.composition_id
      AND c.carbon_weight_pct IS NOT NULL
      AND sc2.is_trace = 0
)
WHERE is_trace = 0;

-- Set NULL for trace rows or where component has no carbon data
UPDATE stream_composition
SET carbon_fraction = NULL
WHERE is_trace = 1
   OR component_id IN (SELECT component_id FROM components WHERE carbon_weight_pct IS NULL);

-- 3. Stream-level: carbon_pct (exclude trace and unknown)
UPDATE streams
SET carbon_pct = (
    SELECT SUM(sc.carbon_fraction)
    FROM stream_composition sc
    JOIN components c ON sc.component_id = c.component_id
    WHERE sc.stream_id = streams.stream_id
      AND sc.is_trace = 0
      AND c.name != 'unknown'
      AND sc.carbon_fraction IS NOT NULL
);

-- 4. Stream-level: carbon_pct_complete flag
UPDATE streams
SET carbon_pct_complete = (
    SELECT CASE
        WHEN COUNT(*) = 0 THEN NULL
        WHEN SUM(CASE WHEN c.carbon_weight_pct IS NULL THEN 1 ELSE 0 END) = 0 THEN 1
        ELSE 0
    END
    FROM stream_composition sc
    JOIN components c ON sc.component_id = c.component_id
    WHERE sc.stream_id = streams.stream_id
      AND sc.is_trace = 0
      AND c.name != 'unknown'
);
```

---

## Testing

After implementation, verify with:

```bash
# Run migration
python migrate_add_carbon.py

# Recalculate everything
python carbon.py recalculate

# Check status
python carbon.py status

# Verify a known component (e.g., methane CH4: carbon_atoms=1, MW=16.04, expected ≈ 0.749)
python carbon.py show CM___ # (find methane's ID)

# Check gaps
python carbon.py list-gaps

# Manually set carbon % for a named material
python carbon.py set-component CM___ --carbon-pct 0.45

# Verify cascade
python carbon.py show CM___
```

---

## Spec Update Reminder

After implementation, update `industrial_cluster_spec_V2.md`:
- Add `carbon_weight_pct`, `carbon_weight_pct_manual` to the `components` table definition
- Add `carbon_fraction` to the `stream_composition` table definition
- Add `carbon_pct`, `carbon_pct_complete` to the `streams` table definition
- Add a "Carbon Weight % Calculation" section (similar to "Stream Normalization") documenting the feature
- Add `migrate_add_carbon.py` and `carbon.py` to the file structure
- Update the TODO list
