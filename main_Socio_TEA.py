"""
Created on Wed Sep 18 16:39:13 2024

@author: Mhdella
"""

global case_fg, solver_type, eq_fg, eps_imax, h2_fg, idiv_plt_sw, ccs_fg, \
        H2_prop, price_fg, year_fg, obj_fg, Q_max_fg, h2_plt, ws_limit, \
        num_simulations, HPHB_sw, heat_pumps, hydrogen_boilers, others, \
        intervention_levels, base_sw, hour_of_day, EZ_ATR_FC_CHP_fg, \
        STI_scenario

base_sw = 'Base'
## base_sw = 'MC'


# HPHB_sw='Base_MC_Interv'
# HPHB_sw='HP_Interv'
# HPHB_sw='HB_Interv'
# HPHB_sw='HP_HB_Interv'


# HPHB_mix_fg='HB_HP_50_50'
HPHB_mix_fg='HB_HP_70_30'


EZ_ATR_FC_CHP_fg = 'Optimal'
# EZ_ATR_FC_CHP_fg ='H2CostWeight'
# EZ_ATR_FC_CHP_fg = 0.5
# EZ_ATR_FC_CHP_fg = 0.8
# EZ_ATR_FC_CHP_fg = 1.0


h2_fg = 0
# h2_fg = 1
# h2_fg = 2 
# h2_fg = 3
# h2_fg = 4


# h2_plt = '0.0'
# h2_plt = '0.1'
# h2_plt = '0.2'
# h2_plt = '0.5'
# h2_plt = '0.7'
# h2_plt= '0.9'
# h2_plt= '1.0'


# ccs_fg=0
ccs_fg=1

        
ws_limit=0
# ws_limit=1
# ws_limit=2


ext_sw=0
# ext_sw=1
      
        
idiv_plt_sw = 0
# idiv_plt_sw = 1


# case_fg = 'no_update'

case_fg = '1_iter'


# Q_max_fg=0
# Q_max_fg=1
Q_max_fg=2


eps_imax = 1
# eps_imax = 0.0

# solver_type ='pathimpl'
solver_type ='ipopt'

# eqcs_model_q = 1
eqcs_model_q = 0

eq_fg=1
# eq_fg=0

# price_fg = 0
# price_fg = 1
# price_fg = 2
price_fg = 3
# price_fg = 4
# price_fg = 5
# price_fg = 6 #pirce profile from exil file (avg=125, 37)


# year_fg = 1
year_fg = 0


obj_fg = 0
# obj_fg = 1

# num_simulations =1000
num_simulations =0




# # Range of heat pump or hydrogen boiler intervention 
intervention_levels = [0.1, 0.2, 0.3, 0.4, 0.5]

# intervention_levels = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]


import time
start_time = time.time()

#######################################

import os
import numpy as np
import pandas as pd
import pyomo.environ as pyoen
from pyomo.environ import *
import pyomo.mpec as pyompec
from pyomo.opt import SolverFactory
import matplotlib.pyplot as plt
from tabulate import tabulate
from Aggreg_GT_OPFG import *
from verification_multinet_ins_outs  import *
from multinet_NoT_ele_ng_h2_heat_v1 import *



import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

def dir_outputs(main_dir, subdirs):
    if not os.path.exists(main_dir):
        os.makedirs(main_dir)
    
    for subdir in subdirs:
        subdir_path = os.path.join(main_dir, subdir)
        if not os.path.exists(subdir_path):
            os.makedirs(subdir_path)
            
                        

def data_import(year, scenario):
    path_I = r'Refined FES scenario inputs/' 

    systemData = {
        'Carbon Price'      : pd.read_excel(path_I + 'Carbon price/carbon_price.xlsx'), # carbon price ,
        'Installed capacity': pd.read_excel(path_I + 'InstalledCapacity/installed_capacity.xlsx' , sheet_name=scenario, index_col = 0) ,
        'Power Demand'      : pd.read_excel(path_I + 'PowerDemand_Heating_Input/powerDemand_'+ scenario + '.xlsx', sheet_name = year, index_col = 0),
        'Gas Consumption'   : pd.read_excel(path_I + 'gasConsumption_heating_input/gasCons_'+ scenario + '.xlsx', sheet_name = year, index_col = 0),
        'Players'           : pd.read_csv('Data/market_players2.csv'), #import the parameters
        'Levelised cost'    : pd.read_excel(path_I + 'Levelised_costs_for_model_input.xlsx'),
        'Construction cost' : pd.read_excel(path_I + 'Construction_cost_for_model_input.xlsx'),

        }
    
    
    systemData ['temp_system'] = temp_system
    systemData ['price_fg'] = price_fg
    
    chp_id = [5, 13, 14, 23]  #Keep 26 CHP from gas to elec + heat
    systemData['Players']['type'][chp_id] = 'GT'
    
    systemData['Players']['max_p_mw'] = systemData['Installed capacity'][int(year)][:]

    
    if ws_limit==2:
        systemData['Players']['max_p_mw'][[1, 2, 6, 7, 8, 10, 11,12, 17, 20, 22, 24]]=1e12
    
    
    return systemData


def variable_list(model, year, data):
    ub = data['Installed capacity'][int(year)] - data['Installed capacity'][2022]
    def fb(model,i):
        return (None,ub[i])
    
    # Variable list -----------------------------------------------------------
    model.p     = pyoen.Set(initialize=data['Players']['id'])

    model.q = pyoen.Var(model.p, within=NonNegativeReals, bounds=(0, 2000), initialize=None)  
    model.I = pyoen.Var(model.p, within=NonNegativeReals, initialize=None)  
    model.sigma = pyoen.Var(model.p, within=NonNegativeReals, initialize=0)  
    model.delta = pyoen.Var(model.p, within=NonNegativeReals, initialize=0)
    model.alpha = pyoen.Var(model.p, initialize=0)  
        
    return model




