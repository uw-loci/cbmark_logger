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

# Column lists for each subplot
graph_columns = {
    'PMON temperatures': ["pmon1", "pmon2", "pmon3", "pmon4", "pmon5", "pmon6"],
    'CCS temperatures': ["ccs_A_temp", "ccs_B_temp", "ccs_C_temp"],
    'Chamber pressure': ["vtrx_pressure"], # Not including 902b yet because it's not in the webmonitor file,
    'CCS voltages': ["ccs_A_voltage", "ccs_B_voltage", "ccs_C_voltage"],
    'CCS currents': ["ccs_A_current", "ccs_B_current", "ccs_C_current"]
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



# This function extracts data from the web monitor log file, which is in JSON format
# It outputs a pandas DataFrame with a timestamp index and columns for each sensor reading
def getDataFromWebMonitorFile(filename):
    records = []   # This list will store flattened log records

    with open(filename, "r") as file:

        for line in file:

            data = json.loads(line)

            # Extract the nested dictionaries
            status = data["status"]
            temps = status["temperatures"]

            # Step 2: Build a flat dictionary (table style)
            record = {

                # Timestamp (String for now, converted later to datetime)
                "timestamp": data["timestamp"],

                # Convert VTRX pressure string ("1.20E+3") to float
                "vtrx_pressure": status["pressure"],

                # Define key:value pairs for sensor readings
                "pmon1": temps["1"],
                "pmon2": temps["2"],
                "pmon3": temps["3"],
                "pmon4": temps["4"],
                "pmon5": temps["5"],
                "pmon6": temps["6"],

                "ccs_A_temp": status["clamp_temperature_A"],
                "ccs_B_temp": status["clamp_temperature_B"],
                "ccs_C_temp": status["clamp_temperature_C"],

                "ccs_A_current": status["Cathode A - Heater Current:"],
                "ccs_B_current": status["Cathode B - Heater Current:"],
                "ccs_C_current": status["Cathode C - Heater Current:"],
                "ccs_A_voltage": status["Cathode A - Heater Voltage:"],
                "ccs_B_voltage": status["Cathode B - Heater Voltage:"],
                "ccs_C_voltage": status["Cathode C - Heater Voltage:"]
            }

            records.append(record)

    # Create the table style dataframe from the list of records
    # each column = sensor
    # each row = timestamp
    df = pd.DataFrame(records)


    # Convert timestamp column to datetime objects for easier plotting
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Coerce VTRX pressure to numeric, changing error strings to NaN
    df["vtrx_pressure"] = pd.to_numeric(df["vtrx_pressure"], errors="coerce")

    # Convert PMON columns to numeric, changing error strings to NaN
    # PMON data contains some non-numeric values, which this fixes
    pmon_columns = [
        "pmon1", "pmon2", "pmon3", "pmon4", "pmon5", "pmon6"
    ]

    for col in pmon_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")


    # Set timestamp as the index to make plotting easier
    df = df.set_index("timestamp")

    return df


# This function extracts pressure data from the 902b log file, which is in a custom text format
# It outputs a dataframe with a timestamp index and a column for pressure readings

# This is a remnant of IC's first revision of the code, which was based on code from ND
# This function uses regex, so it is a bit slow and should be called on only if needed (i.e. if the 902b pressure graph is enabled)
# If it stops parsing correctly, print the lines being read and use regex101.com to debug the regex string
def get902bPressureData(filename):
    '''
    Extract pressure data from txt file

    @param:
        filename -> str
    
    @return:
        2D list of Time and Pressure -> list
    '''
    
    # Create an empty list to store the extracted data before converting it to a DataFrame
    data = []                          
    # Regex pattern to parse lines in the 902b log file for timestamps and pressure readings
    regex_pattern = re.compile(r'\[\d{4}-\d{2}-\d{2} (\d{2}:\d{2}:\d{2})\.\d{3}\] @\d{3}ACK(\d*\.\d*);FF', re.I)
    # Columns for the DataFrame
    columns=["Time", "Pressure (mbar)"]
    
    with open(filename, "r") as f:
        for line in f:
            p = regex_pattern.search(line)
            if p:
                time_str = p.group(1)
                pressure = p.group(2)

                data.append((time_str, pressure))
                
    # Convert the list of tuples into a DataFrame and convert data types
    df = pd.DataFrame(data, columns=columns)
    if(not df.empty) :
        df['Time'] = pd.to_datetime(df['Time'].astype(str), format = "mixed")

        for col in range(1, len(columns)) :
            df[columns[col]] = pd.to_numeric(df[columns[col]])

    return df

# This function extracts ccs voltage set data from the dashboard log file
# It outputs a dataframe with a timestamp index and a column for voltage set point readings

# This is a remnant of IC's first revision of the code, which was based on code from ND
# This function uses regex on a huge file, so it is pretty slow and should be called on only if needed (i.e. if the CCS voltage set graph is enabled)
# If it stops parsing correctly, print the lines being read and use regex101.com to debug the regex string
def getCCSVoltageSetData(filename):
    '''
    Extract voltage data from txt file

    @param:
        filename -> str
    
    @return:
        2D list of Time and Voltage -> list
    '''
    
    # Create an empty list to store the extracted data before converting it to a DataFrame
    data = []                
    # Regex pattern to parse lines in the dashboard file for timestamps and voltage set points
    regex_pattern = re.compile(r'\[(\d{2}:\d{2}:\d{2})\].*?INFO: Voltage set to (\d*\.\d*)', re.I)
    # Columns for the DataFrame
    columns=["Time", "ccsSetVoltage"]

    with open(filename, "r") as f:
        for line in f:
            p = regex_pattern.search(line)
            if p:
                time_str = p.group(1)
                setPoint = p.group(2)

                data.append((time_str, setPoint))

    # Convert the list of tuples into a DataFrame and convert data types
    df = pd.DataFrame(data, columns=columns)
    if(not df.empty) :
        df['Time'] = pd.to_datetime(df['Time'].astype(str), format = "mixed")

        for col in range(1, len(columns)) :
            df[columns[col]] = pd.to_numeric(df[columns[col]])

    return df

# This function extracts ccs current set data from the dashboard log file
# It outputs a dataframe with a timestamp index and a column for current set point readings

# This is a remnant of IC's first revision of the code, which was based on code from ND
# This function uses regex on a huge file, so it is pretty slow and should be called on only if needed (i.e. if the CCS current set graph is enabled)
# If it stops parsing correctly, print the lines being read and use regex101.com to debug the regex string
def getCCSCurrentSetData(filename):
    '''
    Extract current data from txt file

    @param:
        filename -> str
    
    @return:
        2D list of Time and Current -> list
    '''
    
    # Create an empty list to store the extracted data before converting it to a DataFrame
    data = []                          
    # Regex pattern to parse lines in the dashboard file for timestamps and current set points
    regex_pattern = re.compile(r'\[(\d{2}:\d{2}:\d{2})\].*?INFO: Current set to (\d*\.\d*)', re.I)
    # Columns for the DataFrame
    columns=["Time", "ccsSetCurrent"]
    
    with open(filename, "r") as f:
        for line in f:
            p = regex_pattern.search(line)
            if p:
                time_str = p.group(1)
                setPoint = p.group(2)

                data.append((time_str, setPoint))


    # Convert the list of tuples into a DataFrame and convert data types
    df = pd.DataFrame(data, columns=columns)
    if(not df.empty) :
        df['Time'] = pd.to_datetime(df['Time'].astype(str), format = "mixed")

        for col in range(1, len(columns)) :
            df[columns[col]] = pd.to_numeric(df[columns[col]])

    return df





# This function extracts HV PSU data from Tera Term HV Monitor log files, which are in a custom text format
# It outputs a dataframe with a timestamp index and columns for voltage set point, voltage actual, and current readings for the specified PSU

# This is a remnant of IC's first revision of the code, which was based on code from ND
# This function uses regex on a huge file, so it is pretty slow and should be called on only if needed (i.e. if one of the HV graphs are enabled)
# If it stops parsing correctly, print the lines being read and use regex101.com to debug the regex string
def getHVData(filename, psu_type = "3kv"):
    '''
    Extract pressure data from txt file

    @param:
        filename -> str
    
    @return:
        2D list of time and HV current -> list
    '''
    
    # Create an empty list to store the extracted data before converting it to a DataFrame
    data = []                          
    # Regex pattern to parse lines in the Tera Term log file for timestamps and HV PSU readings (voltage set point, voltage actual, and current)
    regex_pattern = re.compile(r'\[\d{4}-\d{2}-\d{2} (.*?)\] Set: -?(\d{1,4}) V,  HV: -?(\d{1,4}) V,  I: -?(\d{1,2}\.\d{2,3}) mA', re.I)
    # Columns for the DataFrame
    columns=["Time", f"hvActualVolt{psu_type}", f"hvSetVolt{psu_type}", f"hvCurrent{psu_type}"]
    
    with open(filename, "r") as f:
        for line in f:
            p = regex_pattern.search(line)
            if p:
                time_str = p.group(1)
                a0 = (float(p.group(3)))
                a1 = (float(p.group(2)))
                a2 = (float(p.group(4)))
                log_time = datetime.strptime(time_str, "%H:%M:%S.%f").time()

                data.append((time_str, a0, a1, a2))

    # Convert the list of tuples into a DataFrame and convert data types
    df = pd.DataFrame(data, columns=columns)
    if(not df.empty) :
        df['Time'] = pd.to_datetime(df['Time'].astype(str), format = "mixed")

        for col in range(1, len(columns)) :
            df[columns[col]] = pd.to_numeric(df[columns[col]])

    return df



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
    pressure902b_df = get902bPressureData(teraTerm_log_file902b)
    hv20kv_df = getHVData(teraTerm_log_file20kv, "20kv")
    hv3kv_df = getHVData(teraTerm_log_file3kv, "3kv")
    hvPos1kv_df = getHVData(teraTerm_log_filePos1kv, "Pos1kv")
    hvNeg1kv_df = getHVData(teraTerm_log_fileNeg1kv, "Neg1kv")
    ccsSetCurrent_df = getCCSCurrentSetData(dashboard_log_file)
    ccsSetVoltage_df = getCCSVoltageSetData(dashboard_log_file)

    # Filter by time range
    start_dt = pd.to_datetime(start_time)
    end_dt = pd.to_datetime(end_time)


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
        'vtrx_pressure' :      0,
        '902b_pressure' :      0,
            
        'pmon1' :              0,
        'pmon2' :              0,
        'pmon3' :              0,
        'pmon4' :              0,
        'pmon5' :              0,
        'pmon6' :              0,

        'ccs_A_temp' :         0,
        'ccs_B_temp' :         0,
        'ccs_C_temp' :         0,

        'hvSetVolt80kv' :      0,
        'hvActualVolt80kv' :   0,
        'hvCurrent80kv' :      0,
      
        'hvSetVolt20kv' :      0,
        'hvActualVolt20kv' :   0,
        'hvCurrent20kv' :      0,
          
        'hvSetVolt3kv' :       1,
        'hvActualVolt3kv' :    1,
        'hvCurrent3kv' :       1,
          
        'hvSetVoltPos1kv' :    0,
        'hvActualVoltPos1kv' : 0,
        'hvCurrentPos1kv' :    0,
    
        'hvSetVoltNeg1kv' :    0,
        'hvActualVoltNeg1kv' : 0,
        'hvCurrentNeg1kv' :    0,
        
        'ccs_A_voltage' :      1,
        'ccs_B_voltage' :      1,
        'ccs_C_voltage' :      1,
  
        'ccs_A_current' :      1,
        'ccs_B_current' :      1,
        'ccs_C_current' :      1,

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
