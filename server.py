"""
server.py

FastAPI entry point for the Industrial Cluster web app.

Usage:
    python server.py                        # default DB
    python server.py --db path/to/other.db  # custom DB
    python server.py --port 8001            # custom port

Frontend (production): served from frontend/dist/
Frontend (development): run `cd frontend && npm run dev` (proxies /api to this server)
"""

import argparse
import os
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Make analysis/ importable from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from api.deps import set_db_path
from api.routes import companies, flows, streams, components, carbon, graph, normalization

app = FastAPI(title="Industrial Cluster Analysis", version="1.0.0")

# Allow the Vite dev server to proxy requests during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers
app.include_router(companies.router)
app.include_router(flows.router)
app.include_router(streams.router)
app.include_router(components.router)
app.include_router(carbon.router)
app.include_router(graph.router)
app.include_router(normalization.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve built frontend (only if dist/ exists)
_frontend_dist = Path(__file__).parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Industrial Cluster web server.")
    parser.add_argument("--db", default="industrial_cluster.db", help="Path to SQLite database.")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to.")
    args = parser.parse_args()

    set_db_path(args.db)
    uvicorn.run("server:app", host=args.host, port=args.port, reload=True)
