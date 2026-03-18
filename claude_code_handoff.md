# Claude Code Task: Symbiosis Matcher Web App

## Context

This is an existing industrial symbiosis project. The data pipeline (`extract.py`) is complete and produces `industrial_cluster.db` — an SQLite database with tables: `companies`, `components`, `streams`, `stream_composition`, `flows`. See `industrial_cluster_spec_V2.md` in the project root for the full schema and data model.

A working React prototype exists as a single-file artifact (`reference/symbiosis_matcher.jsx`). Your job is to integrate it into the project as a real web application: a FastAPI backend serving data from the SQLite database, and a Vite + React frontend that looks and behaves identically to the prototype.

**Read `industrial_cluster_spec_V2.md` first.** It describes every table, column, and relationship.

---

## Deliverables

### 1. Database schema changes

Add two columns to the existing `companies` table:

```sql
ALTER TABLE companies ADD COLUMN scaling_factor REAL DEFAULT 1.0;
ALTER TABLE companies ADD COLUMN included INTEGER DEFAULT 1;
```

- `scaling_factor`: multiplier for all flow values of that company (range 0.1–5.0, default 1.0)
- `included`: whether the company is part of the current cluster analysis (1 = included, 0 = excluded)

Write a migration script `migrate_add_company_columns.py` that:
1. Connects to `industrial_cluster.db`
2. Checks if columns already exist (idempotent)
3. Adds them with defaults if missing
4. Prints confirmation

### 2. Backend: `server.py` (FastAPI)

Place in project root. Serves the frontend static files AND provides a REST API.

**Startup:**
```
cd project/
python server.py
# → serves at http://localhost:8000
```

Dependencies: `fastapi`, `uvicorn`, `aiofiles` (add a `requirements-server.txt`).

**API endpoints:**

```
GET  /api/data
```
Returns the full dataset as a single JSON object matching this shape (identical to what the frontend expects):

```json
{
  "metadata": {
    "total_companies": 14,
    "total_streams": 134,
    "total_candidates": ...,
    "unique_company_pairs": ...,
    "min_score_threshold": 0.15
  },
  "companies": [
    {
      "company_id": "C001",
      "name": "...",
      "sector": "...",
      "location": "...",
      "scaling_factor": 1.0,
      "included": 1
    }
  ],
  "streams": [
    {
      "stream_id": "S001",
      "company_id": "C001",
      "stream_name": "...",
      "stream_type": "raw_material",
      "direction": "input",
      "flow_kton_per_year": 850.0,
      "temperature_c": 25.0,
      "pressure_bar": 1.0,
      "composition_raw": "...",
      "components": [
        {
          "component_id": "CM001",
          "name": "Fe2O3",
          "category": "oxide",
          "fraction": 0.92,
          "is_trace": 0,
          "hazardous": 0
        }
      ]
    }
  ],
  "candidates": [ ... ],
  "flows": [ ... ]
}
```

The `candidates` array must be computed server-side. **Import and reuse the scoring logic from `analysis/match_candidates.py`** — do not rewrite it. The scoring algorithm is:

- `component_overlap`: Jaccard index of non-trace component sets
- `fraction_similarity`: 1 − mean |frac_out − frac_in| for shared components
- `flow_compatibility`: min(available, required) / max(available, required)
- `temperature_proximity`: 1 / (1 + |T_out − T_in| / 100), or 0.5 if unknown
- `pressure_proximity`: 1 / (1 + |P_out − P_in| / 10), or 0.5 if unknown
- `composite_score`: weighted average (0.35, 0.25, 0.20, 0.10, 0.10)
- Discard candidates with composite_score < 0.15

Each candidate object includes: `from_company_id`, `to_company_id`, `from_stream_id`, `to_stream_id`, `from_stream_name`, `to_stream_name`, `from_stream_type`, `to_stream_type`, `composite_score`, `component_overlap`, `fraction_similarity`, `flow_compatibility`, `temperature_proximity`, `pressure_proximity`, `shared_components` (array of `{name, hazardous, fraction_out, fraction_in}`), `has_hazardous`, `available_flow_kton`, `required_flow_kton`.

