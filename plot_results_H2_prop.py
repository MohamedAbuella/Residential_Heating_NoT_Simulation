import os
import pandas as pd
import matplotlib.pyplot as plt

def plot_OPGF_outcomes_H2(excel_file, H2_invs_outs, OPGF_H2_df, GT_H2_df):
    # Extract the scenario from the file path
    scenario = os.path.basename(excel_file).split('_')[-1].replace('.xlsx', '')
    
    # Derive the output directory from the excel_file path
    output_dir = os.path.dirname(os.path.dirname(excel_file))
    
    # Load the Excel file and get all sheet names (representing years)
    xls = pd.ExcelFile(excel_file)
    years = xls.sheet_names
    
    # Prepare dictionaries to hold the aggregated data for each variable
    data = {
        'Cost_OPGF': [],
        'Emissions_OPGF': [],
        'Cost_GT': [],
        'Emissions_GT': [],
        'NPV': [],
        'Total_supply': [],
        'Total_demand': [],
        'Ele_Emissions_GT': [],
        'years': []
    }
    
    # Iterate through each year (sheet) in the Excel file
    for year in years:
        df = pd.read_excel(xls, sheet_name=year)
        
        # Filter the data for H2 Proportion = 0.2
        filtered_df = df[df['H2 Proportion'] == H2_invs_outs]
        
        # Extract relevant columns and append to corresponding lists
        if not filtered_df.empty:
            data['Cost_OPGF'].append(filtered_df['Cost_OPGF'].values[0])
            data['Emissions_OPGF'].append(filtered_df['Emissions_OPGF'].values[0])
            data['Cost_GT'].append(filtered_df['Cost_GT'].values[0])
            data['Emissions_GT'].append(filtered_df['Emissions_GT'].values[0])
            data['NPV'].append(filtered_df['NPV'].values[0])
            data['Total_supply'].append(filtered_df['Total_supply'].values[0])
            data['Total_demand'].append(filtered_df['Total_demand'].values[0])
            data['Ele_Emissions_GT'].append(filtered_df['Ele_Emissions_GT'].values[0])
            data['years'].append(year)
    
    # Convert years to numeric type for plotting
    years_numeric = [int(year) for year in data['years']]
    
    # Plot Cost_OPGF over the years
    plt.figure(figsize=(10, 6))
    plt.plot(years_numeric, data['Cost_OPGF'], marker='o', color='blue', label='Cost Operation')
    plt.xlabel('Year')
    plt.ylabel('Cost Operation (£)')
    plt.title('Cost Operation over the Years')
    plt.grid(True)
    plt.savefig(f'{output_dir.rsplit("/", 1)[0]}/{scenario}/Figures/Cost_OPGF_vs_Years.png', dpi=300)
    plt.show()

    # Plot Emissions_OPGF over the years
    plt.figure(figsize=(10, 6))
    plt.plot(years_numeric, data['Emissions_OPGF'], marker='o', color='green', label='Emissions Operation')
    plt.xlabel('Year')
    plt.ylabel('Emissions Operation (Tonne CO2)')
    plt.title('Emissions Operation over the Years')
    plt.grid(True)
    plt.savefig(f'{output_dir.rsplit("/", 1)[0]}/{scenario}/Figures/Emissions_OPGF_vs_Years.png', dpi=300)
    plt.show()
    
    # Plot Cost_OPGF over the years
    plt.figure(figsize=(10, 6))
    plt.plot(years_numeric, data['Cost_GT'], marker='o', color='red', label='Cost Planning')
    plt.xlabel('Year')
    plt.ylabel('Cost Planning (£)')
    plt.title('Cost Planning over the Years')
    plt.grid(True)
    plt.savefig(f'{output_dir.rsplit("/", 1)[0]}/{scenario}/Figures/Cost_Planning_vs_Years.png', dpi=300)
    plt.show()

    # Plot Emissions_OPGF over the years
    plt.figure(figsize=(10, 6))
    plt.plot(years_numeric, data['Emissions_GT'], marker='o', color='green', label='Emissions Planning')
    plt.xlabel('Year')
    plt.ylabel('Emissions Planning (Tonne CO2)')
    plt.title('Emissions Planning over the Years')
    plt.grid(True)
    plt.savefig(f'{output_dir.rsplit("/", 1)[0]}/{scenario}/Figures/Emissions_Planning_vs_Years.png', dpi=300)
    plt.show()


    # Plot NPV over the years
    plt.figure(figsize=(10, 6))
    plt.plot(years_numeric, data['NPV'], marker='o', color='black', label='NPV')
    plt.xlabel('Year')
    plt.ylabel('NPV (£)')
    plt.title('NPV over the Years')
    plt.grid(True)
    plt.savefig(f'{output_dir.rsplit("/", 1)[0]}/{scenario}/Figures/NPV_vs_Years.png', dpi=300)
    plt.show()

    # Plot Total Supply and Demand over the years on the same plot
    plt.figure(figsize=(10, 6))
    plt.plot(years_numeric, data['Total_supply'], marker='o', color='red', label='Total Supply', linestyle='-')
    plt.plot(years_numeric, data['Total_demand'], marker='o', color='blue', label='Total Demand', linestyle='--')
    plt.xlabel('Year')
    plt.ylabel('Energy (GWh)')
    plt.title('Total Supply and Total Demand over the Years')
    plt.grid(True)
    plt.legend()
    plt.savefig(f'{output_dir.rsplit("/", 1)[0]}/{scenario}/Figures/Supply_Demand_vs_Years.png', dpi=300)
    plt.show()

    # Now, add the stackplot for the Generation Mix (H2)
    plot_OPGF_H2(OPGF_H2_df, GT_H2_df, output_dir, scenario, H2_invs_outs)

