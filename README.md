# cbmark_logger
Data interpreter for cathode benchmarking experiment for the e-beam system. Displays select data from experiment, taken from EBeam Dashboard and Tera Term (logging serial output from Knob Box Arduino).

# Tera term setup
1. Download and install Tera Term from https://github.com/TeraTermProject/osdn-download/releases (default options work)
2. Open Tera Term and close the connection dialog
3. Enter the "Additional Settings" menu (press alt, s, d or "Setup" -> "Additional Settings")
4. Switch to the "logs" tab
5. Check the "auto start logging" and "Timestamp" options
6. Change file path and log file name as desired but note what you set them to so that you can enter them
7. Press "OK" in the bottom right of the "Tera Term: Additional Settings" window
8. Press the "Save Setup" button (press alt, s, s or "Setup" -> "Save Setup") and replace TERATERM.ini
9. Create a new connection with the knob box Arduino (ALT+N or File -> New Connection, then click Serial and click on the Arduino COM port)

# Using Generate_combined_graph
The current iteration as of 1:15PM on 6/11/25 has a few quirks that should be resolved soon, but they are listed here. This guide is meant for VSCode and assumes you have Python and the required extensions installed in VSCode

1. Open VSCode to the CBMARK_LOGGER folder
2. Open and scroll down to the bottom of Generate_combined_graph.ipynb
3. Ensure that your file paths are correct in the first few lines of code inside the while loop of the bottommost cell. 
    - In order to use a specific file (instead of automatically picking the most recent in a directory), you must uncomment the first two lines of code in the while loop, then comment out the 4 lines of code that follow them. If you would prefer, there are directions there too. 
4. Press the "Run All" button on the top hotbar (mid left)
    - You may see a request to install ipykernel. Click the install button in the pop-up to do this automatically.
    - You may see an error saying that you need to make a virtual environment, which VScode will do for you if you click the prompt for it.
6. If there are any imports that are missing, use pip to install them in the top cell.
7. The bottommost cell will be continuously running at this point, which you may want to terminate if you only want a one-time graph. One-time graphs can be generated using the second-to-bottommost cell if you wish. 
8. The graph will be repeatedly generated now from the most recent Tera Term log file and the most recent Dashboard log file. If you wish to stop the program, press the "Interrupt" button that appears where the "Run All" button used to be.

