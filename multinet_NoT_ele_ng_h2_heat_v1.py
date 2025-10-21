# -*- coding: utf-8 -*-
"""
Created on Sat Jul  6 12:56:24 2024

@author: Mhdella
"""

# importing the libs
import pandapipes as ppipes
import pandapower as ppower
import pandapower.converter as pc
import matplotlib.pyplot as matplot
from generate_plots import *

# Libraries for parallel processing
from multiprocessing import Process, Pool
import multiprocessing
from pandas import DataFrame
from numpy import array
from joblib import Parallel, delayed
from tqdm import tqdm, trange

from numpy.random import random
import pandas as pd
import numpy as np
import pulp as lp
import time
import os
import openpyxl
from openpyxl import Workbook, load_workbook

#start_time = time.time()

# importing the major 
from pandapipes.multinet.create_multinet import create_empty_multinet, add_net_to_multinet
from pandapipes.multinet.control.controller.multinet_control import P2GControlMultiEnergy, G2PControlMultiEnergy, GasToGasConversion

from pandapipes.multinet.control.run_control_multinet import run_control

from pandapipes.properties.fluids import _add_fluid_to_net


from pandapipes.properties.fluids import Fluid

from mixture_properties_calcs import *



def data_source(systemData, num_simulations, H2_prop, heat_pumps, hydrogen_boilers, others):
    
    global time_series_profiles
    time_series_profiles = {}
    
    EF = mdot_energy_conv(H2_prop) 
    
      
    # time_series_profiles['g_load_time_series'] = systemData['Gas Consumption']
    # time_series_profiles['e_load_time_series'] = systemData['Power Demand']
    
    from HP_H2B_Social_Interv_multinet_NoT import apply_monte_carlo_interventions  
    systemData = apply_monte_carlo_interventions(systemData, num_simulations, heat_pumps, hydrogen_boilers, others)
    
    systemData['Gas Consumption_MWh'] = systemData['Adjusted Gas Demand']
    systemData['Power Demand'] = systemData['Adjusted Power Demand']
    systemData['Gas Consumption_kg_s']=systemData['Gas Consumption_MWh']*(0.4*1000)/(EF*3600) # to convert from MWh to kg/s
    net_ng = ppipes.create_empty_network(fluid="hgas")
    systemData['Gas Consumption_m3_h'] = systemData['Gas Consumption_kg_s']*3600/net_ng.fluid.get_density(288.15) # from kg/s to m3/s 
     
    systemData['Hydrogen Consumption_MWh'] = systemData['Adjusted Hydrogen Demand']
    
    systemData['Hydrogen Consumption_kg_s']=systemData['Hydrogen Consumption_MWh']*(0.4*1000)/(EF*3600) # to convert from MWh to kg/s
    net_hyd = ppipes.create_empty_network(fluid="hydrogen")
    systemData['Hydrogen Consumption_m3_h'] = systemData['Hydrogen Consumption_kg_s']*3600/net_hyd.fluid.get_density(288.15) # from kg/s to m3/s 

    
    time_series_profiles['g_load_time_series'] = systemData['Gas Consumption_m3_h']
    time_series_profiles['e_load_time_series'] = systemData['Power Demand']
    time_series_profiles['hyd_load_time_series'] = systemData['Hydrogen Consumption_m3_h']


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

def energy_h2_gas(H2_prop, optimal_q_g):
    molar_mass_h2=2.01588 # g/mole 
    molar_mass_gas=16.6045 # g/mole 
    HHV_h2=39.41 #kWh/kg
    HHV_gas=14.62 #kWh/kg
    molar_mass_mix = H2_prop*molar_mass_h2 + (1-H2_prop)*molar_mass_gas
    mass_fr_h2 = (H2_prop*molar_mass_h2)/molar_mass_mix
    mass_fr_gas= ((1-H2_prop)*molar_mass_gas)/molar_mass_mix
    EF = mass_fr_h2*HHV_h2+ mass_fr_gas*HHV_gas
    mdot_mix = optimal_q_g/EF
    mdot_h2 = mdot_mix*mass_fr_h2
    mdot_gas = mdot_mix*mass_fr_gas
    qg_h2 = mdot_h2*HHV_h2
    qg_gas = mdot_gas*HHV_gas
    mdot_qg = {'mdot_h2': mdot_h2,
        'mdot_gas': mdot_gas,
        'qg_h2': qg_h2,
        'qg_gas': qg_gas}
    
    return mdot_qg



def gas_network(time_steps, HB_NGB_share, temp_system):
    
    # net = ppipes.create_empty_network(fluid="lgas")    
    net_ng = ppipes.create_empty_network(fluid="hgas")
    
    temp_system = 288.15  #  temperature in Kelvin

    mixture_properties = calculate_mixture_properties('hgas', 'hydrogen', HB_NGB_share, temp_system)

    
    net = ppipes.create_empty_network(fluid='hgas')
    
    
    
    fluid_new = ppipes.create_constant_fluid('hgas_hydrogen_mixture', 
                          fluid_type='gas',
                          density=mixture_properties['density'],
                          viscosity=mixture_properties['viscosity'],
                          compressibility=mixture_properties['compressibility'],
                          heat_capacity=mixture_properties['heat_capacity'],
                          molar_mass=mixture_properties['molar_mass'],
                          higher_heating_value=mixture_properties['higher_heating_value'],
                          lower_heating_value=mixture_properties['lower_heating_value'],
                          der_compressibility=mixture_properties['der_compressibility'],
                          hhv=mixture_properties['higher_heating_value'])
    
    _add_fluid_to_net(net, fluid_new, overwrite=True)
    
    
    
    EF=mdot_energy_conv(HB_NGB_share)


    n1 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 1", geodata=(0, 0))
    n2 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 2", geodata=(0, -1))
    n3 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 3", geodata=(1, 0))
    n4 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 4", geodata=(0, -2))
    n5 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 5", geodata=(0, -3))
    n6 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 6", geodata=(1, -3))
    n7 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 7", geodata=(1, -2))
    n8 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 8", geodata=(1, -1))
    n9 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 9", geodata=(2, 0))
    n10 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 10", geodata=(2, -1))
    n11 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 11", geodata=(2, -2))
    n12 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 12", geodata=(3, -1))
    n13 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 13", geodata=(3, 0))
    n14 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 14", geodata=(2, -3))
    n15 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 15", geodata=(3, -2))
    
    
    # Create branch elements (pipes)
    pipe1 = ppipes.create_pipe_from_parameters(net, from_junction=n1, to_junction=n3, 
                                                length_km=6.970, k_mm=0.025, diameter_m=0.750, name="Branch 1")
    pipe2 = ppipes.create_pipe_from_parameters(net, from_junction=n3, to_junction=n9, 
                                                length_km=7.620, k_mm=0.025, diameter_m=0.750, name="Branch 2")
    pipe3 = ppipes.create_pipe_from_parameters(net, from_junction=n9, to_junction=n10, 
                                                length_km=4.606, k_mm=0.025, diameter_m=0.750, name="Branch 3")
    pipe4 = ppipes.create_pipe_from_parameters(net, from_junction=n2, to_junction=n4, 
                                                length_km=3.750, k_mm=0.025, diameter_m=0.750, name="Branch 4")
    pipe5 = ppipes.create_pipe_from_parameters(net, from_junction=n4, to_junction=n5, 
                                                length_km=3.340, k_mm=0.025, diameter_m=0.750, name="Branch 5")
    pipe6 = ppipes.create_pipe_from_parameters(net, from_junction=n5, to_junction=n6, 
                                                length_km=6.780, k_mm=0.025, diameter_m=0.750, name="Branch 6")
    pipe7 = ppipes.create_pipe_from_parameters(net, from_junction=n6, to_junction=n7, 
                                                length_km=9.130, k_mm=0.025, diameter_m=0.750, name="Branch 7")
    pipe8 = ppipes.create_pipe_from_parameters(net, from_junction=n7, to_junction=n8, 
                                                length_km=8.090, k_mm=0.025, diameter_m=0.750, name="Branch 8")
    pipe9 = ppipes.create_pipe_from_parameters(net, from_junction=n8, to_junction=n10, 
                                                length_km=5.360, k_mm=0.025, diameter_m=0.750, name="Branch 9")
    pipe10 = ppipes.create_pipe_from_parameters(net, from_junction=n12, to_junction=n13, 
                                                length_km=9.581, k_mm=0.025, diameter_m=0.450, name="Branch 10")
    pipe11 = ppipes.create_pipe_from_parameters(net, from_junction=n11, to_junction=n14, 
                                                length_km=7.100, k_mm=0.025, diameter_m=0.450, name="Branch 11")
    pipe12 = ppipes.create_pipe_from_parameters(net, from_junction=n11, to_junction=n15, 
                                                length_km=4.231, k_mm=0.025, diameter_m=0.400, name="Branch 12")
    pipe13 = ppipes.create_pipe_from_parameters(net, from_junction=n10, to_junction=n12, 
                                                length_km=1.000, k_mm=0.025, diameter_m=0.450, name="Branch 13")
    pipe14 = ppipes.create_pipe_from_parameters(net, from_junction=n10, to_junction=n11, 
                                                length_km=1.000, k_mm=0.025, diameter_m=0.450, name="Branch 14")
    
    
    #-------------------------------------------------------------------------------
    # Create junction elements
    # Sinks    
    
    sink1 = ppipes.create_sink(net, junction=n1, 
                               mdot_kg_per_s=time_series_profiles['g_load_time_series']['1-SLWK'][time_steps]
                               * net_ng.fluid.get_density(temp_system) /3600, name="Sink 1")
    sink2 = ppipes.create_sink(net, junction=n2,
                               mdot_kg_per_s=time_series_profiles['g_load_time_series']['2-BISH'][time_steps]
                               * net_ng.fluid.get_density(temp_system) /3600, name="Sink 2")
    sink3 = ppipes.create_sink(net, junction=n3,
                               mdot_kg_per_s=time_series_profiles['g_load_time_series']['3-PRES'][time_steps]
                               * net_ng.fluid.get_density(temp_system) /3600, name="Sink 3")
    sink4 = ppipes.create_sink(net, junction=n4,
                               mdot_kg_per_s=time_series_profiles['g_load_time_series']['4-LEAS'][time_steps]
                               * net_ng.fluid.get_density(temp_system) /3600, name="Sink 4")
    sink5 = ppipes.create_sink(net, junction=n5, 
                               mdot_kg_per_s=time_series_profiles['g_load_time_series']['5-MIDD'][time_steps]
                               * net_ng.fluid.get_density(temp_system) /3600, name="Sink 5")
    sink6 = ppipes.create_sink(net, junction=n6, 
                               mdot_kg_per_s=time_series_profiles['g_load_time_series']['6-USHAT'][time_steps]
                              * net_ng.fluid.get_density(temp_system) /3600, name="Sink 6")
    sink7 = ppipes.create_sink(net, junction=n7,
                               mdot_kg_per_s=time_series_profiles['g_load_time_series']['7-WEDMRI'][time_steps]
                               * net_ng.fluid.get_density(temp_system) /3600, name="Sink 7")
    sink8 = ppipes.create_sink(net, junction=n8,
                               mdot_kg_per_s=time_series_profiles['g_load_time_series']['8-TANFRI'][time_steps]
                               * net_ng.fluid.get_density(temp_system) /3600, name="Sink 8")
    sink9 = ppipes.create_sink(net, junction=n9, 
                               mdot_kg_per_s=time_series_profiles['g_load_time_series']['9-RTYN'][time_steps]
                               * net_ng.fluid.get_density(temp_system) /3600, name="Sink 9")
    sink10 = ppipes.create_sink(net, junction=n10,
                                mdot_kg_per_s=time_series_profiles['g_load_time_series']['10-LOWTRI'][time_steps]
                                * net_ng.fluid.get_density(temp_system) /3600, name="Sink 10")
    sink11 = ppipes.create_sink(net, junction=n11, 
                                mdot_kg_per_s=time_series_profiles['g_load_time_series']['11-LOWTROT'][time_steps]
                                * net_ng.fluid.get_density(temp_system) /3600, name="Sink 11")
    sink12 = ppipes.create_sink(net, junction=n12,
                                mdot_kg_per_s=time_series_profiles['g_load_time_series']['12-LOWTROL'][time_steps]
                                * net_ng.fluid.get_density(temp_system) /3600, name="Sink 12")
    sink13 = ppipes.create_sink(net, junction=n13, 
                                mdot_kg_per_s=time_series_profiles['g_load_time_series']['13-LAMERI'][time_steps]
                                * net_ng.fluid.get_density(temp_system) /3600, name="Sink 13")
    sink14 = ppipes.create_sink(net, junction=n14, 
                                mdot_kg_per_s=time_series_profiles['g_load_time_series']['14-PLANVI'][time_steps]
                                * net_ng.fluid.get_density(temp_system) /3600, name="Sink 14")
    sink15 = ppipes.create_sink(net, junction=n15, 
                                mdot_kg_per_s=time_series_profiles['g_load_time_series']['15-BLAYRI'][time_steps]
                                * net_ng.fluid.get_density(temp_system) /3600, name="Sink 15", controllable=True)
    
    ext_grid1 = ppipes.create_ext_grid(net, junction=n1, p_bar=39, t_k=temp_system, name="Grid Connection 1")
    ext_grid2 = ppipes.create_ext_grid(net, junction=n2, p_bar=39, t_k=temp_system, name="Grid Connection 2")
    
    #ppipes.to_json(net, "Gas_Network.json")
    
    return net



