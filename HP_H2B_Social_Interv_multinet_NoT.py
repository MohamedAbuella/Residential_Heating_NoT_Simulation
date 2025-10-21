# -*- coding: utf-8 -*-
"""
Created on Thu Mar  9 12:37:54 2023

@author: naj112

This code provides the complete output of OPFG with optimal dispatch
from the electric generators, gas providers, P2G, G2P, and hydrogen VCS.
"""

import os 
import pulp as lp
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from Aggreg_gens import *

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

def dir_outputs(main_dir, subdirs):
    if not os.path.exists(main_dir):
        os.makedirs(main_dir)
    
    for subdir in subdirs:
        subdir_path = os.path.join(main_dir, subdir)
        if not os.path.exists(subdir_path):
            os.makedirs(subdir_path)
            

# Function to import system data and apply trends to update demand
def data_import(year, scenario, STI_scenario, ws_limit):
    path = r'Refined FES scenario inputs/'
    

    # Get scaling factors and node proportions from trend_social_scale
    (
        power_FES_trend,
        gas_FES_trend,
        power_scaling_factor,
        gas_scaling_factor,
        node_proportions_power,
        node_proportions_gas,
        social_power_demand,
        social_gas_demand_MWh,
        social_hydrogen_demand_MWh
        
    ) = trend_social_scale(path, year, scenario, STI_scenario)

    # # Scale social demands to match the total original demand
    # scaled_social_power_demand = social_power_demand['Base load Electrcity Demand'] * power_scaling_factor
    # scaled_social_gas_demand = social_gas_demand_MWh['Base load Gas Demand'] * gas_scaling_factor
    
    
    # # Social demands without scaling
    # scaled_social_power_demand = social_power_demand['Demand (MWh)'] * power_FES_trend
    # scaled_social_gas_demand = social_gas_demand_MWh['Demand (MWh)'] * gas_FES_trend
    
    scaled_social_power_demand = social_power_demand['Demand (MWh)'] * 1
    scaled_social_gas_demand = social_gas_demand_MWh['Demand (MWh)'] * 1
    scaled_social_hydrogen_demand = social_hydrogen_demand_MWh['Demand (MWh)'] * 1
    
    # --- FIX FOR INTEGER TIME INDEX ---
    # Convert integer hour index (0–23) to string "HH:00:00" format
    if np.issubdtype(scaled_social_power_demand.index.dtype, np.number):
        scaled_social_power_demand.index = scaled_social_power_demand.index.map(lambda x: f"{int(x):02d}:00:00")
    else:
        # If index is already in time format, ensure it's "HH:MM:SS"
        scaled_social_power_demand.index = (
            pd.to_datetime(scaled_social_power_demand.index, format="%H:%M", errors="coerce")
            .dt.strftime("%H:%M:%S")
        )
    
    # Do the same for gas demand
    if np.issubdtype(scaled_social_gas_demand.index.dtype, np.number):
        scaled_social_gas_demand.index = scaled_social_gas_demand.index.map(lambda x: f"{int(x):02d}:00:00")
    else:
        scaled_social_gas_demand.index = (
            pd.to_datetime(scaled_social_gas_demand.index, format="%H:%M", errors="coerce")
            .dt.strftime("%H:%M:%S")
        )
    
    # Align indices for both node proportions and scaled demand
    node_proportions_power.index = node_proportions_power.index.astype(str).str.slice(0,8)
    scaled_social_power_demand.index = scaled_social_power_demand.index.astype(str).str.slice(0,8)
    
    node_proportions_gas.index = node_proportions_gas.index.astype(str).str.slice(0,8)
    scaled_social_gas_demand.index = scaled_social_gas_demand.index.astype(str).str.slice(0,8)
    scaled_social_hydrogen_demand.index = scaled_social_hydrogen_demand.index.astype(str).str.slice(0,8)

    # Distribute the scaled social demands across nodes
    scaled_power_demand = node_proportions_power.mul(scaled_social_power_demand, axis=0)
    scaled_gas_consumption = node_proportions_gas.mul(scaled_social_gas_demand, axis=0)
    
    scaled_social_hydrogen_demand.index = [f"{int(i):02d}:00:00" for i in scaled_social_hydrogen_demand.index]
    scaled_hydrogen_consumption = node_proportions_gas.mul(scaled_social_hydrogen_demand, axis=0)

    # Handle any NaNs
    scaled_power_demand = scaled_power_demand.fillna(0)
    scaled_gas_consumption = scaled_gas_consumption.fillna(0)
    scaled_hydrogen_consumption = scaled_hydrogen_consumption.fillna(0)
    


    # Load other system data (unchanged)
    systemData = {
        'Carbon Price': pd.read_excel(path + 'Carbon price/carbon_price.xlsx'),
        'Installed capacity': pd.read_excel(
            path + 'InstalledCapacity/installed_capacity.xlsx',
            sheet_name=scenario,
            index_col=0
        ),
        'Power Demand': scaled_power_demand,
        'Gas Consumption': scaled_gas_consumption,
        'Hydrogen Consumption': scaled_hydrogen_consumption,

        'Levelised cost': pd.read_excel(path + 'Levelised_costs_for_model_input.xlsx'),
        'Construction cost': pd.read_excel(path + 'Construction_cost_for_model_input.xlsx'),
        'Players': pd.read_csv('Data/market_players2.csv'),
        'Original Power Demand': pd.read_excel(
            path + 'PowerDemand_Heating_Input/powerDemand_' + scenario + '.xlsx',
            sheet_name=year,
            index_col=0
        ),
        'Original Gas Demand': pd.read_excel(
            path + 'gasConsumption_heating_input/gasCons_' + scenario + '.xlsx',
            sheet_name=year,
            index_col=0
        ),
        
        # Add the adjusted demands for 12 scenarios
        'Adjusted Power Demand 12Scenarios': scaled_power_demand,
        'Adjusted Gas Consumption 12Scenarios': scaled_gas_consumption,
        'Adjusted hydrogen Consumption 12Scenarios': scaled_hydrogen_consumption,

    }
    
    systemData['Players']['max_p_mw'] = systemData['Installed capacity'][int(year)][:]

    
    if ws_limit==2:
        systemData['Players']['max_p_mw'][[1, 2, 6, 7, 8, 10, 11,12, 17, 20, 22, 24]]=1e12
        
        systemData['Players']['max_p_mw']=1e12 
        
    

    return systemData



