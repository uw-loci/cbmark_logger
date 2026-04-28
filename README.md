# cbmark_logger

Data interpreter for cathode benchmarking experiment for the e-beam system. Displays select data from experiment, taken from EBeam Dashboard and Tera Term (logging serial output from Knob Box Arduino).

## Tera Term setup (Manual)

1. Download and install Tera Term from <https://github.com/TeraTermProject/osdn-download/releases> (default options work)
2. Open Tera Term and close the connection dialog
3. Enter the "Additional Settings" menu (press ALT, S, D or "Setup" -> "Additional Settings")
4. Switch to the "Log" tab
5. Check the "Auto start logging" and "Timestamp" options ("Append" and "Plain Text" should already be checked, you can leave it this way)
6. Change "Default log save folder" (filepath) and "Default log file name" as desired but note what you set them to so that you can enter them
7. Press "OK" in the bottom right of the "Tera Term: Additional Settings" window
8. Press the "Save Setup" button (press ALT, S, S or "Setup" -> "Save Setup") and replace TERATERM.ini
9. Create a new connection with the serial device (ALT+N or File -> New Connection, then click Serial and click on the correct COM port)
    - For an Arduino Mega, the COM port will be named Arduino Mega. This will be the case for the Knob Box Arduinos or High Voltage Monitor Arduinos.
    - Other devices, such as USB RS-485 adapters (for the 902b especially) will need to be differentiated through other means, such as by opening Device Manager and watching to see which COM port appears when the adapter is plugged in.
10. Click "OK" once COM port has been selected

## Tera Term setup (Macro)

1. Download and install Tera Term from <https://github.com/TeraTermProject/osdn-download/releases> (default options work).
2. Open Tera Term and create a new connection with the serial device (ALT+N or File -> New Connection, then click Serial and click on the correct COM port)
    - For an Arduino Mega, the COM port will be named Arduino Mega. This will be the case for the Knob Box Arduinos or High Voltage Monitor Arduinos.
    - Other devices, such as USB RS-485 adapters (for the 902b especially) will need to be differentiated through other means, such as by opening Device Manager and watching to see which COM port appears when the adapter is plugged in.
3. Open the macro file explorer (ALT, O, M or "Control" -> "Macro") and select the corresponding .ttl macro file in cbmark_logger\Tera Term Macros
    - This will start logging, set the baud rate (if not correctly set already), and may send a recurring command (like polling the 902b for pressure readings)
4. If the Tera Term macro has a recurring command, you can stop the macro by showing the macro window (ALT, O, W or "Control" -> "Show Macro Window") and pressing "End"
5. The file path in the macro will default to the corresponding Tera Term logs folder in C:\Users\Experiment\cbmark_logger\ but it may be changed if somewhere else is more convenient.

## Using Generate_combined_graph

If you already have the environment set up, you can skip to the "Run CBMARK_LOGGER" section.

### Create a venv for Python and import dependencies for CBMARK_LOGGER

1. Open a terminal to the CBMARK_LOGGER folder
2. Run the following commands:
    - python -m venv .venv
    - ./.venv/Scripts/activate
    - pip install -r requirements.txt

### Set up VSCode

1. Install the following extensions (ctrl+shift+x or click the button on the left) :
    - Jupyter
    - Python
        - Note that both of these install other extensions automatically
2. Open VSCode to the CBMARK_LOGGER folder
3. Select the venv as the Jupyter kernel
    - Click on the kernel button in the top left of the editor window
    - Select the ".venv (Python [version here])" option
4. Ensure that your file paths are correct
    - File paths are located at the top of the second cell, labelled "# Define global variables and settings"
    - If you would like to use the most recent file, append the path to the folder with /*
        - Make sure that any file paths added use / instead of \
    - If you would like to use a specific file, simply replace the appropriate file path
        - Make sure that any file paths added use / instead of \
5. Select the number of previous webMonitor files to read
    - This reads the rotated log files from before the most recent one
    - This setting is located at the top of the second cell, labelled "# Define global variables and settings"
6. Press the "Run All" button on the top hotbar (mid left)
    - You may see a request to install ipykernel. Click the install button in the pop-up to do this automatically.
    - You may see an error saying that you need to make a virtual environment, which VScode will do for you if you click the prompt for it.
7. To change settings:
    - Interrupt the graphing loop by pressing the stop button on the bottommost cell
    - Change any settings you need in the second cell
        - You must re-run that cell for changes to take effect
    - Check or uncheck the boxes above the graphing cell to change displayed subplots
    - Run the graphing cell again (bottommost cell)