def parameter_list(t, model, year, data):
    

    # Parameter list ----------------------------------------------------------
    model.years = pyoen.Param(initialize= int(year) - 2022) # value in 'years'

    model.rate  = pyoen.Param(initialize=0.05) # value in percent
       
    model.AF    = pyoen.Param(initialize=( (1 + model.rate)**model.years - 1 )
                        / (model.rate * (1 + model.rate)**model.years)) # Annuity factor
    
    model.c     = pyoen.Param(model.p, initialize=data['Levelised cost'][int(year)], mutable=True) #value in £/MWh
    model.eps   = pyoen.Param(model.p, initialize=data['Construction cost'][int(year)]) # value in £/MW
    model.phi   = pyoen.Param(model.p, initialize=data['Players']['phi']) # value in percent
    model.lamda = pyoen.Param(model.p, initialize=data['Players']['economic_life']) # value in years
    model.emis  = pyoen.Param(model.p, initialize=data['Players']['emissions'], mutable=True) # tonne CO2/MWh 
    prev_year = systemData['Installed capacity'].columns[systemData['Installed capacity'].columns.get_loc(int(year))-1]
    model.iMAX  = pyoen.Param(model.p, initialize=data['Installed capacity'][int(year)]-data['Installed capacity'][prev_year], mutable=True)  # in MW

    model.ty  = pyoen.Param(model.p, initialize=data['Players']['type'])
   
    model.k = pyoen.Param(model.p, initialize=data['Players']['max_p_mw'], mutable=True)
    
    model.opex = pyoen.Param(model.p, initialize=data['Players']['costs'], mutable=True) # value in £/MWh

    # CCS parameters stored once
    systemData['CCS'] = {
        'capture_rate': 0.90,          # 90% CO2 capture
        'energy_penalty': 0.10,        # 10% energy penalty
        'EF_gas': 0.20,                # tCO2 / MWh_gas
        'opex_per_tCO2': 15.0,         # £ / tCO2
        'applicable_years': ['2040', '2045', '2050'],  # years when CCS is applied
        'chp_id': [5, 13, 14, 23],
        'Allgas': [0, 1, 3, 4, 5, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 23, 25, 26, 29]}
    


    if ccs_fg == 1 and str(year) in systemData['CCS']['applicable_years']:
        
        ccs_params = systemData['CCS']
        
        for i in ccs_params['Allgas']:
            # Residual emissions
            captured_tCO2_per_MWh = model.emis[i].value * ccs_params['capture_rate']
            model.emis[i] = model.emis[i] * (1-ccs_params['capture_rate'])

            # CCS opex added to levelised cost            
            ccs_cost_per_MWh = ccs_params['opex_per_tCO2'] * captured_tCO2_per_MWh
            model.c[i] = model.c[i] + ccs_cost_per_MWh
            model.opex[i] = model.opex[i] + ccs_cost_per_MWh

            
            # Energy penalty: reduce net output
            model.k[i] = model.k[i] * (1 - ccs_params['energy_penalty'])
            model.iMAX[i] = model.iMAX[i] * (1 - ccs_params['energy_penalty'])
            


                
    model.iMAX[29] = 10  #meth

    
    if ws_limit == 1:
        
        model.k[6] = 500 #solar
        model.k[7] = 500 #solar
        model.k[22] = 500 #solar
        model.k[2] = 500 #wind    
        model.k[8] = 500 #wind
        model.k[20] = 500 #wind
        model.k[24] = 500 #wind
    
    if ws_limit == 2:
        
        model.k[6] = 1e12 #solar
        model.k[7] =  1e12 #solar
        model.k[22] =  1e12 #solar
        model.k[2] =  1e12 #wind    
        model.k[8] =  1e12 #wind
        model.k[20] =  1e12 #wind
        model.k[24] =  1e12 #wind
        model.k[1] =  1e12 #biomass
        model.k[10] =  1e12 #biomass
        model.k[11] =  1e12 #biomass
        model.k[12] =  1e12 #biomass
        model.k[17] =  1e12 #biomass

    
    model.k[27] = 1000*H2_prop
    model.k[28] = 1000*H2_prop
    # for i in range(25, 30):  # Range includes 25 to 29
    #     model.k[i] = 0
    
    #########################


    from HP_H2B_Social_Interv_multinet_NoT import apply_monte_carlo_interventions
    data = apply_monte_carlo_interventions(systemData, num_simulations, heat_pumps, hydrogen_boilers, others)

    # data['Gas Consumption_MWh'] = data['Adjusted Gas Demand']
    # data['Power Demand'] = data['Adjusted Power Demand']
    data['Gas Consumption_MWh'] = data['Adjusted Gas Consumption 12Scenarios']
    data['Power Demand'] = data['Adjusted Power Demand 12Scenarios']
    data['Gas Consumption'] = data['Gas Consumption_MWh']*(0.4*1000)/(EF*3600)# to convert from MWh to kg/s
    
    data['hydrogen Consumption_MWh'] =data['Adjusted hydrogen Consumption 12Scenarios']
    data['hydrogen Consumption'] = data['hydrogen Consumption_MWh']*(0.4*1000)/(EF*3600)# to convert from MWh to kg/s


    # net_ng = ppipes.create_empty_network(fluid="hgas")
    # mdot_g = max(data['Gas Consumption'])*net_ng.fluid.get_density(288.15)/3600 # from m3/s to kg/s

    if Q_max_fg==0:
        model.Q_e = pyoen.Param(initialize=np.sum(data['Power Demand'], axis=1)[0])# value in MWh
        model.Q_g = pyoen.Param(initialize=np.sum(data['Gas Consumption'], axis=1)[0] * (EF*3600)/(0.4*1000)) # value in MWh
    elif Q_max_fg==1:
        model.Q_e = pyoen.Param(initialize=max(np.sum(data['Power Demand'], axis=1)))# value in MWh
        model.Q_g = pyoen.Param(initialize=max(np.sum(data['Gas Consumption'], axis=1)) * (EF*3600)/(0.4*1000)) # value in MWh
    elif Q_max_fg==2:
        model.Q_e = pyoen.Param(initialize=np.sum(data['Power Demand'], axis=1)[t])# value in MWh
        model.Q_g = pyoen.Param(initialize=np.sum(data['Gas Consumption'], axis=1)[t] * (EF*3600)/(0.4*1000)) # value in MWh


    model.Q_h = pyoen.Param(initialize=(0)) # value in MWh
    
    # ###########################
    

    if price_fg==0:
        model.pE = pyoen.Param(initialize=33.69) # in £/MWh
        model.pG = pyoen.Param(initialize=9.73)
        model.pH = pyoen.Param(initialize=9)

    elif price_fg==1:
        model.pE = pyoen.Param(initialize=(250)) # in £/MWh
        model.pG = pyoen.Param(initialize=(250))
        model.pH = pyoen.Param(initialize=(250))

    elif price_fg==2:
        model.pE = pyoen.Param(initialize=(75)) # in £/MWh
        model.pG = pyoen.Param(initialize=(30))
        model.pH = pyoen.Param(initialize=(100))
        
    elif price_fg==3 or price_fg==6:
        model.pE = pyoen.Param(initialize=(125)) # in £/MWh
        model.pG = pyoen.Param(initialize=(37))
        model.pH = pyoen.Param(initialize=(150))
    
    elif price_fg==4:
        model.pE = pyoen.Param(initialize=(125)) # in £/MWh
        model.pG = pyoen.Param(initialize=(37))
        model.pH = pyoen.Param(initialize=(75))
            
        
    if price_fg == 5:
        
        model.pE = pyoen.Param(initialize=(125)) # in £/MWh
        model.pG = pyoen.Param(initialize=(37))
                
        global Cost_H2
        
        ## pH_values = {'2025': 80, '2030': 75, '2035': 70, '2040': 65, '2045': 60, '2050': 55} ## LCOH of Blue H2 
        pH_values = {'2025': 100, '2030': 90, '2035': 75, '2040': 70, '2045': 65, '2050': 60} ## LCOH of Greene H2

        model.pH = pyoen.Param(initialize=pH_values[year])
        Cost_H2 = model.pH.value

    # Cost_H2 = 100
    # Cost_H2 = 10
    # Cost_H2 = 0
    # Cost_H2 = model.pH.value


    # model.CO2 = pyoen.Param(initialize=(43.29)) #£/tonne C02
    carbonPrice = systemData['Carbon Price'].set_index('Year').loc[int(year)][scenario]
    # Carbon price    
    model.CO2 = pyoen.Param(initialize= (carbonPrice)) #£/tonne C02
    
    # model.CO2 = pyoen.Param(initialize= 0) #£/tonne C02


    return model





# Complementarity Conditions
def complementarity_conditions(model):
    # Production complementarity condition
    def technical_rule(model, i):
        return pyompec.complements(
            model.q[i] >= 0,
            model.AF * (model.pE - model.c[i] - model.CO2 * model.emis[i]) - model.sigma[i] - model.alpha[i] <= 0
        )

    
    # Investment complementarity condition
    def investment_rule(model, i): 
        return pyompec.complements(
        model.I[i] >= 0,
        -model.AF * model.phi[i] * model.eps[i] - model.eps[i] * (1 - (model.lamda[i] - model.years) /
        (model.lamda[i] * (1 + model.rate)**model.years)) + model.sigma[i] - model.delta[i] <= 0
    )


    # Technical limit condition
    def technical_limit(model, i):
        return pyompec.complements(
            model.sigma[i] >= 0,
            model.q[i] - model.k[i] - model.I[i] <= 0
        )
    

    # Investment limit condition
    def investment_limit(model, i):
        return pyompec.complements(
            model.delta[i] >= 0,
            model.I[i] - model.iMAX[i] <= 0
        )
    
    
    model.c1 = pyompec.Complementarity(model.p, rule=technical_rule)
    model.c2 = pyompec.Complementarity(model.p, rule=investment_rule)
    model.c3 = pyompec.Complementarity(model.p, rule=technical_limit)
    model.c4 = pyompec.Complementarity(model.p, rule=investment_limit)

    return model



if eqcs_model_q != 1:
    
    def equality_constraints(model, data):
        
        # Equality constraints --------------------------------------------------------      
        
        model.c5 = pyoen.Constraint(expr= sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='wind'].tolist()) + 
                                    sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='solar'].tolist()) + 
                                    sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='biomass'].tolist()) +
                                    sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='CHP'].tolist()) + 
                                    sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='GT'].tolist()) + 
                                    sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='G2P'].tolist()) + 
                                    sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='FC'].tolist()) +
                                    # -sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='P2G'].tolist()) + 
                                    # -sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='EZ'].tolist()) +
                                    # -sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='meth'].tolist()) +
                                   -model.Q_e == 0)
        
        
        
        model.c6 = pyoen.Constraint(expr= sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='meth'].tolist()) +  
                                    sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='P2G'].tolist()) +
                                    -sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='CHP'].tolist()) + 
                                    -sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='GT'].tolist()) + 
                                    -model.Q_g == 0)
        
           
                
        model.c7 = pyoen.Constraint(expr= sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='EZ'].tolist()) + 
                                    -sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='FC'].tolist()) +
                                    -model.Q_h ==0)
        
        
        return model
    
elif eqcs_model_q == 1:
    
    # Equalicty Constraints
    def equality_constraints(model, data):
        if eq_fg==1:
            model.c5 = pyoen.Constraint(
                expr=sum(model.q[i] for i in data['Players'].index) - model.Q_e == 0)
        else:
            model.c5 = pyoen.Constraint(
            expr=sum(model.q[i] for i in data['Players'].index) - model.Q_e >= 0)
    
        return model