# Function to calculate trends and scale for original demand
def trend_social_scale(path, year, scenario, STI_scenario):
    
    # # Load the fixed demand profiles from 'Social Interventions.xlsx'
    # social_power_demand = pd.read_excel(path + 'Social Interventions.xlsx',sheet_name='s',index_col=0)
    # social_gas_demand_MWh = pd.read_excel( path + 'Social Interventions.xlsx',sheet_name='Gas Demand Profile',index_col=0)
    
    # Import adjusted demands for 8 scenarios
    
    path_II = r'Data/'
    
    social_power_demand = pd.read_excel(path_II + 'Electricity_Demands_12_Scenarios.xlsx', sheet_name=STI_scenario, index_col=0)
    social_gas_demand_MWh   = pd.read_excel(path_II + 'Gas_Demands_12_Scenarios.xlsx', sheet_name=STI_scenario, index_col=0)
    social_hydrogen_demand_MWh   = pd.read_excel(path_II + 'Hydrogen_Demands_12_Scenarios.xlsx', sheet_name=STI_scenario, index_col=0)

    # Load the original power and gas demands for the specific scenario and year
    original_power_demand = pd.read_excel(path + 'PowerDemand_Heating_Input/powerDemand_' + scenario + '.xlsx',sheet_name=year,index_col=0)
    original_gas_consumption_m3_h = pd.read_excel(path + 'gasConsumption_heating_input/gasCons_' + scenario + '.xlsx',sheet_name=year,index_col=0)
    original_gas_consumption_m3_h.index = original_power_demand.index  # Ensure same index
    original_gas_consumption = original_gas_consumption_m3_h * 0.01055 # to convert from m3/h to MWh
    

    # Load the original power and gas demands for 2022 and with specific scenario
    base_power_demand = pd.read_excel(path + 'PowerDemand_Heating_Input/powerDemand_' + scenario + '.xlsx',sheet_name='2022',index_col=0)
    base_gas_consumption_m3_h = pd.read_excel(path + 'gasConsumption_heating_input/gasCons_' + scenario + '.xlsx',sheet_name='2022',index_col=0)
    
    
    # Compute EFS trend factors
    power_FES_trend = original_power_demand.sum(axis=1).mean() / base_power_demand.sum(axis=1).mean()
    gas_FES_trend =  original_gas_consumption_m3_h.sum(axis=1).mean() / base_gas_consumption_m3_h.sum(axis=1).mean()
        
    # Compute total original demand per hour
      
    total_original_power_per_hour = original_power_demand.sum(axis=1)  # Series of length 24
    total_original_gas_per_hour = original_gas_consumption.sum(axis=1)

    # Compute total social demand over all hours
    total_social_power = social_power_demand['Demand (MWh)'].sum()
    total_social_gas = social_gas_demand_MWh['Demand (MWh)'].sum()
    
    # Compute scaling factors
    power_scaling_factor = total_social_power / total_original_power_per_hour.sum()
    gas_scaling_factor =  total_social_gas / total_original_gas_per_hour.sum()

    # Compute node proportions per hour
    node_proportions_power = original_power_demand.div(total_original_power_per_hour, axis=0)
    node_proportions_gas = original_gas_consumption.div(total_original_gas_per_hour, axis=0)
    
    # Handle any division by zero in node proportions
    node_proportions_power = node_proportions_power.fillna(0)
    node_proportions_gas = node_proportions_gas.fillna(0)
    
    
    return (
        power_FES_trend,
        gas_FES_trend,
        power_scaling_factor,
        gas_scaling_factor,
        node_proportions_power,
        node_proportions_gas,
        social_power_demand,
        social_gas_demand_MWh,
        social_hydrogen_demand_MWh
        
    )