# Modified version of plot_OPGF_H2 to handle H2 proportion input
def plot_OPGF_H2(OPGF_H2_df, GT_H2_df, output_dir, scenario, h2_plt):
    # Plot Generation Mix (Energy Resource Allocation)
    data = OPGF_H2_df.set_index('Player Type')
    
    plt.figure(figsize=(10, 6))
    plt.stackplot(data.columns, 
                  data.loc['GT'], 
                  data.loc['biomass'], 
                  data.loc['wind'], 
                  data.loc['solar'], 
                  data.loc['CHP'], 
                  data.loc['meth'], 
                  data.loc['P2G'], 
                  # data.loc['G2P'], 
                  data.loc['EZ'], 
                  data.loc['FC'],
                  labels=['GT', 'Biomass', 'Wind', 'Solar', 'CHP', 'Methane', 'P2G', 'G2P', 'EZ', 'FC'],
                  colors=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', 
                          '#e377c2', '#7f7f7f', '#bcbd22','#00FFFF'])

    plt.title(f'Generation Mix for Operation vs Years at H2 Proportion = {h2_plt}')
    plt.xlabel('Years')
    plt.ylabel('Generation Capacity (MWh)')
    plt.legend(loc='upper left')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/Figures/Fig_Operation_Generation_Mix_vs_years_{scenario}_H2Prop_{h2_plt}.png', dpi=300)
    plt.show()




################################################################################


import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


def load_emissions_data(excel_file, years):
    emissions_data = {}
    
    # Loop over each year to read the emissions data from the respective sheet
    for year in years:
        # Load the sheet for the given year
        sheet_data = pd.read_excel(excel_file, sheet_name=year)
        
        # Extract Emissions_GT and Emissions_OPGF from the first row
        emissions_data[year] = {
            # 'Emissions_GT': sheet_data['Emissions_GT'].values[0],
            'Emissions_GT': sheet_data['Ele_Emissions_GT'].values[0],
            'Emissions_OPGF': sheet_data['Emissions_OPGF'].values[0]
        }
        
    return emissions_data




  # Custom y-axis formatter that treats data as Wh for display
def format_yticks(x, pos):
    if abs(x) >= 1e12:
        return f'{x / 1e12:.0f} TWh'  # Display in TWh (10^12 Wh)
    elif abs(x) >= 1e9:
        return f'{x / 1e9:.0f} GWh'   # Display in GWh (10^9 Wh)
    elif abs(x) >= 1e6:
        return f'{x / 1e6:.0f} MWh'   # Display in MWh (10^6 Wh)
    else:
        return f'{x:.1f} Wh'          # Display in Wh
    
    


