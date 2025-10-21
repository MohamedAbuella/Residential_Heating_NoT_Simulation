

def generate_plots(df_plot, output_dir, year, scenario, t, fg_h):
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm  # Import colormap library
    import numpy as np
    
    # Font size settings
    title_fontsize = 18
    axis_label_fontsize = 14
    tick_label_fontsize = 12
    legend_fontsize = 12

    # Plotting Resultant generation vs. H2 proportions
    fig, axs = plt.subplots(1, 2, figsize=(24, 10), dpi=360)

    # Subplot for Resultant Generation vs. H2 Proportions
    axs[0].plot(df_plot['H2_prop'], df_plot['Resultant generation'], marker='o', label='Resultant Generation', color='b')
    axs[0].set_xlabel('H2 Proportion', fontsize=axis_label_fontsize)
    axs[0].set_ylabel('Resultant Generation', fontsize=axis_label_fontsize)
    axs[0].set_title('Resultant Generation vs H2 Proportion', fontsize=title_fontsize)
    axs[0].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    axs[0].legend(fontsize=legend_fontsize)
    axs[0].grid(True)

    # Subplot for Supply - Demand vs. H2 Proportions
    axs[1].plot(df_plot['H2_prop'], df_plot['Supply - Demand'], marker='o', label='Supply - Demand', color='r')
    axs[1].set_xlabel('H2 Proportion', fontsize=axis_label_fontsize)
    axs[1].set_ylabel('Supply - Demand', fontsize=axis_label_fontsize)
    axs[1].set_title('Supply - Demand vs H2 Proportion', fontsize=title_fontsize)
    axs[1].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    axs[1].legend(fontsize=legend_fontsize)
    axs[1].grid(True)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/Figures/Fig_Gen_vs_H2_{year}_{scenario}_hr{t}_{fg_h}.png')
    plt.show()

    fig, axs = plt.subplots(1, 2, figsize=(24, 10), dpi=360)

    # Subplot for Min p_bar vs. H2 Proportions
    axs[0].plot(df_plot['H2_prop'], df_plot['min_p_bar'], marker='o', label='Min Pressure (bar)', color='b')
    axs[0].set_xlabel('H2 Proportion', fontsize=axis_label_fontsize)
    axs[0].set_ylabel('Min Pressure (bar)', fontsize=axis_label_fontsize)
    axs[0].set_title('Min Pressure (bar) vs H2 Proportion', fontsize=title_fontsize)
    axs[0].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    axs[0].legend(fontsize=legend_fontsize)
    axs[0].grid(True)

    # Subplot for Max Flow_Rate (m3/s) vs. H2 Proportions
    axs[1].plot(df_plot['H2_prop'], df_plot['max_pipe_fr_v'], marker='o', label='Max Flow_Rate (m3/s)', color='r')
    axs[1].set_xlabel('H2 Proportion', fontsize=axis_label_fontsize)
    axs[1].set_ylabel('Max Flow_Rate (m3/s)', fontsize=axis_label_fontsize)
    axs[1].set_title('Max Flow_Rate (m3/s) vs H2 Proportion', fontsize=title_fontsize)
    axs[1].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    axs[1].legend(fontsize=legend_fontsize)
    axs[1].grid(True)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/Figures/Fig_Gas_vs_H2_{year}_{scenario}_hr{t}_{fg_h}.png')
    plt.show()

    fig, axs = plt.subplots(1, 2, figsize=(24, 10), dpi=360)

    # Subplot for Max flow rate at skins (m3/s) vs. H2 Proportions
    axs[0].plot(df_plot['H2_prop'], df_plot['max_flrt (m3/s)'], marker='o', label='Max Sink flow (m3/s)', color='b')
    axs[0].set_xlabel('H2 Proportion', fontsize=axis_label_fontsize)
    axs[0].set_ylabel('Max Sink Flow (m3/s)', fontsize=axis_label_fontsize)
    axs[0].set_title('Max Sink Flow (m3/s) vs H2 Proportion', fontsize=title_fontsize)
    axs[0].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    axs[0].legend(fontsize=legend_fontsize)
    axs[0].grid(True)

    # Subplot for Max Heating Energy at sinks (MWh) vs. H2 Proportions
    axs[1].plot(df_plot['H2_prop'], df_plot['max_sink_energy (MWh)'], marker='o', label='Max Energy (MWh)', color='r')
    axs[1].set_xlabel('H2 Proportion', fontsize=axis_label_fontsize)
    axs[1].set_ylabel('Max Sink Energy (MWh)', fontsize=axis_label_fontsize)
    axs[1].set_title('Max Sink Energy (MWh) vs H2 Proportion', fontsize=title_fontsize)
    axs[1].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    axs[1].legend(fontsize=legend_fontsize)
    axs[1].grid(True)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/Figures/Fig_Sinks_vs_H2_{year}_{scenario}_hr{t}_{fg_h}.png')
    plt.show()
    

    fig, axs = plt.subplots(1, 2, figsize=(24, 10), dpi=360)

    # Subplot for Total gas flow (m3/s) vs. H2 Proportions
    axs[0].plot(df_plot['H2_prop'], df_plot['Total_flow_source (m3/s)'], marker='o', label='Total Flow Source (m3/s)', color='b')
    axs[0].plot(df_plot['H2_prop'], df_plot['Total_flow_external (m3/s)'], marker='o', label='Total Flow External  (m3/s)', color='g')
    axs[0].plot(df_plot['H2_prop'], df_plot['Total_flow_sink (m3/s)'], marker='o', label='Total Flow Sink (m3/s)', color='r')
    axs[0].set_xlabel('H2 Proportion', fontsize=axis_label_fontsize)
    axs[0].set_ylabel('Gas Flow (m3/s)', fontsize=axis_label_fontsize)
    axs[0].set_title('Total Gas Flow (m3/s) vs H2 Proportion', fontsize=title_fontsize)
    axs[0].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    axs[0].legend(fontsize=legend_fontsize)
    axs[0].grid(True)
    
    
    # Subplot for Total gas energy  (MWh) vs. H2 Proportions
    axs[1].plot(df_plot['H2_prop'], df_plot['Total_energy_source (MWh)'], marker='o', label='Total Gas Energy Source (MWh)', color='b')
    axs[1].plot(df_plot['H2_prop'], df_plot['Total_energy_external (MWh)'], marker='o', label='Total Gas Energy External (MWh)', color='g')
    axs[1].plot(df_plot['H2_prop'], df_plot['Total_energy_sink (MWh)'], marker='o', label='Total Gas Energy Sink (MWh)', color='r')
    axs[1].set_xlabel('H2 Proportion', fontsize=axis_label_fontsize)
    axs[1].set_ylabel('Gas Energy (MWh)', fontsize=axis_label_fontsize)
    axs[1].set_title('Total Gas Energy (MWh) vs H2 Proportion', fontsize=title_fontsize)
    axs[1].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    axs[1].legend(fontsize=legend_fontsize)
    axs[1].grid(True)
    

    plt.tight_layout()
    plt.savefig(f'{output_dir}/Figures/Fig_total_gas_flow_energy_vs_H2_{year}_{scenario}_hr{t}_{fg_h}.png')
    plt.show()
    

    fig, axs = plt.subplots(1, 2, figsize=(24, 10), dpi=360)

    # Subplot for Total Cost vs. H2 Proportions
    axs[0].plot(df_plot['H2_prop'], df_plot['Total_cost'], marker='o', label='Total_cost', color='b')
    axs[0].set_xlabel('H2 Proportion', fontsize=axis_label_fontsize)
    axs[0].set_ylabel('Total_cost', fontsize=axis_label_fontsize)
    axs[0].set_title('Total_cost vs H2 Proportion', fontsize=title_fontsize)
    axs[0].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    axs[0].legend(fontsize=legend_fontsize)
    axs[0].grid(True)
    
    # Subplot for Gen (MW) vs. H2 Proportions
    axs[1].plot(df_plot['H2_prop'], df_plot['Optimal_q_e'], marker='o', label='Q_el (MWh)', color='r')
    # axs[1].plot(df_plot['H2_prop'], df_plot['Optimal_q_g'], marker='o', label='Q_gas (MWh)', color='g')
    # axs[1].plot(df_plot['H2_prop'], df_plot['Optimal_q_p2g'], marker='o', label='Q_p2g (MWh)', color='c')
    # axs[1].plot(df_plot['H2_prop'], df_plot['Optimal_q_g2p'], marker='o', label='Q_g2p (MWh)', color='m')
    # axs[1].plot(df_plot['H2_prop'], df_plot['Optimal_q_h'], marker='o', label='Q_hyd (MWh)', color='orange')

    axs[1].set_xlabel('H2 Proportion', fontsize=axis_label_fontsize)
    axs[1].set_ylabel('Gen. Energy (MWh)', fontsize=axis_label_fontsize)
    axs[1].set_title('Optimal Gen (MWh) vs H2 Proportion', fontsize=title_fontsize)
    axs[1].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    axs[1].legend(fontsize=legend_fontsize)
    axs[1].grid(True)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/Figures/Fig_Cost_Qe_vs_H2_{year}_{scenario}_hr{t}_{fg_h}.png')
    plt.show()

    fig, axs = plt.subplots(1, 2, figsize=(24, 10), dpi=360)

    # Subplot for Gen (MW) vs. H2 Proportions
    axs[0].plot(df_plot['H2_prop'], df_plot['Optimal_q_e'], marker='o', label='Q_el (MWh)', color='b')
    axs[0].set_xlabel('H2 Proportion', fontsize=axis_label_fontsize)
    axs[0].set_ylabel('Gen. Energy (MWh)', fontsize=axis_label_fontsize)
    axs[0].set_title('Optimal Gen (MWh) vs H2 Proportion', fontsize=title_fontsize)
    axs[0].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    axs[0].legend(fontsize=legend_fontsize)
    axs[0].grid(True)
    
    # Subplot for Gen (MW) vs. H2 Proportions
    axs[1].plot(df_plot['H2_prop'], df_plot['Optimal_q_g'], marker='o', label='Q_g (MWh)', color='r')
    axs[1].plot(df_plot['H2_prop'], df_plot['Optimal_q_p2g'], marker='o', label='Q_p2g (MWh)', color='g')
    axs[1].plot(df_plot['H2_prop'], df_plot['Optimal_q_g2p'], marker='o', label='Q_g2p (MWh)', color='c')
    axs[1].plot(df_plot['H2_prop'], df_plot['Optimal_q_h'], marker='o', label='Q_h (MWh)', color='m')
    axs[1].set_xlabel('H2 Proportion', fontsize=axis_label_fontsize)
    axs[1].set_ylabel('Gen. Energy (MWh)', fontsize=axis_label_fontsize)
    axs[1].set_title('Optimal Gen (MWh) vs H2 Proportion', fontsize=title_fontsize)
    axs[1].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    axs[1].legend(fontsize=legend_fontsize)
    axs[1].grid(True)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/Figures/Fig_Qegp2gh_vs_H2_{year}_{scenario}_hr{t}_{fg_h}.png')
    plt.show()
    
    fig, axs = plt.subplots(1, 2, figsize=(24, 10), dpi=360)

    # Subplot for Gen (MW) vs. H2 Proportions
    axs[0].plot(df_plot['H2_prop'], df_plot['Optimal_q_e'], marker='o', label='Q_el (MWh)', color='b')
    axs[0].set_xlabel('H2 Proportion', fontsize=axis_label_fontsize)
    axs[0].set_ylabel('Gen. Energy (MWh)', fontsize=axis_label_fontsize)
    axs[0].set_title('Optimal Gen. Energy (MWh) vs H2 Proportion', fontsize=title_fontsize)
    axs[0].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    axs[0].legend(fontsize=legend_fontsize)
    axs[0].grid(True)
    
    # Subplot for Gen (MW) vs. H2 Proportions
    axs[1].plot(df_plot['H2_prop'], df_plot['Optimal_q_g'], marker='o', label='Q_g (MWh)', color='r')
    axs[1].plot(df_plot['H2_prop'], df_plot['Optimal_q_h'], marker='o', label='Q_h (MWh)', color='g')
    axs[1].set_xlabel('H2 Proportion', fontsize=axis_label_fontsize)
    axs[1].set_ylabel('Gen. Energy (MWh)', fontsize=axis_label_fontsize)
    axs[1].set_title('Optimal Gen. Energy (MWh) vs H2 Proportion', fontsize=title_fontsize)
    axs[1].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    axs[1].legend(fontsize=legend_fontsize)
    axs[1].grid(True)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/Figures/Fig_Qegh_vs_H2_{year}_{scenario}_hr{t}_{fg_h}.png')
    plt.show()
    
    fig, axs = plt.subplots(1, 2, figsize=(24, 10), dpi=360)
    
    # Subplot for flow rate at sources (m3/s) vs. H2 Proportions
    axs[0].plot(df_plot['H2_prop'], df_plot['flrt_mixture'], marker='o', label='Mixture flow rate (m3/s)', color='g')
    axs[0].plot(df_plot['H2_prop'], df_plot['flrt_h2'], marker='o', label='H2 flow rate (m3/s)', color='b')
    axs[0].plot(df_plot['H2_prop'], df_plot['flrt_gas'], marker='o', label='Gas flow rate (m3/s)', color='r')
    axs[0].set_xlabel('H2 Proportion', fontsize=axis_label_fontsize)
    axs[0].set_ylabel('Flow Rate (m3/s)', fontsize=axis_label_fontsize)
    axs[0].set_title('Mixture Flow Rate (m3/s) vs H2 Proportion', fontsize=title_fontsize)
    axs[0].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    axs[0].legend(fontsize=legend_fontsize)
    axs[0].grid(True)

    # Subplot for Gen (MW) vs. H2 Proportions
    axs[1].plot(df_plot['H2_prop'], df_plot['Optimal_q_g'], marker='o', label='Mixture Qg (MWh)', color='g')
    axs[1].plot(df_plot['H2_prop'], df_plot['qg_h2'], marker='o', label='Qg_H2 (MWh)', color='b')
    axs[1].plot(df_plot['H2_prop'], df_plot['qg_gas'], marker='o', label='Qg_Gas (MWh)', color='r')
    axs[1].set_xlabel('H2 Proportion', fontsize=axis_label_fontsize)
    axs[1].set_ylabel('Energy (MWh)', fontsize=axis_label_fontsize)
    axs[1].set_title('Mixture Energy (MWh) vs H2 Proportion', fontsize=title_fontsize)
    axs[1].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    axs[1].legend(fontsize=legend_fontsize)
    axs[1].grid(True)
    

    plt.tight_layout()
    plt.savefig(f'{output_dir}/Figures/Fig_Mixture_H2_Gas_{year}_{scenario}_hr{t}_{fg_h}.png')
    plt.show()
    
    
    
    
    fig, axs = plt.subplots(1, 2, figsize=(24, 10), dpi=360)
    cmap = cm.get_cmap('viridis_r', len(df_plot['H2_prop']))  # Use the reversed colormap 'viridis_r'
    
    # Subplot for pressure profile (bar) vs. H2 Proportions
    pressure_profile = df_plot['pressure_profile']
    node_numbers = pressure_profile[0].index 
    
    # Loop through each H2 proportion and plot the corresponding pressure profile
    for i, h2_prop in enumerate(df_plot['H2_prop']):
        color = cmap(i)  # Get color from reversed colormap
        axs[0].plot(node_numbers, pressure_profile[i], marker='o', color=color, label=f'H2 Prop: {h2_prop:.2f}')
    
    axs[0].set_xlabel('Node Number', fontsize=axis_label_fontsize)
    axs[0].set_ylabel('Pressure (bar)', fontsize=axis_label_fontsize)
    axs[0].set_title('Pressure Profile vs. Node Number', fontsize=title_fontsize)
    axs[0].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    axs[0].legend(fontsize=legend_fontsize)
    axs[0].grid(True)
    
    # Subplot for flow rate profile (m3/s) vs. H2 Proportions
    flow_rate_profile = df_plot['flow_rate_profile']
    node_numbers = flow_rate_profile[0].index  
    
    # Loop through each H2 proportion and plot the corresponding flow_rate profile
    for i, h2_prop in enumerate(df_plot['H2_prop']):
        color = cmap(i)  # Get color from reversed colormap
        axs[1].plot(node_numbers, flow_rate_profile[i], marker='o', color=color, label=f'H2 Prop: {h2_prop:.2f}')
    
    axs[1].set_xlabel('Pipe Number', fontsize=axis_label_fontsize)
    axs[1].set_ylabel('Flow Rate (m3/s)', fontsize=axis_label_fontsize)
    axs[1].set_title('Pipe Flows Profile vs. Pipe Number', fontsize=title_fontsize)
    axs[1].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    axs[1].legend(fontsize=legend_fontsize)
    axs[1].grid(True)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/Figures/Fig_profile_pressure_flow_vs_H2_{year}_{scenario}_hr{t}_{fg_h}.png')
    plt.show()
    
    
    ####### Better represent ticks of y-axis for the pressure profile #######
    
    # from matplotlib.ticker import ScalarFormatter
    
    # # Plotting
    # fig, axs = plt.subplots(1, 2, figsize=(24, 10), dpi=360)
    # cmap = cm.get_cmap('viridis_r', len(df_plot['H2_prop']))  # Use the reversed colormap 'viridis_r'
    
    # # Subplot for pressure profile (bar) vs. H2 Proportions
    # pressure_profile = df_plot['pressure_profile']
    # node_numbers = pressure_profile[0].index 
    
    # # Loop through each H2 proportion and plot the corresponding pressure profile
    # for i, h2_prop in enumerate(df_plot['H2_prop']):
    #     color = cmap(i)  # Get color from reversed colormap
    #     axs[0].plot(node_numbers, pressure_profile[i], marker='o', color=color, label=f'H2 Prop: {h2_prop:.2f}')
    
    # axs[0].set_xlabel('Node Number', fontsize=axis_label_fontsize)
    # axs[0].set_ylabel('Pressure (bar)', fontsize=axis_label_fontsize)
    # axs[0].set_title('Pressure Profile vs. Node Number', fontsize=title_fontsize)
    # axs[0].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    # axs[0].legend(fontsize=legend_fontsize)
    # axs[0].grid(True)
    
    # # Improve y-axis format for pressure profile
    # formatter = ScalarFormatter(useOffset=True, useMathText=False)  # Use offset notation
    # formatter.set_powerlimits((-2, 2))  # Define when to use scientific notation (if values are too small)
    # axs[0].yaxis.set_major_formatter(formatter)
    
    # # Subplot for flow rate profile (m3/s) vs. H2 Proportions
    # flow_rate_profile = df_plot['flow_rate_profile']
    # node_numbers = flow_rate_profile[0].index  
    
    # # Loop through each H2 proportion and plot the corresponding flow_rate profile
    # for i, h2_prop in enumerate(df_plot['H2_prop']):
    #     color = cmap(i)  # Get color from reversed colormap
    #     axs[1].plot(node_numbers, flow_rate_profile[i], marker='o', color=color, label=f'H2 Prop: {h2_prop:.2f}')
    
    # axs[1].set_xlabel('Pipe Number', fontsize=axis_label_fontsize)
    # axs[1].set_ylabel('Flow Rate (m3/s)', fontsize=axis_label_fontsize)
    # axs[1].set_title('Pipe Flows Profile vs. Pipe Number', fontsize=title_fontsize)
    # axs[1].tick_params(axis='both', which='major', labelsize=tick_label_fontsize)
    # axs[1].legend(fontsize=legend_fontsize)
    # axs[1].grid(True)
    
    # plt.tight_layout()
    # plt.savefig(f'{output_dir}/Figures/Fig_better_profile_pressure_flow_vs_H2_{year}_{scenario}_hr{t}_{fg_h}.png')
    # plt.show()
        
        
   
