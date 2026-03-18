# GTEC Analysis Software (Alpha 1.1)

A high-performance telemetry analysis suite specifically designed for extracting and analyzing data from MoTeC `.ld` files. Built for sim racers and race engineers, it strictly focuses on Vehicle Dynamics Engineering.

## Features
- **Roll Gradient Analysis**: Analyze front-to-rear roll stiffness.
- **Static Setup Viewer**: Extracts setup parameters embedded within the telemetry (tire pressures, ride heights, brake bias, etc).
- **Dynamic Aero/Rake Analyzer**: Interactive graphical analysis mapping your car's ride height over speed to calculate dynamic rake. 
- **Tire Temperature & Pressure Analysis**: Lap-by-lap breakdown of optimal tire operating windows.
- **Fuel & Setup Correlation**: Pinpoints the fastest laps of your stint and maps them to fuel loads and starting tire temps.
- **Sector Tire Temp Performance Graph**: Calculates empirical optimal tire temperatures for any sector by finding the actual fastest laps.
- **Custom Math Graphing Tool (Sandbox)**: Create custom formulas combining any telemetry channels, then instantly plot the results over a specific sector, a single lap, or the entire stint.
- **GTEC Preset Automator (Batch Report)**: Automatically loop through your favorite tools without UI prompts, generating a cleanly formatted `report.txt` and high-res PNG graphs directly to a new timestamped folder.

*Graphing features support 3 cycleable modes via the Settings menu: Legacy Matplotlib, Web-based Plotly, and Native CustomTkinter dark-mode interfaces.*

## Installation & Usage

You can download the standalone `.exe` version of this tool from the Releases folder. 
Upon launching `gtec.exe`, it will automatically check for dependencies, patch missing modules, and create a `telemetry/` directory. Drop your MoTeC `.ld` files into this directory, and the software will scan them and let you select sessions to analyze.

### To Run From Source:
1. Ensure you have Python 3 installed.
2. Clone this repository.
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the program:
   ```bash
   python gtec.py
   ```

*Note: Missing dependencies and internal modules (`ldparser`) will attempt to auto-patch themselves on startup.*

## Compiling
If you are modifying the code and want to compile your own standalone `.exe` for Windows, use PyInstaller:
```cmd
pyinstaller --onefile --paths "ldparser" --collect-all matplotlib --collect-all plotly --collect-all customtkinter gtec.py
```