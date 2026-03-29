"""
carbon_tui.py

Interactive TUI for browsing and editing carbon accounting data.
Entry points:
  browse_components(db_path) — list components, filter to gaps, edit MW/carbon atoms
  browse_streams(db_path)    — list streams, filter to incomplete, drill to composition
"""

import difflib
import re
import sqlite3
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import carbon
import manage_companies
import manage_companies_tui
import manage_flows_tui
import questionary

DB_PATH = "industrial_cluster.db"
CORRECTIONS_PATH = Path(__file__).parent.parent / "migrations" / "correct_components.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _fmt_carbon_status(carbon_weight_pct, carbon_weight_pct_manual) -> str:
    if carbon_weight_pct is None:
        return "missing"
    if carbon_weight_pct_manual:
        return f"{carbon_weight_pct:.4f} (manual)"
    return f"{carbon_weight_pct:.4f}"


def _set_field_in_block(block: str, field: str, value) -> str:
    """Update a field inside an Enrich block, or insert it before the closing line."""
    pat = re.compile(r'(\n\s+' + re.escape(field) + r'\s*=\s*)[^,\n]+')
    if pat.search(block):
        return pat.sub(rf'\g<1>{value}', block)
    # Insert before the closing `\n    )` line
    close = block.rfind('\n')
    return block[:close] + f'\n        {field}={value},' + block[close:]


# ---------------------------------------------------------------------------
# correct_components.py updater
# ---------------------------------------------------------------------------

def _update_corrections(
    component_name: str,
    molecular_weight: float | None,
    carbon_atoms: int | None,
    corrections_path: Path = CORRECTIONS_PATH,
) -> None:
    """Write or update an Enrich entry in correct_components.py for component_name."""
    if molecular_weight is None and carbon_atoms is None:
        return

    text = corrections_path.read_text()

    # Search for an existing Enrich( block with this name
    escaped = re.escape(component_name)
    pattern = re.compile(
        r'Enrich\(\s*\n\s*name\s*=\s*["\']' + escaped + r'["\']',
        re.IGNORECASE,
    )
    match = pattern.search(text)

    if match:
        # Find the full extent of the Enrich block (balance parentheses)
        block_start = match.start()
        depth = 0
        block_end = None
        for i in range(block_start, len(text)):
            if text[i] == '(':
                depth += 1
            elif text[i] == ')':
                depth -= 1
                if depth == 0:
                    block_end = i + 1
                    break

        if block_end is None:
            print("  Warning: could not find end of Enrich block; skipping corrections update.")
            return

        block = text[block_start:block_end]

        if molecular_weight is not None:
            block = _set_field_in_block(block, "molecular_weight", molecular_weight)
        if carbon_atoms is not None:
            block = _set_field_in_block(block, "carbon_atoms", carbon_atoms)

        text = text[:block_start] + block + text[block_end:]

    else:
        # Build and insert a new Enrich block before the closing ] of CORRECTIONS
        parts = [
            '    Enrich(\n',
            f'        name="{component_name}",\n',
            '        reason="Set via TUI carbon accounting tool",\n',
        ]
        if molecular_weight is not None:
            parts.append(f'        molecular_weight={molecular_weight},\n')
        if carbon_atoms is not None:
            parts.append(f'        carbon_atoms={carbon_atoms},\n')
        parts.append('    ),\n')
        new_block = ''.join(parts)

        close_idx = text.rfind('\n]')
        if close_idx == -1:
            print("  Warning: could not find CORRECTIONS closing ]; skipping corrections update.")
            return
        text = text[:close_idx] + '\n' + new_block + text[close_idx:]

    corrections_path.write_text(text)
    print(f"  Updated corrections file: {corrections_path.name}")


# ---------------------------------------------------------------------------
# Merge helpers
# ---------------------------------------------------------------------------

def _build_alias_pool(cur: sqlite3.Cursor) -> dict:
    """Return {lowercased_name_or_alias: component_id} for every component."""
    cur.execute("SELECT component_id, name, aliases FROM components")
    pool = {}
    for r in cur.fetchall():
        pool[r['name'].lower()] = r['component_id']
        if r['aliases']:
            for alias in r['aliases'].split(','):
                alias = alias.strip()
                if alias:
                    pool[alias.lower()] = r['component_id']
    return pool