# Function to apply socio-technical interventions with Monte Carlo simulation (Normal Distribution)
def apply_monte_carlo_interventions(systemData, num_simulations, heat_pumps, hydrogen_boilers, others):
    
    COP=3  #Heat pump efficiency

    # Extract original gas and electricity demand
    gas_demand = systemData['Gas Consumption']
    elec_demand = systemData['Power Demand']
    hydrogen_demand = systemData['Hydrogen Consumption']
    
    # Initialize arrays to store simulation results
    gas_demand_sim = np.zeros((num_simulations, *gas_demand.shape))
    elec_demand_sim = np.zeros((num_simulations, *elec_demand.shape))
    

    # Calculate probabilities for each intervention    
    # Define probabilities based on user-defined percentages
    no_intervention_prob = 1 - (heat_pumps + hydrogen_boilers + others)
    other_interventions_probs = [others * 0.25] * 4  # Distribute 'others' equally among the four interventions
    
    # Combine all intervention probabilities into a single list
    intervention_probs = [no_intervention_prob] + other_interventions_probs + [heat_pumps, hydrogen_boilers]
    
    
    # # Mean and standard deviations for each intervention
    MC_std=0 #For all interventions
    
    if others == 0:
        heating_setpoint_mean=0
        insulation_mean=0
        delayed_heating_mean=0
        radiator_valves_mean=0

    else:
        heating_setpoint_mean = 1 - 0.20
        insulation_mean = 1 - 0.77
        delayed_heating_mean = 1 - 0.055 
        radiator_valves_mean = 1 - 0.04 
    

    heat_pump_gas_mean = 1 - heat_pumps  # Adjust based on heat pump percentage
    heat_pump_elec_mean = heat_pumps # Adjust based on heat pump percentage
      
    # hydrogen_boilers_mean = 1 - hydrogen_boilers # Adjust based on hydrogen boiler percentage
    hydrogen_boilers_mean = 1  
    
    global dic_i
    dic_i = {}


    interventions = [0, 1, 2, 3, 4, 5, 6]  # These correspond to the six interventions (0 = none)

    for i in range(num_simulations):
        # Create copies of gas and electricity demand for adjustments
        gas_demand_adj = gas_demand.copy()
        elec_demand_adj = elec_demand.copy()
        
        # Randomly select one intervention or none based on the probabilities
        selected_intervention = np.random.choice(interventions, p=intervention_probs)
        dic_i[i] = selected_intervention  # Store the selected intervention for this iteration

        # Apply only the selected intervention
        if selected_intervention == 1:  # Decrease heating setpoint
            reduction_factor = np.random.normal(heating_setpoint_mean, MC_std)
            gas_demand_adj *= max(0, reduction_factor)  # Ensure no negative values

        elif selected_intervention == 2:  # Improve insulation
            reduction_factor = np.random.normal(insulation_mean, MC_std)
            gas_demand_adj *= max(0, reduction_factor)

        elif selected_intervention == 3:  # Delay heating start
            reduction_factor = np.random.normal(delayed_heating_mean, MC_std)
            gas_demand_adj *= max(0, reduction_factor)

        elif selected_intervention == 4:  # Use radiator valves
            reduction_factor = np.random.normal(radiator_valves_mean, MC_std)
            gas_demand_adj *= max(0, reduction_factor)

        elif selected_intervention == 5:  # Use heat pumps (affects both gas and electricity)
            gas_reduction_factor = np.random.normal(heat_pump_gas_mean, MC_std)
            elec_increase_factor = np.random.normal(heat_pump_elec_mean, MC_std)
            gas_demand_adj *= max(0, gas_reduction_factor)
            ### elec_demand_adj *= max(0, elec_increase_factor)
            elec_demand_temp = ((np.mean(gas_demand.copy(), axis=1)) * elec_increase_factor)/COP
            per_column_share = elec_demand_temp / elec_demand_adj.shape[1]
            # elec_demand_adj = elec_demand_adj.add(per_column_share, axis=0)

        elif selected_intervention == 6:  # Use hydrogen boilers
            reduction_factor = np.random.normal(hydrogen_boilers_mean, MC_std)
            gas_demand_adj *= max(0, reduction_factor)
            
            


        # Store adjusted demands for each simulation
        gas_demand_sim[i, :, :] = gas_demand_adj.values
        elec_demand_sim[i, :, :] = elec_demand_adj.values
        

    # Average results across all simulations
    adjusted_gas_demand = np.mean(gas_demand_sim, axis=0)
    adjusted_elec_demand = np.mean(elec_demand_sim, axis=0)

    # # Create new DataFrames with original structure but updated values
    # systemData['Adjusted Gas Demand'] = pd.DataFrame(adjusted_gas_demand, index=gas_demand.index, columns=gas_demand.columns)
    # systemData['Adjusted Power Demand'] = pd.DataFrame(adjusted_elec_demand, index=elec_demand.index, columns=elec_demand.columns)

    # Create new DataFrames with original structure but updated values
    systemData['Adjusted Gas Demand'] = gas_demand
    systemData['Adjusted Power Demand'] = elec_demand
    systemData['Adjusted Hydrogen Demand'] = hydrogen_demand


    # from generate_plots import plot_TEA_social_intervention 
    # year = '2025'
    # scenario = 'FS'
    # plot_TEA_social_intervention(systemData, year, scenario)
    # st=stop
    
    
    return systemData


