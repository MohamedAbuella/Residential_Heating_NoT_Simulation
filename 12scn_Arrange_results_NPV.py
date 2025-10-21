# -*- coding: utf-8 -*-
"""
Created on Tue Oct  7 10:42:14 2025

@author: fsdn2
"""

# -*- coding: utf-8 -*-
"""
Arranges TEA results for 12 scenarios: extracts from Excel, saves to TXT + Excel,
and generates comparative plots for costs, NPV & emissions.
Supports filtering by a selected hydrogen blending case (H2 ratio).
"""

import pandas as pd
import os
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# === USER INPUT ===
price_fg = "price_3"        
CCS_fg = "With_CCS"          
CCS_fg = "Without_CCS"          

year = "2050"         

# Hydrogen blending selection
# Options: "A", "B", "C", "D" or None for all
selected_h2_ratio = None 
# selected_h2_ratio = "A"  
# selected_h2_ratio = "D"  


# Automatically detect working directory
script_dir = os.path.abspath(os.getcwd())
project_base = script_dir  

## Base path for results
base_path = os.path.join(project_base, "Output", "Res")
# base_path = os.path.join(project_base, "Output", "Res_H2_0_1_CCS")
# base_path = os.path.join(project_base, "Output", "Res_H2_0_1_noCCS")

base_path = os.path.join(project_base, "Output", "Res_noCCS")

# Define scenarios
scenarios = [f"Scenario {i}" for i in range(1, 13)]

# # Hydrogen ratio mapping
# h2_ratios = {
#     "A": ("H_0.0", 0),
#     "B": ("H_0.1", 10),
#     "C": ("H_0.2", 20),
#     "D": ("H_1.0", 100)
# }

h2_ratios = {
    "A": ("H_0.0", 0),
    "D": ("H_1.0", 100)
}

# Determine which H2 levels to plot
if selected_h2_ratio:
    h2_levels_to_plot = [h2_ratios[selected_h2_ratio][1]]
else:
    h2_levels_to_plot = [v[1] for v in h2_ratios.values()]

h2_colors = {0: 'red', 10: 'blue', 20: 'orange', 100: 'green'}

# === COLLECT RESULTS ===
results = {scenario: [] for scenario in scenarios}

for scenario in scenarios:
    for case, (h2_folder, h2_percentage) in h2_ratios.items():
        if selected_h2_ratio and case != selected_h2_ratio:
            continue

        file_path = os.path.join(
            base_path, h2_folder, CCS_fg, price_fg,
            scenario, "FS", "Results", "tech_econ_analysis_FS.xlsx"
        )

        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue

        try:
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            target_sheet = next(
                (s for s in sheet_names if str(year) in s or "Year" in s),
                sheet_names[0]
            )

            df = pd.read_excel(file_path, sheet_name=target_sheet)
            required_cols = ["H2 Proportion", "Operational_Cost", "Emissions_OPGF", "NPV"]
            if not all(col in df.columns for col in required_cols):
                print(f"Missing required columns in {file_path}, sheet {target_sheet}")
                continue

            h2_prop = df["H2 Proportion"].iloc[0] * 100
            cost = df["Operational_Cost"].iloc[0] / 1_000_000  # million £

            emissions = round(df["Emissions_OPGF"].iloc[0], 0)
            
            npv = df["NPV"].iloc[0] * 365 / 1_000_000  # Convert to million £
            

            results[scenario].append({
                "Case": case,
                "H₂ Ratio (%)": h2_percentage,
                "Emissions (tonnes)": emissions,
                "Operational Cost (m£)": round(cost, 2),
                "NPV (m£)": round(npv, 2)
            })

        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue

# === WRITE TO TXT FILE ===
txt_output_file = os.path.join(base_path, f"tables_output_{year}.txt")
with open(txt_output_file, "w", encoding="utf-8") as f:
    for scenario in scenarios:
        if results[scenario]:
            f.write(f"\n{scenario}\n")
            f.write("Case\tH₂ Ratio (%)\tEmissions (tonnes)\tOperational Cost (m£)\tNPV (m£)\n")
            for row in results[scenario]:
                f.write(f"{row['Case']}\t{row['H₂ Ratio (%)']}\t\t{row['Emissions (tonnes)']}\t\t\t{row['Operational Cost (m£)']}\t\t{row['NPV (m£)']}\n")