def plot_social_intervention(systemData, year, scenario):
    
    import os
    import numpy as np
    import matplotlib.pyplot as plt
    
    # Calculate demands
    elec_demand = np.sum(systemData['Power Demand'], axis=1)
    gas_demand = np.sum(systemData['Gas Consumption'], axis=1)
    adjusted_elec = systemData['Adjusted Power Demand']
    adjusted_gas = systemData['Adjusted Gas Demand']
    
    # Create Output folder if not exists
    output_dir = "Output/Social_Interv/MC_Demands"
    os.makedirs(output_dir, exist_ok=True)

    # Plot settings
    font_title = 16
    font_labels = 14
    font_ticks = 12
    font_legend = 12
    linewidth = 2

    # X-axis values
    hours = np.arange(len(elec_demand))

    # ---- First Figure: Electricity ----
    plt.figure(figsize=(10, 6))
    plt.plot(hours, elec_demand, label="Base Social", color='blue', linewidth=linewidth)
    plt.plot(hours, adjusted_elec, label="MC Social", color='red', linewidth=linewidth)
    plt.title(f"Social Intervened Electricity Demand {(year, scenario)}", fontsize=font_title)
    plt.xlabel("Hours", fontsize=font_labels)
    plt.ylabel("Electricity Demand (MWh)", fontsize=font_labels)
    plt.ylim(bottom=0)
    plt.grid(True)
    plt.legend(loc="best", fontsize=font_legend)
    plt.xticks(fontsize=font_ticks)
    plt.yticks(fontsize=font_ticks)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/Fig_Electricity_Demand_{year}_{scenario}.png", dpi=300)
    plt.close()

    # ---- Second Figure: Gas ----
    plt.figure(figsize=(10, 6))
    plt.plot(hours, gas_demand, label="Base Social", color='blue', linewidth=linewidth)
    plt.plot(hours, adjusted_gas, label="MC Social", color='red', linewidth=linewidth)
    plt.title(f"Social Intervened Gas Demand {(year, scenario)}", fontsize=font_title)
    plt.xlabel("Hours", fontsize=font_labels)
    plt.ylabel("Gas Demand (MWh)", fontsize=font_labels)
    plt.ylim(bottom=0)
    plt.grid(True)
    plt.legend(loc="best", fontsize=font_legend)
    plt.xticks(fontsize=font_ticks)
    plt.yticks(fontsize=font_ticks)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/Fig_Gas_Demand_{year}_{scenario}.png", dpi=300)
    plt.close()

        

        