# Function to apply socio-technical interventions with Monte Carlo simulation (Normal Distribution)
def ED_v4_apply_monte_carlo_interventions(systemData, num_simulations, heat_pumps, hydrogen_boilers, others):
    # Extract original gas and electricity demand
    gas_demand = np.sum(systemData['Gas Consumption'], axis=1)
    elec_demand = np.sum(systemData['Power Demand'], axis=1)
    
    # Arrays to store simulation results
    gas_demand_sim = np.zeros((num_simulations, len(gas_demand)))
    elec_demand_sim = np.zeros((num_simulations, len(elec_demand)))
    
    
    # Calculate probabilities for each intervention    
    # Define probabilities based on user-defined percentages
    no_intervention_prob = 1 - (heat_pumps + hydrogen_boilers + others)
    other_interventions_probs = [others * 0.25] * 4  # Distribute 'others' equally among the four interventions
    
    # Combine all intervention probabilities into a single list
    intervention_probs = [no_intervention_prob] + other_interventions_probs + [heat_pumps, hydrogen_boilers]
    
    
    # Mean and standard deviations for each intervention
    heating_setpoint_mean = 1 - (0.80 * others * 0.25/0.1)
    heating_setpoint_std = 0.05   

    insulation_mean = 1 - (0.77 * others * 0.25/0.1)
    insulation_std = 0.05   

    delayed_heating_mean = 1 - (0.055 * others * 0.25/0.1)
    delayed_heating_std = 0.05    

    radiator_valves_mean = 1 - (0.04 * others * 0.25/0.1)
    radiator_valves_std = 0.05    

    heat_pump_gas_mean =  1 - (0.213 * heat_pumps/0.1)  # Adjust based on heat pump percentage
    heat_pump_gas_std = 0.05     

    heat_pump_elec_mean = 1 + (0.071 * heat_pumps/0.1)  # Adjust based on heat pump percentage
    heat_pump_elec_std = 0.05     

    hydrogen_boilers_mean = 1 - (0.10 * hydrogen_boilers)  # Adjust based on hydrogen boiler percentage
    hydrogen_boilers_std = 0.05   
    
    global dic_i
    dic_i = {}


    interventions = [0, 1, 2, 3, 4, 5, 6]  # These correspond to the six interventions (0 = none)

    for i in range(num_simulations):
        # Create copies of gas and electricity demand for adjustments
        gas_demand_adj = gas_demand.copy()
        elec_demand_adj = elec_demand.copy()
        
        # Randomly select one intervention or none based on the probabilities
        selected_intervention = np.random.choice(interventions, p=intervention_probs)
        dic_i[i] = selected_intervention  # Store the selected intervention for this iteration

        # Apply only the selected intervention
        if selected_intervention == 1:  # Decrease heating setpoint
            reduction_factor = np.random.normal(heating_setpoint_mean, heating_setpoint_std)
            gas_demand_adj *= max(0, reduction_factor)  # Ensure no negative values

        elif selected_intervention == 2:  # Improve insulation
            reduction_factor = np.random.normal(insulation_mean, insulation_std)
            gas_demand_adj *= max(0, reduction_factor)

        elif selected_intervention == 3:  # Delay heating start
            reduction_factor = np.random.normal(delayed_heating_mean, delayed_heating_std)
            gas_demand_adj *= max(0, reduction_factor)

        elif selected_intervention == 4:  # Use radiator valves
            reduction_factor = np.random.normal(radiator_valves_mean, radiator_valves_std)
            gas_demand_adj *= max(0, reduction_factor)

        elif selected_intervention == 5:  # Use heat pumps (affects both gas and electricity)
            gas_reduction_factor = np.random.normal(heat_pump_gas_mean, heat_pump_gas_std)
            elec_increase_factor = np.random.normal(heat_pump_elec_mean, heat_pump_elec_std)
            gas_demand_adj *= max(0, gas_reduction_factor)
            elec_demand_adj *= max(0, elec_increase_factor)

        elif selected_intervention == 6:  # Use hydrogen boilers
            reduction_factor = np.random.normal(hydrogen_boilers_mean, hydrogen_boilers_std)
            gas_demand_adj *= max(0, reduction_factor)


        # Store the adjusted demands for this simulation
        gas_demand_sim[i, :] = gas_demand_adj
        elec_demand_sim[i, :] = elec_demand_adj
        

    # Average the results of all simulations for use in further calculations    
    systemData['Adjusted Gas Demand'] = np.mean(gas_demand_sim, axis=0)
    systemData['Adjusted Power Demand'] = np.mean(elec_demand_sim, axis=0)
    
    

    return systemData