print(f"\nText output saved to: {txt_output_file}")

# === WRITE TO EXCEL ===
columns = ["Case", "H₂ Ratio (%)", "Emissions (tonnes)", "Operational Cost (m£)", "NPV (m£)"]
excel_output_file = os.path.join(base_path, f"tables_output_{year}.xlsx")
summary_100 = []

with pd.ExcelWriter(excel_output_file) as writer:
    for scenario, rows in results.items():
        if rows:
            df = pd.DataFrame(rows, columns=columns)
            df.to_excel(writer, sheet_name=scenario[:31], index=False)
            summary_row = df.iloc[-1].copy()
            summary_row["Scenario"] = scenario
            summary_100.append(summary_row)

    if summary_100:
        df_summary = pd.DataFrame(summary_100)
        cols_order = ["Scenario"] + [col for col in df_summary.columns if col != "Scenario"]
        df_summary = df_summary[cols_order]
        df_summary.to_excel(writer, sheet_name="H2_100_Summary", index=False)

print(f"Excel file saved successfully: {excel_output_file}")

# === PLOTTING CONFIGURATION ===
scenario_labels = scenarios
bar_width = 0.2
x = np.arange(len(scenario_labels))
figures_dir = os.path.join(base_path, "Scenario_H2_Figures")
os.makedirs(figures_dir, exist_ok=True)


# === FIGURE 1: Cost and Emissions (Scenarios) ===
fig, ax1 = plt.subplots(figsize=(12, 6))
ax2 = ax1.twinx()

for i, h2 in enumerate(h2_levels_to_plot):
    costs, emissions = [], []
    for scenario in scenario_labels:
        match = next((row for row in results[scenario] if row["H₂ Ratio (%)"] == h2), None)
        if match:
            costs.append(match["Operational Cost (m£)"])
            emissions.append(match["Emissions (tonnes)"])
    offset_x = x + (i - (len(h2_levels_to_plot)-1)/2) * bar_width
    ax1.bar(offset_x, costs, bar_width, color=h2_colors[h2])
    ax2.plot(x, emissions, marker='o', linestyle='--', color=h2_colors[h2])

ax1.set_xlabel("Scenarios", fontsize=15)
ax1.set_ylabel("Operational Cost (m£)", color="blue", fontsize=14)
ax2.set_ylabel("Emissions (tonnes)", color="red", fontsize=14)
# ax1.set_title(f"Operational Cost and Emissions - Year {year}", fontsize=16)
ax1.set_title(f"Operational Cost and Emissions", fontsize=16)
ax1.set_xticks(x)
ax1.set_xticklabels([str(i+1) for i in range(len(scenario_labels))], rotation=15, fontsize=12)
ax1.grid(True, axis='y', linestyle='--', linewidth=0.6, alpha=0.7)
ax1.grid(True, axis='x', linestyle='--', linewidth=0.6, alpha=0.5)

# --- ADD LEGEND ---
legend_elements = [
    Patch(facecolor="gray", label="Operational Cost (bar)"),
    Line2D([0], [0], color="gray", linestyle='--', marker='o', label="Emissions (line)")
] + [Patch(facecolor=h2_colors[h], label=f"H₂ {h}%") for h in h2_levels_to_plot]

ax1.legend(handles=legend_elements, title="Legend", fontsize=11, title_fontsize=12,
           loc="upper left", bbox_to_anchor=(1.05, 1))

plot_output_file = os.path.join(figures_dir, f"Fig_Scenario_BarLine_Cost_{year}.png")
plt.tight_layout()
plt.savefig(plot_output_file, dpi=360)
print(f"Figure 1 (Cost) saved: {plot_output_file}")

# === FIGURE 2: NPV and Emissions (Scenarios) ===
fig_npv, ax1n = plt.subplots(figsize=(12, 6))
ax2n = ax1n.twinx()

