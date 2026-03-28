# cluster_cli.py — Interactive TUI Menu

`analysis/cluster_cli.py` is the single interactive entry point for all analysis and data-management tools. It wraps `manage_companies.py`, `manage_flows_tui.py`, `carbon.py`, and `normalize_streams.py` behind arrow-key menus.

## Usage

```bash
python analysis/cluster_cli.py              # default DB (industrial_cluster.db)
python analysis/cluster_cli.py --db <path>  # custom DB path
```

## Navigation

- **Arrow keys** to move, **Enter** to select.
- **Ctrl-C** or **"Quit"** at any level exits cleanly.
- **"← Back"** returns from a submenu to the parent menu.

## Menu tree

```
Industrial Cluster Analysis
├── Manage Companies
│   ├── (company list with headers; Type tag, Y=green, N=red for Included)
│   ├── + Add Company                (prompts: name)
│   ├── + Add External Node          (prompts: node type, name)
│   │     node types: import_source [IMP], export_sink [EXP], waste_facility [WMF]
│   └── [select a company or external node]
│       ├── Explore
│       │   ├── (metadata header: stream counts, flows, normalization, included)
│       │   ├── (stream table — select a stream)
│       │   └──   └── (composition detail → "← Back to streams")
│       ├── Normalization            (companies only — hidden for external nodes)
│       │   ├── (header: current reference stream + flow)
│       │   ├── Select normalization stream   (toggles reference; auto-recalculates)
│       │   └── Recalculate normalization
│       ├── Create Flow
│       │   ├── (header: flow counts, unconnected streams)
│       │   └── (stream picker → company picker OR "→ Connect to external node" → confirm)
│       ├── Toggle Included           (flips included ↔ excluded; prints confirmation)
│       └── Manage Flows              (filtered to this company — see Manage Flows below)
├── Manage Flows
│   ├── (flow table: ID, From Co/Stream → To Co/Stream, status)
│   └── [select a flow]
│       ├── (metadata header: flow ID, status, from/to companies and streams)
│       ├── Change outflow stream     (pick new source; fixed = inflow side)
│       ├── Change inflow stream      (pick new destination; fixed = outflow side)
│       └── Delete flow               (confirm → remove from DB)
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

---

## Manage Companies

Implemented across `analysis/manage_companies.py` (DB logic) and
`analysis/manage_companies_tui.py` (TUI navigation).

### Company list

Displays an aligned table with column headers:

| Column | Description |
|---|---|
| Type | node type tag: blank for companies, `[IMP]` import_source, `[EXP]` export_sink, `[WMF]` waste_facility |
| ID | company_id (e.g. C001) |
| Name | company or node name |
| Sector | industry sector |
| Inc | included in analysis — **green Y** / **red N** |
| #Streams | total streams |
| #Flows | flows where this company appears on either side |
| #InFlows | distinct streams of this company connected to a flow |

Select `+ Add Company` to insert a new company (prompts for name only; company_id auto-generated).

Select `+ Add External Node` to insert an import source, export sink, or waste facility:
- Prompts for node type and name
- The node appears in the graph as a cluster boundary entity
- External nodes can have streams added later via Explore if needed

### Per-company sub-menu

| Option | Description |
|---|---|
| Explore | Stream table with metadata header; select a stream to view composition |
| Normalization | Set/clear reference stream — **companies only** (hidden for external nodes) |
| Create Flow | Pick a stream → pick a company **or external node** → confirm |
| Toggle Included | Flips `companies.included` 0↔1; prints confirmation |
| Manage Flows | Opens Manage Flows filtered to this company |

### Create Flow — external node connections

When creating a flow from an **output** stream, the company picker includes a
`→ Connect to external node` option that lists `export_sink` and `waste_facility` nodes.
Selecting one creates a flow with `to_stream_id = NULL`.

When creating a flow from an **input** stream, the `→ Connect to external node` option
lists `import_source` nodes. Selecting one creates a flow with `from_stream_id = NULL`
(the from/to sides are automatically swapped so the flow reads: import_source → company.input).

### Explore view

Header shows: `#input | #waste | #product | #flows | normalization stream | included`.

