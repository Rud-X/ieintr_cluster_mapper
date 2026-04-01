"""
api/routes/flows.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, HTTPException, Depends

import analysis.manage_companies as mc
from api.models import Flow, FlowUpdate
from api.deps import get_db

router = APIRouter(prefix="/api/flows", tags=["flows"])


def _row_to_flow(row) -> Flow:
    return Flow(**dict(row))


@router.get("", response_model=list[Flow])
def list_flows(db: str = Depends(get_db)):
    return [_row_to_flow(r) for r in mc.get_all_flows(db)]


@router.get("/{flow_id}", response_model=Flow)
def get_flow(flow_id: str, db: str = Depends(get_db)):
    row = mc.get_flow(flow_id, db)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found.")
    return _row_to_flow(row)


@router.patch("/{flow_id}", response_model=Flow)
def update_flow(flow_id: str, body: FlowUpdate, db: str = Depends(get_db)):
    if mc.get_flow(flow_id, db) is None:
        raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found.")
    if body.status is not None:
        try:
            mc.update_flow_status(flow_id, body.status, db)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    if body.notes is not None:
        mc.update_flow_notes(flow_id, body.notes, db)
    if body.flow_kton_per_year is not None:
        mc.update_flow_quantity(flow_id, body.flow_kton_per_year, db)
    row = mc.get_flow(flow_id, db)
    return _row_to_flow(row)


@router.delete("/{flow_id}")
def delete_flow(flow_id: str, db: str = Depends(get_db)):
    if mc.get_flow(flow_id, db) is None:
        raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found.")
    mc.delete_flow(flow_id, db)
    return {"ok": True}
