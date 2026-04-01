"""
api/routes/graph.py

Graph view endpoint. Returns nodes (companies with their streams) and edges (flows).
Also handles bulk position saves.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import sqlite3
from fastapi import APIRouter, Depends

import analysis.manage_companies as mc
from api.models import GraphView, GraphNode, GraphEdge, GraphStream, GraphPositionsBulk
from api.deps import get_db

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("", response_model=GraphView)
def get_graph(db: str = Depends(get_db)):
    companies = [c for c in mc.get_all_companies(db) if c["included"]]
    included_ids = {c["company_id"] for c in companies}
    flows = [f for f in mc.get_all_flows(db) if f["from_company_id"] in included_ids and f["to_company_id"] in included_ids]

    # Build set of stream_ids that are connected to a flow
    connected_streams = set()
    for f in flows:
        if f["from_stream_id"]:
            connected_streams.add(f["from_stream_id"])
        if f["to_stream_id"]:
            connected_streams.add(f["to_stream_id"])

    nodes = []
    for idx, company in enumerate(companies):
        cid = company["company_id"]
        streams_rows = mc.get_company_streams(cid, db)
        graph_streams = [
            GraphStream(
                stream_id=s["stream_id"],
                stream_name=s["stream_name"],
                direction=s["direction"],
                stream_type=s["stream_type"],
                flow_kton_per_year=s["flow_kton_per_year"],
                carbon_pct=s["carbon_pct"],
                connected=(s["stream_id"] in connected_streams),
            )
            for s in streams_rows
        ]
        nodes.append(GraphNode(
            id=cid,
            label=company["name"],
            sector=company["sector"],
            node_type=company["node_type"],
            included=company["included"],
            color_index=idx % 12,
            x=company["graph_x"],
            y=company["graph_y"],
            streams=graph_streams,
        ))

    edges = [
        GraphEdge(
            id=f["flow_id"],
            from_stream_id=f["from_stream_id"],
            to_stream_id=f["to_stream_id"],
            from_company_id=f["from_company_id"],
            to_company_id=f["to_company_id"],
            status=f["status"],
            flow_type=f["flow_type"],
            flow_kton_per_year=f["flow_kton_per_year"],
            notes=f["notes"],
        )
        for f in flows
    ]

    return GraphView(nodes=nodes, edges=edges)


@router.patch("/positions")
def save_positions(body: GraphPositionsBulk, db: str = Depends(get_db)):
    for company_id, pos in body.positions.items():
        x = pos.get("x")
        y = pos.get("y")
        if x is not None and y is not None:
            mc.update_company_graph_position(company_id, x, y, db)
    return {"ok": True, "updated": len(body.positions)}


@router.post("/normalization/recalculate")
def recalculate_normalization(db: str = Depends(get_db)):
    import analysis.normalize_streams as ns
    ns.normalize(db)
    return {"ok": True}