def power_network(time_steps, genData, systemData, H2_prop):
    

    year = systemData['Year']; scenario = systemData['scenario']
    
    
    if H2_prop==1 or systemData['ccs_fg']==1:
        CO2_penalty =0
    else:
        CO2_penalty = systemData['Carbon Price'].loc[systemData['Carbon Price']['Year'] == int(year), scenario].iloc[0]
    
    systemData['Gen Cost'] = pd.read_csv('Data/genCost.csv')

    systemData['Gen Cost']['5'] = systemData['Players']['costs'][:25] + (systemData['Players']['emissions'][:25] * CO2_penalty)

    
    net_temp = ppower.create_empty_network(f_hz=50, sn_mva=100 )
    net = ppower.create_empty_network(f_hz=50, sn_mva=100 )

    def caseNoT(): 

        ppc = {"version": '2'} 
     
        ##-----  Power Flow Data  -----## 
        ## system MVA base 
        ppc["baseMVA"] = 100.0 
     
        ## bus data 
        # bus_i type Pd Qd Gs Bs area Vm Va baseKV zone Vmax Vmin 
        bus_data = pd.read_csv('Data/busData.csv')
        # bus_data['11']=1.1
        # bus_data['11']=0.9
        ppc["bus"] = bus_data.to_numpy()
        
         ## generator data 
          # bus, Pg, Qg, Qmax, Qmin, Vg, mBase, status, Pmax, Pmin, Pc1, Pc2, 
          # Qc1min, Qc1max, Qc2min, Qc2max, ramp_agc, ramp_10, ramp_30, ramp_q, apf 
        #ppc["gen"] = pd.read_csv('genData.csv').to_numpy()
        ppc["gen"] = genData.to_numpy()

        ppc["branch"] = pd.read_csv('Data/branchData.csv').to_numpy()


         ##-----  OPF Data  -----## 
          ## generator cost data 
          # 1 startup shutdown n x1 y1 ... xn yn 
          # 2 startup shutdown n c(n-1) ... c0 
          
        # ppc["gencost"] = pd.read_csv('Data/genCost.csv').to_numpy()
        
        ppc["gencost"] = systemData['Gen Cost'].to_numpy()
        

        ppc["bus_name"] = pd.read_csv('Data/busName.csv').to_numpy()
        

        return ppc



    ppc = caseNoT()

    net_temp = pc.from_ppc(ppc, f_hz=50, validate_conversion=False) # Importing to temp

    # -------------------------------------------------------------------------------------
    #Create the buses
    net.bus = net_temp.bus # Transferring from the temp network
    
    bus_id = net.bus['name'] # To create a bus id list . Used to call the bus pos
    
    # Create the branches/lines
    for i in range(np.shape(ppc['branch'])[0]):
        ppower.create_line_from_parameters(net, from_bus=list(bus_id).index(ppc['branch'][i][0]), 
                                            to_bus=list(bus_id).index(ppc['branch'][i][1]), 
                                            length_km = 1, r_ohm_per_km=ppc['branch'][i][2] , 
                                            x_ohm_per_km=ppc['branch'][i][3], 
                                            c_nf_per_km=ppc['branch'][i][4], max_i_ka=100)
     
    #Create the generators    
    for i in range(np.shape(ppc['gen'])[0]):
        ppower.create_gen(net, bus=list(bus_id).index(ppc['gen'][i][0]),
                          p_mw=ppc['gen'][i][1],
                          # vm_pu=ppc['gen'][i][5],
                          vm_pu=1.0,
                          max_q_mvar= ppc['gen'][i][3],
                          min_q_mvar=ppc['gen'][i][4],
                          max_p_mw=ppc['gen'][i][8],
                          min_p_mw=ppc['gen'][i][9],
                          controllable=True)
    net.load = net_temp.load    
    net.load['p_mw'] = np.array(time_series_profiles['e_load_time_series'].iloc[time_steps])
    net.load['name'] = np.array(time_series_profiles['e_load_time_series'].columns) # To add the name of the bus
    # Assign the generator costs to the respective generators
    for i in range(np.shape(net.gen)[0]):
        ppower.create_poly_cost(net, element=i, et="gen",
                                cp2_eur_per_mw2=ppc['gencost'][i][4],
                                cp1_eur_per_mw=ppc['gencost'][i][5],
                                cp0_eur=ppc['gencost'][i][6]
                                )
    
    # # Create power storage
    ppower.create_storage(net, bus=0, p_mw=0, max_e_mwh=10, name="Battery")
    # ppower.create_storage(net, bus=0, p_mw=0, max_e_mwh=50, name="Battery", controllable=True)


    # Create external grid as ref bus
    ppower.create_ext_grid(net, 0, min_p_mw=0, max_p_mw=0)
    
    return net




