# Industrial Cluster Material Flow Analysis
This repository includes data and data analysis tools for the course Integrated Project at the Industrial Ecology Master of Science program at Leiden University and TU Delft.

**Dataset license**: The dataset in /data was provided by Korevaar, G., & Ibarra Gonzalez for the purposes of the mentioned course and is used with permission. It is not covered by this repository's GPLv3 license. Contact Korevaar, G., & Ibarra Gonzalez for reuse permissions.

## Developer
The primary developer on this repository is: 
>C. Rud Hansen ([GitHub](https://github.com/Rud-X))

## Data source and rights
The primary data source for the analysis is the provided material in the course:

>Korevaar, G., & Ibarra Gonzalez, P. (2026). Industrial Park Data 2026 [Dataset].

# Repository structure

Here a brief overview of the different folders and what they include

- analysis => CLI tool and functionality
- api => Setup and functionality for backend server API
- data => Data from course material (excel-files)
- data_exploration => Various scripts for different chapters, including export of figures
- docs => Generated documentation for some of the repo functionality
- frontend => Frontend for the web-app
- migrations => Script for migrating the excel files to the database format
- reference => older database files, used for reference

In the root are the files:
- dev.sh => Starts the server for the web-app (see below)
- industrial_cluster.db => The default database file
- LICENSE => License file
- README => This file
- server.py => The backend server for the web-app

# Prerequisites

| Tool | Version used | Needed for |
|---|---|---|
| Python | 3.14 | Backend server, CLI, migrations, analysis scripts |
| Node.js + npm | Node 22, npm 10 | Frontend (Vite + React) dev server and build for web interface |

### Python packages

Install the following packages:

- fastapi
- uvicorn
- questionary
- prompt_toolkit

# Tools
## Web app -> `./dev.sh`

`dev.sh` starts the FastAPI backend (`server.py`) and the Vite frontend dev
server together, and shuts both down on `Ctrl+C`.

```bash
# First time only: install frontend dependencies
cd frontend && npm install && cd ..

# Start both servers
./dev.sh
```

- Backend: http://localhost:8000
- Frontend: http://localhost:5173 (proxies `/api` requests to the backend)

Extra arguments to setup port and which database file to run

```bash
./dev.sh --port 8001 --db industrial_cluster_ch6_7.db
```

## Interactive CLI -> `cluster_cli.py`

CLI/TUI for managing database.

Features:
- Database exploration
    - See companies, flows, streams, and components
- Database manipulation
    - Create streams
    - Create companies (e.g. new WWTP)
    - Create flows
- Carbon accounting 

```bash
python analysis/cluster_cli.py
python analysis/cluster_cli.py --db industrial_cluster_ch6_7.db   # use another DB
```

Navigate with the arrow keys, `Enter` to select, and `Ctrl+C` to go back / quit.

# Chapter specific info

## Chapter 4

### Sankey

TBD

### Mass and carbon balance

To recalculate the mass and carbon balances after adjusting the scaling factors accordingly. Run the `script_mass_balance.py`:

```bash
python ./data_explorationch4//script_mass_balance.py all_included
```

The `all_included` parameter ensures that it is only calculated for the companies that are chosen to be included in the analysis (can be changed either through the web-interface or the CLI)

**Export to CSV:** For exporting to .csv, add the argument `output=csv` to the call

**Other databases:** If you want to use another database version, add the path via the argument: `--db /path/to/db.sqlite`

### Script stream

### Flow compatibility

# AI statement

AI tools have been used to write and modify code in this repository. Primary tools include:
- Claude Code: Sonnet 4.6 & Opus 4.8
- GitHub Copilot: Claude Sonnet 4.6 & Opus 4.8