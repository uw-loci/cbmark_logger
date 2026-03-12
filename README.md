# cbmark_logger
`cbmark_logger` parses cathode benchmarking experiment logs from the EBeam dashboard and Tera Term sources, then turns them into combined monitoring graphs and optional CSV exports. The main way to use this repo is to run [`Generate_combined_graph.ipynb`](Generate_combined_graph.ipynb) in VS Code.

## Setup
Create and activate a project virtual environment before running any notebook:

```powershell
git clone https://github.com/uw-loci/cbmark_logger.git
cd cbmark_logger
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
code .
```

In VS Code, select the `.venv` interpreter or notebook kernel before running any cells.

## What This Repo Does
- Reads experiment logs from the EBeam dashboard and several Tera Term log folders.
- Combines available signals into one monitoring view, including PMON temperatures, CCS temperatures, pressure readings, HV readings, and CCS PSU data.
- Supports both live-style monitoring from the latest log files and offline analysis from specific saved files.
- Can export parsed data to CSV files for later inspection.
- Includes secondary notebooks for interactive graph inspection and PMON hardware logging.

## Recommended Workflow: Generate_combined_graph
Use [`Generate_combined_graph.ipynb`](Generate_combined_graph.ipynb) for normal day-to-day viewing of experiment data.

1. Open `Generate_combined_graph.ipynb` in VS Code and confirm the selected kernel is `.venv`.
2. Run the code cells above the main graph cell, then scroll to the main graph cell near the bottom of the notebook.
3. Choose how the notebook should find input files.
   Keep the auto-discovery block enabled if you want the notebook to use the most recently updated logs.
   Uncomment the specific file path block and comment out the auto-discovery block inside the loop if you want to analyze saved files instead.
4. If you use the default live-style paths, the notebook expects:
   dashboard logs from `C:/Users/Experiment/EBEAM_dashboard/EBEAM-Dashboard-Logs/`
   HV monitor logs from the `Tera Term 20kv HV Monitor logs`, `Tera Term 3kv HV Monitor logs`, `Tera Term +1kv HV Monitor logs`, and `Tera Term -1kv HV Monitor logs` folders
   902b logs from the `902b Logs` folder
5. Edit the `enable` dictionary to choose which signals appear on the graph.
   Set an entry to `1` to plot it and `0` to leave it out.
   At least two enabled data sources must contain data or the graph function will refuse to draw.
6. Adjust `figureWidth` and `figureHeight` if the graph does not fit your display well.
7. Decide whether you want continuous refresh or a one-time plot.
   Leave `run = True` for repeated updates from the newest logs.
   Set `run = False` on the first line inside the `while run:` loop if you want a single static graph.
8. Run the bottom graph cell.
   The notebook will parse the selected logs and render a multi-panel matplotlib graph in the notebook output.
9. Stop the live-refresh loop by interrupting the running cell or notebook kernel when you are done.

## Inputs and Outputs
Inputs used by the combined graph notebook:
- EBeam dashboard logs for PMON, CCS, and related experiment messages.
- Tera Term HV monitor logs for the configured HV supplies.
- 902b pressure logs.
- Optional sample files from `Data samples` when you want to test without live log folders.

Outputs produced by this repo:
- A live or one-time combined graph rendered inside the notebook output.
- Optional CSV exports from the CSV generation cell in [`Generate_combined_graph.ipynb`](Generate_combined_graph.ipynb).
- CSV files written to the `CSV files` folder.

Notes on generated files:
- The `CSV files` folder is the normal working output location for generated CSVs.
- Files in `CSV files` are not automatically treated as archived, version-controlled experiment artifacts.
- Use the `Archive` folder separately if you want to keep selected outputs in the repo history.

## Other Workflows
### Generate_interactive_graph
Use [`Generate_interactive_graph.ipynb`](Generate_interactive_graph.ipynb) when you want an alternate graph view with clickable point inspection.

1. Open the notebook with the `.venv` kernel selected.
2. Configure the file paths near the bottom for either saved files or the latest available logs.
3. Run the notebook cells to build the graph.
4. Click plotted lines to inspect values directly on the graph.

This notebook is useful for closer inspection, but it is not the primary monitoring path for the repo.

### PMON logger
Use [`PMON logger.ipynb`](PMON%20logger.ipynb) to collect PMON temperature logs from connected hardware over Modbus RTU.

1. Open the notebook with the `.venv` kernel selected.
2. Edit the serial connection settings, such as `port` and `unit_numbers`, so they match the attached PMON hardware.
3. Run the notebook cells to start polling and logging temperatures.
4. Stop the logging run with an interrupt when finished.

This notebook creates timestamped PMON log files and is mainly for hardware data collection, not for the main graph-viewing workflow.

## Troubleshooting
- Wrong kernel or missing packages: make sure the notebook kernel is `.venv`, then run `pip install -r requirements.txt` from the activated virtual environment.
- Empty plots from wrong file paths: check whether you are using the live auto-discovery block or specific saved-file paths, then make sure the uncommented block matches the files you actually have.
- Empty plots from missing data: the combined graph needs at least two enabled sources with real data. If fewer than two enabled sources are non-empty, the graph will not render.
- Notebook keeps refreshing: the bottom cell is designed to keep re-reading logs when `run` remains enabled. Interrupt the cell to stop it.
- Graph does not fit the screen well: tune `figureWidth` and `figureHeight` in the main graph cell and rerun it.
- Latest-log mode fails immediately: make sure the expected log folders contain files. The notebook uses the most recently modified file in each folder and will fail if a required folder is empty.

## Development / Logging Notes
The sections below are optional reference material for collecting logs, setting up serial logging, or debugging the experiment environment. Most users who only want to view experiment data should start with `Generate_combined_graph.ipynb` instead.

### Tera Term Setup (Manual)
1. Download and install Tera Term from https://github.com/TeraTermProject/osdn-download/releases.
2. Open Tera Term and close the connection dialog.
3. Open `Setup -> Additional Settings`.
4. Switch to the `Log` tab.
5. Enable `Auto start logging` and `Timestamp`.
6. Set the default log save folder and log file name to match your environment.
7. Press `OK`.
8. Save the setup and replace `TERATERM.ini`.
9. Create a new serial connection and choose the correct COM port.
   For an Arduino Mega, the COM port will usually appear as Arduino Mega.
   Other devices, such as USB RS-485 adapters for the 902b, may need to be identified through Device Manager.
10. Press `OK` after choosing the port.

### Tera Term Setup (Macro)
1. Download and install Tera Term from https://github.com/TeraTermProject/osdn-download/releases.
2. Open Tera Term and create a serial connection to the correct device.
3. Open the macro browser and select the corresponding `.ttl` file from `Tera Term Macros`.
4. The macro can start logging, set the baud rate, and optionally send recurring commands such as 902b polling commands.
5. If the macro is recurring, stop it from the macro window with `End`.
6. Macro file paths default to log folders under `C:\Users\Experiment\cbmark_logger\`, but you can change them if needed.