def hydrogen_network(time_steps, H2_prop, temp_system):
    
    net = ppipes.create_empty_network(fluid="hydrogen")        
    temp_system = 288.15  #  temperature in Kelvin
    

    EF=mdot_energy_conv(H2_prop)


    n1 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 1", geodata=(0, 0))
    n2 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 2", geodata=(0, -1))
    n3 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 3", geodata=(1, 0))
    n4 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 4", geodata=(0, -2))
    n5 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 5", geodata=(0, -3))
    n6 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 6", geodata=(1, -3))
    n7 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 7", geodata=(1, -2))
    n8 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 8", geodata=(1, -1))
    n9 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 9", geodata=(2, 0))
    n10 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 10", geodata=(2, -1))
    n11 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 11", geodata=(2, -2))
    n12 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 12", geodata=(3, -1))
    n13 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 13", geodata=(3, 0))
    n14 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 14", geodata=(2, -3))
    n15 = ppipes.create_junction(net, pn_bar=1, tfluid_k=temp_system, name="Node 15", geodata=(3, -2))
    
    # Create branch elements (pipes)
    pipe1 = ppipes.create_pipe_from_parameters(net, from_junction=n1, to_junction=n3, 
                                                length_km=6.970, k_mm=0.025, diameter_m=0.750, name="Branch 1")
    pipe2 = ppipes.create_pipe_from_parameters(net, from_junction=n3, to_junction=n9, 
                                                length_km=7.620, k_mm=0.025, diameter_m=0.750, name="Branch 2")
    pipe3 = ppipes.create_pipe_from_parameters(net, from_junction=n9, to_junction=n10, 
                                                length_km=4.606, k_mm=0.025, diameter_m=0.750, name="Branch 3")
    pipe4 = ppipes.create_pipe_from_parameters(net, from_junction=n2, to_junction=n4, 
                                                length_km=3.750, k_mm=0.025, diameter_m=0.750, name="Branch 4")
    pipe5 = ppipes.create_pipe_from_parameters(net, from_junction=n4, to_junction=n5, 
                                                length_km=3.340, k_mm=0.025, diameter_m=0.750, name="Branch 5")
    pipe6 = ppipes.create_pipe_from_parameters(net, from_junction=n5, to_junction=n6, 
                                                length_km=6.780, k_mm=0.025, diameter_m=0.750, name="Branch 6")
    pipe7 = ppipes.create_pipe_from_parameters(net, from_junction=n6, to_junction=n7, 
                                                length_km=9.130, k_mm=0.025, diameter_m=0.750, name="Branch 7")
    pipe8 = ppipes.create_pipe_from_parameters(net, from_junction=n7, to_junction=n8, 
                                                length_km=8.090, k_mm=0.025, diameter_m=0.750, name="Branch 8")
    pipe9 = ppipes.create_pipe_from_parameters(net, from_junction=n8, to_junction=n10, 
                                                length_km=5.360, k_mm=0.025, diameter_m=0.750, name="Branch 9")
    pipe10 = ppipes.create_pipe_from_parameters(net, from_junction=n12, to_junction=n13, 
                                                length_km=9.581, k_mm=0.025, diameter_m=0.450, name="Branch 10")
    pipe11 = ppipes.create_pipe_from_parameters(net, from_junction=n11, to_junction=n14, 
                                                length_km=7.100, k_mm=0.025, diameter_m=0.450, name="Branch 11")
    pipe12 = ppipes.create_pipe_from_parameters(net, from_junction=n11, to_junction=n15, 
                                                length_km=4.231, k_mm=0.025, diameter_m=0.400, name="Branch 12")
    pipe13 = ppipes.create_pipe_from_parameters(net, from_junction=n10, to_junction=n12, 
                                                length_km=1.000, k_mm=0.025, diameter_m=0.450, name="Branch 13")
    pipe14 = ppipes.create_pipe_from_parameters(net, from_junction=n10, to_junction=n11, 
                                                length_km=1.000, k_mm=0.025, diameter_m=0.450, name="Branch 14")
    
    
    #-------------------------------------------------------------------------------
    # Create junction elements
    # Sinks    
    
    sink1 = ppipes.create_sink(net, junction=n1, 
                               mdot_kg_per_s=time_series_profiles['hyd_load_time_series']['1-SLWK'][time_steps] * 0
                               * net.fluid.get_density(temp_system) /3600, name="Sink 1")
    sink2 = ppipes.create_sink(net, junction=n2,
                               mdot_kg_per_s=time_series_profiles['hyd_load_time_series']['2-BISH'][time_steps] * 0
                               * net.fluid.get_density(temp_system) /3600, name="Sink 2")
    sink3 = ppipes.create_sink(net, junction=n3,
                               mdot_kg_per_s=time_series_profiles['hyd_load_time_series']['3-PRES'][time_steps] * 0
                               * net.fluid.get_density(temp_system) /3600, name="Sink 3")
    sink4 = ppipes.create_sink(net, junction=n4,
                               mdot_kg_per_s=time_series_profiles['hyd_load_time_series']['4-LEAS'][time_steps] * 0
                               * net.fluid.get_density(temp_system) /3600, name="Sink 4")
    sink5 = ppipes.create_sink(net, junction=n5, 
                               mdot_kg_per_s=time_series_profiles['hyd_load_time_series']['5-MIDD'][time_steps] * 0
                               * net.fluid.get_density(temp_system) /3600, name="Sink 5")
    sink6 = ppipes.create_sink(net, junction=n6, 
                               mdot_kg_per_s=time_series_profiles['hyd_load_time_series']['6-USHAT'][time_steps] * 0
                              * net.fluid.get_density(temp_system) /3600, name="Sink 6")
    sink7 = ppipes.create_sink(net, junction=n7,
                               mdot_kg_per_s=time_series_profiles['hyd_load_time_series']['7-WEDMRI'][time_steps] * 0
                               * net.fluid.get_density(temp_system) /3600, name="Sink 7")
    sink8 = ppipes.create_sink(net, junction=n8,
                               mdot_kg_per_s=time_series_profiles['hyd_load_time_series']['8-TANFRI'][time_steps] * 0
                               * net.fluid.get_density(temp_system) /3600, name="Sink 8")
    sink9 = ppipes.create_sink(net, junction=n9, 
                               mdot_kg_per_s=time_series_profiles['hyd_load_time_series']['9-RTYN'][time_steps] * 0
                               * net.fluid.get_density(temp_system) /3600, name="Sink 9")
    sink10 = ppipes.create_sink(net, junction=n10,
                                mdot_kg_per_s=time_series_profiles['hyd_load_time_series']['10-LOWTRI'][time_steps] * 0
                                * net.fluid.get_density(temp_system) /3600, name="Sink 10")
    sink11 = ppipes.create_sink(net, junction=n11, 
                                mdot_kg_per_s=time_series_profiles['hyd_load_time_series']['11-LOWTROT'][time_steps] * 0
                                * net.fluid.get_density(temp_system) /3600, name="Sink 11")
    sink12 = ppipes.create_sink(net, junction=n12,
                                mdot_kg_per_s=time_series_profiles['hyd_load_time_series']['12-LOWTROL'][time_steps] * 0
                                * net.fluid.get_density(temp_system) /3600, name="Sink 12")
    sink13 = ppipes.create_sink(net, junction=n13, 
                                mdot_kg_per_s=time_series_profiles['hyd_load_time_series']['13-LAMERI'][time_steps] * 0
                                * net.fluid.get_density(temp_system) /3600, name="Sink 13")
    sink14 = ppipes.create_sink(net, junction=n14, 
                                mdot_kg_per_s=time_series_profiles['hyd_load_time_series']['14-PLANVI'][time_steps] * 0
                                * net.fluid.get_density(temp_system) /3600, name="Sink 14")
    sink15 = ppipes.create_sink(net, junction=n15, 
                                mdot_kg_per_s=time_series_profiles['hyd_load_time_series']['15-BLAYRI'][time_steps] * 0
                                * net.fluid.get_density(temp_system) /3600, name="Sink 15", controllable=True)
    
    ext_grid3 = ppipes.create_ext_grid(net, junction=n1, p_bar=39, t_k=temp_system, name="Grid Connection 1")
    ext_grid4 = ppipes.create_ext_grid(net, junction=n2, p_bar=39, t_k=temp_system, name="Grid Connection 2")
    
    #ppipes.to_json(net, "Hydrogen_Network.json")
    
    return net



    
def coupling_p2g(net_power, gas_network, multinet, H2_prop):
    
    
    # create elements corresponding to conversion units
    # Power-to-gas 1
    # global p2g_1_el,p2g_1_gas
    # capacities = [8, 6, 6, 6] # in MW
    capacities = [0, 0, 0, 0] # in MW
    p2g_1_el = ppower.create_load(net_power, bus=90, p_mw=capacities[0], name="p2g1 consumption")
    p2g_1_gas = ppipes.create_source(gas_network, junction=9, mdot_kg_per_s=0, name="p2g1 feed in")
    p2g_1_ctrl = P2GControlMultiEnergy(multinet, p2g_1_el, p2g_1_gas, efficiency=0.8,
                                 name_power_net="power", name_gas_net="gas")
    
    # Power-to-gas 2
    # global p2g_2_el,p2g_2_gas
    p2g_2_el = ppower.create_load(net_power, bus=127, p_mw=capacities[1], name="p2g2 consumption")
    p2g_2_gas = ppipes.create_source(gas_network, junction=9, mdot_kg_per_s=0, name="p2g2 feed in")
    p2g_2_ctrl = P2GControlMultiEnergy(multinet, p2g_2_el, p2g_2_gas, efficiency=0.8,
                                  name_power_net="power", name_gas_net="gas")
    
    # # # Power-to-gas 3
    # global p2g_3_el,p2g_3_gas
    p2g_3_el = ppower.create_load(net_power, bus=127, p_mw=capacities[2], name="p2g3 consumption")
    p2g_3_gas = ppipes.create_source(gas_network, junction=9, mdot_kg_per_s=0, name="p2g3 feed in")
    p2g_3_ctrl = P2GControlMultiEnergy(multinet, p2g_3_el, p2g_3_gas, efficiency=0.8,
                                  name_power_net="power", name_gas_net="gas")
    
    # # Power-to-gas 4
    # global p2g_4_el,p2g_4_gas
    p2g_4_el = ppower.create_load(net_power, bus=8, p_mw=capacities[3], name="p2g4 consumption")
    p2g_4_gas = ppipes.create_source(gas_network, junction=9, mdot_kg_per_s=0, name="p2g4 feed in")
    p2g_4_ctrl = P2GControlMultiEnergy(multinet, p2g_4_el, p2g_4_gas, efficiency=0.8,
                                  name_power_net="power", name_gas_net="gas")
  
    
    

def coupling_chp(net_power, net_hyd, multinet, H2_prop, systemData):
    """
    Coupled Combined Heat and Power (CHP) units.
    Each CHP consumes gas (sink in gas network) and produces electricity (sgen in power network).
    Costs are assigned explicitly based on systemData['Gen Cost'].
    """
    # Define capacities in MW
    capacities = [10, 10]
    # capacities = [0, 0]

    efficiency = 0.4

    # Compute energy conversion factor (kg/s <-> MW)
    EF = mdot_energy_conv(H2_prop)

    # # Extract cost coefficients for CHP units, (adjust according to genCost.csv)
    # chp_cost_row = systemData['Gen Cost'].iloc[5]*0
    chp_cost_row = systemData['Gen Cost'].iloc[5]

    cp2, cp1, cp0 = 0, chp_cost_row[5], chp_cost_row[6]
    
    hyd_cost = 85  # Initial with approx. marginal cost of H2 from EZ & ATR
    cp1 = hyd_cost  

    print(f"CHP cost coefficients: cp1={cp1:.4f}, cp0={cp0:.4f}")

    # --- CHP 1 ---
    g2p_1_gas = ppipes.create_sink(
        net_hyd, junction=9,
        mdot_kg_per_s=(capacities[0] * 1000 * efficiency) / (EF * 3600),
        name="CHP1 consumption")

    g2p_1_el = ppower.create_sgen(
        net_power, bus=89, p_mw=0,
        min_p_mw=0, max_p_mw=capacities[0],
        controllable=True, name="CHP1 feed in")

    ppower.create_poly_cost(
        net_power, element=len(net_power.sgen)-1, et="sgen",
        cp2_eur_per_mw2=cp2, cp1_eur_per_mw=cp1, cp0_eur=cp0)

    g2p_1_ctrl = G2PControlMultiEnergy(
        multinet, g2p_1_el, g2p_1_gas, efficiency=efficiency,
        name_power_net="power", name_gas_net="hydrogen", calc_gas_from_power=False)

    # --- CHP 2 ---
    g2p_2_gas = ppipes.create_sink(
        net_hyd, junction=9,
        mdot_kg_per_s=(capacities[1] * 1000 * efficiency) / (EF * 3600),
        name="CHP2 consumption")

    g2p_2_el = ppower.create_sgen(
        net_power, bus=23, p_mw=0,
        min_p_mw=0, max_p_mw=capacities[1],
        controllable=True, name="CHP2 feed in")

    ppower.create_poly_cost(
        net_power, element=len(net_power.sgen)-1, et="sgen",
        cp2_eur_per_mw2=cp2, cp1_eur_per_mw=cp1, cp0_eur=cp0)

    g2p_2_ctrl = G2PControlMultiEnergy(
        multinet, g2p_2_el, g2p_2_gas, efficiency=efficiency,
        name_power_net="power", name_gas_net="hydrogen", calc_gas_from_power=False)

    return [g2p_1_ctrl, g2p_2_ctrl]


