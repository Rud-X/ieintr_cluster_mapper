# Industrial Cluster Material Flow Analysis


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