if __name__ == "__main__":
    years = ['2022', '2025', '2030', '2035', '2040', '2045', '2050']
    scenarios = ['CT', 'FS', 'LW', 'ST']  # Future Energy Scenarios    scenario
    STI_Scenarios = ['Scenario 1', 'Scenario 2', 'Scenario 3', 'Scenario 4',
                    'Scenario 5', 'Scenario 6', 'Scenario 7', 'Scenario 8']  # STI scenarios
    

    year = years[1]  # e.g., '2025'
    scenario = scenarios[1]  
    STI_scenario = STI_Scenarios[0]   # STI scenario
    
    H2_prop = 0  # Initial hydrogen proportion
    
    # # Step 1: Load system data
    # systemData = data_import(year, scenario)
    systemData = data_import(year, scenario, STI_scenario, ws_limit)

    
    # num_simulations=1000
    num_simulations=10
    heat_pumps = 0.3
    hydrogen_boilers =0.3
    others=0.4
    
    # apply_monte_carlo_interventions(systemData, num_simulations)
    apply_monte_carlo_interventions(systemData, num_simulations, heat_pumps, hydrogen_boilers, others)

    # Using the Counter from collections to count the frequency of each unique value
    from collections import Counter
    
    # Count the occurrences of each value in the dictionary
    value_frequencies = Counter(dic_i.values())
    print()
    print('scenarios_count', value_frequencies)
    

    ###################################
    
    dic_edemand={}; dic_gdemand={}
    for year in years:
        # systemData = data_import(year, scenario)
        systemData = data_import(year, scenario, STI_scenario, ws_limit)

        
        e_demand_sum = np.sum(systemData['Power Demand'], axis=1).sum()
        e_demand_avg = np.sum(systemData['Power Demand'], axis=1).mean()
        g_demand_sum = np.sum(systemData['Gas Consumption'], axis=1).sum()
        g_demand_avg = np.sum(systemData['Gas Consumption'], axis=1).mean()
    
        
        dic_edemand[year]={'e_demand_sum': e_demand_sum, 
                           'e_demand_mean': e_demand_avg}
        
        dic_gdemand[year]={'g_demand_sum': g_demand_sum, 
                           'g_demand_mean': g_demand_avg}
        
    # Convert the dictionaries to DataFrames
    # For average demands
    avg_demands_data = {
        'Electricity': [dic_edemand[year]['e_demand_mean'] for year in dic_edemand],
        'Gas': [dic_gdemand[year]['g_demand_mean'] for year in dic_gdemand]
    }
    avg_demands_df = pd.DataFrame(avg_demands_data, index=dic_edemand.keys()).T
    
    # For summed demands
    sum_demands_data = {
        'Electricity': [dic_edemand[year]['e_demand_sum'] for year in dic_edemand],
        'Gas': [dic_gdemand[year]['g_demand_sum'] for year in dic_gdemand]
    }
    sum_demands_df = pd.DataFrame(sum_demands_data, index=dic_edemand.keys()).T
    
    # Display the DataFrames
    avg_demands_df.columns.name = 'Year'
    sum_demands_df.columns.name = 'Year'
    
    print("Average Demands DataFrame:")
    print(avg_demands_df)
    
    print("\nSummed Demands DataFrame:")
    print(sum_demands_df)
    
