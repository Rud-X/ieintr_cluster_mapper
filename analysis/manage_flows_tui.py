"""
manage_flows_tui.py

TUI for browsing and editing flows.

Public entry point:
  run(db_path, company_filter=None)
    — shows flow table; if company_filter is set, shows only flows for that company
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import questionary

import manage_companies
import manage_companies_tui

DB_PATH = "industrial_cluster.db"


# ---------------------------------------------------------------------------
# Formatting helper
# ---------------------------------------------------------------------------

def _fmt_flow_row(f, fid_w: int, fc_w: int, fs_w: int, tc_w: int, ts_w: int) -> str:
    from_sid  = f["from_stream_id"]  or "-"
    from_name = f["from_stream_name"] or f"(external: {f['from_node_type']})"
    to_sid    = f["to_stream_id"]    or "-"
    to_name   = f["to_stream_name"]  or f"(external: {f['to_node_type']})"
    return (
        f"{f['flow_id']:<{fid_w}}  "
        f"{f['from_company_id']:<{fc_w}} {from_sid:<{fs_w}} "
        f"[{from_name}]"
        f"  →  "
        f"{f['to_company_id']:<{tc_w}} {to_sid:<{ts_w}} "
        f"[{to_name}]"
        f"  {f['status']}"
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(db_path: str = DB_PATH, company_filter: str = None, stream_filter: str = None) -> None:
    """Flow table screen. Pass company_filter or stream_filter to narrow the list."""
    while True:
        if stream_filter:
            flows = manage_companies.get_flows_for_stream(stream_filter, db_path)
            title = f"Flows — stream {stream_filter}"
        elif company_filter:
            flows = manage_companies.get_flows_for_company(company_filter, db_path)
            title = f"Flows — {company_filter}"
        else:
            flows = manage_companies.get_all_flows(db_path)
            title = "Manage Flows"

        if not flows:
            print("\n  (no flows)\n")
            questionary.select(title, choices=["← Back"]).ask()
            return

        fid_w = max(len("ID"),      max(len(f["flow_id"]) for f in flows))
        fc_w  = max(len("From Co"), max(len(f["from_company_id"]) for f in flows))
        fs_w  = max(len("Stream"),  max(len(f["from_stream_id"] or "-") for f in flows))
        tc_w  = max(len("To Co"),   max(len(f["to_company_id"]) for f in flows))
        ts_w  = max(len("Stream"),  max(len(f["to_stream_id"]   or "-") for f in flows))

        choices = [_fmt_flow_row(f, fid_w, fc_w, fs_w, tc_w, ts_w) for f in flows]
        choices.append("← Back")

        choice = questionary.select(title, choices=choices).ask()
        if choice is None or choice == "← Back":
            return

        flow_id = choice.split()[0]
        _flow_submenu(flow_id, db_path)


# ---------------------------------------------------------------------------
# Flow sub-menu
# ---------------------------------------------------------------------------

def _flow_submenu(flow_id: str, db_path: str) -> None:
    while True:
        flow = manage_companies.get_flow(flow_id, db_path)
        if flow is None:
            print(f"  Flow '{flow_id}' not found.")
            return

        print()
        print(f"  Flow  : {flow['flow_id']}  [{flow['status']}]  type={flow['flow_type']}")
        if flow["from_stream_id"]:
            from_detail = (f"{flow['from_stream_id']} ({flow['from_stream_name']}) "
                           f"[{flow['from_direction']}]")
        else:
            from_detail = f"(external — {flow['from_node_type']})"
        if flow["to_stream_id"]:
            to_detail = (f"{flow['to_stream_id']} ({flow['to_stream_name']}) "
                         f"[{flow['to_direction']}]")
        else:
            to_detail = f"(external — {flow['to_node_type']})"
        print(f"  From  : {flow['from_company_id']} ({flow['from_company_name']}) — {from_detail}")
        print(f"  To    : {flow['to_company_id']} ({flow['to_company_name']}) — {to_detail}")
        print()

        choice = questionary.select(
            f"Flow {flow_id}",
            choices=["Change outflow stream", "Change inflow stream",
                     "Delete flow", "← Back"],
        ).ask()

        if choice is None or choice == "← Back":
            return
        elif choice == "Change outflow stream":
            _change_from_stream(flow_id, db_path)
        elif choice == "Change inflow stream":
            _change_to_stream(flow_id, db_path)
        elif choice == "Delete flow":
            deleted = _delete_flow(flow_id, db_path)
            if deleted:
                return  # flow no longer exists, exit sub-menu


# ---------------------------------------------------------------------------
# Change stream helpers
# ---------------------------------------------------------------------------

def _change_from_stream(flow_id: str, db_path: str) -> None:
    """Replace the outflow (source) side. Fixed side = inflow (to_stream)."""
    flow = manage_companies.get_flow(flow_id, db_path)
    if flow is None:
        return

    if flow["to_stream_id"]:
        fixed_stream = manage_companies.get_stream(flow["to_stream_id"], db_path)
        if fixed_stream is None:
            print(f"  Error: inflow stream '{flow['to_stream_id']}' not found.")
            return
    else:
        # Destination is an external node — fake a minimal input-direction stream dict
        fixed_stream = {
            "stream_id": "(external)",
            "stream_name": flow["to_company_name"],
            "direction": "input",
        }

    result = manage_companies_tui.pick_stream_for_flow(
        fixed_stream, flow["to_company_id"], db_path
    )
    if result is None:
        return

    new_stream, new_company_id = result

    print()
    if new_stream is not None:
        print(f"  New outflow: {new_stream['stream_id']} ({new_stream['stream_name']}) "
              f"at {new_company_id}")
        confirm_text = f"Update flow {flow_id}: replace outflow with {new_stream['stream_id']}?"
        new_stream_id = new_stream["stream_id"]
    else:
        ext = manage_companies.get_company(new_company_id, db_path)
        ext_label = f"[{ext['node_type']}] {ext['name']}" if ext else new_company_id
        print(f"  New outflow: {ext_label}  ({new_company_id})  (external)")
        confirm_text = f"Update flow {flow_id}: replace outflow with {new_company_id} (external)?"
        new_stream_id = None
    print()

    confirm = questionary.confirm(confirm_text).ask()

    if confirm:
        manage_companies.update_flow_from_stream(
            flow_id, new_stream_id, new_company_id, db_path
        )
        print(f"\n  Flow {flow_id} updated.\n")
    else:
        print("  (cancelled)")


def _change_to_stream(flow_id: str, db_path: str) -> None:
    """Replace the inflow (destination) side. Fixed side = outflow (from_stream)."""
    flow = manage_companies.get_flow(flow_id, db_path)
    if flow is None:
        return

    if flow["from_stream_id"]:
        fixed_stream = manage_companies.get_stream(flow["from_stream_id"], db_path)
        if fixed_stream is None:
            print(f"  Error: outflow stream '{flow['from_stream_id']}' not found.")
            return
    else:
        # Source is an external import node — fake a minimal output-direction stream dict
        fixed_stream = {
            "stream_id": "(external)",
            "stream_name": flow["from_company_name"],
            "direction": "output",
        }

    result = manage_companies_tui.pick_stream_for_flow(
        fixed_stream, flow["from_company_id"], db_path
    )
    if result is None:
        return

    new_stream, new_company_id = result

    print()
    if new_stream is not None:
        print(f"  New inflow: {new_stream['stream_id']} ({new_stream['stream_name']}) "
              f"at {new_company_id}")
        confirm_text = f"Update flow {flow_id}: replace inflow with {new_stream['stream_id']}?"
        new_stream_id = new_stream["stream_id"]
    else:
        ext = manage_companies.get_company(new_company_id, db_path)
        ext_label = f"[{ext['node_type']}] {ext['name']}" if ext else new_company_id
        print(f"  New inflow: {ext_label}  ({new_company_id})  (external)")
        confirm_text = f"Update flow {flow_id}: replace inflow with {new_company_id} (external)?"
        new_stream_id = None
    print()

    confirm = questionary.confirm(confirm_text).ask()

    if confirm:
        manage_companies.update_flow_to_stream(
            flow_id, new_stream_id, new_company_id, db_path
        )
        print(f"\n  Flow {flow_id} updated.\n")
    else:
        print("  (cancelled)")


def _delete_flow(flow_id: str, db_path: str) -> bool:
    """Confirm and delete a flow. Returns True if deleted."""
    confirm = questionary.confirm(
        f"Delete flow {flow_id}? This cannot be undone."
    ).ask()

    if confirm:
        manage_companies.delete_flow(flow_id, db_path)
        print(f"\n  Flow {flow_id} deleted.\n")
        return True

    print("  (cancelled)")
    return False
