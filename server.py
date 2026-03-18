"""
server.py — FastAPI backend for the Industrial Symbiosis Matcher.

Startup:
    cd project/
    python server.py
    → serves at http://localhost:8000

API:
    GET    /api/data
    PUT    /api/companies/{company_id}
    POST   /api/flows
    PUT    /api/flows/{flow_id}
    DELETE /api/flows/{flow_id}

Static files served from frontend/dist/ at /.
"""

import argparse
import sqlite3
import sys
import os
from contextlib import contextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# ── Import scoring logic from analysis/ ──────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "analysis"))
from match_candidates import (  # noqa: E402
    load_streams_with_composition,
    compute_candidates,
)

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_DB = os.path.join(os.path.dirname(__file__), "industrial_cluster.db")
MIN_SCORE = 0.15

app = FastAPI(title="Industrial Symbiosis Matcher")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB path is set at startup (see __main__ / lifespan)
_db_path: str = DEFAULT_DB


@contextmanager
def get_db():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ── Pydantic models ───────────────────────────────────────────────────────────

class CompanyUpdate(BaseModel):
    scaling_factor: Optional[float] = None
    included: Optional[int] = None


class FlowCreate(BaseModel):
    from_company_id: str
    to_company_id: str
    from_stream_id: str
    to_stream_id: str
    flow_kton_per_year: float
    status: str = "candidate"
    notes: str = ""


class FlowUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    flow_kton_per_year: Optional[float] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_companies(cur) -> list[dict]:
    cur.execute(
        "SELECT company_id, name, sector, location, scaling_factor, included "
        "FROM companies"
    )
    return [dict(r) for r in cur.fetchall()]


def load_flows(cur) -> list[dict]:
    cur.execute(
        "SELECT flow_id, from_company_id, to_company_id, "
        "from_stream_id, to_stream_id, flow_kton_per_year, status, notes "
        "FROM flows"
    )
    return [dict(r) for r in cur.fetchall()]


def next_flow_id(cur) -> str:
    cur.execute("SELECT flow_id FROM flows ORDER BY flow_id")
    existing = [r[0] for r in cur.fetchall()]
    n = 1
    while True:
        fid = f"F{n:03d}"
        if fid not in existing:
            return fid
        n += 1


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/data")
def get_data():
    with get_db() as conn:
        cur = conn.cursor()

        all_companies = load_companies(cur)

        # Compute candidates across ALL companies — the frontend filters by
        # active (included) set client-side, so toggling a company on/off
        # never requires a re-fetch of the full dataset.
        all_streams = load_streams_with_composition(cur)
        candidates = compute_candidates(all_streams, min_score=MIN_SCORE)
        flows = load_flows(cur)

    unique_pairs = len({
        (c["from_company_id"], c["to_company_id"]) for c in candidates
    })

    return {
        "metadata": {
            "total_companies": len(all_companies),
            "total_streams": len(all_streams),
            "total_candidates": len(candidates),
            "unique_company_pairs": unique_pairs,
            "min_score_threshold": MIN_SCORE,
        },
        "companies": all_companies,
        "streams": list(all_streams.values()),
        "candidates": candidates,
        "flows": flows,
    }


@app.put("/api/companies/{company_id}")
def update_company(company_id: str, body: CompanyUpdate):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT company_id FROM companies WHERE company_id = ?", (company_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Company not found")

        updates = {}
        if body.scaling_factor is not None:
            updates["scaling_factor"] = body.scaling_factor
        if body.included is not None:
            updates["included"] = body.included

        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [company_id]
            cur.execute(f"UPDATE companies SET {set_clause} WHERE company_id = ?", values)
            conn.commit()

        cur.execute(
            "SELECT company_id, name, sector, location, scaling_factor, included "
            "FROM companies WHERE company_id = ?",
            (company_id,),
        )
        return dict(cur.fetchone())


@app.post("/api/flows", status_code=201)
def create_flow(body: FlowCreate):
    with get_db() as conn:
        cur = conn.cursor()
        flow_id = next_flow_id(cur)
        cur.execute(
            "INSERT INTO flows (flow_id, from_company_id, to_company_id, "
            "from_stream_id, to_stream_id, flow_kton_per_year, status, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                flow_id,
                body.from_company_id,
                body.to_company_id,
                body.from_stream_id,
                body.to_stream_id,
                body.flow_kton_per_year,
                body.status,
                body.notes,
            ),
        )
        conn.commit()
        cur.execute("SELECT * FROM flows WHERE flow_id = ?", (flow_id,))
        return dict(cur.fetchone())


@app.put("/api/flows/{flow_id}")
def update_flow(flow_id: str, body: FlowUpdate):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT flow_id FROM flows WHERE flow_id = ?", (flow_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Flow not found")

        updates = {}
        if body.status is not None:
            updates["status"] = body.status
        if body.notes is not None:
            updates["notes"] = body.notes
        if body.flow_kton_per_year is not None:
            updates["flow_kton_per_year"] = body.flow_kton_per_year

        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [flow_id]
            cur.execute(f"UPDATE flows SET {set_clause} WHERE flow_id = ?", values)
            conn.commit()

        cur.execute("SELECT * FROM flows WHERE flow_id = ?", (flow_id,))
        return dict(cur.fetchone())


@app.delete("/api/flows/{flow_id}")
def delete_flow(flow_id: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT flow_id FROM flows WHERE flow_id = ?", (flow_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Flow not found")
        cur.execute("DELETE FROM flows WHERE flow_id = ?", (flow_id,))
        conn.commit()
    return {"deleted": True}


# ── Static files (frontend build) ────────────────────────────────────────────
_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="static")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DEFAULT_DB, help="Path to SQLite database")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    _db_path = args.db
    uvicorn.run(app, host=args.host, port=args.port)