def coupling_gfg(net_power, net_hyd, multinet, H2_prop, systemData):
    """
    Coupled Gas-Fired Generator (GFG) units.
    Each GFG consumes gas and produces electricity.
    Costs are assigned from systemData['Gen Cost'].
    """
    
    capacities = [30, 30, 50]
    # capacities = [15, 15, 25]
    # capacities = [0, 0, 0]


    efficiency = 0.55
    EF = mdot_energy_conv(H2_prop)

    # gfg_cost_row = systemData['Gen Cost'].iloc[0]*0
    gfg_cost_row = systemData['Gen Cost'].iloc[0]

    cp2, cp1, cp0 = 0, gfg_cost_row[5], gfg_cost_row[6]
    
    hyd_cost = 85  # Initial with approx. marginal cost of H2 from EZ & ATR
    cp1 = hyd_cost  
    
    print(f"GFG cost coefficients: cp1={cp1:.4f}, cp0={cp0:.4f}")

    # --- GFG 1 ---
    g2p_3_gas = ppipes.create_sink(
        net_hyd, junction=11,
        mdot_kg_per_s=(capacities[0] * 1000 * efficiency) / (EF * 3600),
        name="GFG1 consumption")

    g2p_3_el = ppower.create_sgen(
        net_power, bus=179, p_mw=0,
        min_p_mw=0, max_p_mw=capacities[0],
        controllable=True, name="GFG1 feed in")

    ppower.create_poly_cost(
        net_power, element=len(net_power.sgen)-1, et="sgen",
        cp2_eur_per_mw2=cp2, cp1_eur_per_mw=cp1, cp0_eur=cp0)

    g2p_3_ctrl = G2PControlMultiEnergy(
        multinet, g2p_3_el, g2p_3_gas, efficiency=efficiency,
        name_power_net="power", name_gas_net="hydrogen", calc_gas_from_power=False)

    # --- GFG 2 ---
    g2p_4_gas = ppipes.create_sink(
        net_hyd, junction=11,
        mdot_kg_per_s=(capacities[1] * 1000 * efficiency) / (EF * 3600),
        name="GFG2 consumption")
    g2p_4_el = ppower.create_sgen(
        net_power, bus=179, p_mw=0,
        min_p_mw=0, max_p_mw=capacities[1],
        controllable=True, name="GFG2 feed in")

    ppower.create_poly_cost(
        net_power, element=len(net_power.sgen)-1, et="sgen",
        cp2_eur_per_mw2=cp2, cp1_eur_per_mw=cp1, cp0_eur=cp0)

    g2p_4_ctrl = G2PControlMultiEnergy(
        multinet, g2p_4_el, g2p_4_gas, efficiency=efficiency,
        name_power_net="power", name_gas_net="hydrogen", calc_gas_from_power=False)

    # --- GFG 3 ---
    g2p_5_gas = ppipes.create_sink(
        net_hyd, junction=12,
        mdot_kg_per_s=(capacities[2] * 1000 * efficiency) / (EF * 3600),
        name="GFG3 consumption")

    g2p_5_el = ppower.create_sgen(
        net_power, bus=122, p_mw=0,
        min_p_mw=0, max_p_mw=capacities[2],
        controllable=True, name="GFG3 feed in")

    ppower.create_poly_cost(
        net_power, element=len(net_power.sgen)-1, et="sgen",
        cp2_eur_per_mw2=0, cp1_eur_per_mw=cp1, cp0_eur=cp0)

    g2p_5_ctrl = G2PControlMultiEnergy(
        multinet, g2p_5_el, g2p_5_gas, efficiency=efficiency,
        name_power_net="power", name_gas_net="hydrogen", calc_gas_from_power=False)

    return [g2p_3_ctrl, g2p_4_ctrl, g2p_5_ctrl]




def coupling_fc(net_power, net_hyd, multinet, H2_prop, systemData):

    capacity = 50 # Capacity in MW
    efficiency = 0.60
    
    # Compute energy conversion factor (kg/s <-> MW)
    EF = mdot_energy_conv(H2_prop)
    
    hyd_cost = 85  # Initial with approx. marginal cost of H2 from EZ & ATR
    cp1 = hyd_cost  


    g2p_6_gas = ppipes.create_sink(
        net_hyd, junction=1,
        mdot_kg_per_s=(capacity * 1000 * efficiency) / (EF * 3600),
        name="FC1 consumption")

    g2p_6_el = ppower.create_sgen(
        net_power, bus=23, p_mw=0,
        min_p_mw=0, max_p_mw=capacity,
        controllable=True, name="FC1 feed in")

    ppower.create_poly_cost(
        net_power, element=len(net_power.sgen)-1, et="sgen",
        cp2_eur_per_mw2=0, cp1_eur_per_mw=cp1, cp0_eur=0)

    g2p_6_ctrl = G2PControlMultiEnergy(
        multinet, g2p_6_el, g2p_6_gas, efficiency=efficiency,
        name_power_net="power", name_gas_net="hydrogen", calc_gas_from_power=False)

  
    return [g2p_6_ctrl]



def electrolyser(net_power, net_hyd, multinet, EZ_capacity_value, H2_prop):
    
    capacity = EZ_capacity_value # Capacity in MW
   
    # Electrolyser can be modelled as a P2G
    electzr_in   = ppower.create_load(net_power, bus = 0, p_mw=capacity, name='Electrolyser_consumption' )
    electzr_out  = ppipes.create_source(net_hyd, junction=0, mdot_kg_per_s=0.0, max_p_mw=capacity, name='Electrolyser_out')
    electzr_ctrl = P2GControlMultiEnergy(multinet, electzr_in, electzr_out, efficiency = 0.6, 
                                          name_power_net= 'power', name_gas_net='hydrogen')
    
    return electzr_out




def coupling_chp_heat(net_power, net_gas, multinet, CHP_capacity_value, H2_prop):
    
    # create elements corresponding to conversion units
    # CHP units
    # Gas-to-power 1
    # global g2p_1_gas, g2p_1_el
    # capacities = [9, 9] # in MW
    capacities = [0, 0]
    # capacities = [CHP_capacity_value/2, CHP_capacity_value/2]  # in MW

    EF=mdot_energy_conv(H2_prop)
    
    print('EF=', EF)
    
    
    g2p_1_gas = ppipes.create_sink(net_gas, junction=9, mdot_kg_per_s=(capacities[0] * 1000*0.4)/(EF*3600), name="CHP1 consumption")
    g2p_1_el = ppower.create_sgen(net_power, bus=89, p_mw=0,
                                  min_p_mw=0, max_p_mw=capacities[0], name="CHP1 feed in", controllable=True)
    g2p_1_ctrl = G2PControlMultiEnergy(multinet, g2p_1_el, g2p_1_gas, efficiency=0.4,
                                 name_power_net="power", name_gas_net="gas")
    
    # Gas-to-power 2
    # global g2p_2_gas, g2p_2_el
    g2p_2_gas = ppipes.create_sink(net_gas, junction=9, mdot_kg_per_s=(capacities[1] * 1000*0.4)/(EF*3600), name="CHP2 consumption")
    g2p_2_el = ppower.create_sgen(net_power, bus=23, p_mw=0, 
                                  min_p_mw=0, max_p_mw=capacities[1], name="CHP2 feed in", controllable=True)
    g2p_2_ctrl = G2PControlMultiEnergy(multinet, g2p_2_el, g2p_2_gas, efficiency=0.4,
                                  name_power_net="power", name_gas_net="gas")
    
    




def autothermal_reformer(net_gas, net_hyd, multinet, ATR_capacity_value, H2_prop):
    # Calculate the initial mass flow rate of hydrogen output (kg/s)
    # Hydrogen HHV = 39.41 kWh/kg
    mdot_h2_out = ATR_capacity_value * (39.41* 3600)/(0.4 * 1000) 

    # Calculate the required gas input (kg/s)
    # ATR efficiency = 0.75 (energy out / energy in)

    energy_input_mwh = ATR_capacity_value / 0.75
    mdot_gas_in = energy_input_mwh * (0.4 * 1000) / (39.41 * 3600) 

    # Always use gas junction 9
    gas_junction = 9
    hydrogen_junction = 0  # VCS1_in in hydrogen_network()

    # Create a sink in the gas network to consume gas
    atr_in = ppipes.create_sink(net_gas, junction=gas_junction, mdot_kg_per_s=mdot_gas_in, name="ATR_junction9_consumption")

    # Create a source in the hydrogen network to produce hydrogen (initially 0, controlled dynamically)
    atr_out = ppipes.create_source(net_hyd, junction=hydrogen_junction, mdot_kg_per_s=0, name="ATR_junction9_out")

    # Add Gas-to-Gas conversion controller
    GasToGasConversion(
        multinet=multinet,
        element_index_from=atr_in,
        element_index_to=atr_out,
        efficiency=0.75,
        name_gas_net_from="gas",
        name_gas_net_to="hydrogen"
    )

    return atr_in, atr_out



def hydrogen_boiler(net_hyd, multinet, capacity_HB, H2_prop):
    # mdot_kg_per_s = capacity_HB / (HHV_h2 * 3600) if capacity_HB > 0 else 0
    mdot_kg_per_s = capacity_HB *(0.4 * 1000) / (39.41 * 3600)   if capacity_HB > 0 else 0

    hydrogen_boiler_sink = ppipes.create_sink(
        net_hyd,
        junction=1,
        mdot_kg_per_s=mdot_kg_per_s,
        name="Hydrogen Boiler",
        controllable=True
    )
    print(f"Hydrogen Boiler Sink Created: mdot_kg_per_s={mdot_kg_per_s}, capacity_HB={capacity_HB}")
    return hydrogen_boiler_sink



def hydrogen_blending(net_hyd, multinet, capacity_H2, H2_prop):

    # mdot_kg_per_s = capacity_H2 / (HHV_h2 * 3600) if capacity_H2 > 0 else 0
    mdot_kg_per_s = capacity_H2 *(0.4 * 1000) / (39.41 * 3600) if capacity_H2 > 0 else 0

    hydrogen_blending_sink = ppipes.create_sink(
        net_hyd,
        junction=1,
        mdot_kg_per_s=mdot_kg_per_s,
        name="Hydrogen Blending",
        controllable=True
    )
    print(f"Hydrogen Blending Sink Created: mdot_kg_per_s={mdot_kg_per_s}, capacity_H2={capacity_H2}")
    return hydrogen_blending_sink


    