if obj_fg==0:
    def objective_function(model):
        # Define the NPV Objective Function
        def npv_rule(model):
            PVt = 0
            for i in model.p:
                # Revenue from power output
                revenue = model.q[i] * model.pE
                
                # Operational cost: levelized cost and emission cost
                operational_cost = model.q[i] * (model.c[i] + model.CO2 * model.emis[i])
                
                # Investment and construction cost
                depreciation = 1 - (model.lamda[i] - model.years) / (model.lamda[i] * (1 + model.rate)**model.years)
                NI = model.I[i]*model.eps[i]*depreciation
                FC = model.phi[i]*model.eps[i]*(model.k[i] + model.I[i])
                
                # Net Present Value (NPV) for the player
                PVt += revenue - operational_cost
                
            npv = PVt
            # npv = model.AF*(PVt - FC) - NI
    
            return npv
        
        model.obj = pyoen.Objective(rule=npv_rule, sense=pyoen.maximize)
        
        return model
    
    
if obj_fg==1:
    
    def objective_function(model):
        def objective_rule(model):
            return sum(
                model.q[i] * (model.pE - model.c[i] - model.CO2 * model.emis[i]) - model.delta[i] 
                for i in model.p
            )
        model.obj = Objective(rule=objective_rule, sense=maximize)
        return model



def linear_constraints(model):
    # First part of the constraint: model.q[i] >= 0 (non-negativity)
    def capacity_lower_bound_rule(model, i):
        return model.q[i] >= 0
    
    # Second part of the constraint: model.q[i] <= model.k[i] - model.I[i] (upper bound)
    def capacity_upper_bound_rule(model, i):
        return model.q[i] <= model.k[i] - model.I[i]
    
    # Investment limit: model.I[i] <= model.iMAX[i]
    def investment_limit_rule(model, i):
        return model.I[i] <= model.iMAX[i]
    
    # Adding constraints to the model
    model.c8_lower = pyoen.Constraint(model.p, rule=capacity_lower_bound_rule)
    model.c8_upper = pyoen.Constraint(model.p, rule=capacity_upper_bound_rule)
    model.c9 = pyoen.Constraint(model.p, rule=investment_limit_rule)
    
    return model


import logging
from pyomo.environ import SolverFactory

# Set Pyomo's logging level to error-only
logging.getLogger('pyomo').setLevel(logging.ERROR)

# Solver function
def solver (model, solver_type):
    if solver_type == 'pathimpl':
        solver = SolverFactory('pathampl', executable='pathampl.exe')
    else:
        solver = SolverFactory('ipopt', executable='ipopt.exe')

    
    # solver = SolverFactory('pathampl', executable='pathampl.exe')
    # solver = SolverFactory('ipopt', executable='ipopt.exe')
    
    solver.options['max_iter'] = 100
    solver.options['tol'] = 1e-5
    solver.solve(model, tee=False)
    # model.display()
    
    

def game(t, year, scenario, data, eps_imax):
    
    
    model = pyoen.ConcreteModel()
    
    variable_list(model, year, data)
    
    parameter_list(t, model, year, data)
    
    
    # Adjust iMAX values
    adjustment_factor = eps_imax # Factor for adjusting iMAX 
    new_iMAX = {k: v * adjustment_factor for k, v in model.iMAX.extract_values().items()}
    model.iMAX = pyoen.Param(model.p, initialize=new_iMAX)  # in MW
    
    # objective_function(model)  # Define objective function
        
    complementarity_conditions(model)
   
    linear_constraints(model)  # Added linear constraints for capacity and investment

    equality_constraints(model, data)
    
    solver(model, solver_type)
    
    # print_results(model)
    
    return model


def scale_generator_data(genData):
    ###Scales the active and reactive power limits in generator data
    
    active_power_scale = 2  
    reactive_power_scale = 2 
    
    if HPHB_sw=='HB_Interv' or hydrogen_boilers>0.1:
        active_power_scale = 10
        reactive_power_scale = 10

    # Scale the active power max (column 8)
    genData.iloc[:, 8] = genData.iloc[:, 8] * active_power_scale
    # Scale the reactive power limits (columns 3 and 4)
    genData.iloc[:, 3] = genData.iloc[:, 3] * reactive_power_scale  # Upper reactive power limit
    genData.iloc[:, 4] = genData.iloc[:, 4] * reactive_power_scale  # Lower reactive power limit
    
    genData.iloc[:, 1] = genData.iloc[:, 1] * active_power_scale  
    genData.iloc[:, 2] = genData.iloc[:, 2] * reactive_power_scale 
        

    return genData


def initial_run_OPGF(model, systemData, H2_prop):
    
    global multinet, genCapacities
    # Running the GT model
    genCapacities = model.q.extract_values()
    genCapacities = pd.DataFrame.from_dict(genCapacities, orient = 'index')
    genData = pd.read_csv('Data/genData.csv')
    genData = scale_generator_data(genData)
    
    # # genData['1'] = genCapacities[0:25]
    # # genData['8']  = genCapacities[0:25]

    # from multinet_NoT_V6 import * 
    # multinet = run_OPGF(hour_of_day, genData,  systemData, H2_prop, temp_system, price_fg, num_simulations, heat_pumps, hydrogen_boilers, others) # Running the OPGF
    # return multinet
    
    genData['8'] = systemData['Players']['max_p_mw'][:25]


    multinet = run_OPGF(hour_of_day, genData,  systemData, H2_prop, ccs_fg, temp_system, price_fg, 
                        num_simulations, heat_pumps, hydrogen_boilers, others, base_sw, 
                        HPHB_sw, EZ_ATR_FC_CHP_fg, list_ele_demand, list_gas_demand, STI_scenario) # Running the OPGF
    
    
    chp_gfg_gas = sum(multinet.nets['gas'].res_sink['mdot_kg_per_s'][15:20]) * (EF * 3600) / (0.4 * 1000)
    chp_gfg_h_gas = energy_h2_gas(H2_prop, chp_gfg_gas)
    chp_gfg_gas_cost = chp_gfg_h_gas['qg_gas'] * systemData['Players']['costs'][29]
    chp_gfg_h2_cost = chp_gfg_h_gas['qg_h2'] 
    

    return multinet




def calculate_OPGF_cost(model, multinet, systemData, hydrogen_cost_value):
    global Cost_H2
    Cost_H2 = hydrogen_cost_value
    return cost_check(model, multinet, systemData)




def cost_calc(model):

    total_cost_ele_ng = (
        sum(
            pyoen.value(
                model.q[tech] * model.c[tech]
                if model.ty[tech] not in ['CHP', 'GT'] 
                else energy_h2_gas(H2_prop, model.q[tech])['qg_gas'] * model.c[tech]
            )
            for tech in model.p
        ) +
        sum(
            pyoen.value(
                model.q[tech] * model.CO2 * model.emis[tech]
                if model.ty[tech] not in ['CHP', 'GT'] 
                else energy_h2_gas(H2_prop, model.q[tech])['qg_gas'] * model.CO2 * model.emis[tech]
            )
            for tech in model.p
        ))
    
    hydrogen_cost_chp_gt = sum(
        pyoen.value(
            energy_h2_gas(H2_prop, model.q[tech])['qg_h2'] * Cost_H2
        ) for tech in model.p if model.ty[tech] in ['CHP', 'GT'])
    
    # Add hydrogen costs for electrolyser and fuel cell
    hydrogen_cost_ez_fc = sum(
        pyoen.value(
            model.q[tech] * Cost_H2
        ) for tech in model.p if model.ty[tech] in ['EZ', 'FC']
    )
    
    # Add hydrogen cost for hydrogen boilers (if applicable)
    hydrogen_boiler_cost = sum(
        pyoen.value(
            model.q[tech] * Cost_H2
        ) for tech in model.p if model.ty[tech] == 'HB'
    )
    
    # Add cost for gas sinks (if not already included in model.p)
    gas_sink_cost = sum(
        pyoen.value(
            model.q[tech] * model.c[tech] + energy_h2_gas(H2_prop, model.q[tech])['qg_h2'] * Cost_H2
        ) for tech in model.p if model.ty[tech] == 'GAS_SINK'
    )
    
    total_cost = total_cost_ele_ng + hydrogen_cost_chp_gt + hydrogen_cost_ez_fc + hydrogen_boiler_cost + gas_sink_cost
    
    return total_cost



