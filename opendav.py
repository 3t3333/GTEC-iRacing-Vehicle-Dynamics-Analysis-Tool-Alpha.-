import sys
import os
import time
import subprocess
import traceback
import builtins

# PyInstaller Trace Helper (Never executed at runtime)
if False:
    import matplotx
    import matplotx.styles
    import matplotx.styles._aura
    import scipy.interpolate
    import scipy.stats
    import scipy.spatial
    # Force PyInstaller to see our internal analysis modules
    import analysis.aero_mapping
    import analysis.aero_rake
    import analysis.automator
    import analysis.downforce_mapping
    import analysis.math_sandbox
    import analysis.setup_prediction
    import analysis.setup_viewer
    import analysis.tire_fuel_windows
    import analysis.tire_performance

# Global Docked Overrides
_orig_print = builtins.print
_orig_input = builtins.input

def _docked_print(*args, sep=' ', end='\n', file=None, flush=False):
    if file is None or file is sys.stdout:
        text = sep.join(str(a) for a in args)
        lines = text.split('\n')
        # Only add padding to non-empty lines to prevent trailing spaces on empty lines
        docked_lines = [(" " * 23 + line) if line else "" for line in lines]
        _orig_print('\n'.join(docked_lines), end=end, file=file, flush=flush)
    else:
        _orig_print(*args, sep=sep, end=end, file=file, flush=flush)

def _docked_input(prompt=""):
    lines = prompt.split('\n')
    docked_lines = [(" " * 23 + line) if line else "" for line in lines]
    return _orig_input('\n'.join(docked_lines))

