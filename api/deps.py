"""
api/deps.py

FastAPI dependencies shared across routes.
"""

import os

_DB_PATH = os.environ.get("CLUSTER_DB", "industrial_cluster.db")


def get_db() -> str:
    """Returns the database path. Override via CLUSTER_DB env var or set_db_path()."""
    return _DB_PATH


def set_db_path(path: str) -> None:
    """Called from server.py to set the DB path from CLI args."""
    global _DB_PATH
    _DB_PATH = path