def _get_suggestions(
    src_name: str,
    src_id: str,
    pool: dict,
    all_rows: list,
) -> list:
    """Return up to 5 (component_id, name) tuples via difflib name similarity."""
    filtered = {k: v for k, v in pool.items() if v != src_id}
    matches = difflib.get_close_matches(src_name.lower(), filtered.keys(), n=5, cutoff=0.4)
    seen = {}
    for m in matches:
        cid = filtered[m]
        if cid not in seen:
            seen[cid] = None
    name_lookup = {r['component_id']: r['name'] for r in all_rows}
    return [(cid, name_lookup[cid]) for cid in seen if cid in name_lookup]


def _pick_merge_target(src_id: str, src_name: str, db_path: str):
    """Interactive picker; returns (into_id, into_name) or None on cancel."""
    conn = _connect(db_path)
    cur = conn.cursor()
    pool = _build_alias_pool(cur)
    cur.execute("SELECT component_id, name FROM components WHERE component_id != ? ORDER BY name", (src_id,))
    all_rows = cur.fetchall()
    conn.close()

    suggestions = _get_suggestions(src_name, src_id, pool, all_rows)

    def _build_choices(suggestion_set):
        choices = []
        if suggestion_set:
            for cid, name in suggestion_set:
                choices.append(questionary.Choice(title=f"★ {cid}  {name}", value=cid))
            choices.append(questionary.Separator())
        choices.append(questionary.Choice(title="Search by name...", value="__search__"))
        choices.append(questionary.Separator("─── All components ───"))
        for r in all_rows:
            choices.append(questionary.Choice(title=f"{r['component_id']}  {r['name']}", value=r['component_id']))
        choices.append(questionary.Separator())
        choices.append(questionary.Choice(title="← Cancel", value="__cancel__"))
        return choices

    while True:
        choice = questionary.select(
            f"Merge target for '{src_name}':",
            choices=_build_choices(suggestions),
        ).ask()

        if choice is None or choice == "__cancel__":
            return None

        if choice == "__search__":
            query = questionary.text("Search components by name:").ask()
            if query is None:
                return None
            query = query.strip()
            if not query:
                continue

            filtered = {k: v for k, v in pool.items() if v != src_id}
            matches = difflib.get_close_matches(query.lower(), filtered.keys(), n=8, cutoff=0.3)
            result_ids = list(dict.fromkeys(filtered[m] for m in matches))
            name_lookup = {r['component_id']: r['name'] for r in all_rows}
            results = [(cid, name_lookup[cid]) for cid in result_ids if cid in name_lookup]

            if not results:
                print(f"  (no matches for '{query}')")
                search_choices = [
                    questionary.Choice(title="← Back to full list", value="__back__"),
                    questionary.Choice(title="← Cancel", value="__cancel__"),
                ]
            else:
                search_choices = [
                    questionary.Choice(title=f"{cid}  {name}", value=cid)
                    for cid, name in results
                ] + [
                    questionary.Separator(),
                    questionary.Choice(title="← Back to full list", value="__back__"),
                    questionary.Choice(title="← Cancel", value="__cancel__"),
                ]

            search_choice = questionary.select(
                f"Search results for '{query}':",
                choices=search_choices,
            ).ask()

            if search_choice is None or search_choice == "__cancel__":
                return None
            if search_choice == "__back__":
                continue
            name_lookup = {r['component_id']: r['name'] for r in all_rows}
            return (search_choice, name_lookup[search_choice])

        name_lookup = {r['component_id']: r['name'] for r in all_rows}
        return (choice, name_lookup[choice])


_MERGE_FIELDS = [
    ("category",               "category"),
    ("cas_number",             "CAS number"),
    ("molecular_weight",       "molecular weight"),
    ("carbon_atoms",           "carbon atoms"),
    ("carbon_weight_pct_manual", "carbon_weight_pct_manual"),
    ("hazardous",              "hazardous"),
    ("notes",                  "notes"),
]


