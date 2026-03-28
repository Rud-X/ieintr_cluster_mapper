"""
seed_manual_companies.py — Declarative seeding for manually-managed companies.

extract.py wipes the database on every full rebuild. This script re-applies
manual additions idempotently after extraction, using the same pattern as
correct_components.py.

Two seed types:

  ExternalNode — ensures a named external node (import_source, export_sink,
                 waste_facility) exists in the companies table.

  CompanyMeta  — updates non-null metadata fields (sector, location, included)
                 on a company matched by exact name.

Both are matched by name, not by auto-generated ID, so they survive re-extraction
even when company IDs shift.

Workflow for external nodes:
  1. Add the node via the TUI (+ Add External Node)
  2. Add a matching ExternalNode(...) line to SEEDS below
  3. The node now survives full re-extractions
  When deleting the node via the TUI, also remove its ExternalNode(...) line here.

Usage:
    python migrations/seed_manual_companies.py [--db PATH] [--dry-run]

  --dry-run  Print what would be changed without modifying the database.
"""

import argparse
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DB_PATH = "industrial_cluster.db"

VALID_EXTERNAL_TYPES = ("import_source", "export_sink", "waste_facility")


# ---------------------------------------------------------------------------
# Seed types
# ---------------------------------------------------------------------------

@dataclass
class ExternalNode:
    """Ensure an external node with the given name and type exists.

    If absent: inserted with the next available C-prefixed ID.
    If present with matching node_type: skipped (idempotent).
    If present with wrong node_type: warning printed, nothing changed.

    sector and location are set on insertion only (not overwritten on re-run).
    """
    name: str
    node_type: str   # 'import_source', 'export_sink', or 'waste_facility'
    sector: Optional[str]   = field(default=None)
    location: Optional[str] = field(default=None)


@dataclass
class CompanyMeta:
    """Update metadata fields on an existing company matched by exact name.

    Only non-None fields are written; None means "leave unchanged".
    If no company with this name exists, a warning is printed and the entry is skipped.
    """
    name: str
    sector:   Optional[str] = field(default=None)
    location: Optional[str] = field(default=None)
    included: Optional[int] = field(default=None)  # 1 or 0


# ---------------------------------------------------------------------------
# SEEDS — edit this list to declare your manual companies
# ---------------------------------------------------------------------------

SEEDS = [
    # Add one ExternalNode(...) line for each external node you have created via the TUI.
    # Remove the line when you delete the node via the TUI.
    # Examples (uncomment and edit):
    #
    # ExternalNode("Iron Ore Supplier X",   "import_source"),
    # ExternalNode("Veolia Metals",         "waste_facility"),
    # ExternalNode("European Steel Market", "export_sink"),
    #
    # Use CompanyMeta to preserve sector/location for companies extracted from CSV:
    #
    # CompanyMeta("Hydrogen Plant",    sector="Energy",    location="Zone A"),
    # CompanyMeta("Solid Waste Management", included=0),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _next_company_id(cur: sqlite3.Cursor) -> str:
    """Return the next available C-prefixed company ID."""
    rows = cur.execute("SELECT company_id FROM companies ORDER BY company_id").fetchall()
    ids  = [r[0] for r in rows]
    nums = [int(m.group(1)) for cid in ids if (m := re.fullmatch(r"C(\d+)", cid))]
    return f"C{max(nums, default=0) + 1:03d}"


def _apply_external_node(cur: sqlite3.Cursor, s: ExternalNode, dry_run: bool) -> str:
    row = cur.execute(
        "SELECT company_id, node_type FROM companies WHERE name = ?", (s.name,)
    ).fetchone()

    if row is not None:
        if row[1] == s.node_type:
            return f"already present as {row[0]} — skipped"
        else:
            return (
                f"WARNING: '{s.name}' exists as {row[0]} with node_type='{row[1]}' "
                f"(expected '{s.node_type}') — not overwritten"
            )

    if dry_run:
        return f"[{s.node_type}] would be inserted"

    new_id = _next_company_id(cur)
    cur.execute(
        "INSERT INTO companies (company_id, name, included, node_type, sector, location)"
        " VALUES (?, ?, 1, ?, ?, ?)",
        (new_id, s.name, s.node_type, s.sector, s.location),
    )
    return f"inserted as {new_id} [{s.node_type}]"


def _apply_company_meta(cur: sqlite3.Cursor, s: CompanyMeta, dry_run: bool) -> str:
    row = cur.execute(
        "SELECT company_id FROM companies WHERE name = ?", (s.name,)
    ).fetchone()

    if row is None:
        return f"WARNING: company '{s.name}' not found — skipped"

    fields: dict = {}
    if s.sector   is not None: fields["sector"]   = s.sector
    if s.location is not None: fields["location"]  = s.location
    if s.included is not None: fields["included"]  = s.included

    if not fields:
        return "nothing to update (all fields are None)"

    if dry_run:
        return f"would set {fields} on {row[0]}"

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    cur.execute(
        f"UPDATE companies SET {set_clause} WHERE company_id = ?",
        (*fields.values(), row[0]),
    )
    return f"updated {list(fields.keys())} on {row[0]}"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def apply(db_path: str = DB_PATH, dry_run: bool = False) -> None:
    """Apply all SEEDS entries to the database.

    dry_run: If True, print what would be done without modifying anything.
    """
    tag = "[DRY RUN] " if dry_run else ""
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    counts = {"added": 0, "updated": 0, "skipped": 0, "warnings": 0}

    for s in SEEDS:
        if isinstance(s, ExternalNode):
            status = _apply_external_node(cur, s, dry_run)
            label  = f"EXTERNAL  {s.name!r}"
        elif isinstance(s, CompanyMeta):
            status = _apply_company_meta(cur, s, dry_run)
            label  = f"META      {s.name!r}"
        else:
            continue

        print(f"  {tag}{label}: {status}")

        if "WARNING" in status:
            counts["warnings"] += 1
        elif "skipped" in status or "nothing" in status:
            counts["skipped"] += 1
        elif isinstance(s, ExternalNode):
            counts["added"] += 1
        elif isinstance(s, CompanyMeta):
            counts["updated"] += 1

    if not dry_run:
        conn.commit()
    conn.close()

    summary = (
        f"{tag}Summary: "
        f"{counts['added']} added, "
        f"{counts['updated']} updated, "
        f"{counts['skipped']} skipped"
        + (f", {counts['warnings']} WARNING(s)" if counts["warnings"] else "")
    )
    print(f"\n  {summary}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db", default=DB_PATH, metavar="PATH",
        help="Path to the SQLite database (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview changes without modifying the database",
    )
    args = parser.parse_args()
    apply(args.db, dry_run=args.dry_run)
