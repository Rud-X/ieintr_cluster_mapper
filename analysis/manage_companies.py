"""
manage_companies.py

Pure database logic for company management and flow creation.
No TUI / questionary imports. All functions return data or raise on error.

Functions:
  get_all_companies(db_path)              — all companies/nodes with counts
  get_company(company_id, db_path)        — single company row or None
  get_external_nodes(db_path, node_types) — external nodes by type (import_source, etc.)
  get_company_streams(company_id, db_path)— all streams for a company
  get_stream(stream_id, db_path)          — single stream row or None
  get_stream_composition(stream_id, db_path) — composition rows for a stream
  get_company_metadata_header(company_id, db_path) — dict of display metadata
  get_normalization_candidates(company_id, db_path) — output streams eligible as reference
  get_other_companies(exclude_company_id, db_path)  — all companies/nodes except one
  get_streams_by_direction(company_id, direction, db_path) — direction-filtered streams
  get_company_flow_counts(company_id, db_path) — flow/unconnected-stream counts
  get_all_flows(db_path)                  — all flows joined with company/stream names
  get_flows_for_company(company_id, db_path) — flows filtered to one company (either side)
  get_flow(flow_id, db_path)              — single flow with joined names
  next_company_id(db_path)               — next available C-prefixed ID
  next_flow_id(db_path)                  — next available F-prefixed ID
  add_company(name, db_path, node_type)  — insert new company/node, return company_id
  add_external_node(name, node_type, db_path) — insert an external node, return company_id
  delete_company(company_id, db_path)   — delete company if no streams/flows attached
  create_flow(from_stream_id, to_stream_id, from_company_id, to_company_id, db_path)
                                         — insert new flow, return flow_id
  update_flow_from_stream(flow_id, new_from_stream_id, new_from_company_id, db_path)
                                         — update outflow side of an existing flow
  update_flow_to_stream(flow_id, new_to_stream_id, new_to_company_id, db_path)
                                         — update inflow side of an existing flow
  delete_flow(flow_id, db_path)          — delete a flow by ID
  toggle_company_included(company_id, db_path) — flip included 0↔1, return new value
"""

import re
import sqlite3

DB_PATH = "industrial_cluster.db"


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Data queries
# ---------------------------------------------------------------------------

