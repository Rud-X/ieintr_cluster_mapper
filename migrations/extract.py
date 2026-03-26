"""
extract.py — Industrial Cluster Material Flow: CSV → SQLite pipeline
Spec: industrial_cluster_spec_V2.md
"""

import csv
import logging
import re
import sqlite3
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "industrial_cluster.db"
NOMENCLATURE_CSV = BASE_DIR / "data" / "raw_materials_nomenclature.csv"
STREAMS_CSV = BASE_DIR / "data" / "raw_streams_data.csv"

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

DDL = """
CREATE TABLE IF NOT EXISTS companies (
    company_id  TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    sector      TEXT,
    location    TEXT
);

CREATE TABLE IF NOT EXISTS components (
    component_id    TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    aliases         TEXT,
    category        TEXT,
    cas_number      TEXT,
    molecular_weight REAL,
    carbon_atoms    INTEGER,
    hazardous       INTEGER,
    needs_review    INTEGER NOT NULL DEFAULT 0,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS streams (
    stream_id           TEXT PRIMARY KEY,
    company_id          TEXT NOT NULL REFERENCES companies(company_id),
    stream_name         TEXT,
    stream_type         TEXT NOT NULL,
    direction           TEXT NOT NULL,
    flow_kton_per_year  REAL,
    temperature_c       REAL,
    pressure_bar        REAL,
    composition_raw     TEXT,
    notes               TEXT
);

CREATE TABLE IF NOT EXISTS stream_composition (
    composition_id  TEXT PRIMARY KEY,
    stream_id       TEXT NOT NULL REFERENCES streams(stream_id),
    component_id    TEXT NOT NULL REFERENCES components(component_id),
    fraction        REAL NOT NULL,
    is_trace        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS flows (
    flow_id             TEXT PRIMARY KEY,
    from_company_id     TEXT NOT NULL REFERENCES companies(company_id),
    to_company_id       TEXT NOT NULL REFERENCES companies(company_id),
    from_stream_id      TEXT NOT NULL REFERENCES streams(stream_id),
    to_stream_id        TEXT NOT NULL REFERENCES streams(stream_id),
    flow_kton_per_year  REAL,
    status              TEXT NOT NULL DEFAULT 'candidate',
    notes               TEXT
);
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _next_id(prefix: str, counter: dict) -> str:
    counter[prefix] = counter.get(prefix, 0) + 1
    return f"{prefix}{counter[prefix]:03d}"


def _coerce_float(val: str) -> float | None:
    if val is None:
        return None
    val = val.strip()
    if not val:
        return None
    # European decimal comma: replace comma with dot when it looks like a decimal
    val = re.sub(r"(\d),(\d)", r"\1.\2", val)
    try:
        return float(val)
    except ValueError:
        return None


def _coerce_int(val: str) -> int | None:
    f = _coerce_float(val)
    if f is None:
        return None
    return int(f)

# ---------------------------------------------------------------------------
# Nomenclature loader
# ---------------------------------------------------------------------------

def load_nomenclature(conn: sqlite3.Connection) -> int:
    """Load raw_materials_nomenclature.csv into the components table.

    Mapping (spec §Pre-population from nomenclature CSV):
        Chemical          → name
        Abbreviation      → aliases
        CAS Number        → cas_number
        Molecular weight  → molecular_weight
        Carbon Atoms      → carbon_atoms
        needs_review      = 0
    """
    counter: dict = {}

    with open(NOMENCLATURE_CSV, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        rows_inserted = 0
        for row in reader:
            name = row["Chemical"].strip()
            if not name:
                continue
            abbrev = row.get("Abbreviation", "").strip() or None
            cas = row.get("CAS Number", "").strip() or None
            mw = _coerce_float(row.get("Molecular weight", ""))
            ca = _coerce_int(row.get("Carbon Atoms", ""))
            cid = _next_id("CM", counter)

            conn.execute(
                """
                INSERT OR IGNORE INTO components
                    (component_id, name, aliases, cas_number,
                     molecular_weight, carbon_atoms, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (cid, name, abbrev, cas, mw, ca),
            )
            rows_inserted += conn.execute(
                "SELECT changes()"
            ).fetchone()[0]

    return rows_inserted

# ---------------------------------------------------------------------------
# Composition string parser
# ---------------------------------------------------------------------------

def _fix_european_commas(text: str) -> str:
    """Replace decimal commas (e.g. 0,018) with dots."""
    return re.sub(r"(\d),(\d)", r"\1.\2", text)


