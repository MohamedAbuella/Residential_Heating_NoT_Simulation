# -*- coding: utf-8 -*-
"""
Created on Thu May  4 10:41:54 2023

@author: naj112
"""

import numpy as np
import pandas as pd
import pyomo.environ as pyoen
import pyomo.mpec as pyompec

def aggreg_gens_invs(model_type, model, systemData, year, scenario, genCapacities, PlayersOutput, investments, H2_prop, output_dir):

    
    
    # Handling genCapacities
    try:
        # global genCapacities
        genCapacities = model.q.extract_values()
        genCapacities = pd.DataFrame.from_dict(genCapacities, orient='index')
    except NameError:
        genCapacities = pd.DataFrame(0, index=[0], columns=[0])
    
    # Handling investments
    try:
        # global investments
        investments = model.I.extract_values()
        investments = pd.DataFrame.from_dict(investments, orient='index')
    except NameError:
        investments = pd.DataFrame(0, index=[0], columns=[0])
    
    # Extracting player types
    player_types = systemData['Players']['type']
    
     # Extracting 2022 capacities from systemData
    capacities_2022 = systemData['Installed capacity'][int('2022')]
    
    # genCapacities_values = genCapacities.values.flatten()
    
    if model_type == 'GT':
        genCapacities_values = genCapacities.values.flatten()
        
    if model_type == 'OPGF':
        genCapacities_values = PlayersOutput.values.flatten()
       
    investments_values = investments.values.flatten()
    
    # Creating a combined dataframe
    combined_df = pd.DataFrame({
        'Player Type': player_types,
        '2022 Capacity': capacities_2022,
        '2022 Investment': 0,  # Assuming all investments for 2022 are 0
        year+' Capacity': genCapacities_values,
        year+' Investment': investments_values
    })
    
    
    # Calculate differences and percentages, handling division by zero
    combined_df['Capacity Difference'] = combined_df[year+' Capacity'] - combined_df['2022 Capacity']
    combined_df['Capacity % Change'] = np.where(
        combined_df['2022 Capacity'] != 0,
        (combined_df['Capacity Difference'] / combined_df['2022 Capacity']) * 100,
       combined_df['Capacity Difference']   #  where denominator is zero
    )
    
    combined_df['Investment Difference'] = combined_df[year+' Investment'] - combined_df['2022 Investment']
    combined_df['Investment % Change'] = np.where(
        combined_df['2022 Investment'] != 0,
        (combined_df['Investment Difference'] / combined_df['2022 Investment']) * 100,
        combined_df['Investment Difference']   # where denominator is zero
    )
    
    # Saving the results
    combined_df.to_excel('output_results.xlsx', index=False)
    
    # # Displaying the combined dataframe
    # print(combined_df)
    
    
    # Assuming combined_df is already created as per your previous code
    
    # Grouping by 'Player Type' and aggregating the data
    aggregated_df = combined_df.groupby('Player Type').agg({
        '2022 Capacity': 'sum',           # Summing capacities for 2022
        '2022 Investment': 'sum',         # Summing investments for 2022
        year+' Capacity': 'sum',           # Summing capacities for target year
        year+' Investment': 'sum',         # Summing investments for target year
        'Capacity Difference': 'sum',     # Summing capacity differences
        'Capacity % Change': 'mean',      # Calculating average capacity % change
        'Investment Difference': 'sum',   # Summing investment differences
        'Investment % Change': 'mean'     # Calculating average investment % change
    }).reset_index()
    
    # Saving the aggregated results
    aggregated_df.to_excel(f'{output_dir}/Agg_results_imax_H2_{H2_prop}_{year}_{scenario}.xlsx', index=False)


    
    # # Displaying the aggregated dataframe
    # print(aggregated_df)
    
    return aggregated_df