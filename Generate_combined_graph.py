#Import Relevant Modules
import re
from datetime import datetime, date
from time import sleep
import csv
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
from IPython.display import clear_output
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
import matplotlib.ticker as ticker
import json



def getDataFromWebMonitorFile(filename):
    records = []   # This list will store flattened log records

    with open(filename, "r") as file:

        # Loop over every line (each line is a JSON object)
        for line in file:

            # Convert JSON text into a Python dictionary
            data = json.loads(line)

            # Extract the nested "status" dictionary
            status = data["status"]

            # Extract the nested temperature dictionary
            temps = status["temperatures"]

            # --------------------------------------------
            # Step 2: Build a flat dictionary
            # --------------------------------------------
            # Pandas works best with flat key/value pairs
            record = {

                # Timestamp (String for now, converted later to datetime)
                "timestamp": data["timestamp"],

                # Convert VTRX pressure string ("1.20E+3") to float
                "vtrx_pressure": float(status["pressure"]),

                # Extract PMON temperatures
                "pmon1": temps["1"],
                "pmon2": temps["2"],
                "pmon3": temps["3"],
                "pmon4": temps["4"],
                "pmon5": temps["5"],
                "pmon6": temps["6"],

                # CCS temperatures
                "ccs_A_temp": status["clamp_temperature_A"],
                "ccs_B_temp": status["clamp_temperature_B"],
                "ccs_C_temp": status["clamp_temperature_C"],

                # CCS power supply readings
                "ccs_A_current": status["Cathode A - Heater Current:"],
                "ccs_B_current": status["Cathode B - Heater Current:"],
                "ccs_C_current": status["Cathode C - Heater Current:"],
                "ccs_A_voltage": status["Cathode A - Heater Voltage:"],
                "ccs_B_voltage": status["Cathode B - Heater Voltage:"],
                "ccs_C_voltage": status["Cathode C - Heater Voltage:"]
            }

            # Add record to list
            records.append(record)


    # --------------------------------------------
    # Step 3: Create the DataFrame
    # --------------------------------------------

    df = pd.DataFrame(records)

    # Now the data looks like a spreadsheet
    # each column = sensor
    # each row = timestamp


    # --------------------------------------------
    # Step 4: Convert columns to correct data types
    # --------------------------------------------

    df["timestamp"] = pd.to_datetime(df["timestamp"])


    pmon_columns = [
        "pmon1", "pmon2", "pmon3", "pmon4", "pmon5", "pmon6"
    ]

    for col in pmon_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")


    # --------------------------------------------
    # Step 6: Set timestamp as the index
    # --------------------------------------------
    # This makes plotting vs time very easy

    df = df.set_index("timestamp")

    return df



def get902bPressureData(filename):
    '''
    Extract pressure data from txt file

    @param:
        filename -> str
    
    @return:
        2D list of Time and Pressure -> list
    '''
    
    data = []                          
    pressure_pattern = re.compile(r'\[\d{4}-\d{2}-\d{2} (\d{2}:\d{2}:\d{2})\.\d{3}\] @\d{3}ACK(\d*\.\d*);FF', re.I)
    
    with open(filename, "r") as f:
        for line in f:
            p = pressure_pattern.search(line)
            if p:
                time_str = p.group(1)
                pressure = p.group(2)
                log_time = datetime.strptime(time_str, "%H:%M:%S").time()

                data.append((time_str, pressure))
    return data



def getCCSVoltageSetData(filename):
    '''
    Extract pressure data from txt file

    @param:
        filename -> str
    
    @return:
        2D list of Time and Pressure -> list
    '''
    
    data = []                          
    ccsVoltageSetPattern = re.compile(r'\[(\d{2}:\d{2}:\d{2})\].*?INFO: Voltage set to (\d*\.\d*)', re.I)
    
    with open(filename, "r") as f:
        for line in f:
            p = ccsVoltageSetPattern.search(line)
            if p:
                time_str = p.group(1)
                setPoint = p.group(2)
                log_time = datetime.strptime(time_str, "%H:%M:%S").time()

                data.append((time_str, setPoint))
    return data