def LoG_initial(time_steps):
    
    LoG = np.zeros(len(time_steps))
    LoG[0] = 0.5
    return LoG


def form_multinet(net_power, net_gas, net_hyd, H2_prop, systemData):
    # create multinet and add networks:
    multinet = create_empty_multinet('NoT_multinet')
    add_net_to_multinet(multinet, net_power, 'power')
    add_net_to_multinet(multinet, net_gas, 'gas')
    add_net_to_multinet(multinet, net_hyd, 'hydrogen')
    
    
    # Add coupling components to the network
    coupling_p2g(net_power, net_gas, multinet, H2_prop)
    coupling_chp(net_power, net_hyd, multinet, H2_prop, systemData)
    coupling_gfg(net_power, net_hyd, multinet, H2_prop, systemData)
    coupling_fc(net_power, net_hyd, multinet, H2_prop, systemData)
    

    

    return multinet
    
def plot(net_gas, net_power):
    # plot network
    ppipes.plotting.simple_plot(net_gas, plot_sinks=True, plot_sources=True)
    # global xy
    xy = ppipes.plotting.pressure_profile_to_junction_geodata(net_gas)
    matplot.plot(xy['y'])
    matplot.ylim(38.98,39.02)
    
    
    ppower.plotting.simple_plot(net_power)
    ppower.plotting.plotly.pf_res_plotly(net_power)
    ppower.plotting.plotly.vlevel_plotly(net_power)

def plot_LoG(time_steps,LoG):
    
    x = time_steps
    y = LoG*100
    
    matplot.xlabel("time step")
    matplot.ylabel("LoG [%]")
    matplot.ylim(0,100)
    matplot.title("Level-of-Gas-NoT")
    matplot.plot(x, y, "r-o")
    #plt.grid()
    # matplot.show()
    matplot.close()


def LoG_calc(i, LoG, volume):
    Storage_Cap = 0.8
    
    if i == 0:
        LoG[i] = LoG[0] + volume / Storage_Cap
    # else:
    #     LoG[i] = LoG[i-1] + volume  / Storage_Cap
       
    return LoG

def update_LoG(net_power, multinet, LoG, time_step):
    
    print('Electrolyser out: ',multinet.nets['hydrogen'].source['mdot_kg_per_s'][0])
    LoG = LoG_calc(time_step, LoG, multinet.nets['hydrogen'].source['mdot_kg_per_s'][0])
            

    print('Fuel cell in: ',multinet.nets['hydrogen'].sink['mdot_kg_per_s'][0])
    LoG = LoG_calc(time_step, LoG, multinet.nets['hydrogen'].sink['mdot_kg_per_s'][0]*(-1)) 

    return LoG

def print_results(multinet):
        
    difference = np.sum(multinet.nets['power'].res_gen['p_mw']) - np.sum(multinet.nets['power'].load['p_mw'])
    print('---------------Stats-------------------')
    print('Maximum generation capacity : ', sum(multinet.nets['power'].gen['max_p_mw']))
    print('Resultant generation        : ', sum(multinet.nets['power'].res_gen['p_mw']))
    print('Total and resultant load    : ', sum(multinet.nets['power'].res_load['p_mw']))
    print('External grid               : ', multinet.nets['power'].res_ext_grid['p_mw'][0])
    print('Losses                      : ', sum(multinet.nets['power'].res_line['pl_mw']))
    print('Supply - Demand             : ', difference)
    print('---------------------------------------')
    print('Gas demand                  : ', sum(multinet.nets['gas'].res_sink['mdot_kg_per_s']))
    print('Gas external                : ', sum(multinet.nets['gas'].res_ext_grid['mdot_kg_per_s']))
    print('---------------------------------------')




