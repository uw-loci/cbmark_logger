"""
Generate_combined_graph.py

Developer overview (how the live graph works)
---------------------------------------------
This script continuously reads recent log data from disk and updates a Matplotlib
window with multiple subplots.

High-level loop:
1) Background thread (`ThreadPoolExecutor`) reads/parses log files (disk I/O + regex + JSON).
2) Main thread runs the GUI event loop via `plt.pause(refresh_sec)`.
3) When new data is ready, we update existing `Line2D` artists via `line.set_data(...)`
   instead of clearing/re-plotting (which is slower and makes interaction lag).
4) To keep performance stable as logs grow, we only parse the *tail* of each log file
   and then apply a rolling time window + point cap before plotting.

Key performance principles used here:
- Avoid `ax.clear()` and repeated `ax.plot(...)` during live updates.
- Avoid repeated `tight_layout()` / formatter setup every refresh; do it on rebuild only.
- Bound work per refresh with `--window-min`, `--max-points`, and tail-line limits.

See `DEVELOPER_MATPLOTLIB.md` for a Matplotlib-focused explanation of the commands used.
"""

#Import Relevant Modules
import argparse
import re
from datetime import datetime, date
import time
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
from concurrent.futures import ThreadPoolExecutor

REFRESH_SECONDS = 3
RUN_ONCE = False
DEFAULT_WINDOW_MINUTES = 60
DEFAULT_MAX_POINTS = 5000
DEFAULT_WEB_TAIL_LINES = 5000
DEFAULT_TERATERM_TAIL_LINES = 20000
DEBUG_TIMING = False

# Log file location on laptop: 'C:/Users/Experiment/EBEAM_dashboard/EBEAM-Dashboard-Logs/'
# Tera term log file location on laptop: 'C:/Users/Experiment/cbmark_logger/Tera Term logs'

# ================= File paths for log files =================
blank_path = "Data samples/Blank.txt"
dashboard_log_path      = "Data samples/log_2025-07-08_14-18-35.txt"
teraTerm_log_path902b   = "Data samples/Blank.txt"
teraTerm_log_path20kv   = "Data samples/Tera Term log 2025-07-07.txt"
teraTerm_log_path3kv    = "Data samples/Tera Term log 2025-07-07.txt"
teraTerm_log_pathPos1kv = "Data samples/Tera Term log 2025-07-07.txt"
teraTerm_log_pathNeg1kv = "Data samples/Tera Term log 2025-07-07.txt"
webMonitor_path         = "webMonitor_log.txt"
# ============================================================

graph_settings = {
    'PMON temperatures': {
        "lines" : ["pmon1", "pmon2", "pmon3", "pmon4", "pmon5", "pmon6"],
        "unit": "°C",
        "enabled": 1
    },
    'CCS temperatures': {
        "lines": ["ccs_A_temp", "ccs_B_temp", "ccs_C_temp"],
        "unit": "°C",
        "enabled": 1
    },
    'Chamber pressure': {
        "lines": ["vtrx_pressure"],
        "unit": "mbar",
        "enabled": 1
    },
    'CCS voltages': {
        "lines": ["ccs_A_voltage", "ccs_B_voltage", "ccs_C_voltage"],
        "unit": "V",
        "enabled": 1
    },
    'CCS currents': {
        "lines": ["ccs_A_current", "ccs_B_current", "ccs_C_current"],
        "unit": "A",
        "enabled": 1
    }
}

legacy_graph_settings = {
    '20kV PSU voltage':   {
        "lines": ['hvActualVolt20kv', 'hvSetVolt20kv'],
        "unit": "V",
        "enabled": False
    },
    '20kV PSU current':   {
        "lines": ['hvCurrent20kv'],
        "unit": "mA",
        "enabled": False
    },
    '3kV PSU voltage':    {
        "lines": ['hvActualVolt3kv', 'hvSetVolt3kv'],
        "unit": "V",
        "enabled": False
    },
    '3kV PSU current':    {
        "lines": ['hvCurrent3kv'],
        "unit": "mA",
        "enabled": False
    },
    'pos1kV PSU voltage': {
        "lines": ['hvActualVoltPos1kv', 'hvSetVoltPos1kv', 'hvActualVoltNeg1kv', 'hvSetVoltNeg1kv'],
        "unit": "V",
        "enabled": False
    },
    'neg1kV PSU current': {
        "lines": ['hvCurrentPos1kv', 'hvCurrentNeg1kv'],
        "unit": "mA",
        "enabled": False
    },
        'pos1kV PSU voltage': {
        "lines": ['hvActualVoltNeg1kv', 'hvSetVoltNeg1kv'],
        "unit": "V",
        "enabled": False
    },
    'neg1kV PSU current': {
        "lines": ['hvCurrentNeg1kv'],
        "unit": "mA",
        "enabled": False
    },
    # CCS Set voltage/current logging have been changed since the original code was written
    # These settings do not currently work
    # 'CCS Set Voltage':    {
    #     "lines": ['ccsSetVoltage'],
    #     "unit": "V",
    #     "enabled": False
    # },
    # 'CCS Set Current':    {
    #     "lines": ['ccsSetCurrent'],
    #     "unit": "A",
    #     "enabled": False
    # }
}

