"""
correct_components.py — Documented corrections for auto-added needs_review components.

After extract.py runs, any composition component not found in the reference
nomenclature is inserted with needs_review=1. This script applies three types
of corrections to resolve those components:

  Merge   — duplicate or alias of an existing component; redirect all
            stream_composition rows to the canonical entry, add the duplicate
            name as an alias, and remove the duplicate row.

  Enrich  — genuinely new component; fill in chemical data (CAS, MW,
            carbon_atoms, category) and clear needs_review.

  Flag    — still ambiguous or a parser artefact; write an explanatory note
            and keep needs_review=1 for manual follow-up.

All corrections are idempotent: safe to re-run on an already-corrected database.

Lookups are by component name (case-insensitive), not by auto-generated ID,
so corrections survive a full re-extraction even if IDs shift.

Usage:
    python migrations/correct_components.py [--db PATH] [--dry-run]
"""

import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DB_PATH = "industrial_cluster.db"


# ---------------------------------------------------------------------------
# Correction types
# ---------------------------------------------------------------------------

@dataclass
class Merge:
    """Redirect a duplicate component to the canonical entry.

    Steps applied:
      1. All stream_composition rows pointing to `src` are updated to point
         to `into`.
      2. The `src` name is appended to `into`'s aliases (comma-separated),
         so future extractions resolve it directly without a correction.
      3. The `src` component row is deleted.

    If `src` is already absent (a previous run merged it), the correction is
    silently skipped — idempotent.
    """
    src: str    # name of the duplicate (needs_review) component
    into: str   # name of the canonical (existing) component to merge into
    reason: str # human-readable explanation of why these are the same compound


@dataclass
class Enrich:
    """Fill in chemical data for a genuinely new component and clear needs_review.

    Only non-None fields are written; fields already populated in the database
    are not overwritten unless explicitly provided here.
    """
    name: str
    reason: str                            # why this component is genuinely new
    category: Optional[str] = None
    cas_number: Optional[str] = None
    molecular_weight: Optional[float] = None
    carbon_atoms: Optional[int] = None


@dataclass
class Flag:
    """Mark a component as still requiring manual investigation.

    Writes `notes` to components.notes and leaves needs_review=1.
    Used when the correct resolution cannot be determined from the source
    data alone and a human decision is required before merging.
    """
    name: str
    notes: str  # description of what needs to be resolved


# ---------------------------------------------------------------------------
# Corrections list
# -----------------------------------------------------------------------
# To add a correction: append a Merge / Enrich / Flag to CORRECTIONS below.
# To resolve a Flag: replace it with a Merge or Enrich once the ambiguity
# is resolved, and commit the change with an explanatory message.
# ---------------------------------------------------------------------------