```
PUT  /api/companies/{company_id}
```
Request body (partial update — any subset of these fields):
```json
{
  "scaling_factor": 1.43,
  "included": 1
}
```
Writes to the `companies` table. Returns the updated company object.

```
POST /api/flows
```
Request body:
```json
{
  "from_company_id": "C001",
  "to_company_id": "C003",
  "from_stream_id": "S002",
  "to_stream_id": "S009",
  "flow_kton_per_year": 280,
  "status": "candidate",
  "notes": ""
}
```
Generates the next `flow_id` (e.g. `F001`, `F002`...) and inserts into the `flows` table. Returns the created flow with its `flow_id`.

```
PUT  /api/flows/{flow_id}
```
Partial update — any subset of `status`, `notes`, `flow_kton_per_year`. Returns updated flow.

```
DELETE /api/flows/{flow_id}
```
Deletes from `flows` table. Returns `{"deleted": true}`.

**Static file serving:** Serve the built frontend from `frontend/dist/` at `/`. The API routes under `/api/` take priority.

**CORS:** Allow `http://localhost:5173` during development (Vite dev server).

### 3. Frontend: Vite + React app in `frontend/`

Initialize with `npm create vite@latest frontend -- --template react`. The app must look and behave **identically** to the reference prototype in `reference/symbiosis_matcher.jsx`.

**Project structure:**
```
frontend/
├── package.json
├── vite.config.js          ← proxy /api to localhost:8000
├── src/
│   ├── main.jsx
│   ├── App.jsx             ← root component
│   ├── components/
│   │   ├── ForceGraph.jsx  ← D3 force-directed network graph
│   │   ├── ScoreBar.jsx
│   │   ├── ScoreDetail.jsx
│   │   ├── AiEval.jsx      ← Claude API evaluation button
│   │   ├── CandidateList.jsx
│   │   ├── CandidateDetail.jsx
│   │   ├── ManualPairing.jsx
│   │   └── FlowsManager.jsx
│   ├── lib/
│   │   ├── api.js          ← fetch wrappers for /api/*
│   │   ├── scoring.js      ← client-side scorePair() for manual pairing
│   │   └── constants.js    ← colors, score thresholds
│   └── styles/
│       └── index.css       ← minimal global styles (font import, resets)
```

**Critical implementation details — read the reference JSX carefully:**

1. **Data loading:** On mount, `fetch('/api/data')` and populate state. Replace the hardcoded `DEMO_DATA` entirely.

2. **Company toggles:** Left sidebar. Clicking a company toggles `included`. Each active company shows a scale slider (×0.10 to ×5.00) below its name. Changes are **debounced** (300ms) and persisted via `PUT /api/companies/{id}`.

3. **Scale factor display:** In candidate detail, flow values show the original struck through with the scaled value next to it when scale ≠ 1.0. Two buttons: "Scale supplier ×N.NN" and "Scale receiver ×N.NN" compute the ratio to match the other side's (scaled) flow and apply it.

4. **Force graph (D3):** Nodes are companies (colored circles with initials). Candidate edges are dashed lines colored by score. Confirmed flow edges are solid thick green lines with ✓ label. Click an edge to select the candidate. Nodes are draggable. Zoom/pan enabled.

5. **Three tabs in right panel:**
   - **Candidates** — sorted by composite_score descending. Each card shows: score %, company names (colored), stream names, shared component names, "in flows" badge if already added. Click to expand detail view with score breakdown bars, shared component table, "Add to Flows" button, and "Ask Claude for Evaluation" button.
   - **Manual Pair** — two dropdowns (output streams, input streams, filtered by active companies). "Evaluate Fit" runs client-side scoring. Shows same score detail. "Add to Flows" and "Ask Claude" buttons.
   - **Flows (N)** — lists all flows. Status pill cycles: candidate → confirmed → rejected → candidate (click to cycle). Inline note editor (click to edit). Remove button (✕). Summary bar shows counts per status. "Export Flows as JSON" downloads the list.

