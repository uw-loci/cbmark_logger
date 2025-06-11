# cbmark_logger
Data interpreter for cathode benchmarking experiment for the e-beam system. Displays select data from experiment, taken from EBeam Dashboard and Tera Term (logging serial output from Knob Box Arduino).

# Tera term setup
1. Download and install Tera Term from https://github.com/TeraTermProject/osdn-download/releases (default options work)
2. Open Tera Term and enter the "Additional Settings" menu (press alt, s, d or "Setup" -> "Additional Settings")
3. Switch to the "logs" tab
4. Check the "auto start logging" and "Timestamp" options
5. Change file path and log file name as desired but note what you set them to so that you can enter them
6. Press "OK" in the bottom right of the "Tera Term: Additional Settings" window
7. Press the "Save Setup" button (press alt, s, s or "Setup" -> "Save Setup") and replace TERATERM.ini

# Using Generate_combined_graph
The current iteration as of 1:15PM on 6/11/25 has a few quirks that should be resolved soon, but they are listed here. This guide is meant for VSCode and assumes you have Python and the required extensions installed in VSCode

1. Find the log file from the Ebeam Dashboard that you want to graph and copy its directory into the dashboard_log_file variables in the bottom two cells
    - If running the Ebeam Dashboard, its log file will be appended to automatically, which is why the bottommost cell has an infinite loop that remakes the graph
2. Find the log file from Tera Term that you want to graph and copy its directory into the teraTerm_log_file variables in the bottom two cells 
    - If running Tera Term with logging enabled, its log file will be appended to automatically, which is why the bottommost cell has an infinite loop that remakes the graph
3. Press the "run all" button on the top hotbar (mid left)
    - You may see a request to install ipykernel. Click the install button in the pop-up to do this automatically.
    - You may see an error saying that you need to make a virtual environment, which VScode will do for you if you click the prompt for it.
    - You may also only run the cells required for your uses, but pressing "run all" is easy
4. If there are any imports that are missing, use pip to install them in the top cell.
5. The bottommost cell will be continuously running at this point, which you may want to terminate if you only want a one-time graph. One-time graphs can be generated using the second-to-bottommost cell if you wish. 



# Using the separated graph generators
The current iteration as of 1:15PM on 6/11/25 has a few quirks that should be resolved soon, but they are listed here. This guide is meant for VSCode and assumes you have Python and the required extensions installed in VSCode

1. Find the log file from the Ebeam Dashboard that you want to graph and copy its directory into the input for Generate_pressure_graph's getPressuredata() and Generate_PMON_graph's getPMONdata() in the bottom two cells
    - If running the Ebeam Dashboard, its log file will be appended to automatically, which is why the bottommost cell has an infinite loop that remakes the graph
2. Find the log file from Tera Term that you want to graph and copy its directory into the input for Generate_Current_Graph's getCurrentdata() in the bottom two cells
    - If running Tera Term with logging enabled, its log file will be appended to automatically, which is why the bottommost cell has an infinite loop that remakes the graph
3. Press the "run all" button on the top hotbar (mid left)
    - You may see a request to install ipykernel. Click the install button in the pop-up to do this automatically.
    - You may see an error saying that you need to make a virtual environment, which VScode will do for you if you click the prompt for it.
    - You may also only run the cells required for your uses, but pressing "run all" is easy
4. If there are any imports that are missing, use pip to install them in the top cell.
5. The bottommost cell will be continuously running at this point, which you may want to terminate if you only want a one-time graph. One-time graphs can be generated using the second-to-bottommost cell if you wish. 


