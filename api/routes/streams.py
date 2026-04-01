"""
api/routes/streams.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, HTTPException, Depends

import analysis.manage_companies as mc
from api.models import Stream, CompositionRow
from api.deps import get_db

router = APIRouter(prefix="/api/streams", tags=["streams"])


def _row_to_stream(row, composition=None) -> Stream:
    d = dict(row)
    comp_rows = [CompositionRow(**dict(c)) for c in (composition or [])]
    scalar_fields = {k: d.get(k) for k in Stream.model_fields if k != "composition"}
    return Stream(**scalar_fields, composition=comp_rows)


@router.get("", response_model=list[Stream])
def list_streams(db: str = Depends(get_db)):
    rows = mc.get_all_streams(db)
    return [_row_to_stream(r) for r in rows]


@router.get("/{stream_id}", response_model=Stream)
def get_stream(stream_id: str, db: str = Depends(get_db)):
    stream, composition = mc.get_stream_with_composition(stream_id, db)
    if stream is None:
        raise HTTPException(status_code=404, detail=f"Stream '{stream_id}' not found.")
    return _row_to_stream(stream, composition)