def getCCSCurrentSetData(filename):
    '''
    Extract pressure data from txt file

    @param:
        filename -> str
    
    @return:
        2D list of Time and Pressure -> list
    '''
    
    data = []                          
    ccsCurrentSetPattern = re.compile(r'\[(\d{2}:\d{2}:\d{2})\].*?INFO: Current set to (\d*\.\d*)', re.I)
    
    with open(filename, "r") as f:
        for line in f:
            p = ccsCurrentSetPattern.search(line)
            if p:
                time_str = p.group(1)
                setPoint = p.group(2)
                log_time = datetime.strptime(time_str, "%H:%M:%S").time()

                data.append((time_str, setPoint))
    return data



def getHVData(filename):
    '''
    Extract pressure data from txt file

    @param:
        filename -> str
    
    @return:
        2D list of time and HV current -> list
    '''
    
    data = []                          
    pressure_pattern = re.compile(r'\[\d{4}-\d{2}-\d{2} (.*?)\] Set: -?(\d{1,4}) V,  HV: -?(\d{1,4}) V,  I: -?(\d{1,2}\.\d{2,3}) mA', re.I)
    
    with open(filename, "r") as f:
        for line in f:
            p = pressure_pattern.search(line)
            if p:
                time_str = p.group(1)
                a0 = (float(p.group(3)))
                a1 = (float(p.group(2)))
                a2 = (float(p.group(4)))
                log_time = datetime.strptime(time_str, "%H:%M:%S.%f").time()

                data.append((time_str, a0, a1, a2))

    return data