def plot_generation_mix_bar(OPGF_H2_df, GT_H2_df, excel_file, output_dir, scenario):
    
    font_size = 15
    line_thickness = 3
    marksize = 10
    x_tick_size = 14
    y_tick_size = 14
    x_tick_rotation = 0
    
    scenario = os.path.basename(excel_file).split('_')[-1].replace('.xlsx', '')
    output_dir = os.path.dirname(os.path.dirname(excel_file))
    
    # Load Excel and get sheet names (years)
    xls = pd.ExcelFile(excel_file)
    years = xls.sheet_names
    
    # Define generation types and colors, with "meth" (Methane) moved to the end of the list
    generation_types_to_include = ['GT', 'CHP', 'wind', 'solar', 'biomass', 'P2G', 'G2P', 'EZ', 'FC', 'meth']
    generation_colors = ['#1f77b4', '#9467bd', '#2ca02c', '#ff7f0e', '#8c564b', '#e377c2', '#7f7f7f', '#808000', '#00FFFF', 'pink']
    gen_legend_labels = ['GT', 'CHP', 'Wind', 'Solar', 'Biomass', 'P2G', 'G2P', 'EZ', 'FC', 'External Gas']
    
    # Define generation types and colors without Methane (External Gas) and without P2G, G2P for the new figures
    generation_types_without_meth = ['GT', 'CHP', 'wind', 'solar', 'biomass', 'EZ', 'FC', 'G2H']  # Removed P2G and G2P
    generation_colors_without_meth = ['#1f77b4', '#9467bd', '#2ca02c', '#ff7f0e', '#8c564b', '#e377c2', '#00FFFF', 'grey']  # Updated colors
    gen_legend_labels_without_meth = ['GT', 'CHP', 'Wind', 'Solar', 'Biomass', 'Electrolyser', 'Fuel Cell', 'H2 Reformer']  # Updated legend labels

    def scaled_formatter(x, pos):
        if x >= 1e9:
            return f'{x / 1e9:.1f} GWh'
        elif x >= 1e6:
            return f'{x / 1e6:.1f} MWh'
        elif x >= 1e3:
            return f'{x / 1e3:.1f} KWh'
        else:
            return f'{x:.1f} Wh'

    # Prepare data function
    def prepare_generation_data(data_df, model_name, excel_file, years, generation_types):
        generation_data = {gen_type: [] for gen_type in generation_types}
        
        # Load all emissions data
        emissions_data = load_emissions_data(excel_file, years)
        
        emissions = []
        for year in years:
            for gen_type in generation_types:
                value = data_df.loc[data_df['Player Type'] == gen_type, year].values[0] if not data_df.loc[data_df['Player Type'] == gen_type, year].empty else 0
                generation_data[gen_type].append(value * 1e6)
                
            emissions.append(emissions_data[year][f'Emissions_{model_name}'])
        
        return pd.DataFrame(generation_data, index=years), emissions

    # Plot generation mix for both OPGF and GT models
    for model_df, model_name in zip([OPGF_H2_df, GT_H2_df], ['OPGF', 'GT']):
        # Plot with all generation types, including Methane
        generation_df, emissions = prepare_generation_data(model_df, model_name, excel_file, years, generation_types_to_include)
        fig, ax = plt.subplots(figsize=(10, 6))
        generation_df.plot(kind='bar', stacked=True, ax=ax, color=generation_colors)
        
        
        # # Customize axes, titles, and labels
        # ax.set_xlabel('Year', fontsize=font_size)
        ax.set_ylabel('Energy (GWh)', fontsize=font_size)
        ax.set_title(f'Energy Mix and CO2 Emissions', fontsize=font_size + 2)
        ax.yaxis.set_major_formatter(FuncFormatter(scaled_formatter))
        ax.xaxis.set_tick_params(rotation=x_tick_rotation, labelsize=x_tick_size)
        ax.yaxis.set_tick_params(labelsize=y_tick_size)

        # Grid and legend
        ax.grid(visible=True, color='gray', linestyle='--', linewidth=0.5, axis='y')
        ax.legend(gen_legend_labels, title='Generation Source', bbox_to_anchor=(1.15, 1), loc='upper left')

        # Emissions on secondary y-axis
        emissions1 = [0 if abs(val) < 5 else val for val in emissions]
        max_emission1 = abs(max(emissions1))
        ax2 = ax.twinx()
        if max_emission1 < 5:
            ax2.set_ylim(-0.2, 5)  # Set a small visible range
        else:
            ax2.set_ylim(0, max_emission1 * 1.1)  
            
        ax2.plot(years, emissions1, color='red', linestyle='--', marker='o', label='CO2 Emissions', linewidth=line_thickness, markersize=marksize)
        ax2.set_ylabel('CO2 Emissions \n(Tonne)', fontsize=font_size, color='red')
        ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:,.0f}'))
        ax2.tick_params(axis='y', colors='red', labelsize=y_tick_size)
        ax2.yaxis.set_label_coords(1.17, 0.35)
        ax2.yaxis.label.set_color('red')
        ax2.legend(loc='upper left', fontsize=font_size)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/Figures/{model_name}_Generation_Mix_with_Emissions_{scenario}.png', dpi=300)
        plt.show()

        # Plot without Methane (External Gas), P2G, and G2P
        generation_df_without_meth, emissions = prepare_generation_data(model_df, model_name, excel_file, years, generation_types_without_meth)
        fig, ax = plt.subplots(figsize=(10, 6))
        generation_df_without_meth.plot(kind='bar', stacked=True, ax=ax, color=generation_colors_without_meth)
        
        # # Customize axes, titles, and labels
        # ax.set_xlabel('Year', fontsize=font_size)
        ax.set_ylabel('Energy (GWh)', fontsize=font_size)
        ax.set_title(f'Energy Mix and CO2 Emissions', fontsize=font_size + 2)
        ax.yaxis.set_major_formatter(FuncFormatter(scaled_formatter))
        ax.xaxis.set_tick_params(rotation=x_tick_rotation, labelsize=x_tick_size)
        ax.yaxis.set_tick_params(labelsize=y_tick_size)

        # Grid and legend
        ax.grid(visible=True, color='gray', linestyle='--', linewidth=0.5, axis='y')
        ax.legend(gen_legend_labels_without_meth, title='Generation Source', bbox_to_anchor=(1.15, 1), loc='upper left')

        # Emissions on secondary y-axis
        emissions2 = [0 if abs(val) < 5 else val for val in emissions]
        print('emissions2', emissions)

        max_emission2 = abs(max(emissions2))
        ax2 = ax.twinx()
        if max_emission2 < 5:
            emissions2 = [val + 0.2 if val == 0 else val for val in emissions2]
            ax2.set_ylim(-0.1, 5)
        else:
            ax2.set_ylim(-0.1, max_emission2 * 1.1)
            
        ax2.plot(years, emissions2, color='red', linestyle='--', marker='o', label=f'CO2 Emissions', linewidth=line_thickness, markersize=marksize)
        ax2.set_ylabel('CO2 Emissions \n(Tonne)', fontsize=font_size, color='red')
        ax2.set_ylim(bottom=0) 
        ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:,.0f}'))
        ax2.tick_params(axis='y', colors='red', labelsize=y_tick_size)
        ax2.yaxis.set_label_coords(1.17, 0.35)  # Adjust the second parameter to move it vertically
        ax2.yaxis.label.set_color('red')
        ax2.legend(loc='upper left', fontsize=font_size)

        # Layout and save with "Wo_Meth" suffix
        plt.tight_layout()
        plt.savefig(f'{output_dir}/Figures/{model_name}_Generation_Mix_Wo_Meth_P2G_G2P_{scenario}.png', dpi=300)
        plt.show()
        
        