def OPGF(systemData, multinet, genData, net_power, net_gas, net_hyd, H2_prop, price_fg, 
         heat_pumps, hydrogen_boilers, base_sw, HPHB_sw, EZ_ATR_FC_CHP_fg,
         list_ele_demand, list_gas_demand, STI_scenario):
    
    global EF, e_demand, g_demand, hyd_demand
    
    EF = mdot_energy_conv(H2_prop)  # Calculate energy density
    HHV_h2 = mdot_energy_conv(H2_prop)  

    # Demand calculations (unchanged)
    if base_sw == 'Base':
        e_demand = sum(multinet.nets['power'].load['p_mw'][0:33]) 
        g_demand = sum(multinet.nets['gas'].sink['mdot_kg_per_s'][0:15])*(EF*1*3600)/(0.4*1000)        
        hyd_demand = hydrogen_boilers 
        HB_NGB_share = 0
        chp_heating_share = 0 #CHP meets this share % of heating demand
    

    if HPHB_sw=='Base_Interv' and H2_prop==1.0:
        # chp_heating_share = 0.4  #CHP meets this share % of heating demand 
        chp_heating_share = 0 # No Chp in g_demand, CHPs is only Industrial CHP


    chp_elec_eff = 0.4  # CHP electrical efficiency
    chp_heat_eff = 0.4  # CHP heat efficiency
    
    atr_eff = 0.75
    ez_eff = 0.60
    fc_eff = 0.60
    
    capacity_HB = hydrogen_boilers # Hydrogen Boiler Capacity 
    
    capacity_CHP = chp_heating_share * g_demand # CHP heating Capacity 
        
    D_g = energy_h2_gas(0.0, g_demand)  
    D_hyd = energy_h2_gas(1.0, hyd_demand)
    # D_e = energy_h2_gas(1, e_demand)
    # capacity_H2 = D_e['qg_h2']

    HB_NGB_share = D_hyd['mdot_h2']/D_g['mdot_gas']  #In pandapipes fluids blending should be by mdot 

    # capacity_H2 = D_g['qg_h2']
    # capacity_H2 = HB_NGB_share * e_demand # Hydrogen Blending Capacity for FC and H2_GTs (and CHPs if heat needed) 


    capacity_H2 = 130 + 20 # Capacities of gfg and chp 

        
    
    print('capacity_CHP=', capacity_CHP)
    print('capacity_HB=', capacity_HB)
    print('capacity_H2=', capacity_H2)
    print('g_demand=', g_demand)
    print('e_demand=', e_demand)
    print('hyd_demand=', hyd_demand)
    print('HB_NGB_share=', HB_NGB_share)
    print('chp_heating_share=', chp_heating_share)



    
    list_gas_demand.append(round(g_demand, 2))  
    list_ele_demand.append(round(e_demand, 2))

    # Price settings (unchanged)
    if price_fg==0:
        ele_opex_price = 33.69 # in £/MWh
        gas_opex_price = 9.73
        hyd_opex_price = 9
    elif price_fg==1:
        ele_opex_price = 125 # in £/MWh
        gas_opex_price = 37
        hyd_opex_price = 100
    elif price_fg==2:
        ele_opex_price = 125 # in £/MWh
        gas_opex_price = 37
        hyd_opex_price = 120
    elif price_fg==3:
        ele_opex_price = 125 # in £/MWh
        gas_opex_price = 37
        hyd_opex_price = 0
    elif price_fg==4:
        ele_opex_price = 125 # in £/MWh
        gas_opex_price = 37
        hyd_opex_price = 75
        
    elif price_fg == 5:
        ele_opex_price = 125 # in £/MWh
        gas_opex_price = 37
        
        ## hyd_cost_values = {'2025': 80, '2030': 75, '2035': 70, '2040': 65, '2045': 60, '2050': 55} ## LCOH of Blue H2 
        hyd_cost_values = {'2025': 100, '2030': 90, '2035': 75, '2040': 70, '2045': 65, '2050': 60} ## LCOH of Greene H2

        year = systemData['Year']; scenario = systemData['scenario']
        hyd_opex_price = hyd_cost_values[year]
        
    elif price_fg == 6:
        ele_opex_price = systemData['ele_opex_price_t']
        gas_opex_price = systemData['gas_opex_price_t']
        hyd_opex_price = 150
        
    genCount = np.shape(genData)[0]
    prob = lp.LpProblem("OPGF", lp.LpMinimize)
    
    # Variables
    year = systemData['Year']; scenario = systemData['scenario']
    CO2_penalty = systemData['Carbon Price'].loc[systemData['Carbon Price']['Year'] == int(year), scenario].iloc[0]
      
    q_e   = lp.LpVariable.dicts("elect", list(np.arange(genCount)), cat='Continuous')
    q_g   = lp.LpVariable("gas", cat='Continuous')
    q_p2g = lp.LpVariable.dicts("P2G", list(np.arange(4)), cat='Continuous')
    q_g2p = lp.LpVariable.dicts("G2P", list(np.arange(5)), cat='Continuous')
    q_h   = lp.LpVariable("hydrogen", cat='Continuous')
    q_h_electrolyser = lp.LpVariable("hydrogen_electrolyser", cat='Continuous')
    q_h_atr = lp.LpVariable("hydrogen_atr", cat='Continuous')
    q_h_surplus = lp.LpVariable("hydrogen_surplus", cat='Continuous')
    q_fc = lp.LpVariable("fuel_cell_electricity", cat='Continuous')
    
    # Costs
    C_EZ = ele_opex_price / ez_eff + hyd_opex_price
    C_ATR = gas_opex_price / atr_eff + hyd_opex_price + CO2_penalty * 0.05
    f_EZ  = 1 / C_EZ / (1 / C_EZ + 1 / C_ATR)
    f_ATR = 1 - f_EZ

    
    
    # Objective function 
    prob += (
        lp.lpSum(ele_opex_price * q_e[gen] for gen in range(genCount))
        + lp.lpSum(ele_opex_price * q_p2g[p2g] for p2g in range(4))
        + lp.lpSum(gas_opex_price * q_g2p[g2p] for g2p in range(5))
        + lp.lpSum(gas_opex_price * q_g)
        + lp.lpSum(hyd_opex_price * (q_h_electrolyser + q_h_atr))
        + lp.lpSum(ele_opex_price * q_h_electrolyser * (1/ez_eff))
        + lp.lpSum(hyd_opex_price * q_h_surplus)
        + lp.lpSum(CO2_penalty * (0.1) * q_g2p[g2p] for g2p in range(5))
        + lp.lpSum(CO2_penalty * (0.1) * q_g)
        - lp.lpSum(ele_opex_price * q_fc)
    ), "objective"
    
    # Generator constraints
    for i in range(genCount):
        prob += q_e[i] <= genData['8'][i]
        prob += q_e[i] >= 0

    # Gas balance
    gas_energy_for_atr = q_h_atr * (1 / atr_eff)
    q_gh_chp_gt = (sum(multinet.nets['gas'].sink['mdot_kg_per_s'][0:15])*(EF*1*3600)/(0.4*1000)
                   + lp.lpSum(q_g2p[g2p] for g2p in range(5))
                   + gas_energy_for_atr)
    
    # qg_h2_gas = energy_h2_gas(H2_prop, q_gh_chp_gt)
    qg_h2_gas = energy_h2_gas(HB_NGB_share, q_gh_chp_gt)

    prob += q_g == qg_h2_gas['qg_gas']
    prob += q_h == qg_h2_gas['qg_h2']
    
    prob += q_h_electrolyser == f_EZ * (q_h_electrolyser + q_h_atr)
    prob += q_h_atr == f_ATR * (q_h_electrolyser + q_h_atr)
    
    total_H2_needed = capacity_HB + capacity_H2 + q_h_surplus
    prob += q_h_electrolyser == f_EZ * total_H2_needed, "EZ_H2_split"
    prob += q_h_atr       == f_ATR * total_H2_needed, "ATR_H2_split"
    prob += q_h_surplus ==  (q_h_electrolyser + q_h_atr - capacity_HB - capacity_H2), "H2_Surplus_Limit"
    prob += q_fc <= q_h_surplus * fc_eff , "FC_Capacity_Limit"
    prob += q_h_surplus >= 0 
    prob += q_fc >= 0 
    

    # P2G and G2P limits
    p2g_limits = [multinet.nets['power'].load['p_mw'][33],
                  multinet.nets['power'].load['p_mw'][34],
                  multinet.nets['power'].load['p_mw'][35],
                  multinet.nets['power'].load['p_mw'][36]]
    for i in range(4):
        prob += q_p2g[i] <= p2g_limits[i]
        prob += q_p2g[i] >= 0

 
    g2p_limits = [multinet.nets['hydrogen'].sink['mdot_kg_per_s'][15]*(EF*3600)/(0.4*1000),
                  multinet.nets['hydrogen'].sink['mdot_kg_per_s'][16]*(EF*3600)/(0.4*1000),
                  multinet.nets['hydrogen'].sink['mdot_kg_per_s'][17]*(EF*3600)/(0.4*1000),
                  multinet.nets['hydrogen'].sink['mdot_kg_per_s'][18]*(EF*3600)/(0.4*1000),
                  multinet.nets['hydrogen'].sink['mdot_kg_per_s'][19]*(EF*3600)/(0.4*1000)]

    for i in range(5):
        prob += q_g2p[i] <= g2p_limits[i]

        # prob += q_g2p[i] >= capacity_CHP
        prob += q_g2p[i] >= 0


    # Compute effective hydrogen marginal cost from EZ and ATR
    hydrogen_marginal_cost = f_EZ * C_EZ + f_ATR * C_ATR
    systemData['hydrogen_marginal_cost'] = hydrogen_marginal_cost
    
    
    
    # Update hydrogen-dependent unit costs of G2P units (CHP, GFG, Fuel Cell)
    for i, row in net_power.poly_cost.iterrows():
        if row['et'] == 'sgen':
            name = net_power.sgen.at[row['element'], 'name']
            print('g2p_name', name)
            
            if any(key in name for key in ['CHP', 'GFG', 'FC']):
                # net_power.poly_cost.at[i, 'cp1_eur_per_mw'] = hydrogen_marginal_cost
                net_power.poly_cost.at[i, 'cp1_eur_per_mw'] = 0


    # Use hyd marg cost for FC electricity cost
    C_FC  = hydrogen_marginal_cost / fc_eff 
    g2p_share = hydrogen_marginal_cost / 0.7 
    
    # Inverse-cost weighting
    if (C_FC == 0) and (g2p_share == 0):
        fc_share, chp_share = 0.5, 0.5
    elif C_FC == 0:
        fc_share, chp_share = 1.0, 0.0
    elif g2p_share == 0:
        fc_share, chp_share = 0.0, 1.0
    else:
        inv_sum = (1.0 / C_FC) + (1.0 / g2p_share)
        fc_share = (1.0 / C_FC) / inv_sum
        g2p_share = (1.0 / g2p_share) / inv_sum
    

    # Electricity balance
    prob += (lp.lpSum(q_e[gen] for gen in range(genCount)) 
           == sum(multinet.nets['power'].load['p_mw'][0:33])
           + lp.lpSum(q_p2g[p2g] for p2g in range(4)) ), "Electricity_Balance"
    
    prob += lp.lpSum(q_p2g[p2g] for p2g in range(4)) <= sum(p2g_limits), "C4"
    prob += lp.lpSum(q_g2p[g2p] for g2p in range(5)) <= sum(g2p_limits), "C5"
    
    # Solve
    prob.solve(lp.PULP_CBC_CMD(msg=0))
    
         
    # Extract results
    global variable, Total_cost, optimal_q_e, optimal_q_g, optimal_q_p2g, \
           optimal_q_g2p, optimal_q_h, q_gh_chp_gt_value, gas_capacity_value, \
           h_capacity_value, optimal_q_h_electrolyser, optimal_q_h_atr, atr_in, atr_out, \
           optimal_q_h_surplus, optimal_q_fc
           
          
           
    variable = prob.variables()
        
    q_gh_chp_gt_value = (sum(multinet.nets['gas'].sink['mdot_kg_per_s'][0:15])*(EF*1*3600)/(0.4*1000)
                         + lp.lpSum(q_g2p[g2p].value() for g2p in range(5))
                         + (q_h_atr.varValue * (1 / atr_eff) if q_h_atr.varValue is not None else 0))
    
    gas_capacity_value = (energy_h2_gas(H2_prop, q_gh_chp_gt_value)['qg_gas'])
    h_capacity_value = (energy_h2_gas(H2_prop, q_gh_chp_gt_value)['qg_h2'])
    
    optimal_q_e = sum(q_e[gen].varValue for gen in range(genCount))
    optimal_q_g = q_g.varValue
    optimal_q_p2g = sum(q_p2g[p2g].varValue for p2g in range(4))
    optimal_q_g2p = sum(q_g2p[g2p].value() for g2p in range(5))
    optimal_q_h = q_h.varValue
    optimal_q_h_electrolyser = q_h_electrolyser.varValue
    optimal_q_h_atr = q_h_atr.varValue
    optimal_q_h_surplus = q_h_surplus.varValue
    
    print('q_gh_chp_gt=', q_gh_chp_gt_value)
    print('q_g=', optimal_q_g)
    print('q_h=', optimal_q_h)
    print('optimal_q_e=', optimal_q_e)
    print('optimal_q_g=', optimal_q_g)
    print('optimal_q_h=', optimal_q_h)
    print('optimal_q_h_electrolyser=', optimal_q_h_electrolyser)
    print('optimal_q_h_atr=', optimal_q_h_atr)
    print('optimal_q_h_surplus=', optimal_q_h_surplus)
    print('optimal_q_p2g=', optimal_q_p2g)

    

    # Capacities based on chosen mode    
    if EZ_ATR_FC_CHP_fg =='Optimal':
        EZ_capacity_value = optimal_q_h_electrolyser   
        ATR_capacity_value = optimal_q_h_atr 
        
        if HPHB_sw == "Base_Interv" and H2_prop == 1.0:
            FC_capacity_value  = fc_share * capacity_H2
            g2p_capacity_value = g2p_share * capacity_H2
            g2p_capacity = g2p_capacity_value

        else:
            FC_capacity_value = abs(optimal_q_h_surplus) 
            g2p_capacity_value = optimal_q_g2p


    elif EZ_ATR_FC_CHP_fg =='H2CostWeight':
        total_hydrogen = capacity_HB + capacity_H2 + q_h_surplus.varValue
        sum_inv_costs = 1/C_EZ + 1/C_ATR
        q_h_electrolyser_share = (1/C_EZ) / sum_inv_costs
        q_h_atr_share        = (1/C_ATR) / sum_inv_costs
        q_h_electrolyser_value = total_hydrogen * q_h_electrolyser_share
        q_h_atr_value          = total_hydrogen * q_h_atr_share
        
        EZ_capacity_value  = q_h_electrolyser_value
        ATR_capacity_value = q_h_atr_value
        FC_capacity_value = abs(optimal_q_h_surplus) 
        g2p_capacity_value = optimal_q_g2p


    elif EZ_ATR_FC_CHP_fg == 0.5:
        EZ_capacity_value = (capacity_HB + capacity_H2 + FC_capacity_value)/2
        ATR_capacity_value = (capacity_HB + capacity_H2 + FC_capacity_value)/2
        FC_capacity_value = abs(optimal_q_h_surplus) 
        g2p_capacity_value = optimal_q_g2p

    elif EZ_ATR_FC_CHP_fg == 0.8:
        EZ_capacity_value = (capacity_HB + capacity_H2 + FC_capacity_value)*0.2
        ATR_capacity_value = (capacity_HB + capacity_H2 + FC_capacity_value)*0.8
        FC_capacity_value = abs(optimal_q_h_surplus) 
        g2p_capacity_value = optimal_q_g2p

    elif EZ_ATR_FC_CHP_fg == 1.0:
        EZ_capacity_value = capacity_HB + capacity_H2 + FC_capacity_value
        ATR_capacity_value = 0
        FC_capacity_value = abs(optimal_q_h_surplus) 
        g2p_capacity_value = optimal_q_g2p
        
        

        
       
    print("EZ/ATR split: EZ_share=", f_EZ, " ATR_share=", f_ATR)
    print('EZ_capacity_value=', EZ_capacity_value)
    print('ATR_capacity_value=', ATR_capacity_value)
    print("FC/CHP split: fc_share=", fc_share, " chp_share=", g2p_share)
    print('FC_capacity_value=', FC_capacity_value)
    print('g2p_capacity_value=', g2p_capacity_value)
    print('hydrogen_marginal_cost', hydrogen_marginal_cost)
    
    # st=stop
        

    # Update hydrogen network components
    electrolyser(net_power, net_hyd, multinet, EZ_capacity_value, H2_prop)
    atr_in, atr_out = autothermal_reformer(net_gas, net_hyd, multinet, ATR_capacity_value, H2_prop)
    # fuel_cell(net_power, net_hyd, multinet, FC_capacity_value, H2_prop)

    hydrogen_boiler(net_hyd, multinet, capacity_HB, H2_prop)

    hydrogen_blending(net_hyd, multinet, capacity_H2, H2_prop)
    
    
    Total_cost = lp.value(prob.objective)
    

    print('capacity_CHP=', capacity_CHP)
    print('g2p_capacity_value=', g2p_capacity_value)
    print('capacity_HB=', capacity_HB)
    print('h_capacity_value=', h_capacity_value)
    
    systemData['capacity_HB'] = capacity_HB
    
    print('hydrogen_boilers=', hydrogen_boilers)
    print('H2_prop', H2_prop)
    print('HB_NGB_share', HB_NGB_share)
    
    
    # Total cost
    Total_cost = lp.value(prob.objective)
    
    
    coupling_chp_heat(net_power, net_gas, multinet, capacity_CHP, H2_prop)

    return