def cost_check(model, multinet, systemData):
            
    
    cost_GT = cost_calc(model) # Importing the total cost from the GT model
    EF = mdot_energy_conv(H2_prop)
    

    for name, param in {'costs': model.opex, 'emissions': model.emis}.items():
        systemData['Players'][name] = systemData['Players']['id'].map(param.extract_values())
    
    
    players = systemData['Players']
    
    
                
    # Gas sink calculations
    qg_sink = sum(multinet.nets['gas'].res_sink['mdot_kg_per_s']) * (EF * 3600) / (0.4 * 1000)
    qg_sink_h_gas = energy_h2_gas(H2_prop, qg_sink)
    qg_sink_mix = sum(multinet.nets['gas'].res_sink['mdot_kg_per_s']) * (EF * 3600) / (0.4 * 1000)
    qg_sink_gas = qg_sink_h_gas['qg_gas']
    qg_sink_h2 = qg_sink_h_gas['qg_h2']
    hydrogen_cost = qg_sink_h2 * Cost_H2 # Cost of hydrogen
    
    # CHP and GFG units (indices 15 to 19 in gas sinks)
    chp_gfg_gas = sum(multinet.nets['gas'].res_sink['mdot_kg_per_s'][15:20]) * (EF * 3600) / (0.4 * 1000)
    chp_gfg_h_gas = energy_h2_gas(H2_prop, chp_gfg_gas)
    chp_gfg_gas_cost = chp_gfg_h_gas['qg_gas'] * players['costs'][29]
    chp_gfg_h2_cost = chp_gfg_h_gas['qg_h2'] * Cost_H2
    

    
    chp_gfg_emission_cost = chp_gfg_h_gas['qg_gas'] * model.CO2.value * players['emissions'][29]
    
    # Fuel cell hydrogen consumption
    fuel_cell_h2 = multinet.nets['hydrogen'].res_sink['mdot_kg_per_s'][0] * (EF * 3600) / (0.4 * 1000)
    fuel_cell_h2_cost = fuel_cell_h2 * Cost_H2 # Cost of hydrogen
    
    # Hydrogen boilers (assuming capacity_HB is available from OPGF)
    capacity_HB = systemData['capacity_HB']  
    hydrogen_boiler_h2 = capacity_HB  
    hydrogen_boiler_cost = hydrogen_boiler_h2 * Cost_H2
    
    #######################
    ## Emission costs
    global emissionCost, AggType_costs
    
    p_mw_series = multinet['nets']['power']['res_gen']['p_mw'].iloc[:25]
    player_data = systemData['Players'].loc[:24, ['type', 'emissions']]
    
    df_pmw_type_emis = pd.DataFrame({
        'p_mw': p_mw_series.values,
        'type': player_data['type'].values,
        'emissions': player_data['emissions'].values})

    df_chp_gt = df_pmw_type_emis[df_pmw_type_emis['type'].isin(['CHP', 'GT'])].reset_index(drop=True)
    df_other = df_pmw_type_emis[~df_pmw_type_emis['type'].isin(['CHP', 'GT'])].reset_index(drop=True)

    emis_chp_gt= sum(energy_h2_gas(H2_prop, df_chp_gt['p_mw'])['qg_gas'] * df_chp_gt['emissions'] * model.CO2.value)
    emis_other = sum(df_other['p_mw']* df_other['emissions'] * model.CO2.value)
    
    emissionCost = emis_chp_gt + emis_other
    
    # if systemData['Players']['emissions'][0]>0:
    if ccs_fg==0:

        EH = mdot_energy_conv(1)

        q_g2h = multinet['nets']['hydrogen']['res_source']['mdot_kg_per_s'][1]*(EH*3600)/(0.4*1000)

        emissionCost = emissionCost + q_g2h*0.1*model.CO2.value

    
    ################
    
    # Costs for players 26, 27, 28
    Cost_plrs26_27_28 = (sum(pyoen.value(model.q[plr] * model.c[plr] 
        if model.ty[plr] not in ['CHP', 'GT'] 
        else energy_h2_gas(H2_prop, model.q[plr])['qg_gas'] * model.c[plr]) for plr in [26, 27, 28]) 
    + sum(pyoen.value(model.q[plr] * model.CO2 * model.emis[plr] 
        if model.ty[plr] not in ['CHP', 'GT'] 
        else energy_h2_gas(H2_prop, model.q[plr])['qg_gas'] * model.CO2 * model.emis[plr]) for plr in [26, 27, 28]))
    
    # Total OPGF cost
    cost_OPGF = (sum(multinet['nets']['power']['res_gen']['p_mw'] * players['costs'][:25]) +
                  qg_sink_mix * players['costs'][29] +
                  sum(multinet['nets']['power']['res_load']['p_mw'][33:37]) * players['costs'][29] +
                  emissionCost + Cost_plrs26_27_28 + hydrogen_cost +
                  chp_gfg_gas_cost + chp_gfg_h2_cost + chp_gfg_emission_cost +
                  fuel_cell_h2_cost + hydrogen_boiler_cost)
    
    
    print('cost_GT=',cost_GT)
    print('cost_OPGF=',cost_OPGF)
    print('cost_diff=',cost_GT - cost_OPGF)
    
    
    # print('model.c', model.c.extract_values())
    # print('Sys_Cost', players['costs'])    
    # print(systemData['Players'][['type', 'costs']])
    
    AggType_costs = systemData['Players'][['type', 'costs']].drop_duplicates().reset_index(drop=True)
    
    # print(AggType_costs)
    
        
    return [cost_GT, cost_OPGF, cost_GT - cost_OPGF]
    


    
def update_GT(year, scenario, multinet, systemData): 
    
    EH=mdot_energy_conv(1)

    q_ext_mix = abs(sum(multinet.nets['gas'].res_ext_grid['mdot_kg_per_s'])*(EF*3600)/(0.4*1000))
    q_ext_gas = energy_h2_gas(H2_prop, q_ext_mix)['qg_gas'] 
    q_ext_h = energy_h2_gas(H2_prop, q_ext_mix)['qg_h2'] 
        
    q_EZ = multinet['nets']['power']['res_load']['p_mw'][37]
    q_FC = multinet['nets']['power']['res_sgen']['p_mw'][5]
    
    
    # print('hyd_net=', multinet['nets']['hydrogen'])
    # print('hyd_source=', multinet['nets']['hydrogen']['source'])
    # print(multinet['nets']['hydrogen']['res_source'])
    # print(multinet['nets']['hydrogen']['sink'])
    # print(multinet['nets']['hydrogen']['res_sink'])
    # st=stop
    
    q_g2h = multinet['nets']['hydrogen']['res_source']['mdot_kg_per_s'][1]*(EH*3600)/(0.4*1000)

    
    q_h_sink =  q_EZ + q_FC + q_g2h
    # q_h_sink =  sum(multinet.nets['hydrogen'].res_sink['mdot_kg_per_s'])*(39.41*3600)/(0.4*1000)
    
    systemData['Players']['max_p_mw'][0:25] = multinet['nets']['power']['res_gen']['p_mw']   #do the change here
    
    systemData['Players']['max_p_mw'][25] = sum(multinet['nets']['power']['res_load']['p_mw'][33:37])
    
    systemData['Players']['max_p_mw'][5] = sum(multinet['nets']['power']['res_sgen']['p_mw'][:2]) # chp industrial/Distric heating, etc
    systemData['Players']['max_p_mw'][26] = sum(multinet['nets']['power']['res_sgen']['p_mw'][2:5]) #gfg (H2-GT peakers flix)
    # systemData['Players']['max_p_mw'][26] = 0
    # systemData['Players']['max_p_mw'][5] = sum(multinet['nets']['power']['res_sgen']['p_mw'][6:]) #heating chp

    
    if ext_sw==1:
       # systemData['Players']['max_p_mw'][[27, 28]] = q_h_sink + q_ext_h
       systemData['Players']['max_p_mw'][27] = q_EZ + q_ext_h
       systemData['Players']['max_p_mw'][[28]] = q_FC + q_ext_h
       systemData['G2H'] = q_g2h
    elif ext_sw==0:
        # systemData['Players']['max_p_mw'][[27, 28]] = q_h_sink 
        systemData['Players']['max_p_mw'][27] = q_EZ
        systemData['Players']['max_p_mw'][28] = q_FC
        systemData['G2H'] = q_g2h


    
    systemData['Players']['max_p_mw'][29] = q_ext_gas
    

    model = game(t, year, scenario, systemData, eps_imax)
    
    # Assign values from systemData['Players']['max_p_mw'] to model.q for indices 25 to 29
    for i in range(25, 30):
        model.q[i] = systemData['Players']['max_p_mw'][i]

    
    return model




def q_gas_hyd(multinet, H2_prop):  
    players = systemData['Players']
    p_mw = multinet['nets']['power']['res_gen']['p_mw']

    qgas_h_chp_gt, qgas_chp_gt, qh_chp_gt = 0, 0, 0
    
    for i in range(25):
        if players.type[i] in ['CHP', 'GT']:
            p_mw_i = p_mw[i]
            qgas_h_chp_gt += p_mw_i
            energy = energy_h2_gas(H2_prop, p_mw_i)
            qgas_chp_gt += energy['qg_gas']
            qh_chp_gt += energy['qg_h2']
            
            q_chp_gt = {'qgas_h_chp_gt': qgas_h_chp_gt,
                'qgas_chp_gt': qgas_chp_gt,
                'qh_chp_gt': qh_chp_gt}

    
    return q_chp_gt


# Running the analysis over a range of H2 proportions

# Initialize an empty dictionary to store OPGF outcomes for H2_prop = h2_plt
dic_GT_H2 = {}
dic_OPGF_H2 = {}

