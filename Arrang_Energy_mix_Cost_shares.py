# -*- coding: utf-8 -*-
"""
Energy Mix Analysis for 12 Heating Scenarios and 2 H2 Blending Cases
Collects OPGF results, compiles energy mix and cost breakdowns into Excel files,
and generates combined energy mix plots only (no individual scenario plots).
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# ==================== USER SETTINGS ====================
price_fg = "price_3"
CCS_fg = "With_CCS"
CCS_fg = "Without_CCS"
# 
investment_scenario = "FS"
# =======================================================

# Automatically detect working directory
script_dir = os.path.abspath(os.getcwd())
project_base = script_dir

## Base path for results (choose the folder inside Output)

# base_path = os.path.join(project_base, "Output", "Res")
# base_path = os.path.join(project_base, "Output", "Res0")

# base_path = os.path.join(project_base, "Output", "Res_H2_0_1_CCS")
# base_path = os.path.join(project_base, "Output", "Res_H2_0_1_noCCS")

base_path = os.path.join(project_base, "Output", "Res_noCCS")


# ---- Simplified function: reads data only (no plots) ----
def read_energy_mix(opgf_file):
    df = pd.read_excel(opgf_file)
    df.set_index("Player Type", inplace=True)
    df = df.drop([tech for tech in ["meth", "P2G"] if tech in df.index], errors="ignore")
    return df


# ===================== MAIN PROCESS =====================
scenarios = [f"Scenario {i}" for i in range(1, 13)]
h2_cases = ["0.0", "1.0"]

# Keep only these technologies in Excel output
selected_techs = ["GT", "CHP", "biomass", "wind", "solar", "FC", "EZ", "G2H"]

legend_labels = {
    "GT": "GT",
    "CHP": "CHP",
    "biomass": "Biomass",
    "wind": "Wind",
    "solar": "Solar",
    "FC": "Fuel Cell",
    "EZ": "Electrolyser",
    "G2H": "H2 Reformer"
}

for h2 in h2_cases:
    # Create output folders
    h2_folder = os.path.join(base_path, "Energy_Mix", f"H2_{h2}")
    os.makedirs(h2_folder, exist_ok=True)
    figures_folder = os.path.join(h2_folder, "Energy_mix_bar_plots")
    os.makedirs(figures_folder, exist_ok=True)

    all_data = {}

    # --- Collect energy mix data only (no plots) ---
    for scenario in scenarios:
        opgf_file = os.path.join(
            base_path, f"H_{h2}", CCS_fg, price_fg,
            scenario, investment_scenario, "Results", f"OPGF_H2_{h2}_FS.xlsx"
        )

        if os.path.exists(opgf_file):
            df = read_energy_mix(opgf_file)
            df_flat = df[["2050"]].rename(columns={"2050": f"{scenario}_H2_{h2}"})
            all_data.update(df_flat.to_dict(orient="series"))
        else:
            print(f"⚠ File not found: {opgf_file}")
            

    # --- Save combined data to Excel ---
    combined_df = pd.DataFrame(all_data)
    combined_df.columns = [col.split("_H2_")[0] for col in combined_df.columns]
    
    # Filter to only selected techs and rename rows
    combined_df = combined_df.loc[combined_df.index.intersection(selected_techs)]
    combined_df.rename(index=legend_labels, inplace=True)


    combined_df = combined_df.round(2)
    
    # Ensure column name = "Type"
    combined_df.index.name = "Type"

    excel_file = os.path.join(h2_folder, f"EnergyMix_H2_{h2}.xlsx")

    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        # === Sheet 1: Energy Mix ===
        combined_df.to_excel(writer, sheet_name="Energy Mix (MWh)")
        print(f"\n✅ Energy Mix sheet saved for H2={h2}")

        # --- Operational Cost Breakdown ---
        cost_values_dict = {}
        cost_shares_dict = {}

        for scenario in scenarios:
            op_cost_file = os.path.join(
                base_path, f"H_{h2}", CCS_fg, price_fg,
                scenario, investment_scenario, "Results", "OperationalCost_Breakdown_FS.xlsx"
            )
            if os.path.exists(op_cost_file):
                cost_df = pd.read_excel(op_cost_file)
                if "Values (M£/day)" in cost_df.columns and "Shares (%)" in cost_df.columns:
                    cost_df.set_index(cost_df.columns[0], inplace=True)
                    cost_values_dict[scenario] = cost_df["Values (M£/day)"]
                    cost_shares_dict[scenario] = cost_df["Shares (%)"]
                else:
                    print(f"⚠ Missing columns in {op_cost_file}")
            else:
                print(f"⚠ File not found: {op_cost_file}")

        if cost_values_dict:
            cost_values_df = pd.DataFrame(cost_values_dict)
            cost_shares_df = pd.DataFrame(cost_shares_dict)

            # Filter and rename rows
            cost_values_df = cost_values_df.loc[cost_values_df.index.intersection(selected_techs)]
            cost_shares_df = cost_shares_df.loc[cost_shares_df.index.intersection(selected_techs)]

            cost_values_df.rename(index=legend_labels, inplace=True)
            cost_shares_df.rename(index=legend_labels, inplace=True)

            # Add Total row
            cost_values_df.loc["Total"] = cost_values_df.sum(numeric_only=True)
            cost_shares_df.loc["Total"] = cost_shares_df.sum(numeric_only=True)

            cost_values_df.index.name = "Type"
            cost_shares_df.index.name = "Type"

            cost_values_df.to_excel(writer, sheet_name="Operational Cost (M£)")
            cost_shares_df.to_excel(writer, sheet_name="Cost Shares (%)")

            print(f"✅ Cost breakdown sheets saved for H2={h2}")
        else:
            print(f"⚠ No cost breakdown data found for H2={h2}")

    print(f"\n📁 Combined results saved: {excel_file}\n")

    # ===================== Combined Energy Mix Plots =====================
    combined_df_plot = combined_df.copy()

    # Make sure we use the same names as in Excel (legend_labels values)
    electric_techs = ["GT", "CHP", "Biomass", "Wind", "Solar", "Fuel Cell"]
    hydrogen_techs = ["Electrolyser", "H2 Reformer"]

    colors_map = {
        "GT": "#1f77b4",
        "CHP": "#9400D3",
        "Biomass": "#8c564b",
        "Wind": "#2ca02c",
        "Solar": "#FFD700",
        "Fuel Cell": "#00CED1",
        "Electrolyser": "#FF69B4",
        "H2 Reformer": "#bfbfbf"
    }

    scenario_numbers = list(range(1, 13))
    scenario_columns = [f"Scenario {i}" for i in scenario_numbers]

    def plot_combined(df_subset, techs, title, filename, reverse_order=False):
        available_columns = [c for c in scenario_columns if c in df_subset.columns]
        df_plot = df_subset.loc[df_subset.index.intersection(techs), available_columns].T

        x_pos = list(range(len(df_plot)))
        x_labels = [str(i) for i in scenario_numbers[:len(x_pos)]]

        fig, ax = plt.subplots(figsize=(16, 8), dpi=200)
        bottom = [0] * len(df_plot)
        plotting_order = reversed(techs) if reverse_order else techs

        for tech in plotting_order:
            if tech in df_plot.columns:
                ax.bar(
                    x_pos,
                    df_plot[tech].values,
                    bottom=bottom,
                    color=colors_map.get(tech, "#999999"),
                    label=tech
                )
                bottom = [b + v for b, v in zip(bottom, df_plot[tech].values)]

        ax.set_xticks(x_pos)
        ax.set_xticklabels(x_labels, fontsize=14)
        ax.set_xlabel("Scenarios", fontsize=18)
        ax.set_ylabel("Energy (GWh)", fontsize=18)
        ax.set_title(title, fontsize=22)
        ax.tick_params(axis="y", labelsize=14)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, pos: f"{int(v/1e3)}"))
        ax.legend(fontsize=14, loc="upper left", bbox_to_anchor=(0, 1.02), frameon=True)
        ax.grid(True, axis="y", linestyle="--", alpha=0.6)

        plt.tight_layout()
        save_path = os.path.join(figures_folder, filename)
        plt.savefig(save_path, dpi=300)
        plt.close()
        print(f"  Saved combined plot: {save_path}")

    # Electricity plot
    plot_combined(combined_df_plot, electric_techs,
                  f"Electricity Energy Mix",
                  f"Combined_Electricity_H2_{h2}.png")

    # Hydrogen plot
    plot_combined(combined_df_plot, hydrogen_techs,
                  f"Hydrogen Energy Mix",
                  f"Combined_Hydrogen_H2_{h2}.png",
                  reverse_order=True)