Stream table columns: `ID | [direction] | Name | Type | flow kton/yr | C=carbon%`.
All decimal values capped at 3 places.

Selecting a stream shows full composition detail:

| Column | Description |
|---|---|
| Comp ID | component_id |
| Name | component name |
| Fraction | mass fraction (0–1, 3 decimal places) |
| Trace | Y if `is_trace=1` |
| C-frac | carbon_fraction (3 decimal places) |

### Normalization

Header shows the current reference stream ID, name, and flow value.

`Select normalization stream` lists all valid output streams (flow > 0) for the company.
The current reference is marked `[*]`. Selecting it clears the reference; selecting any
other stream sets it as the new reference. Either action triggers a full recalculation.

### Create Flow

Source stream → company picker (excluding own company) → streams of opposite direction
→ confirm → inserts into `flows` table with `status='candidate'`.

---

## Manage Flows

Implemented in `analysis/manage_flows_tui.py`.

Displays a flow table with columns: `flow_id | from_company from_stream [name] → to_company to_stream [name] | status`.
For external node flows, the stream column shows `-` and the name shows `(external: node_type)`.

Selecting a flow shows a metadata header (including `flow_type`) and three actions:

| Action | Description |
|---|---|
| Change outflow stream | Fixed side = inflow. Picker finds a new source; can also pick an external node. Updates `from_stream_id` / `from_company_id`. flow_id unchanged. |
| Change inflow stream | Fixed side = outflow. Picker finds a new destination; can also pick an external node. Updates `to_stream_id` / `to_company_id`. flow_id unchanged. |
| Delete flow | Confirm prompt → `DELETE FROM flows WHERE flow_id = ?` |

The same view is available from within a company's sub-menu, pre-filtered to flows where that company appears on either side.

---

## Architecture

### Files

| File | Role |
|---|---|
| `analysis/cluster_cli.py` | TUI orchestrator — module registry, `main()`, navigation dispatch |
| `analysis/manage_companies.py` | Pure DB logic: company/stream/flow queries and mutations |
| `analysis/manage_companies_tui.py` | TUI for Manage Companies + shared `pick_stream_for_flow()` helper |
| `analysis/manage_flows_tui.py` | TUI for Manage Flows |
| `analysis/explore.py` | Read-only DB exploration (used by Explore module in legacy menus) |
| `analysis/carbon.py` | Carbon accounting backend + CLI |
| `analysis/normalize_streams.py` | Stream normalization backend + CLI |

### Module registry (`MODULES`)

A list of dicts, one per module, each with:
- `"label"` — displayed in the top-level menu
- `"actions"` — list of action dicts

Each action dict has:
- `"label"` — displayed in the submenu
- `"fn"` — callable to invoke
- `"params"` — list of param specs (empty = no prompts needed)

Each param spec has:
- `"prompt"` — text shown to the user
- `"key"` — keyword argument name passed to `fn`
- `"optional": True` — skip if blank input
- `"type": int | float` — cast input before passing

All callables receive `db_path` as a keyword argument.

`Manage Companies` and `Manage Flows` are handled outside the MODULES registry (custom `if` branches in `main()`) because they require context-aware multi-level navigation that cannot be expressed as a flat action list.

### Key functions in `cluster_cli.py`

| Function | Purpose |
|---|---|
| `collect_params(param_specs, db_path)` | Prompts for each spec; returns `kwargs` dict or `None` on cancel |
| `run_module(module, db_path)` | Shows action submenu; loops until Back/Ctrl-C |
| `main(db_path)` | Shows top-level selector; loops until Quit/Ctrl-C |

### Extending

To add a new MODULES-style module: import it at the top of `cluster_cli.py`, then append
one dict to `MODULES`. No other changes needed.

To add a custom multi-level menu (like Manage Companies): add an `if choice == "..."` branch
in `main()` and implement a `run(db_path)` entry point in a new TUI file.

## Dependency

Requires `questionary` (arrow-key TUI library):

```bash
pip install questionary
```