def _resolve_field_conflicts(src, into) -> dict:
    """Prompt for per-field decisions where src and into differ. Returns update dict for into."""
    updates = {}
    for col, label in _MERGE_FIELDS:
        sv = src[col]
        iv = into[col]
        if sv is None:
            continue  # src has nothing — keep into silently
        if iv is None:
            # into is missing data that src has
            confirm = questionary.confirm(
                f"  {label}: src has '{sv}', copy to target?",
                default=False,
            ).ask()
            if confirm:
                updates[col] = sv
        elif sv != iv:
            # Both have different non-NULL values
            kept = questionary.select(
                f"  Conflict in '{label}':",
                choices=[
                    questionary.Choice(title=f"Keep target: {iv}", value="into"),
                    questionary.Choice(title=f"Use source:  {sv}", value="src"),
                ],
            ).ask()
            if kept == "src":
                updates[col] = sv
    return updates


def _execute_merge(
    src_id: str,
    src_name: str,
    into_id: str,
    field_updates: dict,
    db_path: str,
) -> str:
    """Execute the full merge cascade in a single transaction. Returns summary string."""
    conn = _connect(db_path)
    try:
        with conn:
            cur = conn.cursor()

            # A — apply field_updates to into
            if field_updates:
                set_clause = ", ".join(f"{col} = ?" for col in field_updates)
                params = list(field_updates.values()) + [into_id]
                cur.execute(f"UPDATE components SET {set_clause} WHERE component_id = ?", params)

            # B — collect affected stream IDs before redirecting
            cur.execute(
                "SELECT DISTINCT stream_id FROM stream_composition WHERE component_id = ?",
                (src_id,),
            )
            affected_stream_ids = [r["stream_id"] for r in cur.fetchall()]

            # C — redirect stream_composition rows
            cur.execute(
                "UPDATE stream_composition SET component_id = ? WHERE component_id = ?",
                (into_id, src_id),
            )
            rows_redirected = cur.rowcount

            # D — merge aliases: append src_name to into if not already present
            cur.execute("SELECT aliases FROM components WHERE component_id = ?", (into_id,))
            existing_raw = cur.fetchone()["aliases"] or ""
            existing_set = {a.strip().lower() for a in existing_raw.split(",") if a.strip()}
            if src_name.lower() not in existing_set:
                new_aliases = (existing_raw.rstrip(", ") + ", " + src_name).lstrip(", ")
                cur.execute(
                    "UPDATE components SET aliases = ? WHERE component_id = ?",
                    (new_aliases, into_id),
                )

            # E — recalculate carbon_fraction for into_id
            cur.execute(
                "SELECT carbon_weight_pct FROM components WHERE component_id = ?", (into_id,)
            )
            into_cwp = cur.fetchone()["carbon_weight_pct"]

            if into_cwp is not None:
                cur.execute(
                    "UPDATE stream_composition SET carbon_fraction = fraction * ? "
                    "WHERE component_id = ? AND is_trace = 0",
                    (into_cwp, into_id),
                )
            else:
                cur.execute(
                    "UPDATE stream_composition SET carbon_fraction = NULL "
                    "WHERE component_id = ? AND is_trace = 0",
                    (into_id,),
                )

            # F — recalculate carbon_pct + carbon_pct_complete for affected streams
            unknown_row = cur.execute(
                "SELECT component_id FROM components WHERE name = 'unknown'"
            ).fetchone()
            unknown_id = unknown_row["component_id"] if unknown_row else None
            unknown_filter = f"AND sc.component_id != '{unknown_id}'" if unknown_id else ""

            for sid in affected_stream_ids:
                cur.execute(f"""
                    UPDATE streams SET
                        carbon_pct = (
                            SELECT CASE
                                WHEN SUM(CASE WHEN sc.carbon_fraction IS NOT NULL THEN 1 ELSE 0 END) > 0
                                    THEN SUM(COALESCE(sc.carbon_fraction, 0))
                                ELSE NULL
                            END
                            FROM stream_composition sc
                            JOIN components c ON sc.component_id = c.component_id
                            WHERE sc.stream_id = ? AND sc.is_trace = 0 {unknown_filter}
                        ),
                        carbon_pct_complete = (
                            SELECT CASE
                                WHEN COUNT(*) = 0 THEN NULL
                                WHEN SUM(CASE WHEN c.carbon_weight_pct IS NULL THEN 1 ELSE 0 END) = 0 THEN 1
                                ELSE 0
                            END
                            FROM stream_composition sc
                            JOIN components c ON sc.component_id = c.component_id
                            WHERE sc.stream_id = ? AND sc.is_trace = 0 {unknown_filter}
                        )
                    WHERE stream_id = ?
                """, (sid, sid, sid))

            # G — delete src
            cur.execute("DELETE FROM components WHERE component_id = ?", (src_id,))
            if cur.rowcount == 0:
                print(f"  Warning: src component {src_id} was already absent at deletion step.")

    finally:
        conn.close()

    return (
        f"{rows_redirected} composition row(s) redirected, "
        f"{len(affected_stream_ids)} stream(s) recalculated"
    )