CORRECTIONS: list = [

    # -------------------------------------------------------------------
    # MERGES — duplicates / aliases of existing components (29 total)
    # -------------------------------------------------------------------

    Merge("NC3-A", "Propane",
          "Follows the N-C1A/N-C2A/N-C3A naming convention; extracted without hyphen"),

    Merge("hexane", "n-Hexane",
          "Generic name; n-Hexane is the only hexane in the reference table"),

    Merge("2-methyhexane", "2-Methylhexane",
          "Typo: missing 'l' in methyl"),

    Merge("methyhexane", "2-Methylhexane",
          "Same typo as 2-methyhexane; 2-Methylhexane is the only methylhexane in the table"),

    Merge("methylhexane", "2-Methylhexane",
          "Unqualified methylhexane; 2-Methylhexane is the only entry in the reference table"),

    Merge("2-MEHX", "2-Methylhexane",
          "Direct abbreviation match: MEHX alias on 2-Methylhexane"),

    Merge("methyl heptane", "3-Methylheptane",
          "3-Methylheptane (MEHP) is the only methylheptane in the reference table"),

    Merge("3-MEHP", "3-Methylheptane",
          "Direct abbreviation match: MEHP alias on 3-Methylheptane"),

    Merge("3.3-dimethylpentane", "3,3-Dimethylpentane",
          "Period-for-comma typo in the locant"),

    Merge("1.3-cyclopentadiene", "Cyclopentadiene",
          "Period-for-comma typo; 1,3-CPD is the canonical form of cyclopentadiene"),

    Merge("butane", "n-Butane",
          "Generic name; n-Butane is the only butane in the reference table"),

    Merge("Butadiene", "1,3-Butadiene",
          "Industrial default: unqualified 'Butadiene' refers to 1,3-butadiene; stream name confirms"),

    Merge("Isobutene", "Isobutylene",
          "Two accepted names for the same compound (2-methylpropene)"),

    Merge("n-pentene", "1-Pentene",
          "n-pentene = 1-pentene (straight-chain terminal alkene)"),

    Merge("ethyl benzene", "Ethylbenzene",
          "Space in compound name"),

    Merge("4-Trimethylbenzene", "1,2,4-Trimethylbenzene",
          "Abbreviated locant; 1,2,4-TMB is the only trimethylbenzene in the reference table"),

    Merge("DCPD", "Dicyclopentadiene",
          "DCPD is the universal industry abbreviation for dicyclopentadiene"),

    Merge("Naphth", "Naphtha",
          "Truncated name"),

    Merge("Sulfonale", "Sulfolane",
          "Typo: transposed letters (Sulfon-a-le vs Sulfo-l-ane)"),

    Merge("N-C1A", "Methane",
          "Follows the N-C1A/N-C2A/N-C3A pattern: N-C1A = one-carbon alkane = methane"),

    Merge("TRILINOL", "Trilinolein",
          "Process simulation code for trilinolein"),

    Merge("NAOCH3", "Sodium methoxide",
          "NaOCH₃ is the molecular formula for sodium methoxide"),

    Merge("GLYC", "Glycerol",
          "Abbreviated process code; GLY alias on Glycerol confirms"),

    Merge("PTA", "Terephthalic acid",
          "PTA (purified terephthalic acid) is the industry-standard abbreviation"),

    Merge("CH3OH", "Methanol",
          "Molecular formula for methanol"),

    Merge("C2H6", "Ethane",
          "Molecular formula for ethane"),

    Merge("Terbutylalcohol", "tert-Butyl alcohol",
          "Alternate spelling of tert-butyl alcohol"),

    Merge("propylmercaptan", "n-propylmercaptan",
          "Same compound; n-propylmercaptan is the canonical form in the reference table"),

    Merge("propyl mercaptan", "n-propylmercaptan",
          "Same compound as propylmercaptan; space variant"),

    # -------------------------------------------------------------------
    # ENRICHMENTS — genuinely new components absent from reference nomenclature
    # -------------------------------------------------------------------

    Enrich(
        name="propylene mercaptan",
        reason="Allyl mercaptan (prop-2-ene-1-thiol); verified against CAS registry",
        category="organic",
        cas_number="870-23-5",
        molecular_weight=74.14,
        carbon_atoms=3,
    ),

    Enrich(
        name="food waste",
        reason="Not a chemical compound; treated as a named process material with no molecular data",
        category="named_material",
    ),

    # -------------------------------------------------------------------
    # FLAGS — unresolved; require manual investigation before merging
    # -------------------------------------------------------------------

    Flag(
        name="3-methyl heptane 5% o-xylene",
        notes=(
            "Parser artefact — this string appears to be a fragment of a composition "
            "string rather than a component name. Re-examine the source CSV row for "
            "stream 'HC Reformate import' before resolving."
        ),
    ),

    Flag(
        name="butene",
        notes=(
            "Isomer not specified; appears in 7 streams. Could be 1-butene (CM012), "
            "cis-2-butene (CM064), trans-2-butene (CM212), or isobutylene (CM102). "
            "Resolve from source data before merging."
        ),
    ),

    Flag(
        name="BDI",
        notes=(
            "Ambiguous abbreviation. Reference table contains BDI-12 (1,2-Butadiene) "
            "and BDI-13 (1,3-Butadiene). Check source data to determine the correct isomer."
        ),
    ),

    Flag(
        name="Pyridine/Pyrrole",
        notes=(
            "Two compounds listed as a single entry. Pyridine exists in the reference "
            "table (CM178). Pyrrole is absent (CAS 109-97-7, MW 67.09, 4 carbon atoms). "
            "This stream_composition row must be split into two rows manually."
        ),
    ),

    Flag(
        name="METHY-01",
        notes=(
            "Process simulation code, likely a fatty acid methyl ester "
            "(oleate/linoleate/linolenate — all three exist in the reference table). "
            "Check the simulation model to determine which compound is intended."
        ),
    ),

    Flag(
        name="METHY-02",
        notes=(
            "Process simulation code, likely a fatty acid methyl ester. "
            "See METHY-01 notes."
        ),
    ),

    Flag(
        name="METHY-03",
        notes=(
            "Process simulation code, likely a fatty acid methyl ester. "
            "See METHY-01 notes."
        ),
    ),

    Flag(
        name="METFORM",
        notes=(
            "Likely methyl formate (CM118, alias MF) — a common byproduct in "
            "methanol synthesis light-end streams. Confirm against source data "
            "before merging."
        ),
    ),
    Merge("Water", "Water",
          "Same material"),

    Enrich(
        name="Water",
        reason="Set via TUI carbon accounting tool",
        molecular_weight=18.015,
    ),

]


# ---------------------------------------------------------------------------
# Apply helpers
# ---------------------------------------------------------------------------

def _lookup(cur: sqlite3.Cursor, name: str) -> str | None:
    """Return component_id for the given name (case-insensitive), or None."""
    row = cur.execute(
        "SELECT component_id FROM components WHERE name = ? COLLATE NOCASE",
        (name,),
    ).fetchone()
    return row[0] if row else None


