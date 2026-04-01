"""
api/routes/normalization.py

Cluster-level normalization endpoint.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, Depends

import analysis.normalize_streams as ns
from api.deps import get_db

router = APIRouter(prefix="/api/normalization", tags=["normalization"])


@router.post("/recalculate")
def recalculate(db: str = Depends(get_db)):
    ns.normalize(db)
    return {"ok": True}
