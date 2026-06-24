# Industrial Cluster Material Flow Analysis
This repository includes data and data analysis tools for the course Integrated Project at the Industrial Ecology Master of Science program at Leiden University and TU Delft.

## Developer
The primary developer on this repository is: 
>C. Rud Hansen ([GitHub](https://github.com/Rud-X))

## Data source and rights
The primary data source for the analysis is the provided material in the course:

>Korevaar, G., & Ibarra Gonzalez, P. (2026). Industrial Park Data 2026 [Dataset].

# Tools needed

TBD

# Chapter specific info

## Chapter 4

### Mass and carbon balance

To recalculate the mass and carbon balances after adjusting the scaling factors accordingly. Run the `script_mass_balance.py`:

```bash
python ./data_exploration/script_mass_balance.py all_included
```

The `all_included` parameter ensures that it is only calculated for the companies that are chosen to be included in the analysis (can be changed either through the web-interface or the CLI)

**Export to CSV:** For exporting to .csv, add the argument `output=csv` to the call

**Other databases:** If you want to use another database version, add the path via the argument: `--db /path/to/db.sqlite`


# AI statement

AI tools have been used to write and modify code in this repository. Primary tools include:
- Claude Code: Sonnet 4.6 & Opus 4.8
- GitHub Copilot: Claude Sonnet 4.6 & Opus 4.8