# def check_load(multinet, systemData):
#     print('check3_Multinet_load=', sum(multinet.nets['power'].load['p_mw']))
#     # print('just_check_multinet=', multinet['nets'])
#     print('check3_Multinet_res_load=', sum(multinet.nets['power'].res_load['p_mw']) )
#     print('check3_Sys_load=', sum(systemData['Players']['max_p_mw'][0:25]))


def declaration():
    global e_generation, g_supply, hydrogen_conv, e_load, diff_el
    e_generation = []
    g_supply = []
    hydrogen_conv = []
    e_load = []
    diff_el = []
    
    
def store_results(multinet):
    global EF
    # Electricity generation
    e_gen = sum(multinet.nets['power'].res_gen['p_mw'])
    e_generation.append(e_gen)
    
    # Gas supply
    g_supply.append(sum(multinet.nets['gas'].res_sink['mdot_kg_per_s']))
    
    # Hydrogen supply (electrolyser + ATR)
    hydrogen_sources = multinet.nets['hydrogen'].source[['name']].merge(
        multinet.nets['hydrogen'].res_source, left_index=True, right_index=True, how='left'
    )
    electrolyser_mdot = hydrogen_sources.loc[hydrogen_sources['name'] == 'Electrolyser_out', 'mdot_kg_per_s'].iloc[0] if 'Electrolyser_out' in hydrogen_sources['name'].values else 0
    atr_mdot = hydrogen_sources.loc[hydrogen_sources['name'] == 'ATR_out', 'mdot_kg_per_s'].iloc[0] if 'ATR_out' in hydrogen_sources['name'].values else 0
    total_hydrogen_mdot = electrolyser_mdot + atr_mdot
    hydrogen_conv.append(total_hydrogen_mdot)
    
    # Electricity load
    e_load_mw = sum(multinet.nets['power'].res_load['p_mw'])
    e_load.append(e_load_mw)
    
    # Difference between generation and load
    diff_el.append(e_gen - e_load_mw)
    
    results = {
        'electricity': e_gen,
        'gas': sum(multinet.nets['gas'].res_sink['mdot_kg_per_s']),
        'hydrogen': total_hydrogen_mdot,
        'electrolyser_hydrogen': electrolyser_mdot,
        'atr_hydrogen': atr_mdot,
        'load': e_load_mw,
        'Gens-Load': e_gen - e_load_mw,
        'surplus_hydrogen': optimal_q_h_surplus  # Add surplus hydrogen
    }
    return results


def run_OPGF(t, genData, systemData, H2_prop, ccs_fg, temp_system, price_fg, num_simulations,
             heat_pumps, hydrogen_boilers, others, base_sw, HPHB_sw, EZ_ATR_FC_CHP_fg,
             list_ele_demand, list_gas_demand, STI_scenario):
    
    
    # ### To avoide opgf didn't converge ###
    # # if HPHB_sw=='Base_MC_Interv' and H2_prop==1.0:
    # if H2_prop == 1.0:
    #     genData['8']=genData['8']*2
    
    # Increase the capacity solar generators
    for s_idx in [6, 7, 22]:
        genData.at[s_idx, '8'] = genData.at[s_idx, '8'] * 3
    
    # Cap wind generators to 0.3
    for w_idx in [2, 8, 20, 24]:
        genData.at[w_idx, '8'] = genData.at[w_idx, '8'] * 1


            
    global result

    time_steps = [t]
    data_source(systemData, num_simulations, H2_prop, heat_pumps, hydrogen_boilers, others)
    LoG = LoG_initial(time_steps)
    declaration()
    
    systemData['ccs_fg'] = ccs_fg
    
    price = pd.read_excel("Data/prices.xlsx")

    
    for i in time_steps:
        print()
        print('t=', i)
        print()

        net_gas = gas_network(i, H2_prop, temp_system)
        net_power = power_network(i, genData, systemData, H2_prop)
        # net_hyd = hydrogen_network(capacity_HB=hydrogen_boilers)
        net_hyd = hydrogen_network(i, H2_prop, temp_system)


        global multinet
        multinet = form_multinet(net_power, net_gas, net_hyd, H2_prop, systemData)
        
        systemData['ele_opex_price_t'] = price['electricity_price'][t]
        systemData['gas_opex_price_t'] = price['gas_price'][t]
        
        # print('g2p cost before opgf', net_power.poly_cost[['et', 'element', 'cp1_eur_per_mw', 'cp0_eur']])
        # print('check_aftr_OPGF')
        # print('multinet sinks=', multinet.nets['gas'].sink)
        # print('multinet load=', multinet.nets['power'].load)

                      
        OPGF(systemData, multinet, genData, net_power, net_gas, net_hyd, H2_prop, price_fg, 
                               heat_pumps, hydrogen_boilers, base_sw, HPHB_sw, EZ_ATR_FC_CHP_fg, 
                               list_ele_demand, list_gas_demand, STI_scenario)
        


        # Run simulation for both power and hydrogen networks
        run_control(multinet, ctrl_variables={
            'nets': {
                'power': {'run': ppower.rundcopp},
                'hydrogen': {'run': ppipes.pipeflow}
            }
        })
        

    
                        
        print('sgens=', multinet['nets']['power']['res_sgen']['p_mw'])
        print('q_h_sink', multinet['nets']['power']['res_sgen']['p_mw'][5])
        print('CHP_sgens', sum(multinet['nets']['power']['res_sgen']['p_mw'][6:]))
        print('gas demand=', g_demand)
        # print('g2p cost after opgf', net_power.poly_cost[['et', 'element', 'cp1_eur_per_mw', 'cp0_eur']])

        LoG = update_LoG(net_power, multinet, LoG, i)
        
        # Store and print results
        results = store_results(multinet)
        print("Electricity Generation (MWh):", results['electricity'])
        print("Gas Supply (kg/s):", results['gas'])
        print("Total Hydrogen Production (kg/s):", results['hydrogen'])
        print("Electrolyser Hydrogen (kg/s):", results['electrolyser_hydrogen'])
        print("ATR Hydrogen (kg/s):", results['atr_hydrogen'])
        print("Electricity Load (MWh):", results['load'])
        print("Gens-Load (MWh):", results['Gens-Load'])
        
        result = pd.DataFrame({
            'electricity': [results['electricity']],
            'gas': [results['gas']],
            'hydrogen': [results['hydrogen']],
            'electrolyser_hydrogen': [results['electrolyser_hydrogen']],
            'atr_hydrogen': [results['atr_hydrogen']],
            'load': [results['load']],
            'Gens-Load': [results['Gens-Load']]
        })
    
    plot_LoG(time_steps, LoG)
    result = pd.concat([result, pd.DataFrame(LoG, columns=['LoG']).transpose()], axis=0)

    print('g_demand=', g_demand)
    print('chp_sink_MW=', multinet.nets['gas'].sink['mdot_kg_per_s'][9]*(EF*1*3600)/(0.4*1000))
    print('chp_sink_kg/s=', multinet.nets['gas'].sink['mdot_kg_per_s'][9])
    print('chp_sgen_MW=', multinet['nets']['power']['res_sgen']['p_mw'][:5])
    
    
    return multinet




def data_import(year, scenario):
    path = r'Refined FES scenario inputs/' 
    
    systemData = {
        'Carbon Price'      : pd.read_excel(path + 'Carbon price/carbon_price.xlsx'), # carbon price ,
        'Installed capacity': pd.read_excel(path + 'InstalledCapacity/installed_capacity.xlsx' , sheet_name=scenario, index_col = 0) ,
        'Power Demand'      : pd.read_excel(path + 'PowerDemand_Heating_Input/powerDemand_'+ scenario + '.xlsx', sheet_name = year, index_col = 0),
        'Gas Consumption'   : pd.read_excel(path + 'gasConsumption_heating_input/gasCons_'+ scenario + '.xlsx', sheet_name = year, index_col = 0),
        'Players'           : pd.read_csv('Data/market_players2.csv')} #import the parameters
    
    return systemData



# def initial_run_OPGF(t, systemData, H2_prop):
#     # Running the GT model
 
#     ## genData = pd.read_csv('Data/genData.csv')
#     genData = pd.read_csv('Data/genData.csv')
      # genData['8'] = systemData['Players']['max_p_mw'][:25]
    
#     # hour_of_day = 24 # Input how many hours the model shall run
#     hour_of_day = t # Input how many hours the model shall run

#     multinet = run_OPGF(hour_of_day, genData,  systemData, H2_prop, temp_system, price_fg) # Running the OPGF
    
#     return multinet


# Function to dynamically calculate and return results based on multinet
def calculate_results(multinet):
    difference = np.sum(multinet.nets['power'].res_gen['p_mw']) - np.sum(multinet.nets['power'].load['p_mw'])
    
    # Hydrogen supply (electrolyser + ATR)
    hydrogen_sources = multinet.nets['hydrogen'].source[['name']].merge(
        multinet.nets['hydrogen'].res_source, left_index=True, right_index=True, how='left'
    )
    electrolyser_mdot = hydrogen_sources.loc[hydrogen_sources['name'] == 'Electrolyser_out', 'mdot_kg_per_s'].iloc[0] if 'Electrolyser_out' in hydrogen_sources['name'].values else 0
    atr_mdot = hydrogen_sources.loc[hydrogen_sources['name'] == 'ATR_out', 'mdot_kg_per_s'].iloc[0] if 'ATR_out' in hydrogen_sources['name'].values else 0
    total_hydrogen_mdot = electrolyser_mdot + atr_mdot

    results = {
        "Electrolyser out": electrolyser_mdot,
        "ATR out": atr_mdot,
        "Total Hydrogen Production": total_hydrogen_mdot,
        "Fuel cell in": multinet.nets['hydrogen'].sink['mdot_kg_per_s'][0] if not multinet.nets['hydrogen'].sink.empty else 0,
        "Maximum generation capacity": sum(multinet.nets['power'].gen['max_p_mw']),
        "Resultant generation": sum(multinet.nets['power'].res_gen['p_mw']),
        "Total and resultant load": sum(multinet.nets['power'].res_load['p_mw']),
        "External grid": multinet.nets['power'].res_ext_grid['p_mw'][0],
        "Losses": sum(multinet.nets['power'].res_line['pl_mw']),
        "Supply - Demand": difference,
        "Gas demand": sum(multinet.nets['gas'].res_sink['mdot_kg_per_s']),
        "Gas external": sum(multinet.nets['gas'].res_ext_grid['mdot_kg_per_s'])
    }
    
    return results