# Lookup for how many y-axis ticks to use based on the number of plots
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


def parse_args():
    """
    Parse developer-facing CLI options.

    These flags are intentionally the primary "tuning knobs" so users do not have
    to edit this file just to adjust responsiveness or the displayed history size.
    """
    parser = argparse.ArgumentParser(description="Live combined graph for CBMARK logs")
    parser.add_argument("--refresh-sec", type=float, default=REFRESH_SECONDS, help="Seconds between plot refreshes")
    parser.add_argument(
        "--window-min",
        type=float,
        default=DEFAULT_WINDOW_MINUTES,
        help="Rolling time window (minutes) to display for live plotting",
    )
    parser.add_argument(
        "--max-points",
        type=int,
        default=DEFAULT_MAX_POINTS,
        help="Hard cap of points per series after windowing (keeps redraw fast)",
    )
    parser.add_argument(
        "--web-tail-lines",
        type=int,
        default=DEFAULT_WEB_TAIL_LINES,
        help="How many lines from the end of webMonitor log to parse each refresh",
    )
    parser.add_argument(
        "--teraterm-tail-lines",
        type=int,
        default=DEFAULT_TERATERM_TAIL_LINES,
        help="How many lines from the end of each Tera Term log to parse each refresh",
    )
    parser.add_argument("--debug-timing", action="store_true", help="Print basic timing diagnostics")
    return parser.parse_args()


def read_last_lines(path, max_lines, encoding="utf-8"):
    """
    Efficiently read up to `max_lines` lines from the end of a text file.
    Returns a list of decoded lines (without trailing newlines).

    Why:
    - Log files can become huge over multi-hour runs.
    - Parsing the entire file every refresh makes redraws progressively slower.

    Notes:
    - This reads bytes from the end in chunks until enough newlines are found.
    - `errors="replace"` prevents crashes on partially-written UTF-8 sequences.
    """
    if max_lines is None or max_lines <= 0:
        with open(path, "r", encoding=encoding, errors="replace") as f:
            return [line.rstrip("\n") for line in f]

    chunk_size = 64 * 1024
    data = b""
    newline_count = 0

    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        offset = 0

        while file_size > offset and newline_count <= max_lines:
            offset = min(file_size, offset + chunk_size)
            f.seek(file_size - offset)
            chunk = f.read(min(chunk_size, offset))
            data = chunk + data
            newline_count = data.count(b"\n")

    text = data.decode(encoding, errors="replace")
    lines = text.splitlines()
    return lines[-max_lines:]


def apply_window_and_cap_indexed(df, window_minutes, max_points):
    """
    Apply a rolling time-window and a max-point cap to a DataFrame indexed by time.

    This keeps both parsing and Matplotlib updates bounded (stable performance over time).
    """
    if df is None or df.empty:
        return df

    if window_minutes is not None and window_minutes > 0:
        last_ts = df.index.max()
        if pd.notna(last_ts):
            cutoff = last_ts - pd.Timedelta(minutes=window_minutes)
            df = df[df.index >= cutoff]

    if max_points is not None and max_points > 0 and len(df) > max_points:
        df = df.iloc[-max_points:]

    return df