def parse_composition(raw: str) -> list[tuple[str, float, int]]:
    """Parse a composition string into (component_name, fraction, is_trace) tuples.

    Supported formats (spec §Composition string parser):
        Name (93%)          → fraction = 0.93
        23.13% O2           → fraction = 0.2313
        CH3OH 0,018 %       → European comma → fraction = 0.00018
        H2(666 ppm)         → fraction = 6.66e-7
        CO(trace)           → fraction = 0, is_trace = 1
        SiO2: 0.6           → fraction = 0.6 (already decimal)
    """
    if not raw or not raw.strip():
        return []

    text = _fix_european_commas(raw.strip())
    results: list[tuple[str, float, int]] = []

    # Patterns tried in order (most specific first):
    patterns = [
        # "Name (value unit)" or "Name(value unit)"
        re.compile(
            r"([A-Za-z0-9][^,;()]*?)\s*\(\s*([\d.]+)\s*(ppm|%|trace)?\s*\)",
            re.IGNORECASE,
        ),
        # "value% Name" or "value % Name"
        re.compile(
            r"([\d.]+)\s*(%)\s+([A-Za-z0-9][^,;]*?)(?=,|;|$)",
            re.IGNORECASE,
        ),
        # "Name value%" or "Name value %"
        re.compile(
            r"([A-Za-z0-9][^,;:]*?)\s+([\d.]+)\s*(%|ppm)",
            re.IGNORECASE,
        ),
        # "Name: value" (decimal fraction, no unit)
        re.compile(
            r"([A-Za-z0-9][^,;:]*?)\s*:\s*([\d.]+)(?:\s*(?=%|ppm|,|;|$))",
            re.IGNORECASE,
        ),
    ]

    matched_spans: list[tuple[int, int]] = []

    def _record(name: str, value_str: str, unit: str | None) -> None:
        name = name.strip(" \t,;:")
        if not name:
            return
        unit = (unit or "").lower().strip()
        if unit == "trace" or value_str.lower() == "trace":
            results.append((name, 0.0, 1))
            return
        try:
            value = float(value_str)
        except ValueError:
            return
        if unit == "%":
            fraction = value / 100.0
        elif unit == "ppm":
            fraction = value / 1_000_000.0
        else:
            # No unit — treat as decimal fraction if < 1, else assume %
            fraction = value if value <= 1.0 else value / 100.0
        results.append((name, fraction, 0))

    # Pattern 0: Name (value unit) or Name (trace)
    p0 = patterns[0]
    for m in p0.finditer(text):
        name = m.group(1)
        value_str = m.group(2)
        unit = m.group(3) or ""
        if value_str.lower() == "trace" or unit.lower() == "trace":
            results.append((name.strip(), 0.0, 1))
        else:
            _record(name, value_str, unit)
        matched_spans.append(m.span())

    if results:
        return results

    # Pattern 1: value% Name
    p1 = patterns[1]
    for m in p1.finditer(text):
        value_str, unit, name = m.group(1), m.group(2), m.group(3)
        _record(name, value_str, unit)
        matched_spans.append(m.span())

    if results:
        return results

    # Pattern 2: Name value%
    p2 = patterns[2]
    for m in p2.finditer(text):
        name, value_str, unit = m.group(1), m.group(2), m.group(3)
        _record(name, value_str, unit)
        matched_spans.append(m.span())

    if results:
        return results

    # Pattern 3: Name: value (decimal)
    p3 = patterns[3]
    for m in p3.finditer(text):
        name, value_str = m.group(1), m.group(2)
        _record(name, value_str, None)
        matched_spans.append(m.span())

    return results

# ---------------------------------------------------------------------------
# Stream extractor
# ---------------------------------------------------------------------------

STREAM_TYPE_MAP = {
    "raw": "raw_material",
    "product": "product",
    "waste": "waste",
}

DIRECTION_MAP = {
    "raw_material": "input",
    "product": "output",
    "waste": "output",
}