def run_techno_economic_analysis(t, year, scenario, systemData, temp_system, output_dir):
    
    # Create output directories
    global H2_prop, EF, results
    
    EH=mdot_energy_conv(1)
    
    output_dir = f'Output/Res/Outs/'+str(scenario)+'/imax_'+str(eps_imax)+'_prcfg_'+str(price_fg)+'_yrfg_'+str(year_fg)+'_'+str(year)
    subdirs = ['Figures', 'Results', 'Agg_GT_results', 'Agg_OPGF_results']
    dir_outputs(output_dir, subdirs)
    
        
    if h2_fg==1:
        h2_props = np.arange(0, 1.1, 0.1)  # Range of H2 proportions (from 0 to 1, step 0.1)
    elif h2_fg==2:
        h2_props = [0.2]
    elif h2_fg==3:
        h2_props = [0.0, 0.1, 0.2, 0.3]  
    elif h2_fg==4:
         h2_props = [0, 0.2, 1.0]
    elif h2_fg==0:
        h2_props =[H2_prop]
        
    
    results = []  # Store results for all runs
    
    # Initialize dataframes
    global GT_Gens_df, OPGF_Gens_df, capacity_HB, q_EZ, q_FC, q_g2h
    
    GT_Gens_df = pd.DataFrame()
    OPGF_Gens_df = pd.DataFrame()
    

    for H2_prop in h2_props:
        
        from HP_H2B_Social_Interv_multinet_NoT import data_import
        systemData = data_import(year, scenario, STI_scenario, ws_limit)  
        
        systemData['Year'] = year
        systemData['scenario'] = scenario 

        
        EF = mdot_energy_conv(H2_prop)  # Calculate energy density
        model = game(t, year, scenario, systemData, eps_imax)  # Create and solve model
        
        
        multinet = initial_run_OPGF(model,  systemData, H2_prop)  # Run optimization
        if case_fg=='no_update': 'Do nothing'
            
        else:
            model = update_GT(year, scenario, multinet, systemData)

        # Case 1: Hydrogen cost = 0
        opgf_cost_case1 = calculate_OPGF_cost(model, multinet, systemData, hydrogen_cost_value=0)
        
        # Case 2: Hydrogen cost = marginal cost
        opgf_cost_case2 = calculate_OPGF_cost(model, multinet, systemData, hydrogen_cost_value=systemData['hydrogen_marginal_cost'])
 
        
        # Techno-economic cost and results calculation
        Model_costs = cost_check(model, multinet, systemData)
        
        
        objective_function(model)  # Define objective function
        
        genCapacities = model.q.extract_values()
        genCapacities = pd.DataFrame.from_dict(genCapacities, orient='index')
        investments = model.I.extract_values()
        investments =  pd.DataFrame.from_dict(investments, orient = 'index')
         
        # systemData['Players']['type'][26] = 'G2P'
        systemData['Players']['type'][26] = 'GT'
        systemData['Players']['type'][5] = 'CHP'
        
        PlayersOutput =systemData['Players']['max_p_mw']

        global Aggreg_gens_invs_gt, Aggreg_gens_invs_opgf
        agg_dir1=output_dir+'/'+'Agg_GT_results'
        agg_dir2=output_dir+'/'+'Agg_OPGF_results'
        
        Aggreg_gens_invs_gt = aggreg_gens_invs('GT', model, systemData, year, scenario, genCapacities, PlayersOutput, 
                                               investments, H2_prop, agg_dir1)

        Aggreg_gens_invs_opgf = aggreg_gens_invs('OPGF', model, systemData, year, scenario, genCapacities, PlayersOutput,
                                                 investments, H2_prop, agg_dir2)
        
        # print('Aggreg_gens_invs_gt[2050 Capacity]=', Aggreg_gens_invs_gt['2050 Capacity'])
        # print('Aggreg_gens_invs_opgf=', Aggreg_gens_invs_opgf['2050 Capacity'])
        # st=stop
                
        
        data=systemData
        q_p2g = pyoen.value(sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='P2G'].tolist()))
        q_meth = pyoen.value(sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='meth'].tolist()))
        q_chp = pyoen.value(sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='CHP'].tolist()))
        q_gt = pyoen.value(sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='GT'].tolist()))
        q_h = pyoen.value(sum(model.q[i] for i in data['Players'].index[data['Players']['type']=='EZ'].tolist()))
        
        

        total_supply, total_demand = verification_multinet_ins_outs(multinet, EF, H2_prop, eps_imax)  
       
      
        
        cost_check(model, multinet, systemData)
        
        Cost_Emiss_GT = sum(pyoen.value(
                model.q[tech] * model.CO2 * model.emis[tech]
                if model.ty[tech] not in ['CHP', 'GT'] 
                else energy_h2_gas(H2_prop, model.q[tech])['qg_gas'] * model.CO2 * model.emis[tech]) for tech in model.p)
        
        # Calculate the cost of emissions for indices 0 to 24 in model.p
        Cost_ele_Emiss_GT = sum(
            pyoen.value(
                model.q[tech] * model.CO2 * model.emis[tech]
                if model.ty[tech] not in ['CHP', 'GT'] 
                else energy_h2_gas(H2_prop, model.q[tech])['qg_gas'] * model.CO2 * model.emis[tech]
            ) if idx <= 25 else 0  # Only include emissions from index 1 to 25 (Pyomo 1-indexed)
            for idx, tech in enumerate(model.p, start=1))
        
        
        #############################################################
        #############################################################
        
        q_ext_mix = abs(sum(multinet.nets['gas'].res_ext_grid['mdot_kg_per_s'])*(EF*3600)/(0.4*1000))
        q_ext_gas = energy_h2_gas(H2_prop, q_ext_mix)['qg_gas'] 
        q_ext_h = energy_h2_gas(H2_prop, q_ext_mix)['qg_h2'] 
            
        q_EZ = multinet['nets']['power']['res_load']['p_mw'][37]
        q_FC = multinet['nets']['power']['res_sgen']['p_mw'][5]
        q_g2h = multinet['nets']['hydrogen']['res_source']['mdot_kg_per_s'][1]*(EH*3600)/(0.4*1000)
        systemData['G2H']=q_g2h
        
        q_h_sink =  q_EZ + q_FC + q_g2h

        e_demand = sum(multinet.nets['power'].load['p_mw'][0:33])
        g_demand = sum(multinet.nets['gas'].sink['mdot_kg_per_s'][0:15]*(EF*1*3600)/(0.4*1000))
        
        # capacity_HB = hydrogen_boilers * g_demand
        # capacity_H2 = H2_prop * g_demand

        capacity_HB = hydrogen_boilers 
        capacity_H2 = 0
            
        if heat_pumps==1:
            capacity_HB = hydrogen_boilers * e_demand
            capacity_H2 = H2_prop * e_demand
            

        ####### Just for Check ########
        
        # print('e_demand=', e_demand)
        # print('g_demand=', g_demand)
        
        # print('q_ext_mix=',q_ext_mix)
        # print('q_ext_gas=',q_ext_gas)
        # print('q_ext_h=',q_ext_h)
        
        # print('capacity_HB=', capacity_HB)
        # print('capacity_H2=', capacity_H2)

        # print('q_h_sink=',q_h_sink)
        # print('q_EZ=',q_EZ)
        # print('q_FC=',q_FC)
        print('q_g2h=',q_g2h)
        
        # print('res_sinks=', multinet.nets['gas']['res_sink'])
        # print('res_sources=',multinet.nets['gas']['res_source'])
        # print('res_ExtGrid=', multinet.nets['gas']['res_ext_grid'])

        # print('res_load=', multinet.nets['power']['res_load'])
        # print('res_sgens=', multinet.nets['power']['res_sgen'])
        # print('res_ExtGrid=', multinet.nets['power']['res_ext_grid'])
        # print('q_FC=', multinet['nets']['power']['res_sgen']['p_mw'][5])
        
        # print('hyd_res_sinks=', multinet.nets['hydrogen']['res_sink'])
        print('hyd_res_sources=',multinet.nets['hydrogen']['res_source'])
        # print('hyd_res_ExtGrid=', multinet.nets['hydrogen']['res_ext_grid'])
        
        print('hyd_souces MWh', multinet['nets']['hydrogen']['res_source']['mdot_kg_per_s']*(EH*3600)/(1000))
        print('hyd_g2g=', multinet['nets']['hydrogen']['res_source']['mdot_kg_per_s'][0]*(EH*3600)/(1000))

        
        EH=mdot_energy_conv(1)

        # print('res_FC_in=', multinet['nets']['hydrogen']['res_sink']['mdot_kg_per_s']*(EH*3600)/(1000))
    
      
        
        # Add results to a list for storage
        
        if year_fg == 0:
       
            results.append({
                'H2 Proportion': H2_prop,
                'Cost_GT': Model_costs[0],
                # 'Cost_OPGF': Model_costs[1],
                'Cost_OPGF': opgf_cost_case1[1],  # Cost_H2=0, as an endeginous cost to avoid doubel count of ele+gas costs 
                'Cost_OPGF_H2Marg': opgf_cost_case2[1],
                'Cost Difference': Model_costs[2],
                'Cost_H2Marg': systemData['hydrogen_marginal_cost'], # H2 Mariginal Cost from EZ+ATR (i.e., ele+gas costs)
                
                'NPV': pyoen.value(model.obj),
                'Total_supply':total_supply,
                'Total_demand':total_demand,
                'Emissions_GT': Cost_Emiss_GT/model.CO2.value,
                'Emissions_OPGF':emissionCost/model.CO2.value,
                'Cost_Ele_Emissions_GT': Cost_ele_Emiss_GT,
                'Ele_Emissions_GT': Cost_ele_Emiss_GT/model.CO2.value,
                'Hydrogen_Boiler': capacity_HB,
                'Electrolyser': q_EZ,
                'Fuel Cell': q_FC,
                'G2H': q_g2h,
                
            })
            
            
        elif year_fg == 1:
            
            results.append({
                'H2 Proportion': H2_prop,
                'Cost_GT': Model_costs[0] * 8760,
                # 'Cost_OPGF': Model_costs[1] * 8760,
                'Cost_OPGF': opgf_cost_case1[1] * 8760,
                'Cost_OPGF_H2Marg': opgf_cost_case2[1] * 8760,
                'Cost Difference': Model_costs[2] * 8760,
                'Cost_H2Marg': systemData['hydrogen_marginal_cost'] * 8760,

                'NPV': pyoen.value(model.obj) * 8760,
                'Total_supply':total_supply * 8760,
                'Total_demand':total_demand * 8760,
                'Emissions_GT': Cost_Emiss_GT/model.CO2.value * 8760,
                'Emissions_OPGF':emissionCost/model.CO2.value * 8760,
                'Cost_Ele_Emissions_GT': Cost_ele_Emiss_GT * 8760,
                'Ele_Emissions_GT': Cost_ele_Emiss_GT/model.CO2.value * 8760,
                'Hydrogen_Boiler': capacity_HB * 8760,
                'Electrolyser': q_EZ * 8760,
                'Fuel Cell': q_FC * 8760,
                'G2H': q_g2h * 8760,
            })
        
                
        
        #############################################################
        #############################################################
    
        GT_Gens_df, OPGF_Gens_df = create_Agg_gen_dataframes(Aggreg_gens_invs_gt, Aggreg_gens_invs_opgf, H2_prop, GT_Gens_df, OPGF_Gens_df)
        
        col_name = OPGF_Gens_df.columns[1]
        g2h_row = pd.DataFrame([['G2H', results[0]['G2H']]], columns=['Player Type', col_name])
        
        # Append the row
        OPGF_Gens_df = pd.concat([OPGF_Gens_df, g2h_row], ignore_index=True)
        GT_Gens_df = pd.concat([GT_Gens_df, g2h_row], ignore_index=True)

        # Save intermediate results to Excel  
        # Save results after the loop
        GT_Gens_df.to_excel(f'{output_dir}/Results/GT_Gens_{year}_{scenario}.xlsx', index=False)
        OPGF_Gens_df.to_excel(f'{output_dir}/Results/OPGF_Gens_{year}_{scenario}.xlsx', index=False)
        
        pd.DataFrame(results).to_excel(f'{output_dir}/Results/tech_econ_analysis_{year}_{scenario}.xlsx', index=False)


    # Extract the relevant column and rename it to the current year
    selected_data = OPGF_Gens_df[['Player Type', h2_plt]].copy()
    selected_data = selected_data.rename(columns={h2_plt: str(year)})
    dic_OPGF_H2[hour_of_day, year] = selected_data
    
    selected_data_gt = GT_Gens_df[['Player Type', h2_plt]].copy()
    selected_data_gt= selected_data_gt.rename(columns={h2_plt: str(year)})
    dic_GT_H2[hour_of_day, year] = selected_data_gt

  
    # Convert the full list of results to a DataFrame for further analysis
    tech_econ_df = pd.DataFrame(results)

    # Save the final dataframe to Excel
    tech_econ_df.to_excel(f'{output_dir}/Results/tech_econ_analysis_{year}_{scenario}.xlsx', index=False)

    
    if idiv_plt_sw==1:
        # Visualize key findings and save the figure
        visualize_and_save_results(tech_econ_df, output_dir)
        
        # # Display the results
        # print("OPGF_Gens_df:")
        # print(OPGF_Gens_df)
        # print("\nGT_Gens_df:")
        # print(GT_Gens_df)
        
        
    
    return tech_econ_df
    