def _apply_merge(cur: sqlite3.Cursor, c: Merge, dry_run: bool) -> str:
    src_id = _lookup(cur, c.src)
    if src_id is None:
        return "skipped — src already absent (previously merged or never created)"

    into_id = _lookup(cur, c.into)
    if into_id is None:
        return f"ERROR: target '{c.into}' not found in components table"

    if dry_run:
        n = cur.execute(
            "SELECT COUNT(*) FROM stream_composition WHERE component_id = ?",
            (src_id,),
        ).fetchone()[0]
        return (
            f"would redirect {n} stream_composition row(s) to '{c.into}', "
            f"add alias, delete '{c.src}'"
        )

    # 1. Redirect all stream_composition rows
    cur.execute(
        "UPDATE stream_composition SET component_id = ? WHERE component_id = ?",
        (into_id, src_id),
    )
    rows_redirected = cur.rowcount

    # 2. Add src name as alias on the target (avoid duplicates)
    existing_aliases = cur.execute(
        "SELECT aliases FROM components WHERE component_id = ?", (into_id,)
    ).fetchone()[0] or ""
    existing_set = {a.strip().lower() for a in existing_aliases.split(",") if a.strip()}
    if c.src.lower() not in existing_set:
        new_aliases = (existing_aliases.rstrip(", ") + ", " + c.src).lstrip(", ")
        cur.execute(
            "UPDATE components SET aliases = ? WHERE component_id = ?",
            (new_aliases, into_id),
        )

    # 3. Delete the duplicate row
    cur.execute("DELETE FROM components WHERE component_id = ?", (src_id,))

    return f"merged — {rows_redirected} stream_composition row(s) redirected to '{c.into}'"


def _apply_enrich(cur: sqlite3.Cursor, c: Enrich, dry_run: bool) -> str:
    cid = _lookup(cur, c.name)
    if cid is None:
        return "skipped — component not found (may have been merged away)"

    fields: dict = {}
    if c.category is not None:
        fields["category"] = c.category
    if c.cas_number is not None:
        fields["cas_number"] = c.cas_number
    if c.molecular_weight is not None:
        fields["molecular_weight"] = c.molecular_weight
    if c.carbon_atoms is not None:
        fields["carbon_atoms"] = c.carbon_atoms
    fields["needs_review"] = 0

    if dry_run:
        return f"would set {fields}"

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    cur.execute(
        f"UPDATE components SET {set_clause} WHERE component_id = ?",
        (*fields.values(), cid),
    )
    data_fields = [k for k in fields if k != "needs_review"]
    return f"enriched — set {', '.join(data_fields)}, needs_review=0"


def _apply_flag(cur: sqlite3.Cursor, c: Flag, dry_run: bool) -> str:
    cid = _lookup(cur, c.name)
    if cid is None:
        return "skipped — component not found"

    if dry_run:
        return "would write notes, keep needs_review=1"

    cur.execute(
        "UPDATE components SET notes = ?, needs_review = 1 WHERE component_id = ?",
        (c.notes, cid),
    )
    return "flagged — notes written, needs_review=1"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def apply(db_path: str = DB_PATH, dry_run: bool = False) -> None:
    """Apply all CORRECTIONS to the database.

    Args:
        db_path:  Path to the SQLite database file.
        dry_run:  If True, print what would be done without modifying the DB.
    """
    tag = "[DRY RUN] " if dry_run else ""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    counts = {"merged": 0, "enriched": 0, "flagged": 0, "skipped": 0, "errors": 0}

    for c in CORRECTIONS:
        if isinstance(c, Merge):
            status = _apply_merge(cur, c, dry_run)
            label = f"MERGE  {c.src!r:38s} → {c.into!r}"
        elif isinstance(c, Enrich):
            status = _apply_enrich(cur, c, dry_run)
            label = f"ENRICH {c.name!r}"
        elif isinstance(c, Flag):
            status = _apply_flag(cur, c, dry_run)
            label = f"FLAG   {c.name!r}"
        else:
            continue

        print(f"  {tag}{label}: {status}")

        if status.startswith("ERROR"):
            counts["errors"] += 1
        elif "skipped" in status:
            counts["skipped"] += 1
        elif isinstance(c, Merge):
            counts["merged"] += 1
        elif isinstance(c, Enrich):
            counts["enriched"] += 1
        elif isinstance(c, Flag):
            counts["flagged"] += 1

    if not dry_run:
        conn.commit()

    conn.close()

    summary = (
        f"{tag}Summary: "
        f"{counts['merged']} merged, "
        f"{counts['enriched']} enriched, "
        f"{counts['flagged']} flagged, "
        f"{counts['skipped']} skipped"
        + (f", {counts['errors']} ERRORS" if counts["errors"] else "")
    )
    print(f"\n  {summary}")

    if counts["errors"]:
        raise SystemExit(f"correct_components: {counts['errors']} error(s) — see output above")


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
        help="Preview corrections without modifying the database",
    )
    args = parser.parse_args()
    apply(args.db, dry_run=args.dry_run)