def load_hyd_data(excel_file, years):
    hyd_data = {}
    
    # Loop over each year to read the hydrogen mix data from the respective sheet
    for year in years:
        # Load the sheet for the given year
        sheet_data = pd.read_excel(excel_file, sheet_name=year)
        
        # Extract Emissions_GT and hydrogen from the first row
        hyd_data[year] = {
            'Hydrogen_Boiler': sheet_data['Hydrogen_Boiler'].values[0],
            'Electrolyser': sheet_data['Electrolyser'].values[0],
            'Fuel Cell': sheet_data['Fuel Cell'].values[0],
            'G2H': sheet_data['G2H'].values[0],
        }
        
    return hyd_data


def plot_hydrogen_mix_bar(excel_file, output_dir, scenario):
    
    xls = pd.ExcelFile(excel_file)
    years = xls.sheet_names

    hyd_data = load_hyd_data(excel_file, years)
    
    # Extract data from hyd_data dictionary
    years = list(hyd_data.keys())
    categories = ['Hydrogen_Boiler', 'Electrolyser', 'Fuel Cell', 'G2H']
    colors = ['blue',  '#e377c2', '#00FFFF', 'grey']  # Custom colors for the components
    Hyd_labels =['H2 Boiler', 'Electrolyser', 'Fuel Cell', 'H2 Reformer']

    # Prepare data for plotting
    category_values = {category: [hyd_data[year][category] for year in years] for category in categories}

    
    # Plot configuration
    fig, ax = plt.subplots(figsize=(10, 6))

    # Initialize the bottom values for stacking
    bottom_values = [0] * len(years)

    # Create stacked bar chart
    for category, color in zip(categories, colors):
        ax.bar(years, category_values[category], bottom=bottom_values, color=color, label=category)
        bottom_values = [bottom + value for bottom, value in zip(bottom_values, category_values[category])]

    # Annotating total values
    for i, year in enumerate(years):
        total_value = sum(hyd_data[year][category] for category in categories)
        # ax.text(year, total_value + 10, f'{total_value:.1f} MWh', ha='center', va='bottom', fontsize=10, weight='bold')

    # # Customization
    # ax.set_title(f'Hydrogen Energy Mix', fontsize=16)
    ax.set_ylabel('Energy (GWh)', fontsize=14)
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years, fontsize=12)
    ax.tick_params(axis='y', labelsize=12)
    ax.grid(visible=True, axis='y', linestyle='--', alpha=0.5)

    # Legend
    ax.legend(Hyd_labels, bbox_to_anchor=(1.15, 1), loc='upper center', title='Hydrogen Technologies', fontsize=12, title_fontsize=12)


    # Save the figure
    figures_dir = os.path.join(output_dir, "Figures")
    os.makedirs(figures_dir, exist_ok=True)
    file_path = os.path.join(figures_dir, f'Hydrogen_Mix_{scenario}.png')
    plt.tight_layout()
    plt.savefig(file_path, dpi=300)
    plt.show()

