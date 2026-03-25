import sys
import os
import time
import subprocess
import traceback

# We can import ui.splash because it has no 3rd party dependencies
import ui.splash as splash

# Run splash and check before global imports to prevent ModuleNotFoundError
if __name__ == "__main__":
    splash.show_splash_screen()

    spinner = ["|", "/", "-", "\\"]
    spinner_idx = 0
    
    is_frozen = getattr(sys, 'frozen', False)
    fatal_error = False
    
    def update_screen(text):
        global spinner_idx
        sys.stdout.write(f"\r  Initializing System {spinner[spinner_idx % len(spinner)]} \n  {text:<60}\033[F")
        sys.stdout.flush()
        spinner_idx += 1
        time.sleep(0.05)

    # Check numpy
    for _ in range(5): update_screen("Checking dependency: numpy...")
    try:
        import numpy
    except ImportError:
        if is_frozen:
            update_screen("Error: numpy missing from bundle!")
            fatal_error = True
            time.sleep(2)
        else:
            update_screen("Patching: installing numpy...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import numpy

    # Check pandas
    for _ in range(5): update_screen("Checking dependency: pandas...")
    try:
        import pandas
    except ImportError:
        if is_frozen:
            update_screen("Error: pandas missing from bundle!")
            fatal_error = True
            time.sleep(2)
        else:
            update_screen("Patching: installing pandas...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import pandas

    # Check matplotlib
    for _ in range(5): update_screen("Checking dependency: matplotlib...")
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        if is_frozen:
            update_screen("Error: matplotlib missing from bundle!")
            fatal_error = True
            time.sleep(2)
        else:
            update_screen("Patching: installing matplotlib...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "matplotlib"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import matplotlib.pyplot as plt

    # Check plotly
    for _ in range(5): update_screen("Checking dependency: plotly...")
    try:
        import plotly.express as px
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        if is_frozen:
            update_screen("Error: plotly missing from bundle!")
            fatal_error = True
            time.sleep(2)
        else:
            update_screen("Patching: installing plotly...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "plotly"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import plotly.express as px
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots

    # Check customtkinter
    for _ in range(5): update_screen("Checking dependency: customtkinter...")
    try:
        import customtkinter as ctk
    except ImportError:
        if is_frozen:
            update_screen("Error: customtkinter missing from bundle!")
            fatal_error = True
            time.sleep(2)
        else:
            update_screen("Patching: installing customtkinter...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import customtkinter as ctk

    # Check ldparser
    for _ in range(5): update_screen("Checking directory: ldparser...")
    if is_frozen:
        try:
            from ldparser import ldData
        except ImportError:
            update_screen("Error: ldparser missing from bundle!")
            fatal_error = True
            time.sleep(2)
    else:
        ld_path = os.path.join(os.getcwd(), 'ldparser', 'ldparser.py')
        if not os.path.exists(ld_path):
            update_screen("Patching: cloning ldparser repository...")
            subprocess.check_call(["git", "clone", "https://github.com/dchassin/ldparser.git"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    # Check telemetry folder (Always relative to the EXE location, not bundle)
    for _ in range(5): update_screen("Checking directory: telemetry...")
    if not os.path.exists("telemetry"):
        update_screen("Patching: creating telemetry directory...")
        os.makedirs("telemetry")

    if fatal_error:
        sys.stdout.write("\n\n")
        print("\n[!] FATAL ERROR: Required dependencies are missing from the executable.")
        print("    PyInstaller can only bundle packages installed in the environment")
        print("    where it is run. Please run the following command in Windows cmd:")
        print("    pip install numpy pandas matplotlib plotly customtkinter")
        print("    Then rebuild the EXE.")
        input("\nPress Enter to exit...")
        sys.exit(1)

    # Read telemetry files
    if os.path.exists("telemetry"):
        files = [f for f in os.listdir("telemetry") if f.lower().endswith(('.ld', '.id'))]
        for f in files:
            for _ in range(3): update_screen(f"Found file: {f[:50]}")

    # Final success message
    for _ in range(5): update_screen("All systems go.")
        
    sys.stdout.write("\n\n") # move past the second line so clear_screen doesn't look weird
    time.sleep(0.5)
    splash.clear_screen()

# Determine the base path (current dir or _MEIPASS for EXE)
base_path = getattr(sys, '_MEIPASS', os.getcwd())

# -------------------------------------------------------------
# Module Imports (Safe now that dependencies are verified)
# -------------------------------------------------------------
from core.config import get_gui_mode, set_gui_mode, save_config, load_config
from core.telemetry import load_telemetry, ldHead, ldData
from analysis.setup_viewer import run_setup_viewer
from analysis.roll_gradient import run_roll_analysis
from analysis.aero_rake import run_rake_analysis
from analysis.tire_performance import run_tire_analysis, run_sector_tire_analysis
from analysis.fuel_correlation import run_fuel_analysis
from analysis.math_sandbox import run_custom_math_graph
from analysis.automator import run_automator
from analysis.setup_prediction import run_setup_prediction_engine

def main():
    telemetry_dir = "telemetry"
    
    while True:
        if not os.path.exists(telemetry_dir):
            print(f"[!] Directory '{telemetry_dir}' not found. Please create it and add .ld files.")
            sys.exit(1)

        ld_files = [f for f in os.listdir(telemetry_dir) if f.lower().endswith(('.ld', '.id'))]
        
        if not ld_files:
            print(f"[!] No telemetry files (.ld or .id) found in '{telemetry_dir}'.")
            input("Press Enter to refresh or 'q' to quit...")
            continue

        print("\n  Scanning telemetry files for metadata... Please wait.")
        temp_files_info = []
        for f in ld_files:
            f_path = os.path.join(telemetry_dir, f)
            display_name = f
            laps_count = 0
            air_temp_str = "N/A"
            track_temp_str = "N/A"
            try:
                with open(f_path, 'rb') as f_obj:
                    h = ldHead.fromfile(f_obj)
                    driver = str(getattr(h, 'driver', '')).strip() or 'Unknown Driver'
                    car = str(getattr(h, 'vehicleid', '')).strip() or 'Unknown Car'
                    venue = str(getattr(h, 'venue', '')).strip() or 'Unknown Venue'
                    display_name = f"{driver} - {car} - {venue}"
                
                # Load data to get laps
                d = ldData.fromfile(f_path)
                if 'Lap' in d:
                    laps_count = len(set(d['Lap'].data))
                elif 'Lap Number' in d:
                    laps_count = len(set(d['Lap Number'].data))
                    
                # Load temperatures
                if 'AirTemp' in d:
                    air_temp_str = f"{d['AirTemp'].data[0]:.1f}°C"
                elif 'Air Temp' in d:
                    air_temp_str = f"{d['Air Temp'].data[0]:.1f}°C"
                    
                if 'TrackTemp' in d:
                    track_temp_str = f"{d['TrackTemp'].data[0]:.1f}°C"
                elif 'Track Temp' in d:
                    track_temp_str = f"{d['Track Temp'].data[0]:.1f}°C"
            except Exception:
                pass
            
            # Format the display name to include lap count and temps
            if laps_count > 0:
                display_name = f"{display_name} ({laps_count} Laps | Air: {air_temp_str} | Track: {track_temp_str})"
            else:
                display_name = f"{display_name} (Unknown Laps | Air: {air_temp_str} | Track: {track_temp_str})"
                
            temp_files_info.append((laps_count, f, display_name))
            
        # Sort by display name (alphabetical), then by lap count (biggest first)
        temp_files_info.sort(key=lambda x: (x[2].lower(), -x[0]))
        
        # Unpack back into ld_files and file_infos to keep rest of code working
        ld_files = [item[1] for item in temp_files_info]
        file_infos = [item[2] for item in temp_files_info]

        splash.show_home_screen()
        
        session_choice = input("\nSelect session type (number) or 'q' to quit: ").strip().lower()
        if session_choice == 'q':
            splash.show_exit_screen()
            return
        
        if session_choice == '4':
            splash.show_help_screen()
            continue
        
        if session_choice == '3':
            while True:
                splash.print_header("Settings")
                current_gui_mode = get_gui_mode()
                if current_gui_mode == 1:
                    status = "1 (Legacy Matplotlib)"
                elif current_gui_mode == 2:
                    status = "2 (Plotly Web Beta)"
                else:
                    status = "3 (CustomTkinter Beta)"
                    
                print(f"  1. Cycle GUI Mode    [Current: {status}]")
                print("═" * 64)
                s_choice = input("\nSelect an option to cycle (number) or 'p' to go back: ").strip().lower()
                if s_choice == 'p':
                    break
                elif s_choice == '1':
                    new_mode = current_gui_mode + 1
                    if new_mode > 3:
                        new_mode = 1
                    set_gui_mode(new_mode)
                    save_config({'gui_mode': new_mode})
                else:
                    print("[!] Invalid selection.")
                    time.sleep(1)
            continue
            
        if session_choice not in ('1', '2'):
            print("[!] Invalid selection.")
            time.sleep(1)
            continue
            
        is_multi = (session_choice == '2')
        selected_files = []
        go_back = False
        
        if not is_multi:
            splash.print_header("Telemetry Archive")
            for i, info in enumerate(file_infos):
                print(f"  {i + 1}. {info}")
            print("═" * 64)

            while True:
                choice = input("\nSelect a file to analyze (number), 'p' for previous menu, or 'q' to quit: ").strip().lower()
                if choice == 'q':
                    splash.show_exit_screen()
                    sys.exit(0)
                if choice == 'p':
                    go_back = True
                    break
                try:
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(ld_files):
                        selected_files.append(os.path.join(telemetry_dir, ld_files[choice_idx]))
                        break
                    else:
                        print("[!] Invalid selection.")
                except ValueError:
                    print("[!] Please enter a valid number.")
        else:
            while True:
                splash.print_header("Telemetry Archive (Multi-File)")
                for i, info in enumerate(file_infos):
                    print(f"  {i + 1}. {info}")
                print("═" * 64)
                if selected_files:
                    print(f"\nCurrently selected ({len(selected_files)}):")
                    for sf in selected_files:
                        print(f"  - {os.path.basename(sf)}")
                
                print("\nOptions:")
                print("  [Number] Select file to add")
                print("  [d]      Information sum met (done selecting)")
                print("  [p]      Previous menu")
                print("  [q]      Quit")
                
                choice = input("\nSelect an option: ").strip().lower()
                if choice == 'q':
                    splash.show_exit_screen()
                    sys.exit(0)
                if choice == 'p':
                    go_back = True
                    break
                if choice == 'd':
                    if len(selected_files) < 2:
                        print("[!] Please select at least two files for comparison.")
                        time.sleep(1)
                        continue
                    break
                    
                try:
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(ld_files):
                        file_path = os.path.join(telemetry_dir, ld_files[choice_idx])
                        if file_path not in selected_files:
                            selected_files.append(file_path)
                        else:
                            print("[!] File already selected.")
                            time.sleep(1)
                    else:
                        print("[!] Invalid selection.")
                        time.sleep(1)
                except ValueError:
                    print("[!] Please enter a valid option.")
                    time.sleep(1)

        if go_back:
            continue

        splash.clear_screen()
        sessions = []
        for file_path in selected_files:
            data, limit, channels, metadata = load_telemetry(file_path)
            sessions.append({
                'data': data,
                'limit': limit,
                'channels': channels,
                'metadata': metadata,
                'file_path': file_path
            })
        
        while True:
            splash.print_header("Analysis Tools")
            if len(sessions) == 1:
                print(f" File: {sessions[0]['file_path']}")
            else:
                print(f" Comparing {len(sessions)} files")
            print("═" * 64)
            print("  1. Roll Gradient Analysis")
            print("  2. Static Setup Viewer (alpha)")
            print("  3. Dynamic Aero/Rake Analyzer")
            print("  4. Tire Temperature & Pressure Analysis")
            print("  5. Fuel & Setup Correlation Analysis")
            print("  6. Sector Tire Temp Performance Graph")
            print("  7. Custom Math Graphing Tool (Sandbox)")
            print("  8. GTEC Preset Automator (Batch Report)")
            print("  9. Setup Prediction Engine (Alpha)")
            print("═" * 64)

            tool_choice = input("\nSelect a tool (number), 'p' for Main Menu, or 'q' to quit: ").strip().lower()
            if tool_choice == 'q':
                splash.show_exit_screen()
                return
            if tool_choice == 'p':
                break

            if tool_choice == '1':
                run_roll_analysis(sessions)
            elif tool_choice == '2':
                run_setup_viewer(sessions)
            elif tool_choice == '3':
                run_rake_analysis(sessions)
            elif tool_choice == '4':
                run_tire_analysis(sessions)
            elif tool_choice == '5':
                run_fuel_analysis(sessions)
            elif tool_choice == '6':
                run_sector_tire_analysis(sessions)
            elif tool_choice == '7':
                run_custom_math_graph(sessions)
            elif tool_choice == '8':
                run_automator(sessions)
            elif tool_choice == '9':
                run_setup_prediction_engine(sessions)
            else:
                print("[!] Invalid selection.")                
                print("\nPress Enter to try again...")

if __name__ == "__main__":
    if not getattr(sys, 'frozen', False):
        ld_path = os.path.join(os.getcwd(), 'ldparser')
        if ld_path not in sys.path:
            sys.path.insert(0, ld_path)
    try:
        main()
    except Exception as e:
        print("\n" + "!"*60)
        print(" FATAL ERROR DETECTED")
        print("!"*60)
        print(f"\nError: {e}")
        print("\nFull Traceback:")
        traceback.print_exc()
        print("\n" + "!"*60)
        input("\nPlease take a screenshot of this error and press Enter to exit...")
        sys.exit(1)
