"""
api/routes/components.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, HTTPException, Depends

import analysis.manage_companies as mc
import analysis.carbon as carbon
from api.models import Component, ComponentUpdate
from api.deps import get_db

router = APIRouter(prefix="/api/components", tags=["components"])


def _row_to_component(row) -> Component:
    return Component(**dict(row))


@router.get("", response_model=list[Component])
def list_components(db: str = Depends(get_db)):
    rows = mc.get_all_components(db)
    return [_row_to_component(r) for r in rows]


@router.get("/{component_id}", response_model=Component)
def get_component(component_id: str, db: str = Depends(get_db)):
    import sqlite3
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM components WHERE component_id = ?", (component_id,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Component '{component_id}' not found.")
    return _row_to_component(row)


@router.patch("/{component_id}", response_model=Component)
def update_component(component_id: str, body: ComponentUpdate, db: str = Depends(get_db)):
    import sqlite3
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM components WHERE component_id = ?", (component_id,))
    if cur.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Component '{component_id}' not found.")
    conn.close()

    carbon.set_component(
        component_id=component_id,
        carbon_atoms=body.carbon_atoms,
        molecular_weight=body.molecular_weight,
        carbon_pct=body.carbon_pct,
        clear_override=body.clear_override or False,
        db_path=db,
    )

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM components WHERE component_id = ?", (component_id,))
    row = cur.fetchone()
    conn.close()
    return _row_to_component(row)