def get_all_companies(db_path: str = DB_PATH) -> list:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT c.company_id, c.name, c.sector, c.included, c.node_type,
               c.normalize_stream_id, c.scaling_factor, c.normalize_setpoint,
               COUNT(s.stream_id) AS stream_count,
               (SELECT COUNT(*) FROM flows f
                WHERE f.from_company_id = c.company_id
                   OR f.to_company_id   = c.company_id) AS flow_count,
               (SELECT COUNT(DISTINCT sid) FROM (
                    SELECT from_stream_id AS sid FROM flows
                    WHERE from_company_id = c.company_id
                    UNION
                    SELECT to_stream_id AS sid FROM flows
                    WHERE to_company_id = c.company_id)) AS streams_in_flows
        FROM companies c
        LEFT JOIN streams s ON s.company_id = c.company_id
        GROUP BY c.company_id
        ORDER BY c.node_type, c.company_id
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_external_nodes(
    db_path: str = DB_PATH,
    node_types: list = None,
    exclude_company_id: str = None,
) -> list:
    """Return external node rows (import_source, export_sink, waste_facility).

    node_types: list of node_type values to filter to; None = all external types.
    exclude_company_id: optional company_id to exclude from results.
    """
    conn = _connect(db_path)
    cur = conn.cursor()
    valid_external = ("import_source", "export_sink", "waste_facility")
    types = node_types if node_types else list(valid_external)

    placeholders = ",".join("?" * len(types))
    params = list(types)

    if exclude_company_id:
        cur.execute(
            f"SELECT company_id, name, sector, node_type FROM companies"
            f" WHERE node_type IN ({placeholders}) AND company_id != ?"
            f" ORDER BY node_type, company_id",
            params + [exclude_company_id],
        )
    else:
        cur.execute(
            f"SELECT company_id, name, sector, node_type FROM companies"
            f" WHERE node_type IN ({placeholders})"
            f" ORDER BY node_type, company_id",
            params,
        )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_company(company_id: str, db_path: str = DB_PATH):
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM companies WHERE company_id = ?", (company_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_company_streams(company_id: str, db_path: str = DB_PATH) -> list:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM streams
        WHERE company_id = ?
        ORDER BY direction, stream_id
    """, (company_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_stream(stream_id: str, db_path: str = DB_PATH):
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM streams WHERE stream_id = ?", (stream_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_stream_composition(stream_id: str, db_path: str = DB_PATH) -> list:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT sc.component_id, c.name, sc.fraction, sc.is_trace, sc.carbon_fraction
        FROM stream_composition sc
        JOIN components c ON c.component_id = sc.component_id
        WHERE sc.stream_id = ?
        ORDER BY sc.fraction DESC NULLS LAST
    """, (stream_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_company_metadata_header(company_id: str, db_path: str = DB_PATH) -> dict:
    """Return a dict with stream/flow counts and normalization info for the header display."""
    conn = _connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT * FROM companies WHERE company_id = ?", (company_id,))
    company = cur.fetchone()
    if company is None:
        conn.close()
        return {}

    cur.execute("""
        SELECT stream_type, direction, COUNT(*) AS n
        FROM streams
        WHERE company_id = ?
        GROUP BY stream_type, direction
    """, (company_id,))
    type_counts = {(r["stream_type"], r["direction"]): r["n"] for r in cur.fetchall()}

    n_input   = sum(v for (st, d), v in type_counts.items() if d == "input")
    n_waste   = type_counts.get(("waste",   "output"), 0)
    n_product = type_counts.get(("product", "output"), 0)

    cur.execute("""
        SELECT COUNT(*) AS n FROM flows
        WHERE from_company_id = ? OR to_company_id = ?
    """, (company_id, company_id))
    n_flows = cur.fetchone()["n"]

    norm_stream_id   = company["normalize_stream_id"]
    norm_stream_name = None
    norm_factor      = None
    if norm_stream_id:
        cur.execute(
            "SELECT stream_name, flow_kton_per_year FROM streams WHERE stream_id = ?",
            (norm_stream_id,),
        )
        ref = cur.fetchone()
        if ref:
            norm_stream_name = ref["stream_name"]
            if ref["flow_kton_per_year"] and ref["flow_kton_per_year"] > 0:
                norm_factor = ref["flow_kton_per_year"]

    conn.close()
    return {
        "company_name":       company["name"],
        "n_input":            n_input,
        "n_waste":            n_waste,
        "n_product":          n_product,
        "n_flows":            n_flows,
        "normalize_stream_id":   norm_stream_id,
        "normalize_stream_name": norm_stream_name,
        "norm_factor":           norm_factor,
        "included":              company["included"],
    }


def get_normalization_candidates(company_id: str, db_path: str = DB_PATH) -> list:
    """Return output streams with flow > 0 eligible as normalization reference."""
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT stream_id, stream_name, flow_kton_per_year
        FROM streams
        WHERE company_id = ? AND direction = 'output' AND flow_kton_per_year > 0
        ORDER BY flow_kton_per_year DESC
    """, (company_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_other_companies(exclude_company_id: str, db_path: str = DB_PATH) -> list:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT company_id, name, sector, node_type
        FROM companies
        WHERE company_id != ?
        ORDER BY node_type, company_id
    """, (exclude_company_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_streams_by_direction(company_id: str, direction: str, db_path: str = DB_PATH) -> list:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM streams
        WHERE company_id = ? AND direction = ?
        ORDER BY stream_id
    """, (company_id, direction))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_company_flow_counts(company_id: str, db_path: str = DB_PATH) -> dict:
    """Return total flows involving this company, and count of unconnected streams."""
    conn = _connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) AS n FROM flows
        WHERE from_company_id = ? OR to_company_id = ?
    """, (company_id, company_id))
    total_flows = cur.fetchone()["n"]

    cur.execute("""
        SELECT COUNT(*) AS n FROM streams
        WHERE company_id = ?
          AND stream_id NOT IN (
              SELECT from_stream_id FROM flows WHERE from_stream_id IS NOT NULL
              UNION
              SELECT to_stream_id   FROM flows WHERE to_stream_id   IS NOT NULL
          )
    """, (company_id,))
    unconnected = cur.fetchone()["n"]

    conn.close()
    return {"total_flows": total_flows, "unconnected_streams": unconnected}


# ---------------------------------------------------------------------------
# Flow queries
# ---------------------------------------------------------------------------

_FLOWS_JOIN = """
    SELECT f.flow_id, f.status, f.flow_type, f.flow_kton_per_year, f.notes,
           f.from_company_id, fc.name AS from_company_name,
                              fc.node_type AS from_node_type,
           f.from_stream_id,  fs.stream_name AS from_stream_name,
                               fs.direction  AS from_direction,
           f.to_company_id,   tc.name AS to_company_name,
                              tc.node_type AS to_node_type,
           f.to_stream_id,    ts.stream_name AS to_stream_name,
                               ts.direction  AS to_direction
    FROM flows f
    JOIN      companies fc ON fc.company_id = f.from_company_id
    JOIN      companies tc ON tc.company_id = f.to_company_id
    LEFT JOIN streams   fs ON fs.stream_id  = f.from_stream_id
    LEFT JOIN streams   ts ON ts.stream_id  = f.to_stream_id
"""


def get_all_flows(db_path: str = DB_PATH) -> list:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(_FLOWS_JOIN + " ORDER BY f.flow_id")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_flows_for_company(company_id: str, db_path: str = DB_PATH) -> list:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        _FLOWS_JOIN + " WHERE f.from_company_id = ? OR f.to_company_id = ? ORDER BY f.flow_id",
        (company_id, company_id),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_flows_for_stream(stream_id: str, db_path: str = DB_PATH) -> list:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        _FLOWS_JOIN + " WHERE f.from_stream_id = ? OR f.to_stream_id = ? ORDER BY f.flow_id",
        (stream_id, stream_id),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_flow(flow_id: str, db_path: str = DB_PATH):
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(_FLOWS_JOIN + " WHERE f.flow_id = ?", (flow_id,))
    row = cur.fetchone()
    conn.close()
    return row


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def next_company_id(db_path: str = DB_PATH) -> str:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT company_id FROM companies ORDER BY company_id")
    ids = [r["company_id"] for r in cur.fetchall()]
    conn.close()

    numeric = [int(m.group(1)) for cid in ids if (m := re.fullmatch(r"C(\d+)", cid))]
    n = max(numeric, default=0)
    return f"C{n + 1:03d}"


def next_flow_id(db_path: str = DB_PATH) -> str:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT flow_id FROM flows ORDER BY flow_id")
    ids = [r["flow_id"] for r in cur.fetchall()]
    conn.close()

    numeric = [int(m.group(1)) for fid in ids if (m := re.fullmatch(r"F(\d+)", fid))]
    n = max(numeric, default=0)
    return f"F{n + 1:03d}"


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------

VALID_NODE_TYPES = ("company", "import_source", "export_sink", "waste_facility")


def add_company(name: str, db_path: str = DB_PATH, node_type: str = "company") -> str:
    """Insert a new company or external node with the given name. Returns the new company_id."""
    name = name.strip()
    if not name:
        raise ValueError("Company name cannot be blank.")
    if node_type not in VALID_NODE_TYPES:
        raise ValueError(f"node_type must be one of {VALID_NODE_TYPES}.")

    company_id = next_company_id(db_path)
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO companies (company_id, name, included, node_type) VALUES (?, ?, 1, ?)",
        (company_id, name, node_type),
    )
    conn.commit()
    conn.close()
    return company_id