# Function to visualize results and save figures
def visualize_and_save_results(tech_econ_df, output_dir):
    # Plot NPV
    plt.figure(figsize=(10, 6))
    plt.plot(tech_econ_df['H2 Proportion'], tech_econ_df['NPV'], color='black', marker='o')
    plt.xlabel('Hydrogen Proportion')
    plt.ylabel('NPV (£)')
    plt.title('Net Present Value vs Hydrogen Proportion')
    plt.grid(True)
    
    # Save the figure
    plt.savefig(f'{output_dir}/Figures/Fig_NPV_vs_H2s_{year}_{scenario}.png', dpi=300)
    
    # Plot Cost Difference
    plt.figure(figsize=(10, 6))
    plt.plot(tech_econ_df['H2 Proportion'], tech_econ_df['Cost Difference'], color='black', marker='o')
    plt.xlabel('Hydrogen Proportion')
    plt.ylabel('Cost Difference (£)')
    plt.title('Cost Difference vs Hydrogen Proportion')
    plt.grid(True)
    
    # Save the figure
    plt.savefig(f'{output_dir}/Figures/Fig_Cost_Difference_vs_H2s_{year}_{scenario}.png', dpi=300)

    # Plot Long-term Costs (red)
    plt.figure(figsize=(10, 6))
    plt.plot(tech_econ_df['H2 Proportion'], tech_econ_df['Cost_GT'], color='red', marker='o')
    plt.xlabel('Hydrogen Proportion')
    plt.ylabel('Cost (£)')
    plt.title('Costs vs Hydrogen Proportion')
    plt.grid(True)
    
    # Save the figure for Long-term
    plt.savefig(f'{output_dir}/Figures/Fig_Cost_GT_long_term_vs_H2s_{year}_{scenario}.png', dpi=300)

    # Plot Short-term Costs (blue)
    plt.figure(figsize=(10, 6))
    plt.plot(tech_econ_df['H2 Proportion'], tech_econ_df['Cost_OPGF'], color='blue', marker='o')
    plt.xlabel('Hydrogen Proportion')
    plt.ylabel('Cost (£)')
    plt.title('Costs vs Hydrogen Proportion')
    plt.grid(True)

    # Save the figure for Short-term
    plt.savefig(f'{output_dir}/Figures/Fig_Cost_OPGF_short_term_vs_H2s_{year}_{scenario}.png', dpi=300)

    plt.show()

    # Plot Long-term Emissions (red)
    plt.figure(figsize=(10, 6))
    plt.plot(tech_econ_df['H2 Proportion'], tech_econ_df['Emissions_GT'], color='red', marker='o')
    plt.xlabel('Hydrogen Proportion')
    plt.ylabel('Tonne CO2')
    plt.title('Emissions vs Hydrogen Proportion')
    plt.grid(True)

    # Save the figure for Long-term
    plt.savefig(f'{output_dir}/Figures/Fig_Emissions_GT_long_term_vs_H2s_{year}_{scenario}.png', dpi=300)

    # Plot Short-term Emissions (blue)
    plt.figure(figsize=(10, 6))
    plt.plot(tech_econ_df['H2 Proportion'], tech_econ_df['Emissions_OPGF'], color='blue', marker='o')
    plt.xlabel('Hydrogen Proportion')
    plt.ylabel('Tonne CO2')
    plt.title('Emissions vs Hydrogen Proportion')
    plt.grid(True)

    # Save the figure for Short-term
    plt.savefig(f'{output_dir}/Figures/Fig_Emissions_OPGF_short_term_vs_H2s_{year}_{scenario}.png', dpi=300)

    plt.show()

    # Plot Total Supply and Demand on one axis
    plt.figure(figsize=(10, 6))
    
    # Condition check for whether Total Supply and Demand are nearly equal
    if sum(tech_econ_df['Total_supply'] - tech_econ_df['Total_demand']) < 0.1:
        # Plot both on the same line but with shifted markers for visibility
        plt.plot(tech_econ_df['H2 Proportion'], tech_econ_df['Total_supply'], label='Total Supply', color='red', marker='o', linestyle='-', markersize=6)
        
        # Slightly shift the x-values for the Total Demand plot to avoid overlap
        plt.plot(tech_econ_df['H2 Proportion'] + 0.005, tech_econ_df['Total_demand'], label='Total Demand', color='blue', marker='o', linestyle='--', markersize=6)
    else:
        # Default behavior with no shift
        plt.plot(tech_econ_df['H2 Proportion'], tech_econ_df['Total_supply'], label='Total Supply', color='red', marker='o', linestyle='-', markersize=6)
        plt.plot(tech_econ_df['H2 Proportion'], tech_econ_df['Total_demand'], label='Total Demand', color='blue', marker='o', linestyle='--', markersize=6)
    
    plt.xlabel('Hydrogen Proportion')
    plt.ylabel('Energy (MWh)')
    plt.title('Total Supply and Demand vs Hydrogen Proportion')
    
    plt.grid(True)
    plt.legend()
    
    # Save the figure
    plt.savefig(f'{output_dir}/Figures/Fig_Supply_Demand_vs_H2s_{year}_{scenario}.png', dpi=300)
    
    plt.show()


    # Plot Generation Mix (Energy Resource Allocation)
    data = OPGF_Gens_df.set_index('Player Type')
    
    plt.figure(figsize=(10, 6))
    plt.stackplot(data.columns, 
                  data.loc['GT'], 
                  data.loc['biomass'], 
                  data.loc['wind'], 
                  data.loc['solar'], 
                  data.loc['CHP'], 
                  data.loc['meth'], 
                  data.loc['P2G'], 
                  data.loc['G2P'], 
                  data.loc['EZ'], 
                  data.loc['FC'],
                  labels=['GT', 'Biomass', 'Wind', 'Solar', 'CHP', 'Methane', 'P2G', 'G2P', 'EZ', 'FC'],
                  colors=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', 
                          '#e377c2', '#7f7f7f', '#bcbd22','#00FFFF'])

    plt.title(f'Generation Mix vs Hydrogen Proportion')
    plt.xlabel('Hydrogen Proportion')
    plt.ylabel('Generation Capacity (MWh)')
    plt.legend(loc='upper left')
    plt.grid(True)
    plt.tight_layout()
    # plt.savefig(f'{output_dir}/Figures/Fig_Generation_Mix_vs_H2s_{year}_{scenario}.svg')
    plt.savefig(f'{output_dir}/Figures/Fig_Generation_Mix_vs_H2s_{year}_{scenario}.png', dpi=300)


    plt.show()
    
    print('Figures saved to Figures folder.')
    
    
    
        
