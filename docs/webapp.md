# Web App

A browser interface for exploring and editing the cluster database: a **FastAPI** backend (`server.py` + `api/`) and a **React + Vite** frontend (`frontend/`). Both read and write the same SQLite database used by the CLI tools.

## Running

```bash
# First time only: install frontend dependencies
cd frontend && npm install && cd ..

# Start backend (FastAPI, :8000) and frontend dev server (Vite, :5173) together
./dev.sh
./dev.sh --port 8001 --db industrial_cluster_ch6_7.db   # extra args pass through to server.py
```

- **Backend:** http://localhost:8000
- **Frontend (dev):** http://localhost:5173 — Vite proxies `/api` to the backend.
- **Production:** `python server.py` serves the API and, if `frontend/dist/` exists (built via `npm run build`), mounts it at `/`.

`server.py` flags: `--db <path>` (default `industrial_cluster.db`), `--port` (default 8000), `--host` (default 127.0.0.1). The DB path can also be set via the `CLUSTER_DB` environment variable (see `api/deps.py`).

## Backend (`api/`)

| File | Role |
|---|---|
| `api/deps.py` | DB-path resolution (`CLUSTER_DB` env var or `set_db_path()` from `server.py`); `get_db()` dependency |
| `api/models.py` | Pydantic response models (Company, Stream, Flow, Component, carbon + graph payloads) |
| `api/routes/` | One router module per resource, each mounted by `server.py` |

All routers are mounted in `server.py`, plus a `GET /api/health` check. CORS allows the Vite dev origin (`http://localhost:5173`).

### Routes

| Router | Endpoints |
|---|---|
| `companies` (`/api/companies`) | `GET ""`, `GET /{id}`, `PATCH /{id}`, `GET /{id}/streams`, `GET /{id}/flows`, `POST /{id}/flows`, `GET /{id}/normalization`, `POST /{id}/normalization/set`, `POST /{id}/normalization/clear`, `POST /{id}/normalization/setpoint`, `POST /{id}/normalization/custom-factor`, `DELETE /{id}/normalization/custom-factor` |
| `flows` (`/api/flows`) | `GET ""`, `GET /{id}`, `PATCH /{id}`, `DELETE /{id}` |
| `streams` (`/api/streams`) | `GET ""`, `GET /{id}` |
| `components` (`/api/components`) | `GET ""`, `GET /{id}`, `PATCH /{id}` |
| `carbon` (`/api/carbon`) | `GET /status`, `POST /recalculate`, `GET /gaps` |
| `graph` (`/api/graph`) | `GET ""`, `PATCH /positions`, `POST /normalization/recalculate` |
| `normalization` (`/api/normalization`) | `POST /recalculate` |

The normalization and carbon endpoints delegate to the same backend logic as the CLIs (`analysis/normalize_streams.py`, `analysis/carbon.py`); `graph/positions` persists `companies.graph_x` / `graph_y`.

## Frontend (`frontend/src/`)

React (Vite) single-page app, all-inline-styles with a light/dark theme via React Context.

| Area | Contents |
|---|---|
| `components/graph/` | Cluster graph view (`ClusterGraph`, `CompanyNode`, connecting context) |
| `components/table/` | Sortable tables: companies, components, flows, streams |
| `components/detail/` | Detail panels + tabs: company, component, stream, flow, flows/streams/normalization tabs, create-flow modal |
| `components/co2/` | Carbon panel + floating action button |
| `components/layout/` | Split/left/detail panels, view toggle |
| `components/shared/` | Badge, Modal, ConfirmPopover, SortableHeader, Tabs, ToggleSwitch |
| `components/theme/` | Theme FAB |
| `hooks/` | `useCompanies`, `useFlows`, `useGraph` data hooks |
| `lib/` | `api.js` (fetch client), `ThemeContext.jsx`, `theme.js` |

## Prerequisites

- Python with `fastapi` + `uvicorn` (plus the analysis deps).
- Node.js + npm for the frontend (Vite + React).

See `README.md` for exact versions.
