# -*- coding: utf-8 -*-
"""
Created on Tue Sep 24 06:07:27 2024

@author: Mhdella
"""


def mdot_energy_conv(H2_prop):
    molar_mass_h2=2.01588 # g/mole 
    molar_mass_gas=16.6045 # g/mole 
    HHV_h2=39.41 #kWh/kg
    HHV_gas=14.62 #kWh/kg
    molar_mass_mix = H2_prop*molar_mass_h2 + (1-H2_prop)*molar_mass_gas
    mass_fr_h2 = (H2_prop*molar_mass_h2)/molar_mass_mix
    mass_fr_gas= ((1-H2_prop)*molar_mass_gas)/molar_mass_mix
    EF = mass_fr_h2*HHV_h2+ mass_fr_gas*HHV_gas
    return EF


def verification_multinet_ins_outs(multinet, EF, H2_prop, eps_imax):
    """
    Verify the input and output consistency for power, gas, and hydrogen networks.

    Parameters:
    - multinet: The multinet model containing network data.
    - EF: Energy factor for conversions.
    - H2_prop: Hydrogen proportion used in calculations.
    - eps_imax: Investment limits adjustment.

    Returns:
    - None: Prints verification results.
    """
    global total_supply, total_demand
    
    EF = mdot_energy_conv(H2_prop)
    HF = mdot_energy_conv(1)
    
    # Initialize energy totals
    total_supply = 0
    total_demand = 0

    # Power Verification
    power_load = sum(multinet.nets['power'].res_load['p_mw'])
    power_gen = sum(multinet.nets['power'].res_gen['p_mw'])
    power_sgen = sum(multinet.nets['power'].res_sgen['p_mw'])
    power_ext_grid = abs(sum(multinet.nets['power'].res_ext_grid['p_mw']))

    total_supply += (power_gen + power_sgen + power_ext_grid)
    total_demand += power_load

    print("Power Verification:")
    print(f"Total Load: {power_load:.2f} MWh")
    print(f"Total Generation: {power_gen:.2f} MWh + {power_sgen:.2f} MWh + {power_ext_grid:.2e} MWh")
    print(f"Total Generation (Check): {power_gen + power_sgen + power_ext_grid:.2f} MWh")
    print(f"Load vs Generation Check: {abs(power_load - (power_gen + power_sgen + power_ext_grid)):.2f} MWh")
    print()

    # Gas Verification
    gas_sink = sum(multinet.nets['gas'].res_sink['mdot_kg_per_s'])
    gas_source = sum(multinet.nets['gas'].res_source['mdot_kg_per_s'])
    gas_ext_grid = abs(sum(multinet.nets['gas'].res_ext_grid['mdot_kg_per_s']))

    # total_supply += (gas_source + gas_ext_grid)
    # total_demand += gas_sink

    # print("Gas Verification:")
    # print(f"Total Gas Sink: {gas_sink:.2f} kg/s")
    # print(f"Total Gas Source: {gas_source:.2f} kg/s + {gas_ext_grid:.2f} kg/s")
    # print(f"Total Gas Source (Check): {gas_source + gas_ext_grid:.2f} kg/s")
    # print(f"Sink vs Source Check: {abs(gas_sink - (gas_source + gas_ext_grid)):.2f} kg/s")
    # print()

    # Energy Conversion from Gas to Power
    gas_energy_sink = sum(multinet.nets['gas'].sink['mdot_kg_per_s']) * (EF * 3600) / (0.4 * 1000)
    gas_energy_source = sum(multinet.nets['gas'].source['mdot_kg_per_s']) * (EF * 3600) / (0.4 * 1000)
    gas_energy_ext_grid = abs(sum(multinet.nets['gas'].res_ext_grid['mdot_kg_per_s']) * (EF * 3600) / (0.4 * 1000))

    total_supply += (gas_energy_source + gas_energy_ext_grid)
    total_demand += gas_energy_sink

    print("Gas to Power Energy Verification:")
    print(f"Total Gas Energy Sink: {gas_energy_sink:.2f} MWh")
    print(f"Total Gas Energy Source: {gas_energy_source:.2f} MWh + {gas_energy_ext_grid:.2f} MWh")
    print(f"Total Energy (Check): {gas_energy_source + gas_energy_ext_grid:.2f} MWh")
    print(f"Energy Check: {abs(gas_energy_sink - (gas_energy_source + gas_energy_ext_grid)):.2f} MWh")
    print()

    # Hydrogen Verification
    hydrogen_sink = sum(multinet.nets['hydrogen'].res_sink['mdot_kg_per_s'])
    hydrogen_source = sum(multinet.nets['hydrogen'].res_source['mdot_kg_per_s'])
    hydrogen_ext_grid = sum(multinet.nets['hydrogen'].res_ext_grid['mdot_kg_per_s'])

    # total_supply += (hydrogen_source + hydrogen_ext_grid)
    # total_demand += hydrogen_sink

    # print("Hydrogen Verification:")
    # print(f"Total Hydrogen Sink: {hydrogen_sink:.2f} kg/s")
    # print(f"Total Hydrogen Source: {hydrogen_source:.2f} kg/s + {hydrogen_ext_grid:.2f} kg/s")
    # print(f"Total Hydrogen Source (Check): {hydrogen_source + hydrogen_ext_grid:.2f} kg/s")
    # print(f"Sink vs Source Check: {abs(hydrogen_sink - (hydrogen_source + hydrogen_ext_grid)):.2f} kg/s")
    # print()

    # Energy Conversion from Hydrogen to Power
    hydrogen_energy_sink = sum(multinet.nets['hydrogen'].res_sink['mdot_kg_per_s']) * (HF * 3600) / (0.4 * 1000)
    hydrogen_energy_source = sum(multinet.nets['hydrogen'].res_source['mdot_kg_per_s']) * (HF * 3600) / (0.4 * 1000)
    hydrogen_energy_ext_grid = sum(multinet.nets['hydrogen'].res_ext_grid['mdot_kg_per_s']) * (HF * 3600) / (0.4 * 1000)

    # total_supply += (hydrogen_energy_source + hydrogen_energy_ext_grid)/2
    # total_demand += hydrogen_energy_sink
    total_supply += hydrogen_energy_source - hydrogen_energy_ext_grid
    total_demand += hydrogen_energy_sink 

    print("Hydrogen to Power Energy Verification:")
    print(f"Total Hydrogen Energy Sink: {hydrogen_energy_sink:.2f} MWh")
    print(f"Total Hydrogen Energy Source: {hydrogen_energy_source:.2f} MWh + {hydrogen_energy_ext_grid:.2f} MWh")
    print(f"Total Energy (Check): {hydrogen_energy_source + hydrogen_energy_ext_grid:.2f} MWh")
    print(f"Energy Check: {abs(hydrogen_energy_sink - (hydrogen_energy_source + hydrogen_energy_ext_grid)):.2f} MWh")
    print()

    # Aggregate Supply and Demand Check
    print("Aggregate Energy Verification:")
    print(f"Total Supply: {total_supply:.2f} MWh")
    print(f"Total Demand: {total_demand:.2f} MWh")
    print(f"Supply vs Demand Check: {abs(total_supply - total_demand):.2f} MWh")
    
    return  total_supply, total_demand