builtins.print = _docked_print
builtins.input = _docked_input

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
        sys.stdout.write(f"\r{' '*23}  Initializing System {spinner[spinner_idx % len(spinner)]} \n{' '*23}  {text:<60}\033[F")
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

    # Check scipy
    for _ in range(5): update_screen("Checking dependency: scipy...")
    try:
        import scipy
    except ImportError:
        if is_frozen:
            update_screen("Error: scipy missing from bundle!")
            fatal_error = True
            time.sleep(2)
        else:
            update_screen("Patching: installing scipy...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "scipy"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import scipy

    # Check matplotlib
    for _ in range(5): update_screen("Checking dependency: matplotlib...")
    try:
        import matplotlib.pyplot as plt
        import matplotx
    except ImportError:
        if is_frozen:
            update_screen("Error: matplotx missing from bundle!")
            fatal_error = True
            time.sleep(2)
        else:
            update_screen("Patching: installing matplotx...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "matplotx"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import matplotlib.pyplot as plt
            import matplotx

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
        print("    pip install numpy pandas scipy matplotlib matplotx plotly customtkinter")
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
sys.path.insert(0, base_path)

# -------------------------------------------------------------
# Module Imports (Safe now that dependencies are verified)
# -------------------------------------------------------------
import numpy as np
from core.config import get_gui_mode, set_gui_mode, save_config, load_config
from core.telemetry import load_telemetry, ldHead, ldData
from analysis.setup_viewer import run_setup_viewer
from analysis.aero_rake import run_rake_analysis
from analysis.tire_performance import run_tire_analysis, run_sector_tire_analysis
from analysis.tire_fuel_windows import run_tire_fuel_windows
from analysis.math_sandbox import run_custom_math_graph
from analysis.automator import run_automator
from analysis.tire_energy import run_tire_energy_profiler
from analysis.suspension_histograms import run_suspension_histograms

def main():
    telemetry_dir = "telemetry"
    
    while True:
        if not os.path.exists(telemetry_dir):
            print(f"[!] Directory '{telemetry_dir}' not found. Please create it and add .ld files.")
            sys.exit(1)

        from core.config import get_data_mode
        data_mode = get_data_mode()

        if data_mode == 1:
            allowed_exts = ('.ld', '.id', '.ibt')
            mode_name = "Auto-Detect"
        elif data_mode == 2:
            allowed_exts = ('.ld', '.id')
            mode_name = "Strict MoTeC"
        else:
            allowed_exts = ('.ibt',)
            mode_name = "Strict iRacing"

        ld_files = [f for f in os.listdir(telemetry_dir) if f.lower().endswith(allowed_exts)]

        if not ld_files:
            print(f"[!] No telemetry files {allowed_exts} found in '{telemetry_dir}'.")
            print(f"    Current Data Mode: {mode_name} (Change in Settings if needed)")
            input("\nPress Enter to refresh or 'q' to quit...")
            continue

        print(f"\n  Scanning telemetry files for metadata ({mode_name})... Please wait.")
        temp_files_info = []
        for f in ld_files:
            f_path = os.path.join(telemetry_dir, f)
            display_name = f
            laps_count = 0
            air_temp_str = "N/A"
            track_temp_str = "N/A"
            
            if f.lower().endswith('.ibt'):
                try:
                    from core import ibt_adapter
                    # Use meta_only=True for blazingly fast menu scanning
                    d = ibt_adapter.fromfile(f_path, meta_only=True)
                    driver = getattr(d.head, 'driver', 'iRacing User')
                    car = getattr(d.head, 'vehicleid', 'iRacing Car')
                    venue = getattr(d.head, 'venue', 'iRacing Track')
                    display_name = f"{driver} - {car} - {venue}"
                    
                    if 'Lap' in d:
                        laps_count = len(np.unique(d['Lap'].data))
                except Exception:
                    display_name = f"{f} [iRacing Telemetry]"
                    laps_count = 0
                
                temp_files_info.append((laps_count, f, display_name))
                continue

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
        
        session_choice = input("\nSelect option (number) or 'q' to quit: ").strip().lower()
        if session_choice == 'q':
            splash.show_exit_screen()
            return
        
        if session_choice == '2':
            from analysis.projects import run_project_manager
            run_project_manager()
            continue
        
        if session_choice == '3':
            splash.show_help_screen()
            continue
        
        if session_choice == '4':
            from ui.settings import show_settings
            show_settings()
            continue
        if session_choice != '1':
            print("[!] Invalid selection.")
            import time
            time.sleep(1)
            continue
            
        selected_files = []
        go_back = False
        
        splash.print_header("Telemetry Archive")
        for i, info in enumerate(file_infos):
            print(f"  {i + 1}. {info}")
        print("─" * 100)
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
            print("─" * 100)
            print("  1. Tire Energy & Work Profiler")
            print("  2. Static Setup Viewer (alpha)")
            print("  3. Dynamic Aero/Rake Analyzer")
            print("  4. Tire & Fuel Windows")
            print("  5. Sector Tire Temp & Load Mapping")
            print("  6. Custom Math Graphing Tool (Sandbox)")
            print("  7. Empirical Aero Map Generator (GUI Support)")
            print("  8. Downforce Mapping Module (GUI Support)")
            print("  9. Pitch Kinematics & Platform Analyzer")
            print("─" * 100)

            tool_choice = input("\nSelect a tool (number), 'p' for Main Menu, or 'q' to quit: ").strip().lower()
            if tool_choice == 'q':
                splash.show_exit_screen()
                return
            if tool_choice == 'p':
                break

            if tool_choice == '1':
                run_tire_energy_profiler(sessions)
            elif tool_choice == '2':
                run_setup_viewer(sessions)
            elif tool_choice == '3':
                run_rake_analysis(sessions)
            elif tool_choice == '4':
                run_tire_fuel_windows(sessions)
            elif tool_choice == '5':
                run_sector_tire_analysis(sessions)
            elif tool_choice == '6':
                run_custom_math_graph(sessions)
            elif tool_choice == '7':
                from analysis.aero_mapping import run_aero_mapping
                run_aero_mapping(sessions)
            elif tool_choice == '8':
                from analysis.downforce_mapping import run_downforce_mapping
                run_downforce_mapping(sessions)
            elif tool_choice == '9':
                from analysis.pitch_kinematics import run_pitch_analyzer
                run_pitch_analyzer(sessions)
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
