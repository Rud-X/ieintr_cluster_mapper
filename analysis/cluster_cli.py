"""
cluster_cli.py

Interactive TUI menu for the industrial cluster analysis tools.
Wraps carbon.py and normalize_streams.py via arrow-key navigation.

Usage:
    python analysis/cluster_cli.py
    python analysis/cluster_cli.py --db industrial_cluster.db
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import carbon
import carbon_tui
import explore
import manage_companies_tui
import manage_flows_tui
import normalize_streams
import questionary

DB_PATH = "industrial_cluster.db"

# ---------------------------------------------------------------------------
# Module registry
# ---------------------------------------------------------------------------

MODULES = [
    {
        "label": "Carbon Accounting",
        "actions": [
            {"label": "Status overview",    "fn": carbon.status,                "params": []},
            {"label": "Recalculate all",    "fn": carbon.recalculate,           "params": []},
            {"label": "Browse Components",  "fn": carbon_tui.browse_components, "params": []},
            {"label": "Browse Streams",     "fn": carbon_tui.browse_streams,    "params": []},
        ],
    },
    {
        "label": "Explore",
        "actions": [
            {"label": "Database summary",    "fn": explore.summary,       "params": []},
            {"label": "List companies",      "fn": explore.list_companies, "params": []},
            {"label": "Company full dump",   "fn": explore.show_company,
             "params": [{"prompt": "Company ID", "key": "company_id"}]},
            {"label": "Drill-down explorer", "fn": explore.drill_down,    "params": []},
        ],
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def collect_params(param_specs: list, db_path: str) -> dict | None:
    """
    Prompt for each param spec. Optional params are skipped if blank.
    Returns {"db_path": db_path, **collected} or None on cancel/invalid input.
    """
    collected = {}
    for spec in param_specs:
        raw = questionary.text(spec["prompt"] + ":").ask()
        if raw is None:  # Ctrl-C
            return None

        raw = raw.strip()

        if not raw:
            if spec.get("optional"):
                continue
            print(f"  (cancelled — {spec['prompt']} is required)")
            return None

        cast = spec.get("type")
        if cast is not None:
            try:
                raw = cast(raw)
            except (ValueError, TypeError):
                print(f"  Error: expected {cast.__name__} for '{spec['prompt']}'.")
                return None

        collected[spec["key"]] = raw

    return {"db_path": db_path, **collected}


def run_module(module: dict, db_path: str) -> None:
    """Show action selector for a module; loop until Back or Ctrl-C."""
    action_labels = [a["label"] for a in module["actions"]] + ["← Back"]

    while True:
        choice = questionary.select(
            module["label"],
            choices=action_labels,
        ).ask()

        if choice is None or choice == "← Back":
            return

        action = next(a for a in module["actions"] if a["label"] == choice)

        if action["params"]:
            kwargs = collect_params(action["params"], db_path)
            if kwargs is None:
                continue
        else:
            kwargs = {"db_path": db_path}

        print()
        try:
            action["fn"](**kwargs)
        except Exception as exc:
            print(f"Error: {exc}")
        print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(db_path: str = DB_PATH) -> None:
    module_labels = (
        ["Manage Companies", "Manage Flows", "Manage Streams", "Manage Components"]
        + [m["label"] for m in MODULES]
        + ["Quit"]
    )

    while True:
        choice = questionary.select(
            "Industrial Cluster Analysis",
            choices=module_labels,
        ).ask()

        if choice is None or choice == "Quit":
            print("Goodbye.")
            return

        if choice == "Manage Companies":
            manage_companies_tui.run(db_path)
            continue

        if choice == "Manage Flows":
            manage_flows_tui.run(db_path)
            continue

        if choice == "Manage Streams":
            carbon_tui.manage_streams(db_path)
            continue

        if choice == "Manage Components":
            carbon_tui.manage_components(db_path)
            continue

        module = next(m for m in MODULES if m["label"] == choice)
        run_module(module, db_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive TUI for industrial cluster analysis.")
    parser.add_argument("--db", default=DB_PATH, help="Path to SQLite database.")
    args = parser.parse_args()
    main(args.db)