for i, h2 in enumerate(h2_levels_to_plot):
    npv_vals, emissions = [], []
    for scenario in scenario_labels:
        match = next((row for row in results[scenario] if row["H₂ Ratio (%)"] == h2), None)
        if match:
            npv_vals.append(match["NPV (m£)"])
            emissions.append(match["Emissions (tonnes)"])
    offset_x = x + (i - (len(h2_levels_to_plot)-1)/2) * bar_width
    ax1n.bar(offset_x, npv_vals, bar_width, color=h2_colors[h2])
    ax2n.plot(x, emissions, marker='o', linestyle='--', color=h2_colors[h2])

ax1n.set_xlabel("Scenarios", fontsize=15)
ax1n.set_ylabel("NPV (m£)", color="blue", fontsize=14)
ax2n.set_ylabel("Emissions (tonnes)", color="red", fontsize=14)
# ax1n.set_title(f"NPV and Emissions - Year {year}", fontsize=16)
ax1n.set_title(f"NPV and Emissions", fontsize=16)
ax1n.set_xticks(x)
ax1n.set_xticklabels([str(i+1) for i in range(len(scenario_labels))], rotation=15, fontsize=12)
ax1n.grid(True, axis='y', linestyle='--', linewidth=0.6, alpha=0.7)
ax1n.grid(True, axis='x', linestyle='--', linewidth=0.6, alpha=0.5)

legend_elements_npv = [
    Patch(facecolor="gray", label="NPV (bar)"),
    Line2D([0], [0], color="gray", linestyle='--', marker='o', label="Emissions (line)")
] + [Patch(facecolor=h2_colors[h], label=f"H₂ {h}%") for h in h2_levels_to_plot]

ax1n.legend(handles=legend_elements_npv, title="Legend", fontsize=11, title_fontsize=12,
            loc="upper left", bbox_to_anchor=(1.05, 1))

plot_output_file_npv = os.path.join(figures_dir, f"Fig_Scenario_BarLine_NPV_{year}.png")
plt.tight_layout()
plt.savefig(plot_output_file_npv, dpi=360)
print(f"Figure 2 (NPV) saved: {plot_output_file_npv}")


# === FIGURES 3 & 4: Cost and NPV vs H₂ Ratio (Separate per H₂ case, no legends) ===
cmap = plt.cm.get_cmap('tab20', len(scenario_labels))
scenario_colors = {s: cmap(i) for i, s in enumerate(scenario_labels)}