def apply_window_and_cap_timecol(df, window_minutes, max_points, time_col="Time"):
    """
    Apply a rolling time-window and a max-point cap to a DataFrame with a time column.

    Used for legacy Tera Term logs which store timestamps in a column rather than index.
    """
    if df is None or df.empty or time_col not in df.columns:
        return df

    if window_minutes is not None and window_minutes > 0:
        last_ts = df[time_col].max()
        if pd.notna(last_ts):
            cutoff = last_ts - pd.Timedelta(minutes=window_minutes)
            df = df[df[time_col] >= cutoff]

    if max_points is not None and max_points > 0 and len(df) > max_points:
        df = df.iloc[-max_points:]

    return df



# This function extracts data from the web monitor log file, which is in JSON format
# It outputs a pandas DataFrame with a timestamp index and columns for each sensor reading
def getDataFromWebMonitorFile(filename, tail_lines=None):
    """
    Parse the web monitor JSON-lines log into a pandas DataFrame.

    Output shape:
    - Index: `timestamp` (datetime)
    - Columns: sensor readings (PMON, CCS temps/volts/amps, VTRX pressure, etc.)

    Performance:
    - `tail_lines` lets us parse only the most recent lines for live plotting.
    """
    records = []   # This list will store flattened log records

    lines = read_last_lines(filename, tail_lines) if tail_lines else None
    if lines is None:
        with open(filename, "r", encoding="utf-8", errors="replace") as file:
            lines = file.readlines()

    for line in lines:
        if not line.strip():
            continue

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
            "ccs_C_voltage": status["Cathode C - Heater Voltage:"],
        }

        records.append(record)

    # Create the table style dataframe from the list of records
    # each column = sensor
    # each row = timestamp
    df = pd.DataFrame(records)

    if(df.empty) :
        print("WebMonitor file is empty!")
        return


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
def get902bPressureData(filename, tail_lines=None):
    '''
    Extract pressure data from txt file

    @param:
        filename -> str
    
    @return:
        2D list of Time and Pressure -> list
    '''
    # NOTE: This currently returns a DataFrame but is not plotted by default in the
    # combined graph (legacy configuration). We keep it available for future use.
    
    # Create an empty list to store the extracted data before converting it to a DataFrame
    data = []                          
    # Regex pattern to parse lines in the 902b log file for timestamps and pressure readings
    regex_pattern = re.compile(r'\[\d{4}-\d{2}-\d{2} (\d{2}:\d{2}:\d{2})\.\d{3}\] @\d{3}ACK(\d*\.\d*);FF', re.I)
    # Columns for the DataFrame
    columns=["Time", "Pressure (mbar)"]
    
    lines = read_last_lines(filename, tail_lines) if tail_lines else None
    if lines is None:
        with open(filename, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

    for line in lines:
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

# This is not currently working because CCS set point logging was changed significantly
# def getCCSVoltageSetData(filename):
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

# This is not currently working because CCS set point logging was changed significantly
# def getCCSCurrentSetData(filename):
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
def getHVData(filename, psu_type = "3kv", tail_lines=None):
    '''
    Extract pressure data from txt file

    @param:
        filename -> str
    
    @return:
        2D list of time and HV current -> list
    '''
    # NOTE: Despite the docstring above, this function extracts *HV PSU* readings
    # (setpoint voltage, actual voltage, and current) from a Tera Term log.
    
    # Create an empty list to store the extracted data before converting it to a DataFrame
    data = []                          
    # Regex pattern to parse lines in the Tera Term log file for timestamps and HV PSU readings (voltage set point, voltage actual, and current)
    regex_pattern = re.compile(r'\[\d{4}-\d{2}-\d{2} (.*?)\] Set: -?(\d{1,4}) V,  HV: -?(\d{1,4}) V,  I: -?(\d{1,2}\.\d{2,3}) mA', re.I)
    # Columns for the DataFrame
    columns=["Time", f"hvActualVolt{psu_type}", f"hvSetVolt{psu_type}", f"hvCurrent{psu_type}"]
    
    lines = read_last_lines(filename, tail_lines) if tail_lines else None
    if lines is None:
        with open(filename, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

    for line in lines:
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

def getAllData(web_tail_lines=None, teraterm_tail_lines=None, window_minutes=None, max_points=None):
    """
    Collect the latest data needed for all enabled graphs.

    Responsibilities:
    - Find the most recently modified log file for each source (glob + ctime).
    - Parse each source (web monitor JSON-lines; Tera Term regex-based logs).
    - Apply rolling window + max point caps so plot updates remain fast.

    Returns:
    - webMonitor_df: DataFrame indexed by timestamp
    - legacy_graph_dataframes: mapping of subplot name -> DataFrame with a `Time` column
    """
    # =========== Find the most recent log files ===========
    teraTerm_files = glob.glob(teraTerm_log_path20kv)
    teraTerm_log_file20kv = max(teraTerm_files, key=os.path.getctime) if teraTerm_files else None

    teraTerm_files = glob.glob(teraTerm_log_path3kv)
    teraTerm_log_file3kv = max(teraTerm_files, key=os.path.getctime) if teraTerm_files else None

    teraTerm_files = glob.glob(teraTerm_log_pathPos1kv)
    teraTerm_log_filePos1kv = max(teraTerm_files, key=os.path.getctime) if teraTerm_files else None

    teraTerm_files = glob.glob(teraTerm_log_pathNeg1kv)
    teraTerm_log_fileNeg1kv = max(teraTerm_files, key=os.path.getctime) if teraTerm_files else None

    teraTerm_files = glob.glob(teraTerm_log_path902b)
    teraTerm_log_file902b = max(teraTerm_files, key=os.path.getctime) if teraTerm_files else None

    # Pick the most recently edited dashboard log file
    dashboard_files = glob.glob(dashboard_log_path)
    dashboard_log_file = max(dashboard_files, key=os.path.getctime) if dashboard_files else None

    # Pick the most recently edited dashboard log file
    webMonitor_files = glob.glob(webMonitor_path)
    webMonitorFile = max(webMonitor_files, key=os.path.getctime) if webMonitor_files else None
    # ======================================================

    # Extract data from web monitor file and break up columns into different graphs
    webMonitor_df = getDataFromWebMonitorFile(webMonitorFile, tail_lines=web_tail_lines) if webMonitorFile else pd.DataFrame()
    pressure902b_df = get902bPressureData(teraTerm_log_file902b, tail_lines=teraterm_tail_lines) if teraTerm_log_file902b else pd.DataFrame()
    hv20kv_df = getHVData(teraTerm_log_file20kv, "20kv", tail_lines=teraterm_tail_lines) if teraTerm_log_file20kv else pd.DataFrame()
    hv3kv_df = getHVData(teraTerm_log_file3kv, "3kv", tail_lines=teraterm_tail_lines) if teraTerm_log_file3kv else pd.DataFrame()
    hvPos1kv_df = getHVData(teraTerm_log_filePos1kv, "Pos1kv", tail_lines=teraterm_tail_lines) if teraTerm_log_filePos1kv else pd.DataFrame()
    hvNeg1kv_df = getHVData(teraTerm_log_fileNeg1kv, "Neg1kv", tail_lines=teraterm_tail_lines) if teraTerm_log_fileNeg1kv else pd.DataFrame()
    # ccsSetCurrent_df = getCCSCurrentSetData(dashboard_log_file)
    # ccsSetVoltage_df = getCCSVoltageSetData(dashboard_log_file)

    legacy_graph_dataframes = {
        '20kV PSU voltage':   hv20kv_df,
        '20kV PSU current':   hv20kv_df,
        '3kV PSU voltage':    hv3kv_df,
        '3kV PSU current':    hv3kv_df,
        '1kV PSU voltage': hvPos1kv_df,
        '1kV PSU current': hvPos1kv_df,
        'Neg1kV PSU voltage': hvNeg1kv_df,
        'Neg1kV PSU current': hvNeg1kv_df,
        # 'CCS Set Voltage':    ccsSetVoltage_df,
        # 'CCS Set Current':    ccsSetCurrent_df
    }

    # Apply rolling window + point caps to keep live plotting fast.
    if webMonitor_df is not None and not webMonitor_df.empty:
        webMonitor_df = apply_window_and_cap_indexed(webMonitor_df, window_minutes, max_points)

    for key, df in list(legacy_graph_dataframes.items()):
        if df is not None and not df.empty:
            legacy_graph_dataframes[key] = apply_window_and_cap_timecol(df, window_minutes, max_points, time_col="Time")

    # Keep pressure902b_df around if/when legacy plots use it again.
    _ = pressure902b_df

    return webMonitor_df, legacy_graph_dataframes

def build_plot_specs(webMonitor_df, legacy_graph_dataframes):
    """
    Convert the configuration dictionaries + available data into an ordered list
    of subplot "specs".

    A spec defines:
    - which subplot exists (name, kind)
    - which lines (columns) are drawn on that subplot

    This lets us build the figure once and reuse the same plotting structure on each refresh.
    """
    specs = []

    if webMonitor_df is not None and not webMonitor_df.empty:
        for subplot, cfg in graph_settings.items():
            if not cfg.get("enabled"):
                continue

            cols = [c for c in cfg.get("lines", []) if c in webMonitor_df.columns]
            if not cols:
                continue

            has_any_data = any(not webMonitor_df[c].dropna().empty for c in cols)
            if not has_any_data:
                continue

            specs.append(
                {
                    "kind": "web",
                    "name": subplot,
                    "lines": cols,
                }
            )

    for subplot, cfg in legacy_graph_settings.items():
        if not cfg.get("enabled"):
            continue

        df = legacy_graph_dataframes.get(subplot)
        if df is None or df.empty:
            continue

        cols = [c for c in cfg.get("lines", []) if c in df.columns]
        if not cols:
            continue

        has_any_data = any(not df[c].dropna().empty for c in cols)
        if not has_any_data:
            continue

        specs.append(
            {
                "kind": "legacy",
                "name": subplot,
                "lines": cols,
            }
        )

    return specs


def build_figure_and_lines(specs):
    """
    Create the Matplotlib figure/subplots and pre-create the `Line2D` artists.

    Key idea:
    - We create lines once (empty data).
    - Live updates only call `line.set_data(x, y)` which is much faster than re-plotting.

    Returns:
    - fig: Matplotlib Figure
    - axes: flat array of Axes
    - line_artists: dict keyed by (subplot_index, column_name) -> Line2D
    """
    numPlots = len(specs)
    if numPlots < 2:
        print("Number of non-empty plots must be >= 2!")
        return None, None, None

    fig, axs = plt.subplots(numPlots, 1, figsize=(18, 11), sharex=True)
    axes = np.atleast_1d(axs).ravel()
    line_artists = {}

    for idx, spec in enumerate(specs):
        ax = axes[idx]
        ax.set_ylabel(spec["name"])
        ax.grid(True)
        ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=num_y_ticks[numPlots]))

        for col in spec["lines"]:
            (line,) = ax.plot([], [], label=col, linewidth=1)
            line_artists[(idx, col)] = line

        ax.legend(loc="upper left")

    # Format x axis once (shared x).
    axes[numPlots - 1].xaxis.set_major_locator(ticker.MaxNLocator(nbins=40))
    axes[numPlots - 1].xaxis.set_major_formatter(mdates.DateFormatter("%I:%M:%S"))
    for label in axes[numPlots - 1].get_xticklabels():
        label.set_rotation(45)
        label.set_ha("right")
    axes[numPlots - 1].set_xmargin(0)

    fig.tight_layout(h_pad=0, w_pad=0, rect=[0, 0.03, 1, 0.95])
    return fig, axes, line_artists


