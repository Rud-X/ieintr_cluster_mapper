"""
api/routes/carbon.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import sqlite3
from fastapi import APIRouter, Depends

import analysis.carbon as carbon_svc
from api.models import CarbonStatus, CarbonGap
from api.deps import get_db

router = APIRouter(prefix="/api/carbon", tags=["carbon"])


@router.get("/status", response_model=CarbonStatus)
def carbon_status(db: str = Depends(get_db)):
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    def count(q, *params):
        cur.execute(q, params)
        return cur.fetchone()[0]

    total_comp    = count("SELECT COUNT(*) FROM components")
    formula_comp  = count("SELECT COUNT(*) FROM components WHERE carbon_weight_pct IS NOT NULL AND (carbon_weight_pct_manual IS NULL OR carbon_weight_pct_manual = 0)")
    manual_comp   = count("SELECT COUNT(*) FROM components WHERE carbon_weight_pct IS NOT NULL AND carbon_weight_pct_manual = 1")
    null_comp     = count("SELECT COUNT(*) FROM components WHERE carbon_weight_pct IS NULL")
    actionable    = count("SELECT COUNT(*) FROM components WHERE carbon_weight_pct IS NULL AND needs_review = 0")
    total_streams = count("SELECT COUNT(*) FROM streams")
    with_carbon   = count("SELECT COUNT(*) FROM streams WHERE carbon_pct IS NOT NULL")
    null_carbon   = count("SELECT COUNT(*) FROM streams WHERE carbon_pct IS NULL")
    conn.close()

    return CarbonStatus(
        total_components=total_comp,
        formula_components=formula_comp,
        manual_components=manual_comp,
        null_components=null_comp,
        actionable_gaps=actionable,
        total_streams=total_streams,
        streams_with_carbon=with_carbon,
        streams_null_carbon=null_carbon,
    )


@router.post("/recalculate")
def recalculate(db: str = Depends(get_db)):
    carbon_svc.recalculate(db)
    return {"ok": True}


@router.get("/gaps", response_model=list[CarbonGap])
def list_gaps(db: str = Depends(get_db)):
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT c.component_id, c.name, c.carbon_atoms, c.molecular_weight, c.needs_review,
               COUNT(DISTINCT sc.stream_id) AS stream_count
        FROM components c
        LEFT JOIN stream_composition sc ON c.component_id = sc.component_id AND sc.is_trace = 0
        WHERE c.carbon_weight_pct IS NULL
        GROUP BY c.component_id
        ORDER BY stream_count DESC, c.component_id
    """)
    rows = cur.fetchall()
    conn.close()
    return [CarbonGap(**dict(r)) for r in rows]