def getGraph(teraTerm_log_file902b, teraTerm_log_file20kv, teraTerm_log_file3kv, teraTerm_log_filePos1kv, teraTerm_log_fileNeg1kv, 
             dashboard_log_file, webMonitorFile, enable, figureWidth, figureHeight, 
             start_time='00:00:01', end_time='23:59:59'):
    '''
    Displays Graph of PMON, pressure, and HV current (beam current) using multiple panes in one graph window
    Takes 

    args:
        pmon data : list of data -> list
        pressure_data : list of data -> list
        hvCurrent_data : list of data -> list
    
    '''

    # Extract data from web monitor file and break up columns into different graphs
    webMonitor_df = getDataFromWebMonitorFile(webMonitorFile)
    pmon_columns = ["pmon1", "pmon2", "pmon3", "pmon4", "pmon5", "pmon6"]
    pressure_columns = ["vtrx_pressure"] # Not including 902b yet because it's not in the webmonitor file
    ccs_temp_columns = ["ccs_A_temp", "ccs_B_temp", "ccs_C_temp"]
    ccs_voltage_columns = ["ccs_A_voltage", "ccs_B_voltage", "ccs_C_voltage"]
    ccs_current_columns = ["ccs_A_current", "ccs_B_current", "ccs_C_current"]

    # Put the graph column lists into a new data structure
    graph_columns = {
        'PMON temperatures': pmon_columns,
        'CCS temperatures': ccs_temp_columns,
        'Chamber pressure': pressure_columns,
        'CCS voltages': ccs_voltage_columns,
        'CCS currents': ccs_current_columns
    }

    graph_units = {
        'PMON temperatures': "°C",
        'CCS temperatures': "°C",
        'Chamber pressure': "mbar",
        'CCS voltages': "V",
        'CCS currents': "A"
    }

    graphs_enabled = {
        'PMON temperatures': False,
        'CCS temperatures': False,
        'Chamber pressure': False,
        'CCS voltages': False,
        'CCS currents': False
    }

    legacy_graph_columns = {
        '20kV PSU voltage': ['hvActualVolt20kv', 'hvSetVolt20kv'],
        '20kV PSU current': ['hvCurrent20kv'],
        '3kV PSU voltage': ['hvActualVolt3kv', 'hvSetVolt3kv'],
        '3kV PSU current': ['hvCurrent3kv'],
        'Pos1kV PSU voltage': ['hvActualVoltPos1kv', 'hvSetVoltPos1kv'],
        'Pos1kV PSU current': ['hvCurrentPos1kv'],
        'Neg1kV PSU voltage': ['hvActualVoltNeg1kv', 'hvSetVoltNeg1kv'],
        'Neg1kV PSU current': ['hvCurrentNeg1kv'],
        'CCS Set Voltage': ['ccsSetVoltage'],
        'CCS Set Current': ['ccsSetCurrent']
    }

    legacy_graph_units = {
        '20kV PSU voltage': "V",
        '20kV PSU current': "mA",
        '3kV PSU voltage': "V",
        '3kV PSU current': "mA",
        'Pos1kV PSU voltage': "V",
        'Pos1kV PSU current': "mA",
        'Neg1kV PSU voltage': "V",
        'Neg1kV PSU current': "mA",
        'CCS Set Voltage': "V",
        'CCS Set Current': "A"
    }

    legacy_graphs_enabled = {
        '20kV PSU voltage':   False,
        '20kV PSU current':   False,
        '3kV PSU voltage':    False,
        '3kV PSU current':    False,
        'Pos1kV PSU voltage': False,
        'Pos1kV PSU current': False,
        'Neg1kV PSU voltage': False,
        'Neg1kV PSU current': False,
        'CCS Set Voltage':    False,
        'CCS Set Current':    False
    }



    pressure902b_raw = get902bPressureData(teraTerm_log_file902b)
    hv_20kv_raw = getHVData(teraTerm_log_file20kv)
    hv_3kv_raw = getHVData(teraTerm_log_file3kv)
    hv_Pos1kv_raw = getHVData(teraTerm_log_filePos1kv)
    hv_Neg1kv_raw = getHVData(teraTerm_log_fileNeg1kv)
    ccsSetCurrent_raw = getCCSCurrentSetData(dashboard_log_file)
    ccsSetVoltage_raw = getCCSVoltageSetData(dashboard_log_file)
    
    # Filter by time range
    start_dt = pd.to_datetime(start_time)
    end_dt = pd.to_datetime(end_time)

    # Convert all other datasets to DataFrames and convert values to floats
    def to_df(data, columns):
        df = pd.DataFrame(data, columns=columns)
        df['Time'] = pd.to_datetime(df['Time'].astype(str), format = "mixed")
        for col in range(1, len(columns)) :
            df[columns[col]] = pd.to_numeric(df[columns[col]])
        return df[(df["Time"] >= start_dt) & (df["Time"] <= end_dt)]

    pressure902b_df = to_df(pressure902b_raw, ["Time", "Pressure (mbar)"])
    hv20kv_df = to_df(hv_20kv_raw, ["Time", "hvActualVolt20kv", "hvSetVolt20kv", "hvCurrent20kv"])
    hv3kv_df = to_df(hv_3kv_raw, ["Time", "hvActualVolt3kv", "hvSetVolt3kv", "hvCurrent3kv"])
    hvPos1kv_df = to_df(hv_Pos1kv_raw, ["Time", "hvActualVoltPos1kv", "hvSetVoltPos1kv", "hvCurrentPos1kv"])
    hvNeg1kv_df = to_df(hv_Neg1kv_raw, ["Time", "hvActualVoltNeg1kv", "hvSetVoltNeg1kv", "hvCurrentNeg1kv"])
    ccsSetCurrent_df = to_df(ccsSetCurrent_raw, ["Time", "ccsSetCurrent"])
    ccsSetVoltage_df = to_df(ccsSetVoltage_raw, ["Time", "ccsSetVoltage"])

    legacy_graph_dataframes = {
        '20kV PSU voltage':   hv20kv_df,
        '20kV PSU current':   hv20kv_df,
        '3kV PSU voltage':    hv3kv_df,
        '3kV PSU current':    hv3kv_df,
        'Pos1kV PSU voltage': hvPos1kv_df,
        'Pos1kV PSU current': hvPos1kv_df,
        'Neg1kV PSU voltage': hvNeg1kv_df,
        'Neg1kV PSU current': hvNeg1kv_df,
        'CCS Set Voltage':    ccsSetVoltage_df,
        'CCS Set Current':    ccsSetCurrent_df
    }

    # Count the number of non-empty data frames we have
    numPlots = 0

    for entry in graph_columns :
        for col in graph_columns[entry] :
            if enable[col] and not(webMonitor_df[col].empty) :
                numPlots += 1
                graphs_enabled[entry] = True
                break # Only count 1 plot for each graph type, even if multiple columns are enabled

    # Still using the legacy hacky method for data that is not in the webmonitor file

    if ((enable['902b_pressure'] and not (pressure902b_df.empty))):
        numPlots += 1

    for entry in legacy_graph_columns :
        for col in legacy_graph_columns[entry] :
            dataframe = legacy_graph_dataframes[entry]
            if enable[col] and not(dataframe[col].empty) :
                numPlots += 1
                legacy_graphs_enabled[entry] = True
                break # Only count 1 plot for each graph type, even if multiple columns are enabled


    ###################
    # Graph the data! #
    ###################
    curr_plot_num = 0
    
    # Lookup table for numPlots vs num_y_ticks
    num_y_ticks = [
        0, # 0 plots
        0, # 1 plot (can't do just 1 plot with this method)
        20, # 2 plots
        10, # 3 plots
        10, # 4 plots
        7, # 5 plots
        3, # 6 plots
        3, # 7 plots
        3, # 8 plots
        3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3 
    ]   
    
    if(numPlots < 2) :
        print("Number of non-empty plots must be >= 2!")
        return

    # Set graph details, including figure aspect ratio and graph height ratios
    fig, axs = plt.subplots(numPlots, 1, figsize=(figureWidth, figureHeight), sharex=True)

    # Plot all web monitor data
    for entry in graph_columns :
        if(graphs_enabled[entry]) :
            for col in graph_columns[entry] :
            
                if enable[col] and not(webMonitor_df[col].empty) :
                    label = col + ' (' +  webMonitor_df[col].iloc[-1].astype(str) + graph_units[entry] + ')'
                    axs[curr_plot_num].plot(webMonitor_df[col], label=label)
        
            axs[curr_plot_num].set_ylabel(entry)
            curr_plot_num += 1

    # Plot all legacy data
    for entry in legacy_graph_columns :
        if(legacy_graphs_enabled[entry]) :
            for col in legacy_graph_columns[entry] :
                dataframe = legacy_graph_dataframes[entry]
                if enable[col] and not(dataframe[col].empty) :
                    label = col + ' (' +  dataframe[col].iloc[-1].astype(str) + legacy_graph_units[entry] + ')'
                    axs[curr_plot_num].plot(dataframe['Time'], dataframe[col], label=label)

            axs[curr_plot_num].set_ylabel(entry)
            curr_plot_num += 1

    # Format Y axes
    for x in range(0, numPlots) :
        axs[x].legend(loc='upper left')
        axs[x].grid(True)
        axs[x].yaxis.set_major_locator(ticker.MaxNLocator(nbins=num_y_ticks[numPlots]))


    # Format x axis
    axs[numPlots-1].xaxis.set_major_locator(ticker.MaxNLocator(nbins=40))
    axs[numPlots-1].xaxis.set_major_formatter(mdates.DateFormatter('%I:%M:%S'))
    for label in axs[numPlots-1].get_xticklabels():
        label.set_rotation(45)       # Rotate the label
        label.set_ha('right')        # Align the label to the right of the tick mark
    axs[numPlots-1].set_xmargin(0)

    plt.tight_layout(h_pad=0, w_pad=0, rect=[0, 0.03, 1, 0.95])
    plt.show()