def update_lines(specs, axes, line_artists, legacy_graph_dataframes, webMonitor_df):
    """
    Fast path for live updates.

    For each enabled subplot/line:
    - compute x/y arrays from the latest DataFrames
    - update the existing `Line2D` artist with `set_data`

    We also do a lightweight y-limits autoscale per subplot (based on current data only).
    """
    all_x_mins = []
    all_x_maxs = []

    for idx, spec in enumerate(specs):
        ax = axes[idx]
        ys_for_limits = []

        if spec["kind"] == "web":
            if webMonitor_df is None or webMonitor_df.empty:
                continue
            x = webMonitor_df.index
            if len(x) == 0:
                continue

            all_x_mins.append(x.min())
            all_x_maxs.append(x.max())

            for col in spec["lines"]:
                y = webMonitor_df[col].to_numpy()
                line_artists[(idx, col)].set_data(x, y)
                ys_for_limits.append(y)

        else:
            df = legacy_graph_dataframes.get(spec["name"])
            if df is None or df.empty or "Time" not in df.columns:
                continue
            x = df["Time"]
            if len(x) == 0:
                continue

            all_x_mins.append(x.min())
            all_x_maxs.append(x.max())

            for col in spec["lines"]:
                y = df[col].to_numpy()
                line_artists[(idx, col)].set_data(x, y)
                ys_for_limits.append(y)

        # Fast y autoscale (bounded by max_points).
        if ys_for_limits:
            y_concat = np.concatenate([np.asarray(y, dtype=float) for y in ys_for_limits if len(y) > 0])
            y_concat = y_concat[np.isfinite(y_concat)]
            if y_concat.size > 0:
                y_min = float(np.min(y_concat))
                y_max = float(np.max(y_concat))
                if y_min == y_max:
                    pad = 1.0 if y_min == 0 else abs(y_min) * 0.05
                    y_min -= pad
                    y_max += pad
                else:
                    pad = (y_max - y_min) * 0.05
                    y_min -= pad
                    y_max += pad
                ax.set_ylim(y_min, y_max)

    if all_x_mins and all_x_maxs:
        x_min = min(all_x_mins)
        x_max = max(all_x_maxs)
        axes[-1].set_xlim(x_min, x_max)

    axes[-1].figure.canvas.draw_idle()
    axes[-1].figure.canvas.flush_events()