6. **Flow persistence:** "Add to Flows" calls `POST /api/flows`. Status changes and note edits call `PUT /api/flows/{id}`. Remove calls `DELETE /api/flows/{id}`. After each mutation, refresh the flows from the server response (optimistic update is fine, but the server is the source of truth for flow_id generation).

7. **AI evaluation:** The "Ask Claude for Evaluation" button calls the Anthropic API directly from the browser (same as the prototype — `fetch("https://api.anthropic.com/v1/messages", ...)`). Model: `claude-sonnet-4-20250514`, max_tokens: 1000. The prompt template is in the reference JSX in the `AiEval` component — copy it exactly.

8. **Styling:** Dark theme. JetBrains Mono font. All colors and CSS are inline in the reference — preserve them exactly. Do not introduce a CSS framework. The reference uses these specific hex values:
   - Background: `#0f1117` (main), `#181b23` (card), `#1e2230` (hover)
   - Border: `#2a2e3a`
   - Text: `#e8eaed` (primary), `#9aa0ad` (secondary), `#5f6577` (dim)
   - Accent: `#5B9BD5`
   - Score colors: `#4ade80` (≥70%), `#facc15` (≥50%), `#fb923c` (≥30%), `#f87171` (<30%)
   - Company colors cycle: `#E8915A, #5B9BD5, #7BC67E, #D4A0D9, #E06C75, #C9B458, #6CC1C8, #F28B82, #A4C9A4, #B8A9C9, #D4956B, #8BB8D0`

9. **Minimum score slider:** In the header. Range 0–90%, step 5%. Filters the candidate list and graph edges client-side.

### 4. Files to create (summary)

```
project/
├── server.py                           ← FastAPI backend
├── migrate_add_company_columns.py      ← one-time DB migration
├── requirements-server.txt             ← fastapi, uvicorn, aiofiles
├── analysis/
│   └── match_candidates.py             ← ALREADY EXISTS, import from server.py
├── reference/
│   └── symbiosis_matcher.jsx           ← the prototype artifact (for reference only)
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── components/
│       │   ├── ForceGraph.jsx
│       │   ├── ScoreBar.jsx
│       │   ├── ScoreDetail.jsx
│       │   ├── AiEval.jsx
│       │   ├── CandidateList.jsx
│       │   ├── CandidateDetail.jsx
│       │   ├── ManualPairing.jsx
│       │   └── FlowsManager.jsx
│       ├── lib/
│       │   ├── api.js
│       │   ├── scoring.js
│       │   └── constants.js
│       └── styles/
│           └── index.css
```

---

## Constraints

- **Do not modify `extract.py`** — it is stable and tested.
- **Do not modify the existing database tables** other than adding the two columns to `companies`.
- **Import scoring logic from `analysis/match_candidates.py`** in the server — do not duplicate it. You may need to adjust imports (add `sys.path` manipulation or restructure as needed), but do not change the scoring algorithm.
- **The database file is `industrial_cluster.db` in the project root.** Hard-code this path in `server.py` with an optional `--db` argument.
- **The frontend must look identical to the reference prototype.** Copy all inline styles, colors, font choices, layout structure, and interaction patterns exactly. The reference is the spec for the UI.

## Steps

1. Read `industrial_cluster_spec_V2.md` to understand the full data model
2. Read `reference/symbiosis_matcher.jsx` end-to-end to understand every UI feature
3. Read `analysis/match_candidates.py` to understand the scoring logic you'll import
4. Run `migrate_add_company_columns.py` to add the new columns
5. Build `server.py` with all endpoints, verify with curl
6. Scaffold the frontend, split the reference into components, wire up API calls
7. Test the full flow: load data → toggle companies → browse candidates → add to flows → change status → export
8. Build the frontend (`npm run build`) and verify it serves from FastAPI