# Convert the results dictionary to a tabulated format for the Excel sheet
def format_results_to_df(results, H2_prop, temp_system, year, scenario, t):
    conditions = {
        "H2_prop": H2_prop,
        "temp_system": temp_system,
        "year": year,
        "scenario": scenario,
        "hour": t
    }
    
    # Convert conditions to a DataFrame
    conditions_df = pd.DataFrame([conditions])
    
    # Convert results to a DataFrame (transpose to ensure each result is in a separate row)
    results_df = pd.DataFrame.from_dict(results, orient='index', columns=['Value']).reset_index()
    results_df.columns = ['Metric', 'Value']
    
    # Combine conditions and results
    combined_df = pd.concat([conditions_df, results_df], ignore_index=True)
    
    return combined_df




if __name__ == "__main__":
    
    temp_system = 288.15  # Temperature in Kelvin
    price_fg = 1

    years = ['2022', '2025', '2030', '2035', '2040', '2045', '2050']
    scenarios = ['CT', 'FS', 'LW', 'ST']
    hour_of_day = [1, 2, 3, 24]  # hour_of_day, t = 1,2,3,..,24

    year = years[0]
    scenario = scenarios[1]
    
    t = hour_of_day[0]  # hour_of_day, t = 1
    # t = hour_of_day[2]  # hour_of_day, t = 1,2,3

    # t = hour_of_day[3]  # hour_of_day, t = 1,2,3,..,24

    # H2_proportions = [0.3]; fg_h = 'H_0.3'
    
    # H2_proportions = [0, 1]; fg_h = 'H_01'
    
    H2_proportions = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]; fg_h = 'H_0_1'

    # H2_proportions = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]; fg_h = 'H_0_0.5'

    
    # Define the output directory and subdirectories
    output_dir = 'Output'+'/'+f'{year}_{scenario}_hr{t}_{fg_h}'
    # subdirs = ['Junctions', 'Pipes', 'Sinks']
    subdirs = ['Figures']

    
    # Create the main output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Create the subdirectories if they don't exist
    for subdir in subdirs:
        subdir_path = os.path.join(output_dir, subdir)
        if not os.path.exists(subdir_path):
            os.makedirs(subdir_path)
        
        
    output_file = f'{output_dir}/Simulation_{year}_{scenario}_hr{t}_{fg_h}.xlsx'
    junction_output_file = f'{output_dir}/res_junction_{year}_{scenario}_hr{t}_{fg_h}.xlsx'
    pipe_output_file = f'{output_dir}/res_pipe_{year}_{scenario}_hr{t}_{fg_h}.xlsx'
    sink_output_file = f'{output_dir}/res_sink_{year}_{scenario}_hr{t}_{fg_h}.xlsx'

   # Initialize the list to collect resultant data
    resultant_list = []

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer, \
         pd.ExcelWriter(junction_output_file, engine='openpyxl') as junction_writer, \
         pd.ExcelWriter(pipe_output_file, engine='openpyxl') as pipe_writer, \
         pd.ExcelWriter(sink_output_file, engine='openpyxl') as sink_writer:

        
        initial_data = {'Message': ['This sheet is initially visible and will be replaced.']}
        initial_df = pd.DataFrame(initial_data)
        initial_df.to_excel(writer, sheet_name='Init', index=False)
        initial_df.to_excel(junction_writer, sheet_name='Init', index=False)
        initial_df.to_excel(pipe_writer, sheet_name='Init', index=False)
        initial_df.to_excel(sink_writer, sheet_name='Init', index=False)


        for H2_prop in H2_proportions:
            # Simulate data import, initial run, and result calculation
            EF=mdot_energy_conv(H2_prop)
            system_data = data_import(year, scenario)
            multinet = initial_run_OPGF(t, system_data, H2_prop)
            results = calculate_results(multinet)
            
            
            # Format results to DataFrame
            results_df = format_results_to_df(results, H2_prop, temp_system, year, scenario, t)

            # Save results to Excel sheet
            sheet_name = f'H2_prop_{int(H2_prop * 100)}%'
            results_df.to_excel(writer, sheet_name=sheet_name, index=False)

            # Add results for node pressure and pipe flows
            res_junction_df = multinet.nets['gas'].res_junction
            res_pipe_df = multinet.nets['gas'].res_pipe
            res_sink_df = multinet.nets['gas'].res_sink
            # Adding the 'hhv'  ##kWh/kg
            res_sink_df['HHV_mix'] =EF
            res_sink_df['sink_energy']=EF*res_sink_df['mdot_kg_per_s']*3600/1000
            
            # Save the additional results to separate Excel files
            res_junction_df.to_excel(junction_writer, sheet_name=sheet_name, index=False)
            res_pipe_df.to_excel(pipe_writer, sheet_name=sheet_name, index=False)
            res_sink_df.to_excel(sink_writer, sheet_name=sheet_name, index=False)
            
            # Find the minimum p_bar value in res_junction_df
            pressure_profile = res_junction_df['p_bar']
            min_p_bar = res_junction_df['p_bar'].min()
            flow_rate_profile = res_pipe_df['vdot_norm_m3_per_s']
            max_fr_v= res_pipe_df['vdot_norm_m3_per_s'].max()
            max_mdot= res_sink_df['mdot_kg_per_s'][:15].max()
            HHV_mix= res_sink_df['HHV_mix'][:15]
            max_sink_energy= res_sink_df['sink_energy'][:15].max()
            total_sink_mdot= sum(multinet.nets['gas'].res_sink['mdot_kg_per_s'])
            total_source_mdot= sum(multinet.nets['gas'].res_source['mdot_kg_per_s'])
            external_mdot=-sum(multinet.nets['gas'].res_ext_grid['mdot_kg_per_s'])
            total_sink_q = total_sink_mdot * EF * 3600/1000
            total_source_q = total_source_mdot * EF * 3600/1000
            external_q = external_mdot * EF * 3600/1000
            qg_h2_gas=energy_h2_gas(H2_prop, optimal_q_g)
            mixture_mdot=optimal_q_g/HHV_mix.mean()
            mixture_properties = calculate_mixture_properties('hgas', 'hydrogen', H2_prop, temp_system)
            dens_h2=ppipes.create_empty_network(fluid="hydrogen").fluid.get_density(temp_system)
            dens_gas=ppipes.create_empty_network(fluid="hgas").fluid.get_density(temp_system)


            # Add the result along with min_p_bar to the resultant_generation_list
            resultant_list.append({
                'H2_prop': H2_prop,
                'temp_system': temp_system,
                'year': year,
                'scenario': scenario,
                'hour': t, 
                'Resultant generation': results_df[results_df['Metric'] == 'Resultant generation']['Value'].values[0],
                'Total and resultant load': results_df[results_df['Metric'] == 'Total and resultant load']['Value'].values[0],
                'Supply - Demand': results_df[results_df['Metric'] == 'Supply - Demand']['Value'].values[0],
                'External grid':  results_df[results_df['Metric'] == 'External grid']['Value'].values[0],
                'Gas demand':  results_df[results_df['Metric'] == 'Gas demand']['Value'].values[0],
                'Gas external':  results_df[results_df['Metric'] == 'Gas external']['Value'].values[0],
                'Electrolyser out':  results_df[results_df['Metric'] == 'Electrolyser out']['Value'].values[0],
                'Fuel cell in':  results_df[results_df['Metric'] == 'Fuel cell in']['Value'].values[0],
                'min_p_bar': min_p_bar,
                'max_pipe_fr_v': max_fr_v,
                'max_flrt (m3/s)': max_mdot/mixture_properties['density'],
                'HHV_mix (kWh/m3)': HHV_mix*mixture_properties['density'],
                'max_sink_energy (MWh)': max_sink_energy,
                'Total_cost': Total_cost,
                'Total_energy_sink (MWh)': total_sink_q,
                'Total_energy_source (MWh)': total_source_q,
                'Total_energy_external (MWh)': external_q,      
                'Total_flow_sink (m3/s)': total_sink_mdot/mixture_properties['density'],
                'Total_flow_source (m3/s)': total_source_mdot/mixture_properties['density'],
                'Total_flow_external (m3/s)': external_mdot/mixture_properties['density'],
                'Optimal_q_e': optimal_q_e,
                'Optimal_q_g': optimal_q_g,
                'Optimal_q_p2g': optimal_q_p2g,
                'Optimal_q_g2p': optimal_q_g2p,
                'Optimal_q_h': optimal_q_h,
                'qg_h2': qg_h2_gas['qg_h2'],
                'qg_gas': qg_h2_gas['qg_gas'],
                'flrt_h2': qg_h2_gas['mdot_h2']/dens_h2,
                'flrt_gas': qg_h2_gas['mdot_gas']/dens_gas,
                'flrt_mixture':mixture_mdot/mixture_properties['density'],
                'pressure_profile':pressure_profile,
                'flow_rate_profile':flow_rate_profile,
                
            })

        del writer.book['Init']
        del junction_writer.book['Init']
        del pipe_writer.book['Init']
        del sink_writer.book['Init']
    
    print(f"Results saved to {output_file}")
    print(f"Node pressures saved to {junction_output_file}")
    print(f"Pipe flows saved to {pipe_output_file}")
    print(f"Pipe flows saved to {sink_output_file}")

    
    # Convert the list to a DataFrame
    df_plot = pd.DataFrame(resultant_list)
    # df_plot.set_index('H2_prop', inplace=True)

    df_plot.to_excel(f'{output_dir}/Rsults_{year}_{scenario}_hr{t}_{fg_h}.xlsx')

   
    # Plotting Results vs. H2 proportions
    generate_plots(df_plot, output_dir, year, scenario, t, fg_h)
    
    