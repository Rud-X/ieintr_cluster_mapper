# Task: Per-Company Stream Normalization — Phase 1 (Database Only)

## Context

Read `industrial_cluster_spec_V2.md` for full system context — data model, tables, existing migration patterns, extraction pipeline.

## Goal

Add the ability to normalize a company's stream flow rates relative to a single reference product stream. When a reference stream is set, all of that company's `flow_kton_per_year` values are divided by the reference stream's value, so the reference becomes `1.0` and everything else scales proportionally.

This is **independent** of the existing `scaling_factor` column (which is display-only, applied client-side). Do not modify `scaling_factor` behavior.

## Normalization formula

```
norm_flow_kton_per_year = flow_kton_per_year / ref_flow
```

Where `ref_flow` is the `flow_kton_per_year` of the designated reference stream.

---

## Deliverable 1: `migrate_add_normalization.py`

Migration script. Follow the exact pattern in the existing `migrate_add_company_columns.py`.

### Requirements

- Must be **idempotent** — safe to run multiple times without error
- Use `ALTER TABLE` with column-existence checks (same technique as `migrate_add_company_columns.py`)
- Target database: `industrial_cluster.db`

### Schema changes

**`companies` table — add column:**

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `normalize_stream_id` | `TEXT` | `NULL` | FK → `streams.stream_id`. The reference stream to normalize against. Must be an `output`-direction stream belonging to that company. `NULL` = normalization disabled. |

**`streams` table — add column:**

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `norm_flow_kton_per_year` | `REAL` | `NULL` | Normalized flow value. `NULL` when the owning company has no `normalize_stream_id` set. |

---

## Deliverable 2: `normalize_streams.py`

Standalone script that recalculates `norm_flow_kton_per_year` for all companies. Idempotent — safe to re-run at any time.

### Logic per company

1. Read `normalize_stream_id` from `companies`
2. **If `NULL`:** set `norm_flow_kton_per_year = NULL` for all streams of that company
3. **If set:**
   a. Look up the reference stream's `flow_kton_per_year` (call it `ref_flow`)
   b. **Validate all of these — log warning and skip the company if any fail:**
      - Reference `stream_id` exists in `streams`
      - Reference stream's `company_id` matches this company
      - Reference stream has `direction = 'output'`
      - `ref_flow > 0`
   c. For every stream of that company: `UPDATE streams SET norm_flow_kton_per_year = flow_kton_per_year / ref_flow`

### Logging

Print a summary at the end:
- How many companies were normalized
- How many were skipped (no reference set)
- Any validation errors with company name and reason

---

## Constraints

- **Do NOT modify** `extract.py` — it is stable and upstream of this feature
- **Do NOT modify** `analysis/match_candidates.py` — scoring uses raw values intentionally
- **Do NOT modify** any existing `flow_kton_per_year` values in the DB
- **Do NOT modify** the frontend or `server.py` — those are Phase 2

## Verification

After implementation, confirm:

1. Run `migrate_add_normalization.py` twice — second run produces no errors
2. Run `normalize_streams.py` with all `normalize_stream_id` values as `NULL` — all `norm_flow_kton_per_year` should be `NULL`
3. Manually set one company's `normalize_stream_id` to one of its output streams in the DB, re-run `normalize_streams.py` — that company's streams should have correct normalized values, the reference stream should have `norm_flow_kton_per_year = 1.0`
4. Set `normalize_stream_id` to an input stream or a stream from another company, re-run — script should log a warning and skip that company
