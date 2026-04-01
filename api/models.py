"""
api/models.py

Pydantic schemas — the stable contract between backend and frontend.
These are domain objects, not raw DB rows. Routes serialize sqlite3.Row
results through these models before returning them.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------

class Component(BaseModel):
    component_id: str
    name: str
    aliases: Optional[str] = None
    category: Optional[str] = None
    cas_number: Optional[str] = None
    molecular_weight: Optional[float] = None
    carbon_atoms: Optional[int] = None
    carbon_weight_pct: Optional[float] = None
    carbon_weight_pct_manual: Optional[int] = None
    hazardous: Optional[int] = None
    needs_review: Optional[int] = None
    notes: Optional[str] = None


class ComponentUpdate(BaseModel):
    carbon_atoms: Optional[int] = None
    molecular_weight: Optional[float] = None
    carbon_pct: Optional[float] = None
    clear_override: Optional[bool] = None


# ---------------------------------------------------------------------------
# Stream composition
# ---------------------------------------------------------------------------

class CompositionRow(BaseModel):
    component_id: str
    name: str
    fraction: Optional[float] = None
    is_trace: int
    carbon_fraction: Optional[float] = None


# ---------------------------------------------------------------------------
# Streams
# ---------------------------------------------------------------------------

class Stream(BaseModel):
    stream_id: str
    company_id: str
    company_name: Optional[str] = None
    stream_name: str
    stream_type: Optional[str] = None
    direction: str
    flow_kton_per_year: Optional[float] = None
    norm_flow_kton_per_year: Optional[float] = None
    temperature_c: Optional[float] = None
    pressure_bar: Optional[float] = None
    composition_raw: Optional[str] = None
    carbon_pct: Optional[float] = None
    carbon_pct_complete: Optional[int] = None
    notes: Optional[str] = None
    composition: list[CompositionRow] = []


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------

class Company(BaseModel):
    company_id: str
    name: str
    sector: Optional[str] = None
    location: Optional[str] = None
    node_type: str
    scaling_factor: Optional[float] = None
    scaling_factor_manual: Optional[int] = None
    normalize_setpoint: Optional[float] = None
    included: int
    normalize_stream_id: Optional[str] = None
    stream_count: Optional[int] = None
    flow_count: Optional[int] = None
    streams_in_flows: Optional[int] = None
    graph_x: Optional[float] = None
    graph_y: Optional[float] = None


class CompanyUpdate(BaseModel):
    included: Optional[int] = None
    name: Optional[str] = None
    sector: Optional[str] = None
    location: Optional[str] = None
    graph_x: Optional[float] = None
    graph_y: Optional[float] = None


class GraphPositionsBulk(BaseModel):
    positions: dict[str, dict]  # {company_id: {x: float, y: float}}


# ---------------------------------------------------------------------------
# Flows
# ---------------------------------------------------------------------------

class Flow(BaseModel):
    flow_id: str
    status: str
    flow_type: Optional[str] = None
    flow_kton_per_year: Optional[float] = None
    notes: Optional[str] = None
    from_company_id: str
    from_company_name: Optional[str] = None
    from_node_type: Optional[str] = None
    from_stream_id: Optional[str] = None
    from_stream_name: Optional[str] = None
    from_direction: Optional[str] = None
    to_company_id: str
    to_company_name: Optional[str] = None
    to_node_type: Optional[str] = None
    to_stream_id: Optional[str] = None
    to_stream_name: Optional[str] = None
    to_direction: Optional[str] = None


class FlowCreate(BaseModel):
    from_stream_id: Optional[str] = None
    to_stream_id: Optional[str] = None
    from_company_id: str
    to_company_id: str


class FlowUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    flow_kton_per_year: Optional[float] = None


# ---------------------------------------------------------------------------
# Graph view
# ---------------------------------------------------------------------------

class GraphStream(BaseModel):
    stream_id: str
    stream_name: str
    direction: str
    stream_type: Optional[str] = None
    flow_kton_per_year: Optional[float] = None
    carbon_pct: Optional[float] = None
    connected: bool  # True if this stream is part of any flow


class GraphNode(BaseModel):
    id: str           # company_id
    label: str        # company name
    sector: Optional[str] = None
    node_type: str
    included: int
    color_index: int  # index into COMPANY_COLORS on the frontend
    x: Optional[float] = None
    y: Optional[float] = None
    streams: list[GraphStream] = []


class GraphEdge(BaseModel):
    id: str           # flow_id
    from_stream_id: Optional[str] = None
    to_stream_id: Optional[str] = None
    from_company_id: str
    to_company_id: str
    status: str
    flow_type: Optional[str] = None
    flow_kton_per_year: Optional[float] = None
    notes: Optional[str] = None


class GraphView(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# ---------------------------------------------------------------------------
# Carbon
# ---------------------------------------------------------------------------

class CarbonStatus(BaseModel):
    total_components: int
    formula_components: int
    manual_components: int
    null_components: int
    actionable_gaps: int
    total_streams: int
    streams_with_carbon: int
    streams_null_carbon: int


class CarbonGap(BaseModel):
    component_id: str
    name: str
    carbon_atoms: Optional[int] = None
    molecular_weight: Optional[float] = None
    needs_review: int
    stream_count: int


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

class NormalizationCandidate(BaseModel):
    stream_id: str
    stream_name: str
    flow_kton_per_year: float
    direction: str
    is_current: bool


class NormalizationSetRequest(BaseModel):
    stream_id: str


class NormalizationSetpointRequest(BaseModel):
    setpoint: float


class CustomFactorRequest(BaseModel):
    value: float