def save_tech_econ_to_excel(writer, df, year):
    """ Save DataFrame to Excel file with a specific sheet name """
    df.to_excel(writer, sheet_name=str(year), index=False)
    

def create_Agg_gen_dataframes(Aggreg_gens_invs_gt, Aggreg_gens_invs_opgf, H2_prop, GT_Gens_df, OPGF_Gens_df):
    # Create GT_Gens_df
    temp_df_gt = Aggreg_gens_invs_gt[['Player Type', year+' Capacity']].copy()
    temp_df_gt.rename(columns={year+' Capacity': f'{round(H2_prop, 1)}'}, inplace=True)

    if GT_Gens_df.empty:
        GT_Gens_df = temp_df_gt
    else:
        GT_Gens_df = pd.merge(GT_Gens_df, temp_df_gt, on='Player Type', how='outer')

    # Create OPGF_Gens_df
    temp_df_opgf = Aggreg_gens_invs_opgf[['Player Type', year+' Capacity']].copy()
    temp_df_opgf.rename(columns={year+' Capacity': f'{round(H2_prop, 1)}'}, inplace=True)

    if OPGF_Gens_df.empty:
        OPGF_Gens_df = temp_df_opgf
    else:
        OPGF_Gens_df = pd.merge(OPGF_Gens_df, temp_df_opgf, on='Player Type', how='outer')

    return GT_Gens_df, OPGF_Gens_df


def aggregate_dic_tech_econ(dic_tech_econ, target_year):
    # Extract and concatenate dataframes for the target year
    dataframes_for_year = [df for (hour, year), df in dic_tech_econ.items() if year == target_year]
    combined_df = pd.concat(dataframes_for_year)
    
    # Keep `H2 Proportion` fixed and sum the rest
    agg_tech_econ_df = combined_df.groupby(level=0).agg({
        'H2 Proportion': 'first',  # Keep first occurrence
        **{col: 'sum' for col in combined_df.columns if col != 'H2 Proportion'}  # Sum others
    })
    
    return agg_tech_econ_df



def aggregate_dic_OPGF_GT(dic_OPGF_GT_H2):
    # Initialize an empty dictionary to store the aggregated results
    agg_dic_OPGF_GT_H2 = {}
    
    # Identify all unique years in the dictionary keys
    years = set(year for _, year in dic_OPGF_GT_H2.keys())
    
    # Loop over each year to aggregate values
    for year in years:
        # Filter DataFrames for the current year (removing hour_of_day restriction)
        dataframes_for_year = [
            df for (_, y), df in dic_OPGF_GT_H2.items() if y == year
        ]
        
        # Concatenate the DataFrames for this year, ignoring the index
        combined_df = pd.concat(dataframes_for_year, ignore_index=True)
        
        # Sum the generation values by grouping on "Player Type" (preserving the Player Type as index)
        agg_df = combined_df.groupby("Player Type", as_index=True).sum()
        
        # Rename the summed column to match the year for clarity
        agg_df.columns = [str(year)]
        
        # Add the aggregated DataFrame to the dictionary with the year as the key
        agg_dic_OPGF_GT_H2[year] = agg_df
    
    return agg_dic_OPGF_GT_H2

            

def calc_operation_cost_day(OPGF_H2_df, AggType_costs, Cost_H2, H2_prop, emissionCost):

    # Define conversion efficiencies
    efficiency_map = {
        'GT': 0.55,
        'CHP': 0.40,
        'FC': 0.60,
        'G2H': 0.75
    }

    # Set of types that have zero cost
    zero_cost_types = {'wind', 'solar', 'EZ', 'P2G', 'meth'}

    # Dictionary to store cost per player type
    player_costs = {}

    for _, row in OPGF_H2_df.iterrows():
        player_type = row['Player Type']
        output_mwh = row['2050']

        if player_type in zero_cost_types:
            total_cost = 0.0
        elif player_type in efficiency_map:
            if player_type == 'FC':
                total_cost = output_mwh * (Cost_H2 / efficiency_map['FC'])
            elif player_type == 'G2H':
                gas_price = AggType_costs.loc[AggType_costs['type'] == 'GT', 'costs'].iloc[0]
                total_cost = output_mwh * (gas_price / efficiency_map['G2H'])
            else:
                # GT and CHP: use marginal cost from Plyrs_aggcosts
                marginal_cost = AggType_costs.loc[AggType_costs['type'] == player_type, 'costs'].iloc[0]
                total_cost = output_mwh * marginal_cost
        else:
            marginal_cost = AggType_costs.loc[AggType_costs['type'] == player_type, 'costs'].iloc[0]
            total_cost = output_mwh * marginal_cost

        player_costs[player_type] = total_cost

    # Add emission cost as a separate line
    player_costs['EmissionCost'] = emissionCost

    # Total operational cost
    total_cost = sum(player_costs.values())

    # Build breakdown DataFrame
    breakdown_df = pd.DataFrame.from_dict(player_costs, orient='index', columns=['Values (£)'])
    breakdown_df['Values (M£/day)'] = breakdown_df['Values (£)'] / 1e6
    breakdown_df['Shares (%)'] = breakdown_df['Values (£)'] / total_cost * 100
    breakdown_df = breakdown_df[['Values (M£/day)', 'Shares (%)']].round(2)

    return total_cost, breakdown_df


# --- Function to save operation costs ---
def save_operation_cost_results(total_cost, breakdown_df, output_dir, scenario):
    """
    Add total operational cost as a new column to the existing 'tech_econ_analysis_{scenario}.xlsx'
    (after 'H2 Proportion' and before 'Cost_GT'), and save the breakdown separately.
    """
    
    excel_file = os.path.join(output_dir, f"Results/tech_econ_analysis_{scenario}.xlsx")
    breakdown_file = os.path.join(output_dir, f"Results/OperationalCost_Breakdown_{scenario}.xlsx")

    # --- 1 Load the existing Excel results file ---
    if os.path.exists(excel_file):
        df = pd.read_excel(excel_file)

        # Check that the required columns exist
        if 'H2 Proportion' not in df.columns or 'Cost_GT' not in df.columns:
            raise KeyError("The expected columns 'H2 Proportion' or 'Cost_GT' were not found in the Excel file.")
        
        # Insert new column right after 'H2 Proportion'
        insert_pos = df.columns.get_loc('H2 Proportion') + 1
        df.insert(insert_pos, 'Operational_Cost', total_cost)

        # Save back to the same Excel file (overwrite)
        with pd.ExcelWriter(excel_file, engine='openpyxl', mode='w') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        print(f" Added 'Operational_Cost' column to {excel_file}")

    else:
        # If the file does not exist, create a new one
        df = pd.DataFrame({'H2 Proportion': [None], 'Operational_Cost': [total_cost]})
        with pd.ExcelWriter(excel_file, engine='openpyxl', mode='w') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        print(f"File not found. Created a new one: {excel_file}")

    # --- 2️ Save breakdown DataFrame separately ---
    breakdown_df.to_excel(breakdown_file, index=True)
    print(f" Breakdown saved to: {breakdown_file}")