#########################################
    
    systemData = apply_monte_carlo_interventions(systemData, num_simulations, heat_pumps, hydrogen_boilers, others)
    
    # Average the results of all simulations for use in further calculations    
    systemData['Adjusted Gas Demand'] 
    systemData['Adjusted Power Demand']

    
        
    # Initialize empty dictionary to store average demand results
    average_demands = {
        'Gas Demand (FS)': [],
        'Power Demand (FS)': []
    }
    
    # List of years we are interested in
    years = ['2022', '2025', '2030', '2035', '2040', '2045', '2050']
    
    # Since your index is just time, no need for datetime conversion for filtering by year.
    # Calculate averages for each year, but you'll need the data for each year separately,
    # assuming you have multiple year datasets.
    
    # Assuming the data for each year is stored separately, for each year:
    for year in years:

        # Calculate the average demand for gas and power per hour, averaging across all hours
        gas_demand_for_hourly = systemData['Adjusted Gas Demand'].sum(axis=1)
        power_demand_for_hourly = systemData['Adjusted Power Demand'].sum(axis=1)
    
        # Calculate the average demand for all time periods (24 hours) for each energy node
        avg_gas_demand = gas_demand_for_hourly.mean()
        avg_power_demand = power_demand_for_hourly.mean()
        
        # Append the results to the dictionary
        average_demands['Gas Demand (FS)'].append(round(avg_gas_demand, 2))
        average_demands['Power Demand (FS)'].append(round(avg_power_demand, 2))
    
    # Convert the dictionary to a DataFrame with years as the index
    df_average_demands = pd.DataFrame(average_demands, index=years)
    
    # Transpose the DataFrame to switch rows and columns
    df_transposed = df_average_demands.transpose()
    
    # Display the DataFrame with rounded values
    print('HP_H2B_adj_demands_avg:')
    display(df_transposed)


#########################################
    
    systemData = ED_v4_apply_monte_carlo_interventions(systemData, num_simulations, heat_pumps, hydrogen_boilers, others)
    
    # Average the results of all simulations for use in further calculations    
    systemData['Adjusted Gas Demand'] 
    systemData['Adjusted Power Demand']
    

    # Your predefined year range
    years = ['2022', '2025', '2030', '2035', '2040', '2045', '2050']
    
    # Initialize an empty dictionary to store the average results for each year
    average_demands = {
        'Gas Demand (FS)': [],
        'Power Demand (FS)': []
    }
    
    # Loop over each year and calculate the average for the 'FS' scenario
    for year_idx, year in enumerate(years):
        # Filter the data based on the year (assuming each index in the array corresponds to a year)
        gas_demand = systemData['Adjusted Gas Demand'][year_idx::len(years)]  # Take values for the current year
        power_demand = systemData['Adjusted Power Demand'][year_idx::len(years)]  # Same for power demand
        
        # Calculate the average for each year in the FS scenario
        avg_gas_demand = np.mean(gas_demand)  # This assumes your data is organized so that you can average across simulations
        avg_power_demand = np.mean(power_demand)  # Same for power demand
        
        # Store the results
        average_demands['Gas Demand (FS)'].append(round(avg_gas_demand, 2))
        average_demands['Power Demand (FS)'].append(round(avg_power_demand, 2))
    
    # Convert the results into a DataFrame
    df_average_demands = pd.DataFrame(average_demands, index=years)
    df_average_demands = df_average_demands.transpose()
    
    # Display the DataFrame with rounded values
    print('ED_v4_adj_demands_avg:')
    display(df_average_demands)
    