def _write_merge_correction(
    src_name: str,
    into_name: str,
    reason: str,
    corrections_path: Path = CORRECTIONS_PATH,
) -> None:
    """Append a Merge entry to correct_components.py before the closing ] of CORRECTIONS."""
    try:
        text = corrections_path.read_text()
    except FileNotFoundError:
        print(f"  Warning: {corrections_path} not found; merge not recorded in corrections file.")
        return

    escaped_reason = reason.replace('\\', '\\\\').replace('"', '\\"')
    new_entry = (
        f'    Merge("{src_name}", "{into_name}",\n'
        f'          "{escaped_reason}"),\n'
    )

    close_idx = text.rfind('\n]')
    if close_idx == -1:
        print("  Warning: could not find CORRECTIONS closing ]; merge not recorded.")
        return

    text = text[:close_idx] + '\n' + new_entry + text[close_idx:]
    corrections_path.write_text(text)
    print(f"  Updated corrections file: {corrections_path.name}")


def _merge_component(component_id: str, db_path: str) -> None:
    """Orchestrate a full component merge: pick target, resolve conflicts, execute, record."""
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM components WHERE component_id = ?", (component_id,))
    src = cur.fetchone()
    conn.close()

    if src is None:
        print(f"  Component {component_id} not found.")
        return

    src_name = src['name']
    print(f"\n  Merging: {component_id}  {src_name}")

    result = _pick_merge_target(component_id, src_name, db_path)
    if result is None:
        return
    into_id, into_name = result

    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM components WHERE component_id = ?", (into_id,))
    into = cur.fetchone()

    # Safety check: src and into cannot share any stream
    cur.execute("""
        SELECT sc1.stream_id FROM stream_composition sc1
        JOIN stream_composition sc2 ON sc1.stream_id = sc2.stream_id
        WHERE sc1.component_id = ? AND sc2.component_id = ?
        LIMIT 5
    """, (component_id, into_id))
    overlap = [r["stream_id"] for r in cur.fetchall()]
    conn.close()

    if into is None:
        print(f"  Error: target component {into_id} not found.")
        return

    if overlap:
        print(f"  Cannot merge: both components appear in the same stream(s): {', '.join(overlap)}")
        print("  Resolve this manually before merging.")
        return

    print(f"  Into:    {into_id}  {into_name}")

    field_updates = _resolve_field_conflicts(src, into)

    # Merge preview
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) AS n FROM stream_composition WHERE component_id = ?", (component_id,)
    )
    row_count = cur.fetchone()["n"]
    cur.execute(
        "SELECT COUNT(DISTINCT stream_id) AS n FROM stream_composition WHERE component_id = ?",
        (component_id,),
    )
    stream_count = cur.fetchone()["n"]
    conn.close()

    print(f"\n  Preview:")
    print(f"    Redirect {row_count} composition row(s) from '{src_name}' → '{into_name}'")
    print(f"    Recalculate carbon for {stream_count} stream(s)")
    print(f"    Add '{src_name}' to {into_name}'s aliases")
    print(f"    Delete component {component_id}")
    if field_updates:
        print(f"    Field updates on target: {field_updates}")

    reason_raw = questionary.text("Reason for merge:").ask()
    if reason_raw is None:
        return
    reason = reason_raw.strip()
    if not reason:
        print("  (cancelled — reason is required)")
        return

    confirmed = questionary.confirm(
        f"Permanently merge '{src_name}' into '{into_name}'?",
        default=False,
    ).ask()
    if not confirmed:
        print("  (cancelled)")
        return

    print()
    summary = _execute_merge(component_id, src_name, into_id, field_updates, db_path)
    _write_merge_correction(src_name, into_name, reason)
    print(f"  Merged '{src_name}' into '{into_name}': {summary}")


# ---------------------------------------------------------------------------
# Component submenu
# ---------------------------------------------------------------------------

