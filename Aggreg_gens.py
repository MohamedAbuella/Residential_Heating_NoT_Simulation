# -*- coding: utf-8 -*-
"""
Created on Thu May  4 10:41:54 2023

@author: naj112
"""

import numpy as np
import pandas as pd
import pyomo.environ as pyoen
import pyomo.mpec as pyompec

def aggreg_gens(systemData, year, scenario, genCapacities, H2_prop, output_dir):




    # Extracting player types
    player_types = systemData['Players']['type']
    
     # Extracting 2022 capacities from systemData
    capacities_2022 = systemData['Installed capacity'][int('2022')]
    
    genCapacities_values = genCapacities.values.flatten()
    
    # Creating a combined dataframe
    combined_df = pd.DataFrame({
        'Player Type': player_types,
        '2022 Capacity': capacities_2022,
        year+' Capacity': genCapacities_values,
    })
    
    
    # Calculate differences and percentages, handling division by zero
    combined_df['Capacity Difference'] = combined_df[year+' Capacity'] - combined_df['2022 Capacity']
    combined_df['Capacity % Change'] = np.where(
        combined_df['2022 Capacity'] != 0,
        (combined_df['Capacity Difference'] / combined_df['2022 Capacity']) * 100,
       combined_df['Capacity Difference']   #  where denominator is zero
    )
    
    
    # Saving the results
    combined_df.to_excel('output_results.xlsx', index=False)
    
    # # Displaying the combined dataframe
    # print(combined_df)
    
    
    # Assuming combined_df is already created as per your previous code
    
    # Grouping by 'Player Type' and aggregating the data
    aggregated_df = combined_df.groupby('Player Type').agg({
        '2022 Capacity': 'sum',           # Summing capacities for 2022
        year+' Capacity': 'sum',           # Summing capacities for target year
        'Capacity Difference': 'sum',     # Summing capacity differences
        'Capacity % Change': 'mean',      # Calculating average capacity % change
    }).reset_index()
    
    # # Saving the aggregated results
    # aggregated_df.to_excel(f'{output_dir}/Agg_results_H2_{H2_prop}_{year}_{scenario}.xlsx', index=False)


    
    # # Displaying the aggregated dataframe
    # print(aggregated_df)
    
    return aggregated_df