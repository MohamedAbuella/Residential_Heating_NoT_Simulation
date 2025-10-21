import os
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from pandapipes.properties.properties_toolbox import (
    calculate_mixture_density,
    calculate_mass_fraction_from_molar_fraction,
    calculate_mixture_viscosity,
    calculate_mixture_heat_capacity
)

from pandapipes import *


# Main function to calculate and save mixture properties
def calculate_mixture_properties(fluid1_str, fluid2_str, fluid2_prop, temperature):
########################################
    fluid1 = fluid1_str
    fluid2 = fluid2_str
    temperature = temperature
    hydrogen_proportion = fluid2_prop
    
    
    # molar_lgas = pd.read_csv(os.path.join(pp_dir, 'properties', 'lgas', 'molar_mass.txt'),
    #                             header=None, sep=' ', comment='#').values[0]
    
    fluid1 = pandapipes.call_lib(fluid1)
    fluid2 = pandapipes.call_lib(fluid2)
    
    dens_lgas = fluid1.get_density(temperature)
    visc_lgas = fluid1.get_viscosity(temperature)
    cp_lgas = fluid1.get_heat_capacity(temperature)
    molar_lgas = fluid1.get_molar_mass()
    comp_lgas = fluid1.get_compressibility(1.0)
    der_comp_lgas = fluid1.get_der_compressibility()
    hhv_lgas = fluid1.all_properties["hhv"].get_at_value()
    lhv_lgas = fluid1.all_properties["lhv"].get_at_value()
    
    
    dens_h2 = fluid2.get_density(temperature)
    visc_h2 = fluid2.get_viscosity(temperature)
    cp_h2 = fluid2.get_heat_capacity(temperature)
    molar_h2 = fluid2.get_molar_mass()
    comp_h2 = fluid2.get_compressibility(1.0)
    der_comp_h2 = fluid2.get_der_compressibility()
    hhv_h2 = fluid2.all_properties["hhv"].get_at_value()
    lhv_h2 = fluid2.all_properties["lhv"].get_at_value()
    
    
    components_density = np.concatenate([[dens_lgas], [dens_h2]])
    components_viscosity = np.concatenate([[visc_lgas], [visc_h2]])
    components_heat_capacity = np.concatenate([[cp_lgas], [cp_h2]])
    components_hhv = np.concatenate([[hhv_lgas], [hhv_h2]]).flatten()
    components_lhv = np.concatenate([[lhv_lgas], [lhv_h2]]).flatten()
    components_compressibility = np.concatenate([[comp_lgas], [comp_h2]])
    components_der_compressibility = np.concatenate([[der_comp_lgas], [der_comp_h2]])
    
    components_molar_mass = np.concatenate([[molar_lgas], [molar_h2]])
    components_molar_mass = components_molar_mass.flatten()
    
    
    components_molar_proportions = np.array([1-hydrogen_proportion, hydrogen_proportion])
    
    components_mass_proportions = calculate_mass_fraction_from_molar_fraction(components_molar_proportions,components_molar_mass)
    
        
    mix_density = calculate_mixture_density(components_density, components_mass_proportions)
    
    mix_heat_capacity = calculate_mixture_heat_capacity(components_heat_capacity, components_mass_proportions)
    
    mix_viscosity = calculate_mixture_viscosity(components_viscosity, components_molar_proportions, components_molar_mass)
    
    mix_hhv = np.sum(components_hhv * components_mass_proportions)
    mix_lhv = np.sum(components_lhv * components_mass_proportions)
    
    
    mix_compressibility = np.sum(components_compressibility * components_mass_proportions)
    mix_der_compressibility = np.sum(components_der_compressibility * components_mass_proportions)
    
    mix_molar_mass = np.sum(components_molar_mass * components_molar_proportions)

########################################
    properties = {
        'density': mix_density,
        'viscosity': mix_viscosity,
        'heat_capacity': mix_heat_capacity,
        'molar_mass': mix_molar_mass,
        'higher_heating_value': mix_hhv,
        'lower_heating_value': mix_lhv,
        'compressibility': mix_compressibility,
        'der_compressibility': mix_der_compressibility,
    }
    
    
    return properties


# Example usage:
if __name__ == "__main__":
    hydrogen_proportion = 0.3  # Example: 30% hydrogen, 70% lgas
    temperature = 288.15  # Example temperature in Kelvin
    result = calculate_mixture_properties('lgas', 'hydrogen', hydrogen_proportion, temperature)
    print(result)