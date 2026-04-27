#1.	Go to command prompt and install plotly:

#python -m pip install plotly

#2.	Define your processes (nodes), flows (links), flowrates (values) and create sankey diagram:

import plotly.graph_objects as go

# Define process labels (nodes)
labels = [
    "Crude Oil",        # index 0
    "Distillation",     # index 1
    "Naphtha",          # index 2
    "Diesel",           # index 3
    "Residue",          # index 4
    "Steam Cracking",   # index 5
    "Ethylene",         # index 6
    "Propylene"         # index 7
]

# Define flows (links)
source = [
    0,          # Crude Oil → Distillation
    1, 1, 1,    # Distillation → 3 products
    2,          # Naphtha → Steam Cracking
    5, 5        # Steam Cracking → 2 products
]

target = [
    1,          # Crude Oil → Distillation
    2, 3, 4,    # Distillation → products
    5,          # Naphtha → Steam Cracking
    6, 7        # Steam Cracking → products
]

# Define flow rates (kt/y)
values = [
    100,            # Crude to distillation
    30, 50, 20,     # Distillation outputs
    30,             # Naphtha to cracking
    18, 12          # Cracking outputs
]

# Create Sankey diagram
fig = go.Figure(
    data=[
        go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=labels
            ),
            link=dict(
                source=source,
                target=target,
                value=values,
                color=[
                    "blue", "purple", "green",
                    "pink", "lightgreen", "red", "lightblue"
                ]
            )
        )
    ]
)

# Layout
fig.update_layout(
    title_text="Petrochemical Mass Flow Sankey Diagram",
    font_size=12
)

# Show figure
fig.show()