for h2 in h2_levels_to_plot:
    # --- FIGURE 3: COST ---
    fig3, ax1b = plt.subplots(figsize=(12, 6))
    ax2b = ax1b.twinx()

    x_scen = np.arange(len(scenario_labels))
    costs, emissions = [], []
    for scenario in scenario_labels:
        match = next((row for row in results[scenario] if row["H₂ Ratio (%)"] == h2), None)
        if match:
            costs.append(match["Operational Cost (m£)"])
            emissions.append(match["Emissions (tonnes)"])

    ax1b.bar(x_scen, costs, color='steelblue', alpha=0.8)
    ax2b.plot(x_scen, emissions, color='red', linestyle='--', marker='o')

    ax1b.set_xlabel("Scenarios", fontsize=15)
    ax1b.set_ylabel("Operational Cost (m£)", color="blue", fontsize=14)
    ax2b.set_ylabel("Emissions (tonnes)", color="red", fontsize=14)
    ax2b.tick_params(axis='y', colors='red')  # make right axis red
    # ax1b.set_title(f"Operational Cost and Emissions vs H₂ Ratio {h2}% - Year {year}", fontsize=16)
    ax1b.set_title(f"Operational Cost and Emissions", fontsize=16)
    ax1b.set_xticks(x_scen)
    ax1b.set_xticklabels([str(i+1) for i in range(len(scenario_labels))], rotation=15, fontsize=12)
    ax1b.grid(True, axis='y', linestyle='--', linewidth=0.6, alpha=0.7)
    ax1b.grid(True, axis='x', linestyle='--', linewidth=0.6, alpha=0.5)

    plt.tight_layout()
    plot_output_file3 = os.path.join(figures_dir, f"Fig_H2Ratio_{h2}_BarLine_Cost_{year}.png")
    plt.savefig(plot_output_file3, dpi=360)
    # plt.close()
    print(f"Figure (Cost, H₂ {h2}%) saved: {plot_output_file3}")

    # --- FIGURE 4: NPV ---
    fig4, ax1c = plt.subplots(figsize=(12, 6))
    ax2c = ax1c.twinx()

    npvs, emissions_npv = [], []
    for scenario in scenario_labels:
        match = next((row for row in results[scenario] if row["H₂ Ratio (%)"] == h2), None)
        if match:
            npvs.append(match["NPV (m£)"])
            emissions_npv.append(match["Emissions (tonnes)"])

    ax1c.bar(x_scen, npvs, color='seagreen', alpha=0.8)
    ax2c.plot(x_scen, emissions_npv, color='red', linestyle='--', marker='o')

    ax1c.set_xlabel("Scenarios", fontsize=15)
    ax1c.set_ylabel("NPV (m£)", color="blue", fontsize=14)
    ax2c.set_ylabel("Emissions (tonnes)", color="red", fontsize=14)
    ax2c.tick_params(axis='y', colors='red')  # make right axis red
    # ax1c.set_title(f"NPV and Emissions vs H₂ Ratio {h2}% - Year {year}", fontsize=16)
    ax1c.set_title(f"NPV and Emissions", fontsize=16)
    ax1c.set_xticks(x_scen)
    ax1c.set_xticklabels([str(i+1) for i in range(len(scenario_labels))], rotation=15, fontsize=12)
    ax1c.grid(True, axis='y', linestyle='--', linewidth=0.6, alpha=0.7)
    ax1c.grid(True, axis='x', linestyle='--', linewidth=0.6, alpha=0.5)

    plt.tight_layout()
    plot_output_file4 = os.path.join(figures_dir, f"Fig_H2Ratio_{h2}_BarLine_NPV_{year}.png")
    plt.savefig(plot_output_file4, dpi=360)
    # plt.close()
    print(f"Figure (NPV, H₂ {h2}%) saved: {plot_output_file4}")


# === COMPREHENSIVE SUMMARY TABLES ===
summary_all = []
for scenario, rows in results.items():
    for row in rows:
        row_copy = row.copy()
        row_copy["Scenario"] = scenario
        summary_all.append(row_copy)

if summary_all:
    df_summary_all = pd.DataFrame(summary_all)
    df_summary_all["Scenario_Num"] = df_summary_all["Scenario"].str.extract(r"Scenario (\d+)").astype(int)
    
    # Pivot COSTS
    df_costs = df_summary_all.pivot_table(index="Scenario_Num", columns="H₂ Ratio (%)", values="Operational Cost (m£)", aggfunc="first").reset_index()
    df_emissions = df_summary_all.pivot_table(index="Scenario_Num", columns="H₂ Ratio (%)", values="Emissions (tonnes)", aggfunc="first").reset_index()
    df_npv = df_summary_all.pivot_table(index="Scenario_Num", columns="H₂ Ratio (%)", values="NPV (m£)", aggfunc="first").reset_index()

    for df in [df_costs, df_emissions, df_npv]:
        df.rename(columns={"Scenario_Num": "Scenario"}, inplace=True)
        df["Scenario"] = ["Scenario " + str(s) for s in df["Scenario"]]
        h2_cols = sorted([col for col in df.columns if isinstance(col, (int, float))])
        rename_dict = {col: f"{int(col)}%" for col in h2_cols}
        df.rename(columns=rename_dict, inplace=True)

    summary_excel_file = os.path.join(figures_dir, f"Summary_Tables_{year}.xlsx")
    with pd.ExcelWriter(summary_excel_file) as writer:
        df_costs.to_excel(writer, sheet_name="Costs", index=False)
        df_emissions.to_excel(writer, sheet_name="Emissions", index=False)
        df_npv.to_excel(writer, sheet_name="NPV", index=False)

    print(f"Summary tables Excel file saved: {summary_excel_file}")
