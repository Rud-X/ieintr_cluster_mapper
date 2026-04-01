"""
api/routes/companies.py

Company and stream endpoints. All DB logic delegated to manage_companies.py.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, HTTPException, Depends

import analysis.manage_companies as mc
import analysis.normalize_streams as ns
from api.models import (
    Company, CompanyUpdate, Stream, CompositionRow,
    Flow, FlowCreate, NormalizationCandidate,
    NormalizationSetRequest, NormalizationSetpointRequest, CustomFactorRequest,
)
from api.deps import get_db

router = APIRouter(prefix="/api/companies", tags=["companies"])


def _row_to_company(row) -> Company:
    d = dict(row)
    return Company(**d)


def _row_to_stream(row, composition=None) -> Stream:
    d = dict(row)
    comp_rows = [CompositionRow(**dict(c)) for c in (composition or [])]
    # Build only the scalar fields (exclude the 'composition' list field)
    scalar_fields = {k: d.get(k) for k in Stream.model_fields if k != "composition"}
    return Stream(**scalar_fields, composition=comp_rows)


def _row_to_flow(row) -> Flow:
    return Flow(**dict(row))


@router.get("", response_model=list[Company])
def list_companies(db: str = Depends(get_db)):
    rows = mc.get_all_companies(db)
    return [_row_to_company(r) for r in rows]


@router.get("/{company_id}", response_model=Company)
def get_company(company_id: str, db: str = Depends(get_db)):
    row = mc.get_company(company_id, db)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found.")
    # Enrich with counts from get_all_companies query
    all_rows = mc.get_all_companies(db)
    for r in all_rows:
        if r["company_id"] == company_id:
            return _row_to_company(r)
    return _row_to_company(row)


@router.patch("/{company_id}", response_model=Company)
def update_company(company_id: str, body: CompanyUpdate, db: str = Depends(get_db)):
    row = mc.get_company(company_id, db)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found.")

    if body.included is not None:
        # Set directly rather than toggle, to be idempotent
        if dict(row)["included"] != body.included:
            mc.toggle_company_included(company_id, db)

    if any(v is not None for v in [body.name, body.sector, body.location]):
        mc.update_company_details(company_id, body.name, body.sector, body.location, db)

    if body.graph_x is not None or body.graph_y is not None:
        current = dict(mc.get_company(company_id, db))
        x = body.graph_x if body.graph_x is not None else current.get("graph_x")
        y = body.graph_y if body.graph_y is not None else current.get("graph_y")
        mc.update_company_graph_position(company_id, x, y, db)

    # Return updated company with counts
    all_rows = mc.get_all_companies(db)
    for r in all_rows:
        if r["company_id"] == company_id:
            return _row_to_company(r)


@router.get("/{company_id}/streams", response_model=list[Stream])
def get_company_streams(company_id: str, db: str = Depends(get_db)):
    if mc.get_company(company_id, db) is None:
        raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found.")
    rows = mc.get_company_streams(company_id, db)
    return [_row_to_stream(r) for r in rows]


@router.get("/{company_id}/flows", response_model=list[Flow])
def get_company_flows(company_id: str, db: str = Depends(get_db)):
    if mc.get_company(company_id, db) is None:
        raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found.")
    rows = mc.get_flows_for_company(company_id, db)
    return [_row_to_flow(r) for r in rows]


@router.post("/{company_id}/flows", response_model=Flow)
def create_flow(company_id: str, body: FlowCreate, db: str = Depends(get_db)):
    if mc.get_company(company_id, db) is None:
        raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found.")
    try:
        flow_id = mc.create_flow(
            body.from_stream_id,
            body.to_stream_id,
            body.from_company_id,
            body.to_company_id,
            db,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    row = mc.get_flow(flow_id, db)
    return _row_to_flow(row)


@router.get("/{company_id}/normalization", response_model=list[NormalizationCandidate])
def get_normalization_candidates(company_id: str, db: str = Depends(get_db)):
    company = mc.get_company(company_id, db)
    if company is None:
        raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found.")
    rows = mc.get_normalization_candidates(company_id, db)
    current_ref = dict(company).get("normalize_stream_id")
    return [
        NormalizationCandidate(
            stream_id=r["stream_id"],
            stream_name=r["stream_name"],
            flow_kton_per_year=r["flow_kton_per_year"],
            direction=r["direction"],
            is_current=(r["stream_id"] == current_ref),
        )
        for r in rows
    ]


@router.post("/{company_id}/normalization/set")
def set_normalization(company_id: str, body: NormalizationSetRequest, db: str = Depends(get_db)):
    ok = ns.set_reference(company_id, body.stream_id, db)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid reference stream.")
    return {"ok": True}


@router.post("/{company_id}/normalization/clear")
def clear_normalization(company_id: str, db: str = Depends(get_db)):
    ok = ns.clear_reference(company_id, db)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found.")
    return {"ok": True}


@router.post("/{company_id}/normalization/setpoint")
def set_normalization_setpoint(company_id: str, body: NormalizationSetpointRequest, db: str = Depends(get_db)):
    mc.set_normalize_setpoint(company_id, body.setpoint, db)
    ns.normalize(db)
    return {"ok": True}


@router.post("/{company_id}/normalization/custom-factor")
def set_custom_factor(company_id: str, body: CustomFactorRequest, db: str = Depends(get_db)):
    if body.value <= 0:
        raise HTTPException(status_code=400, detail="Scaling factor must be > 0.")
    mc.set_custom_scaling_factor(company_id, body.value, db)
    ns.normalize(db)
    return {"ok": True}


@router.delete("/{company_id}/normalization/custom-factor")
def clear_custom_factor(company_id: str, db: str = Depends(get_db)):
    mc.clear_custom_scaling_factor(company_id, db)
    ns.normalize(db)
    return {"ok": True}
