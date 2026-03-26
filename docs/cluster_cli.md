# cluster_cli.py — Interactive TUI Menu

`analysis/cluster_cli.py` is a single interactive entry point that wraps
`carbon.py` and `normalize_streams.py` behind arrow-key menus.

## Usage

```bash
python analysis/cluster_cli.py              # default DB (industrial_cluster.db)
python analysis/cluster_cli.py --db <path>  # custom DB path
```

## Navigation

- **Arrow keys** to move, **Enter** to select.
- **Ctrl-C** or **"Quit"** at any level exits cleanly.
- **"← Back"** returns from a submenu to the module list.

## Menus

```
Industrial Cluster Analysis
├── Carbon Accounting
│   ├── Status overview
│   ├── Recalculate all
│   ├── List gaps
│   ├── Show component          (prompts: Component ID)
│   ├── Set component data      (prompts: Component ID, carbon atoms*, MW*, carbon pct*)
│   └── Clear manual override   (prompts: Component ID)
├── Stream Normalization
│   ├── Normalize all
│   ├── List candidates         (prompts: Company ID)
│   ├── Set reference stream    (prompts: Company ID, Stream ID)
│   └── Clear reference stream  (prompts: Company ID)
└── Explore
    ├── Database summary
    ├── List companies
    ├── Company full dump       (prompts: Company ID)
    └── Drill-down explorer
```

`*` = optional; leave blank to skip that field.

## Architecture

### Module registry (`MODULES`)

A list of dicts, one per module, each with:
- `"label"` — displayed in the top-level menu
- `"actions"` — list of action dicts

Each action dict has:
- `"label"` — displayed in the submenu
- `"fn"` — callable to invoke (imported directly from `carbon` or `normalize_streams`)
- `"params"` — list of param specs (empty = no prompts needed)

Each param spec has:
- `"prompt"` — text shown to the user
- `"key"` — keyword argument name passed to `fn`
- `"optional": True` — skip if blank input
- `"type": int | float` — cast input before passing (error if cast fails)

All callables receive `db_path` as a keyword argument.

### Key functions

| Function | Purpose |
|---|---|
| `collect_params(param_specs, db_path)` | Prompts for each spec; returns `kwargs` dict or `None` on cancel |
| `run_module(module, db_path)` | Shows action submenu; loops until Back/Ctrl-C |
| `main(db_path)` | Shows module selector; loops until Quit/Ctrl-C |

### Extending

To add a new module: import it at the top of `cluster_cli.py`, then append
one dict to `MODULES`. No other changes needed.

## Explore module

Implemented in `analysis/explore.py`. All four functions are **read-only** — no DB writes.

| Action | Function | Description |
|---|---|---|
| Database summary | `explore.summary` | Row counts for all 5 tables; carbon coverage stats; flows by status |
| List companies | `explore.list_companies` | Aligned table of all companies with `#streams`, sector, and included flag |
| Company full dump | `explore.show_company(company_id)` | Company metadata + every stream header + composition rows |
| Drill-down explorer | `explore.drill_down` | Interactive arrow-key navigator: company → stream → composition |

### Drill-down navigation

```
Company picker  →  Stream picker  →  Composition detail
     ↑                  ↑                    ↑
  "← Exit"          "← Back"       "← Back to streams"
```

Ctrl-C at any level exits cleanly.

## Dependency

Requires `questionary` (arrow-key TUI library):

```bash
pip install questionary
```