# Main Cell for graph generation


# Log file location on laptop: 'C:/Users/Experiment/EBEAM_dashboard/EBEAM-Dashboard-Logs/'
# Tera term log file location on laptop: 'C:/Users/Experiment/cbmark_logger/Tera Term logs'

# Enter your Ebeam dashboard and Tera Term log files here and 

# === Uncomment the block of file paths below to use specific files ===
dashboard_log_file = "Data samples/log_2025-07-08_14-18-35.txt"
teraTerm_log_file902b = "Data samples/Blank.txt"
teraTerm_log_file20kv = "Data samples/Tera Term log 2025-07-07.txt"
teraTerm_log_file3kv = "Data samples/Tera Term log 2025-07-07.txt"
teraTerm_log_filePos1kv = "Data samples/Tera Term log 2025-07-07.txt"
teraTerm_log_fileNeg1kv = "Data samples/Tera Term log 2025-07-07.txt"
blank_file = "Data samples/Blank.txt"
# ============================================================

run = True

while run :
    # Uncomment this if you want the loop to run once
    run = False

    # Pick the most recently edited Tera Term log files

    # =========== Comment out the block below to use specific files ===========
    # teraTerm_files = glob.glob("C:/Users/Experiment/cbmark_logger/Tera Term 20kv HV Monitor logs/*")
    # teraTerm_log_file20kv = max(teraTerm_files, key=os.path.getctime)

    # teraTerm_files = glob.glob("C:/Users/Experiment/cbmark_logger/Tera Term 3kv HV Monitor logs/*")
    # teraTerm_log_file3kv = max(teraTerm_files, key=os.path.getctime)

    # teraTerm_files = glob.glob("C:/Users/Experiment/cbmark_logger/Tera Term +1kv HV Monitor logs/*")
    # teraTerm_log_filePos1kv = max(teraTerm_files, key=os.path.getctime)

    # teraTerm_files = glob.glob("C:/Users/Experiment/cbmark_logger/Tera Term -1kv HV Monitor logs/*") 
    # teraTerm_log_fileNeg1kv = max(teraTerm_files, key=os.path.getctime)

    # teraTerm_files = glob.glob("C:/Users/Experiment/cbmark_logger/902b Logs/*") 
    # teraTerm_log_file902b = max(teraTerm_files, key=os.path.getctime)

    # # Pick the most recently edited dashboard log file
    # dashboard_files = glob.glob(os.path.join("C:/Users/Experiment/EBEAM_dashboard/EBEAM-Dashboard-Logs/", 'log_*'))
    # dashboard_log_file = max(dashboard_files, key=os.path.getctime)
    # ============================================================================

    # I strongly encourage playing with these aspect ratio settings to fit your screen and VSCode setup
    figureWidth = 20
    figureHeight = 11

    # You need to have at least two of these be non-empty for my method of graphing to work
    # To customize the graph, just set whichever lines you want drawn to a 1 and whichever ones you don't to a 0
    # In VSCode, you can use the middle mouse button to edit multiple lines simultaneously, which is great for setting these
    enable = {
        'vtrx_pressure' :      1,
        '902b_pressure' :      0,
            
        'pmon1' :              1,
        'pmon2' :              1,
        'pmon3' :              1,
        'pmon4' :              1,
        'pmon5' :              1,
        'pmon6' :              1,

        'ccs_A_temp' :         0,
        'ccs_B_temp' :         0,
        'ccs_C_temp' :         0,

        'hvSetVolt80kv' :      0,
        'hvActualVolt80kv' :   0,
        'hvCurrent80kv' :      0,
      
        'hvSetVolt20kv' :      0,
        'hvActualVolt20kv' :   0,
        'hvCurrent20kv' :      0,
          
        'hvSetVolt3kv' :       0,
        'hvActualVolt3kv' :    0,
        'hvCurrent3kv' :       0,
          
        'hvSetVoltPos1kv' :    0,
        'hvActualVoltPos1kv' : 0,
        'hvCurrentPos1kv' :    0,
    
        'hvSetVoltNeg1kv' :    0,
        'hvActualVoltNeg1kv' : 0,
        'hvCurrentNeg1kv' :    0,
        
        'ccs_A_voltage' :      0,
        'ccs_B_voltage' :      0,
        'ccs_C_voltage' :      0,
  
        'ccs_A_current' :      0,
        'ccs_B_current' :      0,
        'ccs_C_current' :      0,

        'ccsSetCurrent' :      0,
        'ccsSetVoltage' :      0
        
    }



    # Call the function to generate the graph by grabbing lists of data and shoving it in along with the enable matrix
    getGraph(
                teraTerm_log_file902b,
                teraTerm_log_file20kv,
                teraTerm_log_file3kv,
                teraTerm_log_filePos1kv,
                teraTerm_log_fileNeg1kv,
                dashboard_log_file,
                "webMonitor_log.txt",
                enable,
                figureWidth,
                figureHeight
            )
    
    # Clear the screen right before displaying a new graph (no flashing if that's the only output)
    clear_output(True)