def _component_submenu(component_id: str, db_path: str) -> None:
    while True:
        conn = _connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM components WHERE component_id = ?", (component_id,))
        comp = cur.fetchone()
        conn.close()

        if comp is None:
            print(f"  Component {component_id} not found.")
            return

        print(f"\n  {comp['component_id']}  {comp['name']}")
        print(f"    molecular_weight : {comp['molecular_weight']} g/mol")
        print(f"    carbon_atoms     : {comp['carbon_atoms']}")
        pct_str = _fmt_carbon_status(comp['carbon_weight_pct'], comp['carbon_weight_pct_manual'])
        print(f"    carbon_weight_pct: {pct_str}")
        print(f"    needs_review     : {comp['needs_review']}")

        choices = ["Set molecular weight", "Set carbon atoms", "Set both"]
        if comp['carbon_weight_pct_manual']:
            choices.append("Clear manual override")
        choices.append("Merge with another component")
        choices.append("← Back")

        action = questionary.select(
            f"{comp['component_id']}  {comp['name']}",
            choices=choices,
        ).ask()

        if action is None or action == "← Back":
            return

        if action == "Merge with another component":
            _merge_component(component_id, db_path)
            # Re-query: if src was deleted (merge succeeded), exit; else loop back
            conn2 = _connect(db_path)
            cur2 = conn2.cursor()
            cur2.execute("SELECT 1 FROM components WHERE component_id = ?", (component_id,))
            still_exists = cur2.fetchone() is not None
            conn2.close()
            if not still_exists:
                return
            continue

        if action == "Clear manual override":
            print()
            carbon.set_component(component_id, clear_override=True, db_path=db_path)
            continue

        mw = None
        ca = None

        if action in ("Set molecular weight", "Set both"):
            raw = questionary.text("Molecular weight in g/mol:").ask()
            if raw is None:
                continue
            raw = raw.strip()
            if not raw:
                print("  Cancelled.")
                continue
            try:
                mw = float(raw)
            except ValueError:
                print("  Error: expected a number for molecular weight.")
                continue

        if action in ("Set carbon atoms", "Set both"):
            raw = questionary.text("Carbon atoms (integer):").ask()
            if raw is None:
                continue
            raw = raw.strip()
            if not raw:
                print("  Cancelled.")
                continue
            try:
                ca = int(raw)
            except ValueError:
                print("  Error: expected an integer for carbon atoms.")
                continue

        if mw is None and ca is None:
            continue

        print()
        carbon.set_component(component_id, molecular_weight=mw, carbon_atoms=ca, db_path=db_path)
        _update_corrections(comp['name'], mw, ca)


# ---------------------------------------------------------------------------
# Stream actions
# ---------------------------------------------------------------------------

