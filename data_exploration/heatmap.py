import pandas

# Indicator: Matrial Intensity
kpi_all = pandas.DataFrame({
    "companies"           : ["Methanol production plant", "DME plant", "Aromatics plant", "Olefins plant", "CHP plant", "Biogas plant"],
    "material_intensity"  : [5.46,1.39,2.52,9.74,None,3.94],
    "GHG_Scope_1"       : [1.2223, 0, 0, 0.6673, 0.2481, 0.3735],
    "Recycled Input Materials" : [0.0, 0.0, 0.0, 0.0, 0.0, 1],
    "E-factor" : [5.17978982, 1.97E-03, 1.592456081, 9.3354736, 0, 0],
    "Waste Water Generation Rate" : [46.93, 1220.9, 100.07, 99.66, 0, 0]
})

# Make a heatmap
import seaborn as sns
import matplotlib.pyplot as plt

# Separate the outlier KPI from the rest
outlier_kpi = "Waste Water Generation Rate"
main_kpis = [col for col in kpi_all.columns if col not in ["companies", outlier_kpi]]

# Prepare data for both heatmaps
main_data = kpi_all.set_index("companies")[main_kpis].T
outlier_data = kpi_all.set_index("companies")[[outlier_kpi]].T

# Create figure with two subplots (different heights for main vs single row)
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), 
                               gridspec_kw={'height_ratios': [len(main_kpis), 1], 'hspace': 0.05})

# Main heatmap (all KPIs except outlier)
sns.heatmap(main_data, annot=True, cmap="YlGnBu", ax=ax1, 
            cbar_kws={'label': 'Value'}, fmt='.2f')
ax1.set_title("Heatmap of KPIs for Different Companies")
ax1.set_xlabel("")
ax1.set_xticklabels([])  # Hide x labels on top plot

# Secondary heatmap for outlier KPI with its own scale
sns.heatmap(outlier_data, annot=True, cmap="YlOrRd", ax=ax2,
            cbar_kws={'label': 'Waste Water (L/kg)'}, fmt='.1f')
ax2.set_xlabel("Companies")
ax2.set_xticklabels(ax2.get_xticklabels(), rotation=45, ha='right')

# Save and show the plot
plt.tight_layout()
plt.savefig("data_exploration/export/kpi_heatmap.png", dpi=150)
print("Saved to data_exploration/export/kpi_heatmap.png")


