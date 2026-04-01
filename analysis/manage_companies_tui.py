"""
manage_companies_tui.py

TUI navigation for the "Manage Companies" feature.
Wraps manage_companies.py (DB logic) and normalize_streams.py via questionary menus.

Public entry points:
  run(db_path)                    — company list screen, called from cluster_cli.py
  pick_stream_for_flow(fixed_stream, exclude_company_id, db_path)
                                  — shared stream picker used by Create Flow and Manage Flows
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import questionary
from prompt_toolkit.formatted_text import FormattedText

import manage_companies
import normalize_streams

DB_PATH = "industrial_cluster.db"


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

_NODE_TYPE_TAG = {
    "company":       "     ",
    "import_source": "[IMP]",
    "export_sink":   "[EXP]",
    "waste_facility":"[WMF]",
}


def _make_company_choice(row, id_w: int, name_w: int, sec_w: int):
    """Build a questionary.Choice with colored Y/N fields for Inc and Nrm."""
    scale = f"{row['scaling_factor']:.3f}"     if row["scaling_factor"]     is not None else "  n/a"
    setp  = f"{row['normalize_setpoint']:.3f}" if row["normalize_setpoint"] is not None else "  1.000"

    node_type = row["node_type"] if row["node_type"] else "company"
    tag = _NODE_TYPE_TAG.get(node_type, "[???]")

    # Text up to and including right-pad for Inc (3-char right-aligned field)
    part1 = (
        f"{tag} "
        f"{row['company_id']:<{id_w}}  "
        f"{(row['name'] or ''):<{name_w}}  "
        f"{(row['sector'] or ''):<{sec_w}}  "
        "  "  # 2-space right-pad: Y/N sits in a 3-char column
    )
    inc_style = "ansigreen" if row["included"]           else "ansired"
    inc_text  = "Y"         if row["included"]           else "N"

    # Gap + scale + setpoint + gap + 2-space right-pad for Nrm (3-char right-aligned field)
    part2 = f"  {scale:>7}  {setp:>7}    "

    norm_active = row["normalize_stream_id"] or row["scaling_factor_manual"]
    norm_style = "ansigreen" if norm_active else "ansired"
    norm_text  = "Y"         if norm_active else "N"

    part3 = (
        f"  {row['stream_count']:>8}  "
        f"{row['flow_count']:>6}  "
        f"{row['streams_in_flows']:>8}"
    )
    title = FormattedText([
        ("", part1),
        (inc_style, inc_text),
        ("", part2),
        (norm_style, norm_text),
        ("", part3),
    ])
    return questionary.Choice(title=title, value=row["company_id"])


def _fmt_stream_row(s, id_w: int, name_w: int, type_w: int) -> str:
    flow   = f"{s['norm_flow_kton_per_year']:.3f}" if s["norm_flow_kton_per_year"] is not None else "n/a"
    carbon = f"{s['carbon_pct']:.1%}"         if s["carbon_pct"] is not None        else "  n/a"
    return (
        f"{s['stream_id']:<{id_w}}  "
        f"[{s['direction']:<6}]  "
        f"{(s['stream_name'] or ''):<{name_w}}  "
        f"{(s['stream_type'] or ''):<{type_w}}  "
        f"{flow:>10} kton/yr  "
        f"C={carbon}"
    )


# ---------------------------------------------------------------------------
# Public entry point — company list
# ---------------------------------------------------------------------------

def run(db_path: str = DB_PATH) -> None:
    """Company list screen — top-level loop for 'Manage Companies'."""
    while True:
        rows = manage_companies.get_all_companies(db_path)

        if rows:
            id_w   = max(len("ID"),     max(len(r["company_id"]) for r in rows))
            name_w = max(len("Name"),   max(len(r["name"] or "") for r in rows))
            sec_w  = max(len("Sector"), max(len(r["sector"] or "") for r in rows))

            print()
            print(
                f"  {'Type':<5} {'ID':<{id_w}}  {'Name':<{name_w}}  {'Sector':<{sec_w}}  "
                f"{'Inc':>3}  {'Scale':>7}  {'Setp':>7}  {'Nrm':>3}  "
                f"{'#Streams':>8}  {'#Flows':>6}  {'#InFlows':>8}"
            )
            choices = [_make_company_choice(r, id_w, name_w, sec_w) for r in rows]
        else:
            choices = []

        choices += ["+ Add Company", "+ Add External Node", "Quick Toggle Included", "← Back"]

        # .ask() returns company_id (Choice.value) for company rows, or the string for others
        choice = questionary.select("Manage Companies", choices=choices).ask()
        if choice is None or choice == "← Back":
            return

        if choice == "+ Add Company":
            _add_company(db_path)
            continue

        if choice == "+ Add External Node":
            _add_external_node(db_path)
            continue

        if choice == "Quick Toggle Included":
            _quick_toggle_included(db_path)
            continue

        # choice is the company_id directly (from Choice.value)
        _company_submenu(choice, db_path)


# ---------------------------------------------------------------------------
# Add company
# ---------------------------------------------------------------------------

def _add_company(db_path: str) -> None:
    name = questionary.text("Company name:").ask()
    if name is None:
        return
    name = name.strip()
    if not name:
        print("  (cancelled — name is required)")
        return
    try:
        company_id = manage_companies.add_company(name, db_path)
        print(f"\n  Added company {company_id}: {name}\n")
    except Exception as exc:
        print(f"  Error: {exc}")


def _add_external_node(db_path: str) -> None:
    node_type = questionary.select(
        "External node type:",
        choices=[
            questionary.Choice(title="[IMP] Import source   — raw material from outside the cluster", value="import_source"),
            questionary.Choice(title="[EXP] Export sink     — product or material sold outside the cluster", value="export_sink"),
            questionary.Choice(title="[WMF] Waste facility  — material sink (no outflow modelled)", value="waste_facility"),
            "← Back",
        ],
    ).ask()

    if node_type is None or node_type == "← Back":
        return

    name = questionary.text("Node name:").ask()
    if name is None:
        return
    name = name.strip()
    if not name:
        print("  (cancelled — name is required)")
        return

    try:
        node_id = manage_companies.add_external_node(name, node_type, db_path)
        print(f"\n  Added external node {node_id} [{node_type}]: {name}\n")
    except Exception as exc:
        print(f"  Error: {exc}")


# ---------------------------------------------------------------------------
# Quick toggle included
# ---------------------------------------------------------------------------

def _quick_toggle_included(db_path: str) -> None:
    rows = manage_companies.get_all_companies(db_path)
    if not rows:
        print("  (no companies)")
        return

    choices = [
        questionary.Choice(
            title=f"{r['company_id']}  {r['name'] or ''}",
            value=r["company_id"],
            checked=bool(r["included"]),
        )
        for r in rows
    ]

    result = questionary.checkbox(
        "Toggle inclusion  (Space=toggle, Enter=confirm, Ctrl-C=cancel)",
        choices=choices,
    ).ask()

    if result is None:  # Ctrl-C
        return

    newly_included = set(result)
    changed = 0
    for r in rows:
        was_included = bool(r["included"])
        now_included = r["company_id"] in newly_included
        if was_included != now_included:
            manage_companies.toggle_company_included(r["company_id"], db_path)
            changed += 1

    print(f"\n  Updated {changed} company/companies.\n")


# ---------------------------------------------------------------------------
# Company sub-menu
# ---------------------------------------------------------------------------

def _company_submenu(company_id: str, db_path: str) -> None:
    company = manage_companies.get_company(company_id, db_path)
    if company is None:
        print(f"  Company '{company_id}' not found.")
        return

    node_type = company["node_type"] if company["node_type"] else "company"
    is_external = node_type != "company"

    if is_external:
        choices = ["Explore", "Create Flow", "Manage Flows", "Toggle Included",
                   "Delete...", "← Back"]
    else:
        choices = ["Explore", "Normalization", "Create Flow",
                   "Manage Flows", "Toggle Included", "Delete...", "← Back"]

    while True:
        company = manage_companies.get_company(company_id, db_path)
        included_str = "included" if company["included"] else "excluded"
        tag = _NODE_TYPE_TAG.get(node_type, "")
        label = f"{tag} {company['company_id']}  {company['name']}  [{included_str}]"

        choice = questionary.select(label, choices=choices).ask()
        if choice is None or choice == "← Back":
            return
        if choice == "Explore":
            _explore_company(company_id, db_path)
        elif choice == "Normalization":
            _normalization_menu(company_id, db_path)
        elif choice == "Create Flow":
            _create_flow_menu(company_id, db_path)
        elif choice == "Toggle Included":
            new_val = manage_companies.toggle_company_included(company_id, db_path)
            state = "included" if new_val else "excluded"
            print(f"\n  {company_id} is now {state}.\n")
        elif choice == "Manage Flows":
            import manage_flows_tui
            manage_flows_tui.run(db_path, company_filter=company_id)
        elif choice == "Delete...":
            deleted = _delete_company_menu(company_id, node_type, db_path)
            if deleted:
                return  # company no longer exists


# ---------------------------------------------------------------------------
# Delete company
# ---------------------------------------------------------------------------

def _delete_company_menu(company_id: str, node_type: str, db_path: str) -> bool:
    """Prompt for deletion of a company or external node.

    Blocks if the company has attached streams or flows.
    Returns True if the company was deleted, False otherwise.
    """
    counts = manage_companies.get_company_flow_counts(company_id, db_path)
    streams = manage_companies.get_company_streams(company_id, db_path)
    n_streams = len(streams)
    n_flows   = counts["total_flows"]

    print()
    if n_streams > 0 or n_flows > 0:
        parts = []
        if n_streams:
            parts.append(f"{n_streams} stream{'s' if n_streams != 1 else ''}")
        if n_flows:
            parts.append(f"{n_flows} flow{'s' if n_flows != 1 else ''}")
        print(f"  Cannot delete: {' and '.join(parts)} attached.")
        print("  Remove them first, then retry.")
        print()
        return False

    company = manage_companies.get_company(company_id, db_path)
    name    = company["name"] if company else company_id
    print(f"  About to permanently delete: {company_id}  {name}")
    print()

    raw = questionary.text("Type 'delete company' to confirm:").ask()
    if raw is None:
        print("  (cancelled)")
        return False

    if raw.strip() != "delete company":
        print("  (cancelled — text did not match)")
        return False

    try:
        manage_companies.delete_company(company_id, db_path)
    except ValueError as exc:
        print(f"\n  Error: {exc}\n")
        return False

    print(f"\n  {company_id} ({name}) deleted.\n")

    if node_type != "company":
        print(
            "  Reminder: if this node was declared in migrations/seed_manual_companies.py,\n"
            "  remove the corresponding ExternalNode(...) line to keep the seed file in sync.\n"
        )

    return True


# ---------------------------------------------------------------------------
# Explore
# ---------------------------------------------------------------------------

def _print_company_header(company_id: str, db_path: str) -> None:
    h = manage_companies.get_company_metadata_header(company_id, db_path)
    if not h:
        return
    norm_str = (
        f"{h['normalize_stream_id']} ({h['normalize_stream_name']})"
        if h["normalize_stream_id"]
        else "(none set)"
    )
    print()
    print(f"  Inputs: {h['n_input']}  |  Waste: {h['n_waste']}  |  "
          f"Products: {h['n_product']}  |  Flows: {h['n_flows']}")
    print(f"  Normalization: {norm_str}")
    print(f"  Included: {'Y' if h['included'] else 'N'}")
    print()


def _explore_company(company_id: str, db_path: str) -> None:
    while True:
        _print_company_header(company_id, db_path)

        streams = manage_companies.get_company_streams(company_id, db_path)
        if not streams:
            print("  (no streams)")
            questionary.select("", choices=["← Back"]).ask()
            return

        id_w   = max(len("ID"),   max(len(s["stream_id"]) for s in streams))
        name_w = max(len("Name"), max(len(s["stream_name"] or "") for s in streams))
        type_w = max(len("Type"), max(len(s["stream_type"] or "") for s in streams))

        stream_choices = [_fmt_stream_row(s, id_w, name_w, type_w) for s in streams]
        stream_choices.append("← Back")

        choice = questionary.select(
            f"Streams — {company_id}",
            choices=stream_choices,
        ).ask()

        if choice is None or choice == "← Back":
            return

        stream_id = choice.split()[0]
        _show_stream_detail(stream_id, db_path)


def _show_stream_detail(stream_id: str, db_path: str) -> None:
    stream = manage_companies.get_stream(stream_id, db_path)
    comps  = manage_companies.get_stream_composition(stream_id, db_path)

    norm_str   = f"{stream['norm_flow_kton_per_year']:.3f}" if stream["norm_flow_kton_per_year"] is not None else "n/a"
    raw_str    = f"{stream['flow_kton_per_year']:.3f}"     if stream["flow_kton_per_year"]      is not None else "n/a"
    carbon_str = f"{stream['carbon_pct']:.3f}"             if stream["carbon_pct"]              is not None else "n/a"

    print()
    print(f"  Stream  : {stream['stream_id']}  {stream['stream_name']}")
    print(f"  Company : {stream['company_id']}")
    print(f"  Dir     : {stream['direction']}  Type: {stream['stream_type']}")
    print(f"  Flow    : {norm_str} kton/yr (norm)   raw: {raw_str} kton/yr")
    print(f"  carbon_pct={carbon_str}  complete={stream['carbon_pct_complete']}")
    print()

    if not comps:
        print("  (no composition data)")
    else:
        id_w   = max(len("Comp ID"), max(len(c["component_id"]) for c in comps))
        name_w = max(len("Name"),    max(len(c["name"] or "")   for c in comps))
        header = (
            f"  {'Comp ID':<{id_w}}  {'Name':<{name_w}}  "
            f"{'Fraction':>10}  {'Trace':>5}  {'C-frac':>10}"
        )
        print(header)
        print("  " + "-" * (len(header) - 2))
        for c in comps:
            frac   = f"{c['fraction']:.3f}"         if c["fraction"]        is not None else ""
            cfrac  = f"{c['carbon_fraction']:.3f}"  if c["carbon_fraction"] is not None else ""
            print(
                f"  {c['component_id']:<{id_w}}  "
                f"{(c['name'] or ''):<{name_w}}  "
                f"{frac:>10}  "
                f"{'Y' if c['is_trace'] else 'N':>5}  "
                f"{cfrac:>10}"
            )
    print()

    questionary.select("Stream detail", choices=["← Back to streams"]).ask()


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def _normalization_menu(company_id: str, db_path: str) -> None:
    while True:
        company = manage_companies.get_company(company_id, db_path)
        norm_id    = company["normalize_stream_id"] if company else None
        is_manual  = bool(company["scaling_factor_manual"]) if company else False
        sf         = company["scaling_factor"] if company else None
        setpoint   = company["normalize_setpoint"] if company["normalize_setpoint"] is not None else 1.0
        setp_str   = f"{setpoint:.3f}"

        print()
        if is_manual:
            sf_str = f"{sf:.6f}" if sf is not None else "n/a"
            print(f"  Scaling factor: {sf_str}  [MANUAL]")
            print(f"  Normalization reference: (disabled — custom factor active)")
        elif norm_id:
            ref_stream = manage_companies.get_stream(norm_id, db_path)
            ref_name   = ref_stream["stream_name"]             if ref_stream else "?"
            ref_flow   = ref_stream["flow_kton_per_year"]      if ref_stream else None
            ref_norm   = ref_stream["norm_flow_kton_per_year"] if ref_stream else None
            raw_str    = f"{ref_flow:.3f}"  if ref_flow  is not None else "n/a"
            norm_str   = f"{ref_norm:.3f}"  if ref_norm  is not None else "n/a"
            scale      = setpoint / ref_flow if ref_flow  else None
            scale_str  = f"{scale:.3f}"     if scale     is not None else "n/a"
            print(f"  Normalization reference: {norm_id} ({ref_name})")
            print(f"  Unscaled flow:  {raw_str} kton/yr")
            print(f"  Scaled flow:    {norm_str}   (should be {setp_str})")
            print(f"  Scaling factor: {scale_str}  (= {setp_str} / {raw_str})")
        else:
            print("  Normalization reference: (none set)")
        print(f"  Reference setpoint: {setp_str}")
        print()

        stream_choice = questionary.Choice(
            "Select normalization stream",
            disabled="Custom scaling factor active" if is_manual else None,
        )
        choices = [stream_choice, "Recalculate normalization",
                   "Change reference setpoint", "Set custom scaling factor"]
        if is_manual:
            choices.append("Clear custom scaling factor")
        choices.append("← Back")

        choice = questionary.select(
            f"Normalization — {company_id}",
            choices=choices,
        ).ask()

        if choice is None or choice == "← Back":
            return
        if choice == "Select normalization stream":
            _select_norm_stream(company_id, db_path)
        elif choice == "Recalculate normalization":
            print()
            normalize_streams.normalize(db_path=db_path)
            print()
        elif choice == "Change reference setpoint":
            _change_setpoint(company_id, db_path)
        elif choice == "Set custom scaling factor":
            _set_custom_factor(company_id, db_path)
        elif choice == "Clear custom scaling factor":
            print()
            normalize_streams.clear_custom_factor(company_id=company_id, db_path=db_path)
            normalize_streams.normalize(db_path=db_path)
            print()


def _select_norm_stream(company_id: str, db_path: str) -> None:
    candidates = manage_companies.get_normalization_candidates(company_id, db_path)
    if not candidates:
        print("  (no valid streams available for normalization)")
        return

    company       = manage_companies.get_company(company_id, db_path)
    current_ref   = company["normalize_stream_id"] if company else None

    choices = []
    for s in candidates:
        marker    = "[*] " if s["stream_id"] == current_ref else "    "
        flow_str  = f"{s['flow_kton_per_year']:.3f}"
        dir_tag   = f"[{s['direction'][:3]}]"
        choices.append(f"{marker}{s['stream_id']}  {dir_tag}  {flow_str} kton/yr  {s['stream_name']}")
    choices.append("← Back")

    choice = questionary.select(
        "Select reference stream ([*] = current)",
        choices=choices,
    ).ask()

    if choice is None or choice == "← Back":
        return

    # Extract stream_id: skip the 4-char marker prefix then take first token
    stream_id = choice[4:].split()[0]

    print()
    if stream_id == current_ref:
        normalize_streams.clear_reference(company_id=company_id, db_path=db_path)
    else:
        normalize_streams.set_reference(company_id=company_id, stream_id=stream_id, db_path=db_path)

    normalize_streams.normalize(db_path=db_path)
    print()


def _set_custom_factor(company_id: str, db_path: str) -> None:
    company = manage_companies.get_company(company_id, db_path)
    current = company["scaling_factor"] if company else None
    current_str = f"{current:.6f}" if current is not None else "n/a"
    print(f"\n  Current scaling factor: {current_str}")
    raw = questionary.text("New custom scaling factor (must be > 0):").ask()
    if raw is None:
        return
    raw = raw.strip()
    if not raw:
        return
    try:
        new_val = float(raw)
    except ValueError:
        print("  Error: expected a number.")
        return
    if new_val <= 0:
        print("  Error: scaling factor must be > 0.")
        return
    print()
    normalize_streams.set_custom_factor(company_id=company_id, value=new_val, db_path=db_path)
    print()


def _change_setpoint(company_id: str, db_path: str) -> None:
    company = manage_companies.get_company(company_id, db_path)
    current = company["normalize_setpoint"] if company["normalize_setpoint"] is not None else 1.0
    print(f"\n  Current reference setpoint: {current:.3f}")
    raw = questionary.text("New setpoint (blank = reset to 1.0):").ask()
    if raw is None:
        return
    raw = raw.strip()
    if not raw:
        new_val = 1.0
    else:
        try:
            new_val = float(raw)
        except ValueError:
            print("  Error: expected a number.")
            return
    print()
    manage_companies.set_normalize_setpoint(company_id, new_val, db_path)
    normalize_streams.normalize(db_path=db_path)
    print()


# ---------------------------------------------------------------------------
# Create Flow
# ---------------------------------------------------------------------------

def _create_flow_menu(company_id: str, db_path: str) -> None:
    counts  = manage_companies.get_company_flow_counts(company_id, db_path)
    streams = manage_companies.get_company_streams(company_id, db_path)

    print()
    print(f"  Flows for this company: {counts['total_flows']}")
    print(f"  Unconnected streams:    {counts['unconnected_streams']}")
    print()

    if not streams:
        print("  (this company has no streams)")
        questionary.select("", choices=["← Back"]).ask()
        return

    id_w   = max(len("ID"),   max(len(s["stream_id"]) for s in streams))
    name_w = max(len("Name"), max(len(s["stream_name"] or "") for s in streams))
    type_w = max(len("Type"), max(len(s["stream_type"] or "") for s in streams))

    stream_choices = [_fmt_stream_row(s, id_w, name_w, type_w) for s in streams]
    stream_choices.append("← Back")

    choice = questionary.select(
        f"Select source stream — {company_id}",
        choices=stream_choices,
    ).ask()

    if choice is None or choice == "← Back":
        return

    source_stream_id = choice.split()[0]
    source_stream    = manage_companies.get_stream(source_stream_id, db_path)

    _pick_target_for_flow(source_stream, company_id, db_path)


def _pick_target_for_flow(source_stream, source_company_id: str, db_path: str) -> None:
    result = pick_stream_for_flow(source_stream, source_company_id, db_path)
    if result is None:
        return

    target_stream, target_company_id = result

    print()
    print(f"  From: {source_stream['stream_id']} [{source_stream['direction']}] "
          f"{source_stream['stream_name']}  ({source_company_id})")

    if target_stream is not None:
        print(f"  To:   {target_stream['stream_id']} [{target_stream['direction']}] "
              f"{target_stream['stream_name']}  ({target_company_id})")
        confirm_text = f"Create flow {source_stream['stream_id']} → {target_stream['stream_id']}?"
    else:
        ext = manage_companies.get_company(target_company_id, db_path)
        ext_label = f"[{ext['node_type']}] {ext['name']}" if ext else target_company_id
        print(f"  To:   {ext_label}  ({target_company_id})  (external — no stream)")
        confirm_text = f"Create flow {source_stream['stream_id']} → {target_company_id} (external)?"
    print()

    confirm = questionary.confirm(confirm_text).ask()

    if confirm:
        # For import flows: source_stream is the TO side (it's an input stream being connected
        # to an import_source). Swap from/to so the flow reads: import_source → company.input
        if target_stream is None and source_stream["direction"] == "input":
            from_sid  = None
            to_sid    = source_stream["stream_id"]
            from_cid  = target_company_id
            to_cid    = source_company_id
        else:
            from_sid  = source_stream["stream_id"]
            to_sid    = target_stream["stream_id"] if target_stream else None
            from_cid  = source_company_id
            to_cid    = target_company_id

        try:
            flow_id = manage_companies.create_flow(
                from_stream_id=from_sid,
                to_stream_id=to_sid,
                from_company_id=from_cid,
                to_company_id=to_cid,
                db_path=db_path,
            )
            print(f"\n  Flow {flow_id} created (candidate).\n")
        except ValueError as exc:
            print(f"\n  {exc}\n")
    else:
        print("  (cancelled)")


# ---------------------------------------------------------------------------
# Shared stream picker (also used by manage_flows_tui)
# ---------------------------------------------------------------------------

def pick_stream_for_flow(fixed_stream, exclude_company_id: str, db_path: str):
    """
    Interactive company → stream picker. Finds a stream of opposite direction
    to fixed_stream, excluding exclude_company_id's company list.

    For output streams: also offers export_sink and waste_facility external nodes.
    For input streams: also offers import_source external nodes.
    Selecting an external node returns (None, external_company_id).

    Returns (target_stream_row, target_company_id) or None on cancel.
    Does NOT show a confirm prompt — caller handles that.
    """
    opposite = "input" if fixed_stream["direction"] == "output" else "output"

    # External node types relevant to this stream direction
    if fixed_stream["direction"] == "output":
        ext_types = ["export_sink", "waste_facility"]
    else:
        ext_types = ["import_source"]

    all_others = manage_companies.get_other_companies(exclude_company_id, db_path)
    regular_companies = [c for c in all_others if c["node_type"] == "company"]
    external_nodes    = [c for c in all_others if c["node_type"] in ext_types]

    if not regular_companies and not external_nodes:
        print("  (no companies or external nodes in the database)")
        return None

    _CONNECT_EXTERNAL = "→ Connect to external node"

    while True:
        print()
        print(f"  Fixed: {fixed_stream['stream_id']} [{fixed_stream['direction']}] "
              f"{fixed_stream['stream_name']}  →  looking for [{opposite}] streams")
        print()

        id_w   = max(len("ID"),   max((len(c["company_id"]) for c in regular_companies), default=2))
        name_w = max(len("Name"), max((len(c["name"] or "") for c in regular_companies), default=4))

        company_choices = [
            f"{c['company_id']:<{id_w}}  {(c['name'] or ''):<{name_w}}  {c['sector'] or ''}"
            for c in regular_companies
        ]
        if external_nodes:
            company_choices.append(_CONNECT_EXTERNAL)
        company_choices.append("← Back")

        choice = questionary.select("Select target company", choices=company_choices).ask()
        if choice is None or choice == "← Back":
            return None

        # --- External node branch ---
        if choice == _CONNECT_EXTERNAL:
            ext_id_w   = max(len("ID"),   max(len(e["company_id"]) for e in external_nodes))
            ext_name_w = max(len("Name"), max(len(e["name"] or "") for e in external_nodes))
            ext_choices = [
                f"{_NODE_TYPE_TAG.get(e['node_type'], '[???]')} "
                f"{e['company_id']:<{ext_id_w}}  {(e['name'] or ''):<{ext_name_w}}"
                for e in external_nodes
            ]
            ext_choices.append("← Back (different company)")

            e_choice = questionary.select(
                "Select external node", choices=ext_choices
            ).ask()

            if e_choice is None or e_choice.startswith("← Back"):
                continue

            # company_id is the second whitespace-delimited token (after the tag)
            ext_company_id = e_choice.split()[1]
            return (None, ext_company_id)

        # --- Regular company branch ---
        target_company_id = choice.split()[0]

        target_streams = manage_companies.get_streams_by_direction(
            target_company_id, opposite, db_path
        )

        if not target_streams:
            company_obj = manage_companies.get_company(target_company_id, db_path)
            name = company_obj["name"] if company_obj else target_company_id
            print(f"\n  (no {opposite} streams at {name} — choose a different company)\n")
            continue

        tid_w   = max(len("ID"),   max(len(s["stream_id"]) for s in target_streams))
        tname_w = max(len("Name"), max(len(s["stream_name"] or "") for s in target_streams))
        ttype_w = max(len("Type"), max(len(s["stream_type"] or "") for s in target_streams))

        target_choices = [_fmt_stream_row(s, tid_w, tname_w, ttype_w) for s in target_streams]
        target_choices.append("← Back (different company)")

        t_choice = questionary.select(
            f"Select target stream at {target_company_id}",
            choices=target_choices,
        ).ask()

        if t_choice is None or t_choice.startswith("← Back"):
            continue

        target_stream_id = t_choice.split()[0]
        target_stream    = manage_companies.get_stream(target_stream_id, db_path)
        return (target_stream, target_company_id)