if __name__ == "__main__":
    # Initialize a dictionary to store results for plotting
    generation_data_by_intervention = {}
    energy_vectors_by_intervention = {}
    Outcomes_by_intervention = {}
    
    
    ## Define scenarios and hydrogen proportions
    # scenarios_list = ['Base_MC_Interv', 'HP_HB_Interv', 'HP_Interv', 'HB_Interv']
    # h2_proportions = ['0.0', '0.1', '0.2', '1.0']

    # scenarios_list = ['HB_Interv' ,'HP_Interv', 'HP_HB_Interv', 'Base_MC_Interv']
    # h2_proportions = ['1.0', '0.0', '0.1', '0.2']
    
    # scenarios_list = ['Base_MC_Interv']
    # scenarios_list = ['HP_HB_Interv']
    # scenarios_list = ['HP_Interv']
    # scenarios_list = ['HB_Interv']
    
    # STI_Scenarios = ['Scenario 1', 'Scenario 2', 'Scenario 3', 'Scenario 4',
    #                   'Scenario 5', 'Scenario 6', 'Scenario 7', 'Scenario 8'] # STI scenarios
    
    STI_Scenarios = ['Scenario 1', 'Scenario 2', 'Scenario 3', 'Scenario 4',
                      'Scenario 5', 'Scenario 6', 'Scenario 7', 'Scenario 8',
                      'Scenario 9', 'Scenario 10', 'Scenario 11', 'Scenario 12'] # STI scenarios
               
    # STI_Scenarios = ['Scenario 1']
    # STI_Scenarios = ['Scenario 2']
    # STI_Scenarios = ['Scenario 3']
    # STI_Scenarios = ['Scenario 4']
    # STI_Scenarios = ['Scenario 5']
    # STI_Scenarios = ['Scenario 6']
    # STI_Scenarios = ['Scenario 7']
    # STI_Scenarios = ['Scenario 8']
    # STI_Scenarios = ['Scenario 9']


    
    
    h2_proportions = ['0.0']
    # h2_proportions = ['0.1']
    # h2_proportions = ['0.2']
    # h2_proportions = ['1.0']
    
    
    
    # # Loop over scenarios and hydrogen proportions
    for STI_scenario in STI_Scenarios:
        
    # for HPHB_sw in scenarios_list:
        HPHB_sw = 'Base_Interv'

        for h2_plt in h2_proportions:
            
            if HPHB_sw=='Base_Interv':
                # intervention_levels = [0, 0.1] 
               if base_sw=='Base': 
                   intervention_levels = [0]
                   hydrogen_boiler_interventions = [0]
                   heat_pump_interventions = [0]
                   hydrogen_boilers = 0 #initial value
                   heat_pumps = 0
                   others = 1 - (heat_pumps + hydrogen_boilers)

                    
            # years = ['2025', '2030', '2035', '2040', '2045', '2050']
            
            # years = ['2025', '2030', '2045', '2050']
            
            # years = ['2025', '2050']
            
            # years = ['2035', '2050']

            # years = ['2025']
            
            # years = ['2030'] 
            
            # years = ['2035']   
            
            years = ['2050']
            
        
            # scenarios = ['FS', 'CT', 'LW', 'ST']
            # scenarios = ['LW']
            scenarios = ['FS']

            
            # Define the constant temperature system (Kelvin)
            temp_system = 288.15
            
            H2_prop = float(h2_plt)
            
            # hour_of_day = 0 # Input how many hours the model shall run
        
            # Outer loop for each scenario
            for scenario in scenarios:
                # # Prepare the output Excel writer for this scenario
                # output_dir = f'Output/Socio_TEA/MCP/{case_fg}/{scenario}'
                
                if ccs_fg == 0:
                    output_dir = f'Output/Res/H_{H2_prop}/Without_CCS/price_{price_fg}/{STI_scenario}/{scenario}'
                if ccs_fg == 1:
                    output_dir = f'Output/Res/H_{H2_prop}/With_CCS/price_{price_fg}/{STI_scenario}/{scenario}'
            
        
                output_file = f"{output_dir}/Results/tech_econ_analysis_{scenario}.xlsx"
                dir_outputs(output_dir, ['Figures', 'Results'])
                
                with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
                    
                    agg_dic_OPGF_H2={}; agg_dic_GT_H2={}
                    list_ele_demand=[]; list_gas_demand=[]
                    
                    # Inner loop for each year
                    for year in years:
                        
                            dic_tech_econ = {};
                            
                            # for hour_of_day in [0]:
                            # for hour_of_day in [8]:
                            # for hour_of_day in [20]:
                            # for hour_of_day in range(3):
                            for hour_of_day in range(24):
                                
                                # Import the system data for the given year and scenario
                                from HP_H2B_Social_Interv_multinet_NoT import data_import
                                systemData = data_import(year, scenario, STI_scenario, ws_limit)
                                
                                hydrogen_boilers = systemData['Hydrogen Consumption'].loc[f"{hour_of_day:02d}:00:00"].sum()
                                
                                # Run the techno-economic analysis for the given year, scenario, and system data
                                t = hour_of_day
                                tech_econ_df = run_techno_economic_analysis(t, year, scenario, systemData, temp_system, output_dir)
        
                                dic_tech_econ[hour_of_day, year] = tech_econ_df
                                
                            # Aggregate the hourly values to get a day values in a year
                            agg_tech_econ_df = aggregate_dic_tech_econ(dic_tech_econ, year)
                            agg_dic_OPGF_H2 = aggregate_dic_OPGF_GT(dic_OPGF_H2)
                            agg_dic_GT_H2 = aggregate_dic_OPGF_GT(dic_GT_H2)
                            
                            # Save the result for this year in the Excel file under the sheet named after the year
                            tech_econ_df=agg_tech_econ_df.copy()
                            save_tech_econ_to_excel(writer, tech_econ_df, year)
                            
                
                # Concatenate the aggregated dataframes and reset the index
                OPGF_H2_df = pd.concat(agg_dic_OPGF_H2.values(), axis=1).reset_index()
                GT_H2_df = pd.concat(agg_dic_GT_H2.values(), axis=1).reset_index()
                
                # Remove any duplicated columns
                OPGF_H2_df = OPGF_H2_df.loc[:, ~OPGF_H2_df.columns.duplicated()]
                GT_H2_df = GT_H2_df.loc[:, ~GT_H2_df.columns.duplicated()]
                
                # Reorder the year columns based on the 'years' list
                year_columns = [str(year) for year in years]  # Ensure the years are strings
                OPGF_H2_df = OPGF_H2_df[['Player Type'] + year_columns]
                GT_H2_df = GT_H2_df[['Player Type'] + year_columns]
                        
        
                # output_dir = 'Output/Socio_TEA/MCP'+'/'+case_fg+'/'+str(scenario)
                subdirs = ['Figures', 'Results']
                dir_outputs(output_dir, subdirs)
                 
                OPGF_H2_df.to_excel(f"{output_dir}/Results/OPGF_H2_{h2_plt}_{scenario}.xlsx", index=False)
                GT_H2_df.to_excel(f"{output_dir}/Results/GT_H2_{h2_plt}_{scenario}.xlsx", index=False)
                # plot_OPGF_H2(OPGF_H2_df, GT_H2_df, output_dir, scenario)
        
                excel_file = f'{output_dir}/Results/tech_econ_analysis_{scenario}.xlsx'
        
                
                H2_invs_outs = H2_prop
                # model.opex.extract_values()
        
        
                
                from plot_results_H2_prop import *
                plot_OPGF_outcomes_H2(excel_file, H2_invs_outs, OPGF_H2_df, GT_H2_df)
        
                # Load emissions data
                plot_generation_mix_bar(OPGF_H2_df, GT_H2_df, excel_file, output_dir, scenario)
                
                plot_hydrogen_mix_bar(excel_file, output_dir, scenario)
                
                total_cost, breakdown_df = calc_operation_cost_day(OPGF_H2_df, 
                                            AggType_costs, Cost_H2, H2_prop, emissionCost)
                
                print("Total Operational Cost (£):", total_cost)
                print(breakdown_df)
                
                save_operation_cost_results(total_cost, breakdown_df, output_dir, scenario)
                


        
            
    # End time
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Elapsed time: {elapsed_time} seconds")
    
                
        
        
        
        