def main():
    """
    Program entrypoint.

    The Matplotlib window must be updated on the main thread. Disk I/O + parsing runs
    in a background worker, and the main thread:
    - yields to the GUI event loop via `plt.pause(refresh_sec)`
    - applies artist updates when new data arrives
    - rebuilds the figure if the set of enabled/available plots changes
    """
    args = parse_args()
    global DEBUG_TIMING
    DEBUG_TIMING = bool(args.debug_timing)

    plt.ion()

    run = True
    fig = None
    axes = None
    line_artists = None
    last_layout_sig = None

    try:
        # First read is blocking so we can build the initial figure.
        startTime = time.perf_counter()
        webMonitor_df, legacy_graph_dataframes = getAllData(
            web_tail_lines=args.web_tail_lines,
            teraterm_tail_lines=args.teraterm_tail_lines,
            window_minutes=args.window_min,
            max_points=args.max_points,
        )
        if DEBUG_TIMING:
            elapsedTime = time.perf_counter() - startTime
            print(f"Took {elapsedTime}sec to load initial data")

        specs = build_plot_specs(webMonitor_df, legacy_graph_dataframes)
        layout_sig = tuple((s["kind"], s["name"], tuple(s["lines"])) for s in specs)
        if layout_sig != last_layout_sig:
            if fig is not None:
                plt.close(fig)
            fig, axes, line_artists = build_figure_and_lines(specs)
            last_layout_sig = layout_sig
            if fig is not None:
                plt.show(block=False)

        # Background thread handles disk I/O + parsing; matplotlib updates stay on main thread.
        with ThreadPoolExecutor(max_workers=1) as executor:
            data_future = executor.submit(
                getAllData,
                args.web_tail_lines,
                args.teraterm_tail_lines,
                args.window_min,
                args.max_points,
            )

            while run:
                # Let the GUI process events; longer pauses reduce redraw churn and can feel more responsive.
                plt.pause(args.refresh_sec)

                # Only update the graph if all data has been gathered.
                if not data_future.done():
                    continue

                try:
                    webMonitor_df, legacy_graph_dataframes = data_future.result()
                except json.JSONDecodeError:
                    print("JSON decode error! Retrying...")
                    data_future = executor.submit(
                        getAllData,
                        args.web_tail_lines,
                        args.teraterm_tail_lines,
                        args.window_min,
                        args.max_points,
                    )
                    continue

                # Kick off the next refresh immediately (only 1 in flight).
                data_future = executor.submit(
                    getAllData,
                    args.web_tail_lines,
                    args.teraterm_tail_lines,
                    args.window_min,
                    args.max_points,
                )

                specs = build_plot_specs(webMonitor_df, legacy_graph_dataframes)
                layout_sig = tuple((s["kind"], s["name"], tuple(s["lines"])) for s in specs)
                if layout_sig != last_layout_sig:
                    if DEBUG_TIMING:
                        print("Rebuilding figure (plot layout changed)")
                    if fig is not None:
                        plt.close(fig)
                    fig, axes, line_artists = build_figure_and_lines(specs)
                    last_layout_sig = layout_sig
                    if fig is not None:
                        plt.show(block=False)
                    continue

                if fig is None or axes is None or line_artists is None:
                    continue

                startTime = time.perf_counter()
                update_lines(specs, axes, line_artists, legacy_graph_dataframes, webMonitor_df)
                if DEBUG_TIMING:
                    elapsedTime = time.perf_counter() - startTime
                    print(f"Took {elapsedTime}sec to update graph")

                if RUN_ONCE:
                    run = False
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