def add_external_node(name: str, node_type: str, db_path: str = DB_PATH) -> str:
    """Insert a new external node (import_source, export_sink, or waste_facility).
    Returns the new company_id."""
    if node_type not in ("import_source", "export_sink", "waste_facility"):
        raise ValueError(
            "node_type must be one of: 'import_source', 'export_sink', 'waste_facility'."
        )
    return add_company(name, db_path=db_path, node_type=node_type)


def _derive_flow_type(from_node_type: str, to_node_type: str) -> str:
    """Determine flow_type from the node types of both endpoints."""
    if from_node_type == "import_source":
        return "import"
    if to_node_type == "export_sink":
        return "export"
    if to_node_type == "waste_facility":
        return "waste_to_wmf"
    return "internal"


def create_flow(
    from_stream_id,   # str or None (None for import_source endpoints)
    to_stream_id,     # str or None (None for export_sink / waste_facility endpoints)
    from_company_id: str,
    to_company_id: str,
    db_path: str = DB_PATH,
) -> str:
    """
    Insert a new candidate flow.

    from_stream_id / to_stream_id may be None when an endpoint is an external node
    (import_source, export_sink, or waste_facility). flow_type is auto-derived from
    the node types of the two companies.

    Raises ValueError if an identical flow already exists.
    Returns the new flow_id.
    """
    conn = _connect(db_path)
    cur = conn.cursor()

    # Duplicate check — use IS operator so NULL == NULL correctly
    cur.execute(
        """SELECT flow_id FROM flows
           WHERE from_company_id = ? AND to_company_id = ?
             AND from_stream_id IS ? AND to_stream_id IS ?""",
        (from_company_id, to_company_id, from_stream_id, to_stream_id),
    )
    if cur.fetchone():
        conn.close()
        raise ValueError(
            f"A flow from {from_company_id}/{from_stream_id} to "
            f"{to_company_id}/{to_stream_id} already exists."
        )

    # Auto-derive flow_type from node types
    cur.execute(
        "SELECT node_type FROM companies WHERE company_id = ?", (from_company_id,)
    )
    row = cur.fetchone()
    from_node_type = row["node_type"] if row else "company"
    cur.execute(
        "SELECT node_type FROM companies WHERE company_id = ?", (to_company_id,)
    )
    row = cur.fetchone()
    to_node_type = row["node_type"] if row else "company"
    flow_type = _derive_flow_type(from_node_type, to_node_type)

    flow_id = next_flow_id(db_path)
    cur.execute(
        """INSERT INTO flows
           (flow_id, from_company_id, to_company_id, from_stream_id, to_stream_id,
            flow_kton_per_year, flow_type, status)
           VALUES (?, ?, ?, ?, ?, NULL, ?, 'candidate')""",
        (flow_id, from_company_id, to_company_id, from_stream_id, to_stream_id, flow_type),
    )
    conn.commit()
    conn.close()
    return flow_id