def _connect_stream_to_flow(stream_id: str, db_path: str) -> bool:
    """Returns True if a flow was created, False if cancelled."""
    """Connect the given stream to a flow using the shared pick_stream_for_flow picker."""
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT s.stream_id, s.stream_name, s.direction, s.company_id,
               co.name AS company_name
        FROM streams s JOIN companies co USING (company_id)
        WHERE s.stream_id = ?
    """, (stream_id,))
    row = cur.fetchone()
    conn.close()

    if row is None:
        print(f"  Stream {stream_id} not found.")
        return False

    source_company_id = row['company_id']
    fixed_stream = {
        'stream_id':   row['stream_id'],
        'stream_name': row['stream_name'],
        'direction':   row['direction'],
    }

    print(f"\n  Source: {stream_id}  {row['stream_name']}  [{row['direction']}]  ({row['company_name']})")

    result = manage_companies_tui.pick_stream_for_flow(fixed_stream, source_company_id, db_path)
    if result is None:
        return False
    target_stream, target_company_id = result

    # Apply import-flow swap logic (mirrors _create_flow_menu in manage_companies_tui)
    if target_stream is None and fixed_stream['direction'] == 'input':
        from_sid, to_sid = None, fixed_stream['stream_id']
        from_cid, to_cid = target_company_id, source_company_id
    else:
        from_sid = fixed_stream['stream_id']
        to_sid   = target_stream['stream_id'] if target_stream else None
        from_cid, to_cid = source_company_id, target_company_id

    from_label = from_sid or f"[{from_cid}]"
    to_label   = to_sid   or f"[{to_cid}]"
    print(f"  Flow: {from_label} → {to_label}")

    confirmed = questionary.confirm("Create this flow?", default=False).ask()
    if not confirmed:
        print("  (cancelled)")
        return False

    manage_companies.create_flow(
        from_stream_id=from_sid,
        to_stream_id=to_sid,
        from_company_id=from_cid,
        to_company_id=to_cid,
        db_path=db_path,
    )
    print("  Flow created.")
    return True


def _review_stream_components(stream_id: str, db_path: str) -> None:
    """List all components in a stream; any can be selected for editing."""
    while True:
        conn = _connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT c.component_id, c.name, sc.fraction, sc.is_trace,
                   c.carbon_weight_pct, c.carbon_weight_pct_manual
            FROM stream_composition sc
            JOIN components c USING (component_id)
            WHERE sc.stream_id = ?
            ORDER BY sc.fraction DESC NULLS LAST
        """, (stream_id,))
        composition = cur.fetchall()
        conn.close()

        if not composition:
            print("  (no composition data for this stream)")
            return

        id_w   = max(len("ID"),       max(len(r['component_id']) for r in composition))
        name_w = min(40, max(len("Name"), max(len(r['name'])         for r in composition)))
        print(f"\n  {'ID':<{id_w}}  {'Name':<{name_w}}  {'fraction':>10}  carbon_status")
        print(f"  {'-'*id_w}  {'-'*name_w}  {'-'*10}  {'-'*20}")
        for r in composition:
            frac = f"{r['fraction']:.4f}" if r['fraction'] is not None else "    NULL"
            status = "trace" if r['is_trace'] else _fmt_carbon_status(
                r['carbon_weight_pct'], r['carbon_weight_pct_manual']
            )
            print(f"  {r['component_id']:<{id_w}}  {r['name'][:name_w]:<{name_w}}  {frac:>10}  {status}")
        print()

        def _comp_label(r):
            suffix = " [trace]" if r['is_trace'] else (
                " [missing carbon]" if r['carbon_weight_pct'] is None else ""
            )
            return f"{r['component_id']}  {r['name']}{suffix}"

        choices = [
            questionary.Choice(title=_comp_label(r), value=r['component_id'])
            for r in composition
        ] + [questionary.Choice(title="← Back", value="__back__")]

        nav = questionary.select(f"Components — stream {stream_id}", choices=choices).ask()
        if nav is None or nav == "__back__":
            return
        _component_submenu(nav, db_path)


# ---------------------------------------------------------------------------
# Stream detail
# ---------------------------------------------------------------------------