def load_streams(conn: sqlite3.Connection) -> dict:
    """Load raw_streams_data.csv into companies, streams, stream_composition."""
    # Seed counters from existing DB rows so new IDs don't collide.
    def _max_num(prefix: str, table: str, col: str) -> int:
        row = conn.execute(
            f"SELECT MAX(CAST(SUBSTR({col}, {len(prefix)+1}) AS INTEGER)) FROM {table}"
            f" WHERE {col} LIKE '{prefix}%'"
        ).fetchone()
        return row[0] or 0

    counters: dict = {
        "CM": _max_num("CM", "components", "component_id"),
        "C":  _max_num("C",  "companies",  "company_id"),
        "S":  _max_num("S",  "streams",    "stream_id"),
        "CP": _max_num("CP", "stream_composition", "composition_id"),
    }

    # Build lookup: (name_lower → component_id, alias_lower → component_id)
    def build_component_lookup() -> dict[str, str]:
        lookup: dict[str, str] = {}
        for cid, name, aliases in conn.execute(
            "SELECT component_id, name, aliases FROM components"
        ):
            lookup[name.lower()] = cid
            if aliases:
                for alias in aliases.split(","):
                    a = alias.strip().lower()
                    if a:
                        lookup[a] = cid
        return lookup

    comp_lookup = build_component_lookup()

    # Ensure "unknown" sentinel component exists
    unknown_id = conn.execute(
        "SELECT component_id FROM components WHERE name = 'unknown'"
    ).fetchone()
    if unknown_id is None:
        unknown_id = _next_id("CM", counters)
        conn.execute(
            "INSERT INTO components (component_id, name, needs_review) VALUES (?, 'unknown', 0)",
            (unknown_id,),
        )
        comp_lookup["unknown"] = unknown_id
    else:
        unknown_id = unknown_id[0]
        comp_lookup["unknown"] = unknown_id

    companies: dict[str, str] = {}  # name → company_id
    stats = {"streams": 0, "compositions": 0, "new_components": 0, "fraction_warnings": 0}

    with open(STREAMS_CSV, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        for row in reader:
            company_name = row["company"].strip()
            if company_name not in companies:
                cid = _next_id("C", counters)
                conn.execute(
                    "INSERT OR IGNORE INTO companies (company_id, name) VALUES (?, ?)",
                    (cid, company_name),
                )
                companies[company_name] = cid

            company_id = companies[company_name]

            raw_type = row["stream_type"].strip().lower()
            stream_type = STREAM_TYPE_MAP.get(raw_type, raw_type)
            direction = DIRECTION_MAP.get(stream_type, "output")

            stream_id = _next_id("S", counters)
            composition_raw = row.get("composition", "").strip()

            # Temperature column name varies (encoding artefacts in header)
            temp_val = next(
                (v for k, v in row.items() if "temp" in k.lower()),
                "",
            )
            conn.execute(
                """
                INSERT INTO streams
                    (stream_id, company_id, stream_name, stream_type, direction,
                     flow_kton_per_year, temperature_c, pressure_bar, composition_raw)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stream_id,
                    company_id,
                    row.get("stream_name", "").strip(),
                    stream_type,
                    direction,
                    _coerce_float(row.get("kiloton/year", "")),
                    _coerce_float(temp_val),
                    _coerce_float(row.get("pressure (bar)", "")),
                    composition_raw,
                ),
            )
            stats["streams"] += 1

            # Parse composition
            parsed = parse_composition(composition_raw)
            non_trace_sum = 0.0
            for comp_name, fraction, is_trace in parsed:
                key = comp_name.lower()
                if key not in comp_lookup:
                    new_cid = _next_id("CM", counters)
                    conn.execute(
                        """
                        INSERT INTO components (component_id, name, needs_review)
                        VALUES (?, ?, 1)
                        """,
                        (new_cid, comp_name),
                    )
                    comp_lookup[key] = new_cid
                    stats["new_components"] += 1
                    log.warning("Unrecognized component added for review: %r (stream %s)", comp_name, stream_id)

                comp_id = comp_lookup[key]
                cp_id = _next_id("CP", counters)
                conn.execute(
                    """
                    INSERT INTO stream_composition
                        (composition_id, stream_id, component_id, fraction, is_trace)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (cp_id, stream_id, comp_id, fraction, is_trace),
                )
                stats["compositions"] += 1
                if not is_trace:
                    non_trace_sum += fraction

            # Fraction-sum validation
            if parsed:
                if abs(non_trace_sum - 1.0) > 0.02 and non_trace_sum > 0:
                    remainder = 1.0 - non_trace_sum
                    log.warning(
                        "Fraction sum %.4f ≠ 1.0 for stream %s (%r) — recording remainder %.4f as 'unknown'",
                        non_trace_sum, stream_id, row.get("stream_name"), remainder,
                    )
                    cp_id = _next_id("CP", counters)
                    conn.execute(
                        """
                        INSERT INTO stream_composition
                            (composition_id, stream_id, component_id, fraction, is_trace)
                        VALUES (?, ?, ?, ?, 0)
                        """,
                        (cp_id, stream_id, unknown_id, remainder),
                    )
                    stats["fraction_warnings"] += 1

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
        log.info("Removed existing database.")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(DDL)
    conn.commit()
    log.info("Schema created.")

    n_components = load_nomenclature(conn)
    conn.commit()
    log.info("Nomenclature loaded: %d components inserted.", n_components)

    if STREAMS_CSV.exists():
        stats = load_streams(conn)
        conn.commit()
        log.info(
            "Streams loaded: %d streams, %d composition entries, "
            "%d new components flagged for review, %d fraction warnings.",
            stats["streams"], stats["compositions"],
            stats["new_components"], stats["fraction_warnings"],
        )
    else:
        log.info("No raw_streams_data.csv found — skipping stream extraction.")

    # Summary
    counts = {
        tbl: conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        for tbl in ("companies", "components", "streams", "stream_composition", "flows")
    }
    print("\n--- Table counts ---")
    for tbl, n in counts.items():
        print(f"  {tbl:<22} {n}")
    print(f"\nDatabase written to: {DB_PATH}")

    conn.close()


if __name__ == "__main__":
    main()