def update_flow_from_stream(
    flow_id: str,
    new_from_stream_id: str,
    new_from_company_id: str,
    db_path: str = DB_PATH,
) -> None:
    """Replace the outflow (source) side of an existing flow. Keeps flow_id unchanged."""
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE flows SET from_stream_id = ?, from_company_id = ? WHERE flow_id = ?",
        (new_from_stream_id, new_from_company_id, flow_id),
    )
    conn.commit()
    conn.close()


def update_flow_to_stream(
    flow_id: str,
    new_to_stream_id: str,
    new_to_company_id: str,
    db_path: str = DB_PATH,
) -> None:
    """Replace the inflow (destination) side of an existing flow. Keeps flow_id unchanged."""
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE flows SET to_stream_id = ?, to_company_id = ? WHERE flow_id = ?",
        (new_to_stream_id, new_to_company_id, flow_id),
    )
    conn.commit()
    conn.close()


def delete_company(company_id: str, db_path: str = DB_PATH) -> None:
    """Delete a company or external node by ID.

    Raises ValueError if the company has any associated streams or flows —
    those must be removed first.
    """
    conn = _connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT name FROM companies WHERE company_id = ?", (company_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"Company '{company_id}' not found.")

    cur.execute("SELECT COUNT(*) FROM streams WHERE company_id = ?", (company_id,))
    n_streams = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM flows WHERE from_company_id = ? OR to_company_id = ?",
        (company_id, company_id),
    )
    n_flows = cur.fetchone()[0]

    if n_streams > 0 or n_flows > 0:
        conn.close()
        parts = []
        if n_streams:
            parts.append(f"{n_streams} stream{'s' if n_streams != 1 else ''}")
        if n_flows:
            parts.append(f"{n_flows} flow{'s' if n_flows != 1 else ''}")
        raise ValueError(
            f"Cannot delete '{row['name']}': {' and '.join(parts)} attached. "
            "Remove them first."
        )

    cur.execute("DELETE FROM companies WHERE company_id = ?", (company_id,))
    conn.commit()
    conn.close()


def delete_flow(flow_id: str, db_path: str = DB_PATH) -> None:
    """Delete a flow by ID."""
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM flows WHERE flow_id = ?", (flow_id,))
    conn.commit()
    conn.close()


def set_normalize_setpoint(company_id: str, setpoint: float, db_path: str = DB_PATH) -> None:
    """Set the normalization setpoint (target scaled value) for a company."""
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE companies SET normalize_setpoint = ? WHERE company_id = ?",
        (setpoint, company_id),
    )
    conn.commit()
    conn.close()


def toggle_company_included(company_id: str, db_path: str = DB_PATH) -> int:
    """Flip included 0↔1 for a company. Returns the new value."""
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE companies SET included = 1 - included WHERE company_id = ?",
        (company_id,),
    )
    conn.commit()
    cur.execute("SELECT included FROM companies WHERE company_id = ?", (company_id,))
    new_value = cur.fetchone()["included"]
    conn.close()
    return new_value
