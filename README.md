# Industrial Cluster Material Flow Analysis
This repository includes data and data analysis tools for the course Integrated Project at the Industrial Ecology Master of Science program at Leiden University and TU Delft.

**Primary features include:** CLI tool for database manipulation, web-tool for visual interface for industrial symbiosis analysis, and database plotting and manipulation functions.

**Dataset license**: The dataset in /data was provided by Korevaar, G., & Ibarra Gonzalez for the purposes of the mentioned course and is used with permission. It is not covered by this repository's GPLv3 license. Contact Korevaar, G., & Ibarra Gonzalez for reuse permissions.

## Developer
The primary developer on this repository is: 
>C. Rud Hansen ([GitHub](https://github.com/Rud-X))

Contact for questions or improvements.

## Data source and rights
The primary data source for the analysis is the provided material for the course

>**Citation:** Korevaar, G., & Ibarra Gonzalez, P. (2026). Industrial Park Data 2026 [Dataset].

# Repository structure

Here a brief overview of the different folders and what they include

- *analysis* => CLI tool and functionality
- *api* => Setup and functionality for backend server API
- *data* => Data from course material (excel-files)
- *data_exploration* => Various scripts for different chapters, including export of figures
- *docs* => Generated documentation for some of the repo functionality
- *frontend* => Frontend for the web-app
- *migrations* => Script for migrating the excel files to the database format
- *reference* => older database files, used for reference

In the root are the files:
- *dev.sh* => Starts the server for the web-app (see below)
- *industrial_cluster.db* => The default database file
- *LICENSE* => License file
- *README* => This file
- *server.py* => The backend server for the web-app

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

The web app has a visualization and manipulation tool for analysing industrial symbiosis of the park. It is also used to generate block diagrams.

Start the tool by running `dev.sh`. This starts the FastAPI backend (`server.py`) and the Vite frontend dev
server together, and shuts both down when you press `Ctrl+C`. Keep it running in the background while you use the web-interface.

```bash
# First time only: install frontend dependencies
cd frontend && npm install && cd ..

# Start both servers
./dev.sh
```

When it is up and running open the frontend address in a web-browser with the address below (the backend address is just for the dataconnection):
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

To plot sankeys from the data base. Run the `sankey.py`.

Browse through the interface using:

```bash
python ./data_exploration/ch4/sankey.py --help
```

### Mass and carbon balance

To recalculate the mass and carbon balances after adjusting the scaling factors accordingly: Run the `script_mass_balance.py`

```bash
python ./data_exploration/ch4/script_mass_balance.py all_included
```

The `all_included` parameter ensures that it is only calculated for the companies that are chosen to be included in the analysis (can be changed either through the web-interface or the CLI)

**Export to CSV:** For exporting to .csv, add the argument `output=csv` to the call

**Other databases:** If you want to use another database version, add the path via the argument: `--db /path/to/db.sqlite`

### Script stream

To list all streams of the selected companies or export it to .csv format: Run `script_streams.py`

```bash
python ./data_exploration/ch4/script_streams.py
```

Different settings:

```bash
    python script_streams.py all
    python script_streams.py all_included
    python script_streams.py <company_id>
    python script_streams.py all output=csv
    python script_streams.py all --only-water
    python script_streams.py all --exclude-water
    python script_streams.py all --db /path/to/db.sqlite
```

### Flow compatibility

To plot an analyse the flow compatibility: Run the `flow_compatibility.py`

```bash
python ./data_exploration/ch4/flow_compatibility.py
```

Different settings:

```bash
python data_exploration/flow_compatibility.py
python data_exploration/flow_compatibility.py --list-flows
python data_exploration/flow_compatibility.py --select
python data_exploration/flow_compatibility.py --flow FL001 FL002 --visual
python data_exploration/flow_compatibility.py --flow-rate-only --save-text report.txt
python data_exploration/flow_compatibility.py --flow-rate-only --save-csv report.csv
python data_exploration/flow_compatibility.py --save-visual flows.html
python data_exploration/flow_compatibility.py --save-png flows.png
```

## Chapter 6

To calculate and plot energy and material KPIs use: `ch6_calc.ipynb`

It is a notebook with everything from calculation to plotting.

Process of notebook:
1. Explore database
2. Calculate Material KPIs
3. Calculate Energy KPIs
4. Merge Material and Energy KPIs
5. Plot KPIs

Extra:
6. Network mapping plotting

# AI statement

AI tools have been used to write and modify code in this repository. Primary tools include:
- Claude Code: Sonnet 4.6 & Opus 4.8
- GitHub Copilot: Claude Sonnet 4.6 & Opus 4.8