def _stream_detail(stream_id: str, db_path: str) -> None:
    while True:
        conn = _connect(db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT s.stream_name, s.direction, s.carbon_pct, s.carbon_pct_complete,
                   co.name AS company_name
            FROM streams s
            JOIN companies co USING (company_id)
            WHERE s.stream_id = ?
        """, (stream_id,))
        stream = cur.fetchone()

        cur.execute("""
            SELECT c.component_id, c.name, sc.fraction, sc.is_trace,
                   c.carbon_weight_pct, c.carbon_weight_pct_manual
            FROM stream_composition sc
            JOIN components c USING (component_id)
            WHERE sc.stream_id = ?
            ORDER BY sc.fraction DESC NULLS LAST
        """, (stream_id,))
        composition = cur.fetchall()

        cur.execute("""
            SELECT f.flow_id, f.status,
                   f.from_stream_id, f.to_stream_id,
                   fc.name AS from_company, tc.name AS to_company
            FROM flows f
            JOIN companies fc ON f.from_company_id = fc.company_id
            JOIN companies tc ON f.to_company_id   = tc.company_id
            WHERE f.from_stream_id = ? OR f.to_stream_id = ?
        """, (stream_id, stream_id))
        flows = cur.fetchall()
        conn.close()

        if stream is None:
            print(f"  Stream {stream_id} not found.")
            return

        complete_label = {1: "complete", 0: "partial", None: "no data"}.get(
            stream['carbon_pct_complete'], "?"
        )
        pct = f"{stream['carbon_pct']:.4f}" if stream['carbon_pct'] is not None else "NULL"
        print(f"\n  {stream_id}  {stream['stream_name']}  [{stream['direction']}]")
        print(f"  Company: {stream['company_name']}")
        print(f"  carbon_pct: {pct}  ({complete_label})")
        print()

        if composition:
            id_w   = max(len("ID"),       max(len(r['component_id']) for r in composition))
            name_w = min(40, max(len("Name"), max(len(r['name'])         for r in composition)))
            print(f"  {'ID':<{id_w}}  {'Name':<{name_w}}  {'fraction':>10}  carbon_status")
            print(f"  {'-'*id_w}  {'-'*name_w}  {'-'*10}  {'-'*20}")
            for r in composition:
                frac = f"{r['fraction']:.4f}" if r['fraction'] is not None else "    NULL"
                status = "trace" if r['is_trace'] else _fmt_carbon_status(
                    r['carbon_weight_pct'], r['carbon_weight_pct_manual']
                )
                print(f"  {r['component_id']:<{id_w}}  {r['name'][:name_w]:<{name_w}}  {frac:>10}  {status}")
        print()

        if flows:
            print("  Flows:")
            for f in flows:
                from_s = f['from_stream_id'] or f"[{f['from_company']}]"
                to_s   = f['to_stream_id']   or f"[{f['to_company']}]"
                print(f"    {f['flow_id']}  [{f['status']}]  {f['from_company']} → {f['to_company']}  ({from_s} → {to_s})")
        else:
            print("  Flows: (none)")
        print()

        action = questionary.select(
            f"Stream {stream_id}",
            choices=[
                questionary.Choice(title="Connect with flow",    value="connect"),
                questionary.Choice(title="Manage related flows", value="manage_flows"),
                questionary.Choice(title="Review components",    value="review"),
                questionary.Choice(title="← Back",              value="__back__"),
            ],
        ).ask()

        if action is None or action == "__back__":
            return
        if action == "connect":
            if _connect_stream_to_flow(stream_id, db_path):
                return  # flow created — go back to stream list
        elif action == "manage_flows":
            manage_flows_tui.run(db_path, stream_filter=stream_id)
        elif action == "review":
            _review_stream_components(stream_id, db_path)


# ---------------------------------------------------------------------------
# browse_components
# ---------------------------------------------------------------------------

_COMPONENT_FILTERS = [
    ('all',            'Show all'),
    ('missing_carbon', 'Show missing carbon info'),
    ('needs_review',   'Show needs review'),
]


def browse_components(db_path: str = DB_PATH, default_all: bool = False) -> None:
    filter_mode = 'all' if default_all else 'missing_carbon'

    while True:
        conn = _connect(db_path)
        cur = conn.cursor()

        if filter_mode == 'missing_carbon':
            where = "WHERE c.carbon_weight_pct IS NULL"
        elif filter_mode == 'needs_review':
            where = "WHERE c.needs_review = 1"
        else:
            where = ""

        cur.execute(f"""
            SELECT c.component_id, c.name, c.molecular_weight, c.carbon_atoms,
                   c.carbon_weight_pct, c.carbon_weight_pct_manual,
                   COUNT(sc.composition_id) AS stream_count
            FROM components c
            LEFT JOIN stream_composition sc ON c.component_id = sc.component_id AND sc.is_trace = 0
            {where}
            GROUP BY c.component_id
            ORDER BY stream_count DESC, c.name
        """)
        rows = cur.fetchall()
        conn.close()

        filter_items = [
            questionary.Choice(
                title=f"{'●' if filter_mode == key else '○'}  {label}",
                value=f"__filter_{key}__",
            )
            for key, label in _COMPONENT_FILTERS
        ]

        if rows:
            id_w = max(len("ID"), max(len(r['component_id']) for r in rows))
            name_w = min(40, max(len("Name"), max(len(r['name']) for r in rows)))

            def fmt_row(r, id_w=id_w, name_w=name_w):
                mw = f"{r['molecular_weight']:.3f}" if r['molecular_weight'] is not None else "   NULL"
                ca = str(r['carbon_atoms']) if r['carbon_atoms'] is not None else "NULL"
                pct_str = _fmt_carbon_status(r['carbon_weight_pct'], r['carbon_weight_pct_manual'])
                return (
                    f"{r['component_id']:<{id_w}}  {r['name'][:name_w]:<{name_w}}  "
                    f"MW={mw:>9} g/mol  C={ca:>3}  streams={r['stream_count']:>3}  {pct_str}"
                )

            comp_choices = [
                questionary.Choice(title=fmt_row(r), value=r['component_id'])
                for r in rows
            ]
        else:
            comp_choices = []

        count_labels = {'all': 'total', 'missing_carbon': 'missing carbon', 'needs_review': 'needs review'}
        count_label = f"{len(rows)} {count_labels[filter_mode]}"

        choices = (
            filter_items
            + [questionary.Separator()]
            + comp_choices
            + [questionary.Choice(title="← Back", value="__back__")]
        )

        choice = questionary.select(
            f"Browse Components ({count_label})",
            choices=choices,
        ).ask()

        if choice is None or choice == "__back__":
            return
        if isinstance(choice, str) and choice.startswith("__filter_"):
            filter_mode = choice[len("__filter_"):-2]
            continue

        _component_submenu(choice, db_path)


# ---------------------------------------------------------------------------
# browse_streams
# ---------------------------------------------------------------------------

_STREAM_FILTERS = [
    ('all',            'Show all'),
    ('missing_carbon', 'Show missing carbon info'),
    ('non_connected',  'Show non-connected'),
]


def browse_streams(db_path: str = DB_PATH, default_all: bool = False) -> None:
    filter_mode = 'all' if default_all else 'missing_carbon'

    while True:
        conn = _connect(db_path)
        cur = conn.cursor()

        if filter_mode == 'missing_carbon':
            where = "WHERE s.carbon_pct_complete != 1 OR s.carbon_pct_complete IS NULL"
        elif filter_mode == 'non_connected':
            where = """WHERE co.included = 1
            AND s.stream_id NOT IN (
                SELECT from_stream_id FROM flows WHERE from_stream_id IS NOT NULL
                UNION
                SELECT to_stream_id FROM flows WHERE to_stream_id IS NOT NULL
            )"""
        else:
            where = ""

        cur.execute(f"""
            SELECT s.stream_id, s.stream_name, s.direction, s.carbon_pct, s.carbon_pct_complete,
                   co.name AS company_name
            FROM streams s
            JOIN companies co USING (company_id)
            {where}
            ORDER BY co.name, s.stream_name
        """)
        rows = cur.fetchall()
        conn.close()

        # Radio-style filter items at the top
        filter_choices = [
            questionary.Choice(
                title=f"{'●' if filter_mode == key else '○'}  {label}",
                value=f"__filter_{key}__",
            )
            for key, label in _STREAM_FILTERS
        ]

        if rows:
            id_w      = max(len("ID"),      max(len(r['stream_id'])    for r in rows))
            name_w    = min(40, max(len("Name"),    max(len(r['stream_name']) for r in rows)))
            company_w = min(30, max(len("Company"), max(len(r['company_name']) for r in rows)))

            def fmt_row(r, id_w=id_w, name_w=name_w, company_w=company_w):
                pct = f"{r['carbon_pct']:.4f}" if r['carbon_pct'] is not None else "  NULL"
                complete = {1: "complete", 0: "partial ", None: "no data "}.get(
                    r['carbon_pct_complete'], "?       "
                )
                return (
                    f"{r['stream_id']:<{id_w}}  {r['stream_name'][:name_w]:<{name_w}}  "
                    f"{r['company_name'][:company_w]:<{company_w}}  [{r['direction'][:3]}]  "
                    f"carbon={pct}  {complete}"
                )

            stream_choices = [
                questionary.Choice(title=fmt_row(r), value=r['stream_id'])
                for r in rows
            ]
        else:
            stream_choices = []

        count_suffix = {
            'all':            'total',
            'missing_carbon': 'incomplete',
            'non_connected':  'non-connected',
        }[filter_mode]

        choices = (
            filter_choices
            + [questionary.Separator()]
            + stream_choices
            + [questionary.Separator(), questionary.Choice(title="← Back", value="__back__")]
        )

        choice = questionary.select(
            f"Browse Streams ({len(rows)} {count_suffix})",
            choices=choices,
        ).ask()

        if choice is None or choice == "__back__":
            return
        if choice and choice.startswith("__filter_"):
            filter_mode = choice[len("__filter_"):-2]  # strip prefix and trailing __
            continue

        _stream_detail(choice, db_path)


# ---------------------------------------------------------------------------
# Top-level entry points for main menu (default: show all)
# ---------------------------------------------------------------------------

def manage_components(db_path: str = DB_PATH) -> None:
    browse_components(db_path, default_all=True)


def manage_streams(db_path: str = DB_PATH) -> None:
    browse_streams(db_path, default_all=True)