def plot_TEA_social_intervention(systemData, year, scenario):
    
    import os
    import numpy as np
    import matplotlib.pyplot as plt
    
    # Calculate demands
    elec_demand = np.sum(systemData['Power Demand'], axis=1)
    gas_demand = np.sum(systemData['Gas Consumption'], axis=1)
    adjusted_elec = np.sum(systemData['Adjusted Power Demand'], axis=1)
    adjusted_gas = np.sum(systemData['Adjusted Gas Demand'], axis=1)
    
    
    # Create Output folder if not exists
    output_dir = "Output/Social_Interv/MC_Demands"
    os.makedirs(output_dir, exist_ok=True)

    # Plot settings
    font_title = 16
    font_labels = 14
    font_ticks = 12
    font_legend = 12
    linewidth = 2

    # X-axis values
    hours = np.arange(len(elec_demand))

    # ---- First Figure: Electricity ----
    plt.figure(figsize=(10, 6))
    plt.plot(hours, elec_demand, label="Base Social", color='blue', linewidth=linewidth)
    plt.plot(hours, adjusted_elec, label="MC Social", color='red', linewidth=linewidth)
    plt.title(f"Social Intervened Electricity Demand {(year, scenario)}", fontsize=font_title)
    plt.xlabel("Hours", fontsize=font_labels)
    plt.ylabel("Electricity Demand (MWh)", fontsize=font_labels)
    plt.ylim(bottom=0)
    plt.grid(True)
    plt.legend(loc="best", fontsize=font_legend)
    plt.xticks(fontsize=font_ticks)
    plt.yticks(fontsize=font_ticks)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/Fig_Electricity_Demand_{year}_{scenario}.png", dpi=300)
    plt.close()

    # ---- Second Figure: Gas ----
    plt.figure(figsize=(10, 6))
    plt.plot(hours, gas_demand, label="Base Social", color='blue', linewidth=linewidth)
    plt.plot(hours, adjusted_gas, label="MC Social", color='red', linewidth=linewidth)
    plt.title(f"Social Intervened Gas Demand {(year, scenario)}", fontsize=font_title)
    plt.xlabel("Hours", fontsize=font_labels)
    plt.ylabel("Gas Demand (MWh)", fontsize=font_labels)
    plt.ylim(bottom=0)
    plt.grid(True)
    plt.legend(loc="best", fontsize=font_legend)
    plt.xticks(fontsize=font_ticks)
    plt.yticks(fontsize=font_ticks)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/Fig_Gas_Demand_{year}_{scenario}.png", dpi=300)
    plt.close()

            
            