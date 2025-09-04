# cbmark_logger
Data interpreter for cathode benchmarking experiment for the e-beam system. Displays select data from experiment, taken from EBeam Dashboard and Tera Term (logging serial output from Knob Box Arduino).

# Tera Term setup (Manual)
1. Download and install Tera Term from https://github.com/TeraTermProject/osdn-download/releases (default options work)
2. Open Tera Term and close the connection dialog
3. Enter the "Additional Settings" menu (press ALT, S, D or "Setup" -> "Additional Settings")
4. Switch to the "logs" tab
5. Check the "auto start logging" and "Timestamp" options
6. Change file path and log file name as desired but note what you set them to so that you can enter them
7. Press "OK" in the bottom right of the "Tera Term: Additional Settings" window
8. Press the "Save Setup" button (press ALT, S, S or "Setup" -> "Save Setup") and replace TERATERM.ini
9. Create a new connection with the serial device (ALT+N or File -> New Connection, then click Serial and click on the correct COM port)
    - For an Arduino Mega, the COM port will be named Arduino Mega. This will be the case for the Knob Box Arduinos or High Voltage Monitor Arduinos. 
    - Other devices, such as USB RS-485 adapters (for the 902b especially) will need to be differentiated through other means, such as by opening Device Manager and watching to see which COM port appears when the adapter is plugged in.

# Tera Term setup (Macro)
1. Download and install Tera Term from https://github.com/TeraTermProject/osdn-download/releases (default options work).
2. Open Tera Term and create a new connection with the serial device (ALT+N or File -> New Connection, then click Serial and click on the correct COM port)
    - For an Arduino Mega, the COM port will be named Arduino Mega. This will be the case for the Knob Box Arduinos or High Voltage Monitor Arduinos. 
    - Other devices, such as USB RS-485 adapters (for the 902b especially) will need to be differentiated through other means, such as by opening Device Manager and watching to see which COM port appears when the adapter is plugged in.
3. Open the macro file explorer (ALT, O, M or "Control" -> "Macro") and select the corresponding .ttl macro file in cbmark_logger\Tera Term Macros
    - This will start logging, set the baud rate (if not correctly set already), and may send a recurring command (like polling the 902b for pressure readings)
4. If the Tera Term macro has a recurring command, you can stop the macro by showing the macro window (ALT, O, W or "Control" -> "Show Macro Window") and pressing "End"
5. The file path in the macro will default to the corresponding Tera Term logs folder in C:\Users\Experiment\cbmark_logger\ but it may be changed if somewhere else is more convenient.

# Using Generate_combined_graph

1. Open VSCode to the CBMARK_LOGGER folder
2. Open and scroll down to the bottom of Generate_combined_graph.ipynb
3. Ensure that your file paths are correct in the first few lines of code inside the while loop of the bottommost cell. 
    - In order to use a specific file (instead of automatically picking the most recent in a directory), you must uncomment the first two lines of code in the while loop, then comment out the 4 lines of code that follow them. If you would prefer, there are directions there too. 
4. Select at least two non-empty data sources to graph in the Enable dictionary. 
    - Sources that are set to 1 are enabled and sources that are set to 0 are disabled.
5. Press the "Run All" button on the top hotbar (mid left)
    - You may see a request to install ipykernel. Click the install button in the pop-up to do this automatically.
    - You may see an error saying that you need to make a virtual environment, which VScode will do for you if you click the prompt for it.
    - If there are any imports that are missing, use pip to install them in the top cell, which will be done automatically with "Run All"
6. The bottommost cell will be continuously running at this point, which you may want to terminate if you only want a one-time graph. One-time graphs can be generated using the second-to-bottommost cell if you wish.
7.  The graph will be repeatedly generated now from the most recent Tera Term log file and the most recent Dashboard log file. If you wish to stop the program, press the "Interrupt" button that appears where the "Run All" button used to be.
8. If you wish to better fit the graph to your display, try changing the figureWidth and figureHeight fields
9. 

