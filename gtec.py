import sys
import os
import time
import subprocess

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_splash_screen():
    clear_screen()
    
    # ASCII Art Lines
    lines = [
        r"      ____ _____ _____ ____  ",
        r"     / ___|_   _| ____/ ___| ",
        r"    | |  _  | | |  _|| |     ",
        r"    | |_| | | | | |__| |___  ",
        r"     \____| |_| |_____\____| ",
        r"                             ",
        r"    GTEC Analysis Software   ",
        r"    (c) Gomez Systems Group  "
    ]

    # Cyan (0, 255, 255) to Pink (255, 105, 180) gradient logic
    # We will interpolate between these two colors for each line
    start_rgb = (0, 255, 255)  # Cyan
    end_rgb = (255, 20, 147)   # Deep Pink
    
    for i, line in enumerate(lines):
        # Calculate interpolation ratio (0.0 to 1.0)
        ratio = i / (len(lines) - 1)
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
        
        # Apply 24-bit foreground color escape sequence: \033[38;2;R;G;Bm
        sys.stdout.write(f"\033[38;2;{r};{g};{b}m{line}\033[0m\n")
    
    spinner = ["|", "/", "-", "\\"]
    spinner_idx = 0
    sys.stdout.write("\n")
    
    is_frozen = getattr(sys, 'frozen', False)
    fatal_error = False
    
    def update_screen(text):
        nonlocal spinner_idx
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
    clear_screen()

# Run splash and check before global imports to prevent ModuleNotFoundError
if __name__ == "__main__":
    show_splash_screen()

# Determine the base path (current dir or _MEIPASS for EXE)
base_path = getattr(sys, '_MEIPASS', os.getcwd())

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import json

CONFIG_FILE = 'gtec_config.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(conf):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(conf, f)
    except:
        pass

GUI_MODE = load_config().get('gui_mode', 1) # 1=Legacy, 2=Plotly, 3=CustomTkinter

def show_ctk_graph(fig, title):
    ctk.set_appearance_mode("Dark")
    app = ctk.CTk()
    app.geometry("1100x750")
    app.title(title)
    
    canvas = FigureCanvasTkAgg(fig, master=app)
    canvas.draw()
    canvas.get_tk_widget().pack(side=ctk.TOP, fill=ctk.BOTH, expand=True)
    
    toolbar = NavigationToolbar2Tk(canvas, app)
    toolbar.update()
    canvas.get_tk_widget().pack(side=ctk.TOP, fill=ctk.BOTH, expand=True)
    
    app.mainloop()

# Ensure ldparser is accessible
if not getattr(sys, 'frozen', False):
    ld_path = os.path.join(os.getcwd(), 'ldparser')
    if ld_path not in sys.path:
        sys.path.insert(0, ld_path)

try:
    from ldparser import ldData, ldHead
except ImportError as e:
    print(f"\n[!] ERROR: Failed to import ldparser modules: {e}")
    print(f"    Check that you built the EXE using: pyinstaller --onefile --paths \"ldparser\" gtec.py")
    input("\nPress Enter to exit...")
    sys.exit(1)

def show_exit_screen():
    clear_screen()
    
    # ASCII Art Lines
    lines = [
        r"      ____ _____ _____ ____  ",
        r"     / ___|_   _| ____/ ___| ",
        r"    | |  _  | | |  _|| |     ",
        r"    | |_| | | | | |__| |___  ",
        r"     \____| |_| |_____\____| ",
        r"                             ",
        r"    GTEC Analysis Software   ",
        r"    (c) Gomez Systems Group  "
    ]

    start_rgb = (0, 255, 255)  # Cyan
    end_rgb = (255, 20, 147)   # Deep Pink
    
    for i, line in enumerate(lines):
        ratio = i / (len(lines) - 1)
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
        sys.stdout.write(f"\033[38;2;{r};{g};{b}m{line}\033[0m\n")
    
    sys.stdout.write("\n")
    spinner = ["|", "/", "-", "\\"]
    end_time = time.time() + 2
    i = 0
    while time.time() < end_time:
        sys.stdout.write(f"\r  Shutting Down System {spinner[i % len(spinner)]} ")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    print("\n\n  ")
    time.sleep(0.5)

def load_telemetry(file_path):
    print(f"[*] Loading {file_path}...")
    try:
        data = ldData.fromfile(file_path)
        
        # Identify standard channels
        lap_ch = 'Lap' if 'Lap' in data else 'Lap Number'
        dist_ch = 'Lap Distance' if 'Lap Distance' in data else 'LapDist'
        long_g_ch = 'G Force Long' if 'G Force Long' in data else 'LongAccel'
        lat_g_ch = 'G Force Lat' if 'G Force Lat' in data else 'LatAccel'
        time_ch = 'SessionTime'
        
        # Calculate Global Limit
        comb_g_all = np.sqrt(data[long_g_ch].data**2 + data[lat_g_ch].data**2)
        global_limit = np.max(comb_g_all)
        
        return data, global_limit, {
            'lap': lap_ch, 'dist': dist_ch, 'long': long_g_ch, 
            'lat': lat_g_ch, 'time': time_ch
        }
    except Exception as e:
        print(f"[!] Error loading file: {e}")
        sys.exit(1)

def perform_analysis(data, limit, channels, start_m, end_m):
    laps = np.unique(data[channels['lap']].data)
    results = []
    
    # Pre-extract data for performance
    lap_arr = data[channels['lap']].data
    dist_arr = data[channels['dist']].data
    time_arr = data[channels['time']].data
    long_arr = data[channels['long']].data
    lat_arr = data[channels['lat']].data
    comb_arr = np.sqrt(long_arr**2 + lat_arr**2)
    
    for lap in laps:
        idx = np.where(lap_arr == lap)[0]
        if len(idx) < 100: continue
        
        l_dist = dist_arr[idx]
        
        # Window Mask
        mask = (l_dist >= start_m) & (l_dist <= end_m)
        if not np.any(mask): continue
        
        # Metrics
        w_time = time_arr[idx][mask]
        w_comb = comb_arr[idx][mask]
        
        duration = w_time[-1] - w_time[0]
        peak_util = (np.max(w_comb) / limit) * 100
        avg_util = (np.mean(w_comb) / limit) * 100
        
        results.append({
            'Lap': int(lap),
            'Time': duration,
            'Peak': peak_util,
            'Avg': avg_util
        })
    
    return results

def get_static_val(data, possible_names, multiplier=1.0, fmt="{:.1f}", unit=""):
    for name in possible_names:
        if name in data:
            val = data[name].data[0] * multiplier
            return f"{fmt.format(val)} {unit}".strip()
    return "N/A (Not logged)"

def run_setup_viewer(sessions):
    while True:
        clear_screen()
        print("="*60)
        print(" GteC | Static Setup Viewer (alpha)")
        print("="*60)
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            print(f"\n File: {os.path.basename(file_path)}")
            print("-" * 60)
            
            # Pressures
            fl_p = get_static_val(data, ['dpLFTireColdPress', 'LFcoldPressure'], multiplier=0.145038, fmt="{:.1f}", unit="psi")
            fr_p = get_static_val(data, ['dpRFTireColdPress', 'RFcoldPressure'], multiplier=0.145038, fmt="{:.1f}", unit="psi")
            rl_p = get_static_val(data, ['dpLRTireColdPress', 'LRcoldPressure'], multiplier=0.145038, fmt="{:.1f}", unit="psi")
            rr_p = get_static_val(data, ['dpRRTireColdPress', 'RRcoldPressure'], multiplier=0.145038, fmt="{:.1f}", unit="psi")
            
            # Ride heights
            fl_rh = get_static_val(data, ['Ride Height FL', 'LFrideHeight'], multiplier=1000, fmt="{:.1f}", unit="mm")
            fr_rh = get_static_val(data, ['Ride Height FR', 'RFrideHeight'], multiplier=1000, fmt="{:.1f}", unit="mm")
            rl_rh = get_static_val(data, ['Ride Height RL', 'LRrideHeight'], multiplier=1000, fmt="{:.1f}", unit="mm")
            rr_rh = get_static_val(data, ['Ride Height RR', 'RRrideHeight'], multiplier=1000, fmt="{:.1f}", unit="mm")
            
            # Brake Bias
            bb = get_static_val(data, ['dcBrakeBias', 'Brake Bias', 'BrakeBias'], fmt="{:.2f}", unit="%")
            
            # Compound
            comp = get_static_val(data, ['PlayerTireCompound', 'PitSvTireCompound'], fmt="{}", unit="")
            if comp == "0.0": comp = "Dry"
            elif comp == "1.0": comp = "Wet"

            # Try to get wing, camber, spring if they exist
            wing = get_static_val(data, ['RearWing', 'Rear Wing', 'WingAngle', 'RearWingAngle'], fmt="{:.1f}", unit="")
            fl_camb = get_static_val(data, ['Camber FL', 'LFcamber'], fmt="{:.2f}", unit="deg")
            fl_spring = get_static_val(data, ['Spring FL', 'LFspring'], fmt="{:.1f}", unit="N/mm")

            print("[ TIRES & PRESSURES ]")
            print(f"  Compound:        {comp}")
            print(f"  Cold Pressures:  FL: {fl_p:<10} | FR: {fr_p}")
            print(f"                   RL: {rl_p:<10} | RR: {rr_p}")
            print("\n[ AERODYNAMICS & CHASSIS ]")
            print(f"  Ride Heights:    FL: {fl_rh:<10} | FR: {fr_rh}")
            print(f"                   RL: {rl_rh:<10} | RR: {rr_rh}")
            print(f"  Rear Wing:       {wing}")
            print("\n[ SUSPENSION & BRAKES ]")
            print(f"  Spring Rates:    {fl_spring}")
            print(f"  Camber:          {fl_camb}")
            print(f"  Brake Bias:      {bb}")
            print("-" * 60)

        print("\n" + "="*60)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            show_exit_screen()
            sys.exit(0)
        break

def run_roll_analysis(sessions):
    while True:
        clear_screen()
        print("="*60)
        print(" GteC | Roll Gradient Analysis")
        print("="*60)
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            print(f"\nAnalyzing: {os.path.basename(file_path)}")
            
            # Find lateral G channel
            lat_g_ch = None
            for ch in ['G Force Lat', 'LatAccel', 'LatG']:
                if ch in data:
                    lat_g_ch = ch
                    break
                    
            if not lat_g_ch:
                print("  [!] Could not find Lateral G channel.")
                continue

            # Ride height channels
            fl_ch, fr_ch = 'Ride Height FL', 'Ride Height FR'
            rl_ch, rr_ch = 'Ride Height RL', 'Ride Height RR'
            
            required = [fl_ch, fr_ch, rl_ch, rr_ch]
            missing = [ch for ch in required if ch not in data]
            if missing:
                print(f"  [!] Missing required channels: {missing}")
                continue

            # Load and convert to mm
            lat_g = data[lat_g_ch].data
            fl = data[fl_ch].data * 1000
            fr = data[fr_ch].data * 1000
            rl = data[rl_ch].data * 1000
            rr = data[rr_ch].data * 1000

            front_roll_mm = fl - fr
            rear_roll_mm = rl - rr

            # Filter for significant cornering
            mask = np.abs(lat_g) > 0.5
            
            if not np.any(mask):
                print("  [!] Not enough cornering data to calculate roll gradient.")
                continue
                
            cornering_lat_g = lat_g[mask]
            cornering_front_roll = front_roll_mm[mask]
            cornering_rear_roll = rear_roll_mm[mask]

            # Calculate Fastest Lap
            channels = session['channels']
            lap_arr = data[channels['lap']].data
            time_arr = data[channels['time']].data
            laps = np.unique(lap_arr)
            lap_times = []
            for lap in laps:
                idx = np.where(lap_arr == lap)[0]
                if len(idx) < 100: continue
                lap_times.append(time_arr[idx][-1] - time_arr[idx][0])
            
            fastest_str = ""
            if lap_times:
                median_time = np.median(lap_times)
                valid_times = [t for t in lap_times if t >= median_time * 0.89]
                if valid_times:
                    fastest_time = min(valid_times)
                    PINK = '\033[95m'
                    RESET = '\033[0m'
                    fastest_str = f"\n  {PINK}Fastest Lap: {fastest_time:.3f} s{RESET}"

            # Linear regression (y = mx + c) to find gradient
            try:
                front_m, _ = np.polyfit(cornering_lat_g, cornering_front_roll, 1)
                rear_m, _ = np.polyfit(cornering_lat_g, cornering_rear_roll, 1)
                
                total_gradient = abs(front_m) + abs(rear_m)
                if total_gradient == 0:
                    print("  [!] Calculated zero roll (is data valid?).")
                    continue
                    
                front_dist = (abs(front_m) / total_gradient) * 100
                rear_dist = (abs(rear_m) / total_gradient) * 100
                
                print("  " + "-" * 40)
                print(f"  Front Roll Gradient: {abs(front_m):.2f} mm/G")
                print(f"  Rear Roll Gradient:  {abs(rear_m):.2f} mm/G")
                print("  " + "-" * 40)
                print("  Roll Balance (Higher % = Softer end):")
                print(f"  Front: {front_dist:.1f}% | Rear: {rear_dist:.1f}%")
                if fastest_str:
                    print(fastest_str)
            except Exception as e:
                print(f"  [!] Error calculating gradient: {e}")

        print("\n" + "="*60)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            show_exit_screen()
            sys.exit(0)
        break

def run_rake_analysis(sessions):
    while True:
        clear_screen()
        print("="*60)
        print(" GteC | Dynamic Aero/Rake Analyzer")
        print("="*60)
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            print(f"\nAnalyzing: {os.path.basename(file_path)}")
            
            # Find speed channel
            speed_ch = None
            for ch in ['Speed', 'Ground Speed']:
                if ch in data:
                    speed_ch = ch
                    break
                    
            if not speed_ch:
                print("  [!] Could not find Speed channel.")
                continue

            # Ride height channels
            fl_ch, fr_ch = 'Ride Height FL', 'Ride Height FR'
            rl_ch, rr_ch = 'Ride Height RL', 'Ride Height RR'
            
            required = [fl_ch, fr_ch, rl_ch, rr_ch]
            missing = [ch for ch in required if ch not in data]
            if missing:
                print(f"  [!] Missing required channels: {missing}")
                continue
                
            # Lat/Long G to filter
            lat_g_ch, long_g_ch = None, None
            for ch in ['G Force Lat', 'LatAccel', 'LatG']:
                if ch in data: lat_g_ch = ch; break
            for ch in ['G Force Long', 'LongAccel', 'LongG']:
                if ch in data: long_g_ch = ch; break

            if not lat_g_ch or not long_g_ch:
                print("  [!] Missing G channels for filtering.")
                continue

            # Convert speed to mph
            max_speed_raw = np.max(data[speed_ch].data)
            if max_speed_raw > 150: # Assume km/h
                speed = data[speed_ch].data * 0.621371
            else: # Assume m/s
                speed = data[speed_ch].data * 2.23694
                
            fl = data[fl_ch].data * 1000
            fr = data[fr_ch].data * 1000
            rl = data[rl_ch].data * 1000
            rr = data[rr_ch].data * 1000
            
            lat_g = data[lat_g_ch].data
            long_g = data[long_g_ch].data

            front_rh = (fl + fr) / 2.0
            rear_rh = (rl + rr) / 2.0
            rake = rear_rh - front_rh

            # Filter for straights (Lat G near 0, Long G relatively steady, not heavy braking)
            mask = (np.abs(lat_g) < 0.2) & (long_g > -0.5) & (speed > 40)
            
            if not np.any(mask):
                print("  [!] Not enough straight line data to calculate dynamic rake.")
                continue
                
            straight_speed = speed[mask]
            straight_rake = rake[mask]

            # Perform linear regression to get mm/mph
            rake_m, rake_c = np.polyfit(straight_speed, straight_rake, 1)

            print(f"  Max Speed: {np.max(speed):.1f} mph")
            
            PINK = '\033[95m'
            RESET = '\033[0m'
            print(f"  {PINK}Rake Adjustment: {rake_m:+.4f} mm/mph{RESET}")
            
            print("\n  Modeled Rake at speeds:")
            for s in [50, 100, 150, np.max(speed)]:
                r = rake_m * s + rake_c
                if s == np.max(speed):
                    print(f"  @ {s:3.0f} mph (Max): {r:5.1f} mm")
                else:
                    print(f"  @ {s:3} mph:       {r:5.1f} mm")
            print("  " + "-" * 40)
            
            # Interactive Graphing Feature
            ans = input("\n  Launch interactive scatter plot for this session? (y/n): ").strip().lower()
            if ans == 'y':
                print("  [+] Building interactive graph... (Close the graph window to continue)")
                
                # We style it to match the splash screen aesthetic
                if GUI_MODE == 2:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=straight_speed, y=straight_rake, mode='markers',
                                             marker=dict(color='cyan', size=4, opacity=0.4),
                                             name='Telemetry Data'))
                    x_vals = np.array([min(straight_speed), max(straight_speed)])
                    y_vals = rake_m * x_vals + rake_c
                    fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines',
                                             line=dict(color='deeppink', width=3),
                                             name=f'Trend: {rake_m:+.4f} mm/mph'))
                    
                    fig.update_layout(
                        title=f"Dynamic Aero/Rake Correlation<br>{os.path.basename(file_path)}",
                        xaxis_title="Speed (mph)",
                        yaxis_title="Rake (mm) [Rear - Front]",
                        template="plotly_dark",
                        font=dict(family="Consolas", size=13)
                    )
                    fig.show()
                else:
                    plt.style.use('dark_background')
                    plt.rcParams['font.family'] = 'Consolas'
                    fig = plt.figure(figsize=(12, 7), num='GTEC - Dynamic Rake Analyzer')
    
                    # Scatter the raw straightaway data
                    plt.scatter(straight_speed, straight_rake, alpha=0.4, label='Telemetry Data', color='cyan', s=4)
    
                    # Plot the linear regression trend line
                    x_vals = np.array([min(straight_speed), max(straight_speed)])
                    y_vals = rake_m * x_vals + rake_c
                    plt.plot(x_vals, y_vals, color='deeppink', linewidth=1, label=f'Trend: {rake_m:+.4f} mm/mph')
    
                    # Styling
                    plt.title(f"Dynamic Aero/Rake Correlation\n{os.path.basename(file_path)}", fontsize=16, fontweight='bold', pad=20)
                    plt.xlabel("Speed (mph)", fontsize=13)
                    plt.ylabel("Rake (mm) [Rear - Front]", fontsize=13)
                    plt.xticks(fontsize=11)
                    plt.yticks(fontsize=11)
                    plt.legend(fontsize=11, frameon=True, shadow=True)
                    plt.grid(True, linestyle='--', alpha=0.3)
    
                    plt.tight_layout()
                    
                    if GUI_MODE == 3:
                        show_ctk_graph(fig, "GTEC - Dynamic Rake Analyzer")
                    else:
                        plt.show()
        print("\n" + "="*60)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            show_exit_screen()
            sys.exit(0)
        break

def run_sector_analysis(sessions):
    while True:
        clear_screen()
        print("="*60)
        if len(sessions) == 1:
            print(f" GteC | Limit: {sessions[0]['limit']:.3f}G")
            print("="*60)
            print(f" File: {os.path.basename(sessions[0]['file_path'])}")
        else:
            print(" GteC | Multi-File Sector Analysis")
            print("="*60)
            print(f" Files: {len(sessions)} selected")
        print(f" Tool: Sector Analysis")
        print("-"*60)
        
        try:
            inp = input("\nEnter window (e.g., '142-316' or 'fl' for full lap), 'p' for Tools Menu, or 'q' to quit: ").strip().lower()
            if inp == 'q':
                show_exit_screen()
                sys.exit(0)
            if inp == 'p':
                break
            
            is_full_lap = False
            if inp == 'fl':
                is_full_lap = True
                start_m, end_m = 0.0, 0.0 # placeholders
            elif '-' not in inp:
                print("[!] Invalid format. Use 'Start-End' or 'fl'.")
                input("\nPress Enter to try again...")
                continue
            else:
                start_m, end_m = map(float, inp.split('-'))
            
            for session in sessions:
                data = session['data']
                limit = session['limit']
                channels = session['channels']
                file_path = session['file_path']
                
                if is_full_lap:
                    dist_arr = data[channels['dist']].data
                    start_m = 0.0
                    end_m = float(np.max(dist_arr))

                results = perform_analysis(data, limit, channels, start_m, end_m)
                
                if not results:
                    print(f"\n[!] No data found for range {start_m}m to {end_m}m in {os.path.basename(file_path)}.")
                else:
                    air_temp_str = "N/A"
                    track_temp_str = "N/A"
                    if 'AirTemp' in data:
                        air_temp_str = f"{data['AirTemp'].data[0]:.1f}°C"
                    elif 'Air Temp' in data:
                        air_temp_str = f"{data['Air Temp'].data[0]:.1f}°C"
                        
                    if 'TrackTemp' in data:
                        track_temp_str = f"{data['TrackTemp'].data[0]:.1f}°C"
                    elif 'Track Temp' in data:
                        track_temp_str = f"{data['Track Temp'].data[0]:.1f}°C"

                    print(f"\nRESULTS FOR {start_m}m to {end_m}m [{os.path.basename(file_path)} | Air: {air_temp_str} | Track: {track_temp_str}]:")
                    print("-" * 55)
                    print(f"{'Lap':<6} | {'Time (s)':<10} | {'Peak Util%':<12} | {'Avg Util%':<10}")
                    print("-" * 55)
                    
                    # Use median to avoid unusually slow laps (spins/traffic) skewing the threshold
                    median_time = np.median([r['Time'] for r in results])
                    valid_times = [r['Time'] for r in results if r['Time'] >= median_time * 0.89]
                    fastest_time = min(valid_times) if valid_times else None
                    
                    PINK = '\033[95m'
                    RESET = '\033[0m'
                    
                    for r in sorted(results, key=lambda x: x['Time']):
                        row_str = f"{r['Lap']:<6} | {r['Time']:<10.3f} | {r['Peak']:<11.1f}% | {r['Avg']:<10.1f}%"
                        if r['Time'] == fastest_time:
                            print(f"{PINK}{row_str} < FASTEST{RESET}")
                        else:
                            print(row_str)
                
            input("\nPress Enter for a new analysis...")
            
        except ValueError:
            print("[!] Please enter valid numbers.")
            input("\nPress Enter to try again...")
        except KeyboardInterrupt:
            sys.exit(0)

def run_tire_analysis(sessions):
    while True:
        clear_screen()
        print("="*60)
        print(" GteC | Tire Temperature & Pressure Analysis")
        print("="*60)
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            channels = session['channels']
            print(f"\nAnalyzing: {os.path.basename(file_path)}")
            
            # Find Tire Temp Channels
            fl_t_chs = [ch for ch in ['Tyre Temp FL Inner', 'Tyre Temp FL Centre', 'Tyre Temp FL Outer', 'LFtempL', 'LFtempM', 'LFtempR'] if ch in data]
            fr_t_chs = [ch for ch in ['Tyre Temp FR Inner', 'Tyre Temp FR Centre', 'Tyre Temp FR Outer', 'RFtempL', 'RFtempM', 'RFtempR'] if ch in data]
            rl_t_chs = [ch for ch in ['Tyre Temp RL Inner', 'Tyre Temp RL Centre', 'Tyre Temp RL Outer', 'LRtempL', 'LRtempM', 'LRtempR'] if ch in data]
            rr_t_chs = [ch for ch in ['Tyre Temp RR Inner', 'Tyre Temp RR Centre', 'Tyre Temp RR Outer', 'RRtempL', 'RRtempM', 'RRtempR'] if ch in data]
            
            # Find Tire Pressure Channels
            fl_p_ch = next((ch for ch in ['Tyre Pres FL', 'LFpressure', 'dpLFTireColdPress'] if ch in data), None)
            fr_p_ch = next((ch for ch in ['Tyre Pres FR', 'RFpressure', 'dpRFTireColdPress'] if ch in data), None)
            rl_p_ch = next((ch for ch in ['Tyre Pres RL', 'LRpressure', 'dpLRTireColdPress'] if ch in data), None)
            rr_p_ch = next((ch for ch in ['Tyre Pres RR', 'RRpressure', 'dpRRTireColdPress'] if ch in data), None)

            if not (fl_t_chs and fr_t_chs and rl_t_chs and rr_t_chs):
                print("  [!] Missing required tire temperature channels.")
                continue

            lap_arr = data[channels['lap']].data
            time_arr = data[channels['time']].data
            laps = np.unique(lap_arr)
            lap_data = []

            def get_temp_stats(chs, idx):
                temps = np.mean([data[ch].data[idx] for ch in chs], axis=0)
                return np.mean(temps), np.max(temps)

            for lap in laps:
                idx = np.where(lap_arr == lap)[0]
                if len(idx) < 100: continue
                lap_time = time_arr[idx][-1] - time_arr[idx][0]
                
                fl_t_avg, fl_t_peak = get_temp_stats(fl_t_chs, idx)
                fr_t_avg, fr_t_peak = get_temp_stats(fr_t_chs, idx)
                rl_t_avg, rl_t_peak = get_temp_stats(rl_t_chs, idx)
                rr_t_avg, rr_t_peak = get_temp_stats(rr_t_chs, idx)

                avg_temp = np.mean([fl_t_avg, fr_t_avg, rl_t_avg, rr_t_avg])
                peak_temp = np.max([fl_t_peak, fr_t_peak, rl_t_peak, rr_t_peak])
                
                fl_p = np.mean(data[fl_p_ch].data[idx]) if fl_p_ch else 0
                fr_p = np.mean(data[fr_p_ch].data[idx]) if fr_p_ch else 0
                rl_p = np.mean(data[rl_p_ch].data[idx]) if rl_p_ch else 0
                rr_p = np.mean(data[rr_p_ch].data[idx]) if rr_p_ch else 0
                
                avg_press = np.mean([fl_p, fr_p, rl_p, rr_p])
                if avg_press > 100:  # Assuming kPa and converting to psi
                    avg_press *= 0.145038

                lap_data.append({
                    'lap': int(lap),
                    'time': lap_time,
                    'avg_temp': avg_temp,
                    'peak_temp': peak_temp,
                    'avg_press': avg_press
                })

            if not lap_data:
                print("  [!] No valid lap data found.")
                continue

            # Identify valid laps
            median_time = np.median([ld['time'] for ld in lap_data])
            valid_laps = [ld for ld in lap_data if median_time * 0.89 <= ld['time'] <= median_time * 1.11]

            if not valid_laps:
                print("  [!] Not enough valid laps to determine optimal settings.")
                continue

            valid_laps.sort(key=lambda x: x['time'])
            fastest_lap = valid_laps[0]

            PINK = '\033[95m'
            RESET = '\033[0m'
            
            print(f"\n  {PINK}[ OPTIMAL SETUP (Based on fastest lap {fastest_lap['lap']}) ]{RESET}")
            print(f"  Fastest Time:     {fastest_lap['time']:.3f} s")
            print(f"  Optimal Avg Temp: {fastest_lap['avg_temp']:.1f}°C")
            print(f"  Optimal Peak Temp:{fastest_lap['peak_temp']:.1f}°C")
            print(f"  Optimal Avg Press:{fastest_lap['avg_press']:.1f} psi")

            print("\n  [ TEMPERATURE SPREAD ACROSS ALL LAPS ]")
            print(f"  {'Lap':<5} | {'Time (s)':<10} | {'Avg Temp':<10} | {'Peak Temp':<10} | {'Avg Press':<10}")
            print("  " + "-" * 60)
            
            times = [ld['time'] for ld in valid_laps]
            min_t, max_t = min(times), max(times)
            range_t = max_t - min_t if max_t != min_t else 1

            for ld in valid_laps:
                ratio = (ld['time'] - min_t) / range_t
                if ratio < 0.33:
                    color = '\033[92m' # Green
                elif ratio < 0.66:
                    color = '\033[93m' # Yellow
                else:
                    color = '\033[91m' # Red
                
                print(f"  {color}{ld['lap']:<5} | {ld['time']:<10.3f} | {ld['avg_temp']:<8.1f}°C | {ld['peak_temp']:<8.1f}°C | {ld['avg_press']:<8.1f} psi{RESET}")

        print("\n" + "="*60)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            show_exit_screen()
            sys.exit(0)
        break

def run_sector_tire_analysis(sessions):
    while True:
        clear_screen()
        print("="*60)
        print(" GteC | Sector Tire Temp Performance Graph")
        print("="*60)
        
        try:
            inp = input("\nEnter window (e.g., '142-316' or 'fl' for full lap), 'p' for Tools Menu, or 'q' to quit: ").strip().lower()
            if inp == 'q':
                show_exit_screen()
                sys.exit(0)
            if inp == 'p':
                break
            
            is_full_lap = False
            if inp == 'fl':
                is_full_lap = True
                start_m, end_m = 0.0, 0.0 # placeholders
            elif '-' not in inp:
                print("[!] Invalid format. Use 'Start-End' or 'fl'.")
                input("\nPress Enter to try again...")
                continue
            else:
                start_m, end_m = map(float, inp.split('-'))
            
            for session in sessions:
                data = session['data']
                channels = session['channels']
                file_path = session['file_path']
                
                print(f"\nAnalyzing: {os.path.basename(file_path)}")
                
                # Find Tire Temp Channels
                fl_t_chs = [ch for ch in ['Tyre Temp FL Inner', 'Tyre Temp FL Centre', 'Tyre Temp FL Outer', 'LFtempL', 'LFtempM', 'LFtempR'] if ch in data]
                fr_t_chs = [ch for ch in ['Tyre Temp FR Inner', 'Tyre Temp FR Centre', 'Tyre Temp FR Outer', 'RFtempL', 'RFtempM', 'RFtempR'] if ch in data]
                rl_t_chs = [ch for ch in ['Tyre Temp RL Inner', 'Tyre Temp RL Centre', 'Tyre Temp RL Outer', 'LRtempL', 'LRtempM', 'LRtempR'] if ch in data]
                rr_t_chs = [ch for ch in ['Tyre Temp RR Inner', 'Tyre Temp RR Centre', 'Tyre Temp RR Outer', 'RRtempL', 'RRtempM', 'RRtempR'] if ch in data]
                
                all_t_chs = fl_t_chs + fr_t_chs + rl_t_chs + rr_t_chs
                
                if not all_t_chs:
                    print("  [!] Missing required tire temperature channels.")
                    continue

                lap_arr = data[channels['lap']].data
                dist_arr = data[channels['dist']].data
                time_arr = data[channels['time']].data
                
                if is_full_lap:
                    start_m = 0.0
                    end_m = float(np.max(dist_arr))
                laps = np.unique(lap_arr)
                lap_data = []

                for lap in laps:
                    idx = np.where(lap_arr == lap)[0]
                    if len(idx) < 100: continue
                    
                    l_dist = dist_arr[idx]
                    
                    # Window Mask
                    mask = (l_dist >= start_m) & (l_dist <= end_m)
                    if not np.any(mask): continue
                    
                    w_time = time_arr[idx][mask]
                    duration = w_time[-1] - w_time[0]
                    
                    # Get average tire temperature in the sector across all available sensors
                    temps = []
                    for ch in all_t_chs:
                        ch_data = data[ch].data[idx][mask]
                        temps.append(np.mean(ch_data))
                    
                    avg_temp = np.mean(temps)
                    lap_data.append({
                        'lap': int(lap),
                        'time': duration,
                        'temp': avg_temp
                    })

                if not lap_data:
                    print("  [!] No valid data found for that window.")
                    continue

                # Identify valid laps (filter out heavy traffic/spins)
                median_time = np.median([ld['time'] for ld in lap_data])
                valid_laps = [ld for ld in lap_data if median_time * 0.85 <= ld['time'] <= median_time * 1.15]

                if len(valid_laps) < 3:
                    print("  [!] Not enough valid laps to build a correlation graph.")
                    continue

                temps = np.array([ld['temp'] for ld in valid_laps])
                times = np.array([ld['time'] for ld in valid_laps])
                
                print(f"  [+] Found {len(valid_laps)} valid laps. Ready to graph.")

                ans = input(f"\n  Launch interactive scatter plot for {os.path.basename(file_path)}? (y/n): ").strip().lower()
                if ans == 'y':
                    print("  [+] Building interactive graph... (Close the graph window to continue)")
                    
                    if GUI_MODE == 2:
                        fig = go.Figure()
                        
                        fig.add_trace(go.Scatter(x=temps, y=times, mode='markers',
                                                 marker=dict(color='cyan', size=10, opacity=0.8),
                                                 name='Lap Data'))
                                                 
                        # Empirical Optimal Temp
                        sorted_indices = np.argsort(times)
                        top_n = min(3, len(times))
                        fastest_laps_idx = sorted_indices[:top_n]
                        
                        emp_opt_temp = np.mean(temps[fastest_laps_idx])
                        emp_opt_time = np.mean(times[fastest_laps_idx])
                        
                        fig.add_trace(go.Scatter(x=[emp_opt_temp], y=[emp_opt_time], mode='markers',
                                                 marker=dict(color='yellow', size=20, symbol='star'),
                                                 name=f'Optimal (Top {top_n} Avg): {emp_opt_temp:.1f}°C'))
                        
                        fig.add_vline(x=emp_opt_temp, line=dict(color='yellow', dash='dot'), opacity=0.5)

                        try:
                            coeffs = np.polyfit(temps, times, 2)
                            p = np.poly1d(coeffs)
                            
                            x_curve = np.linspace(min(temps), max(temps), 100)
                            y_curve = p(x_curve)
                            
                            a, b, c = coeffs
                            eq_str = f"y = {a:.4f}x² + {b:.4f}x + {c:.4f}"
                            fig.add_trace(go.Scatter(x=x_curve, y=y_curve, mode='lines',
                                                     line=dict(color='deeppink', width=3),
                                                     name=f'Trend Fit<br>{eq_str}'))
                        except Exception as e:
                            print(f"  [!] Could not fit curve: {e}")

                        fig.update_layout(
                            title=f"Sector Tire Temp vs Performance<br>Sector: {start_m}m to {end_m}m | {os.path.basename(file_path)}",
                            xaxis_title="Average Tire Temperature (°C)",
                            yaxis_title="Sector Time (s)",
                            template="plotly_dark",
                            font=dict(family="Consolas", size=13)
                        )
                        fig.show()

                    else:
                        plt.style.use('dark_background')
                        plt.rcParams['font.family'] = 'Consolas'
                        fig = plt.figure(figsize=(12, 7), num='GTEC - Sector Tire Analysis')
    
                        # Scatter Plot
                        plt.scatter(temps, times, alpha=0.8, color='cyan', s=40, label='Lap Data')
    
                        # Empirical Optimal Temp (Average temp of the fastest laps)
                        # This finds where the car is empirically fastest, regardless of curve fit skew
                        sorted_indices = np.argsort(times)
                        top_n = min(3, len(times))  # Top 3 fastest laps
                        fastest_laps_idx = sorted_indices[:top_n]
                        
                        emp_opt_temp = np.mean(temps[fastest_laps_idx])
                        emp_opt_time = np.mean(times[fastest_laps_idx])
                        
                        plt.scatter([emp_opt_temp], [emp_opt_time], color='yellow', marker='*', s=200, zorder=5, label=f'Optimal (Top {top_n} Avg): {emp_opt_temp:.1f}°C')
                        plt.axvline(x=emp_opt_temp, color='yellow', linestyle=':', alpha=0.5)
    
                        # Polynomial Curve Fitting (Quadratic/Parabola)
                        # We still draw the curve to show the general U-shape trend
                        try:
                            coeffs = np.polyfit(temps, times, 2)
                            p = np.poly1d(coeffs)
                            
                            x_curve = np.linspace(min(temps), max(temps), 100)
                            y_curve = p(x_curve)
                            
                            a, b, c = coeffs
                            eq_str = f"y = {a:.4f}x² + {b:.4f}x + {c:.4f}"
                            plt.plot(x_curve, y_curve, color='deeppink', linewidth=2, label=f'Trend Fit\n{eq_str}')
                        except Exception as e:
                            print(f"  [!] Could not fit curve: {e}")
    
                        # Styling
                        plt.title(f"Sector Tire Temp vs Performance\nSector: {start_m}m to {end_m}m | {os.path.basename(file_path)}", fontsize=16, fontweight='bold', pad=20)
                        plt.xlabel("Average Tire Temperature (°C)", fontsize=13)
                        plt.ylabel("Sector Time (s)", fontsize=13)
                        plt.xticks(fontsize=11)
                        plt.yticks(fontsize=11)
                        plt.legend(fontsize=11, frameon=True, shadow=True)
                        plt.grid(True, linestyle='--', alpha=0.3)
    
                        plt.tight_layout()
                        
                        if GUI_MODE == 3:
                            show_ctk_graph(fig, "GTEC - Sector Tire Analysis")
                        else:
                            plt.show()

        except ValueError:
            print("[!] Please enter valid numbers.")
            input("\nPress Enter to try again...")
        except KeyboardInterrupt:
            sys.exit(0)

def run_telemetry_viewer(sessions):
    while True:
        clear_screen()
        print("="*60)
        print(" GteC | Interactive Line Graph Viewer")
        print("="*60)
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            channels = session['channels']
            print(f"\nAnalyzing: {os.path.basename(file_path)}")
            
            # Find Channels
            def get_ch(names):
                return next((ch for ch in names if ch in data), None)
            
            lat_g_ch = get_ch(['G Force Lat', 'LatAccel', 'LatG'])
            speed_ch = get_ch(['Ground Speed', 'Speed'])
            fl_spd_ch = get_ch(['Wheel Speed FL', 'LFspeed'])
            fr_spd_ch = get_ch(['Wheel Speed FR', 'RFspeed'])
            rl_spd_ch = get_ch(['Wheel Speed RL', 'LRspeed'])
            rr_spd_ch = get_ch(['Wheel Speed RR', 'RRspeed'])
            thr_ch = get_ch(['Throttle', 'Throttle Position', 'ThrottleRaw'])
            brk_ch = get_ch(['Brake', 'Brake Pedal Position', 'BrakeRaw'])
            gear_ch = get_ch(['Gear'])
            
            req = [lat_g_ch, speed_ch, fl_spd_ch, fr_spd_ch, rl_spd_ch, rr_spd_ch, thr_ch, brk_ch, gear_ch]
            if not all(req):
                missing = [n for n, c in zip(['LatG', 'Speed', 'FL_Spd', 'FR_Spd', 'RL_Spd', 'RR_Spd', 'Throttle', 'Brake', 'Gear'], req) if not c]
                print(f"  [!] Missing channels for full telemetry view: {missing}")
                continue
                
            lap_arr = data[channels['lap']].data
            time_arr = data[channels['time']].data
            dist_arr = data[channels['dist']].data
            laps = np.unique(lap_arr)
            
            # Find fastest valid lap
            lap_times = []
            for lap in laps:
                idx = np.where(lap_arr == lap)[0]
                if len(idx) < 100: continue
                lap_times.append((lap, time_arr[idx][-1] - time_arr[idx][0]))
                
            if not lap_times:
                print("  [!] No valid laps found.")
                continue
                
            median_time = np.median([t[1] for t in lap_times])
            valid_laps = [t for t in lap_times if median_time * 0.89 <= t[1] <= median_time * 1.11]
            if not valid_laps:
                print("  [!] No laps within valid threshold.")
                continue
                
            fastest_lap, fastest_time = min(valid_laps, key=lambda x: x[1])
            idx = np.where(lap_arr == fastest_lap)[0]
            
            # Extract Data for Fastest Lap
            dist = dist_arr[idx]
            
            def safe_get_data(ch_name):
                try:
                    return data[ch_name].data[idx]
                except Exception:
                    return np.zeros(len(idx))

            lat_g = safe_get_data(lat_g_ch)
            speed = safe_get_data(speed_ch)
            
            # Speeds might be in km/h or mph or m/s, but we just plot raw
            fl_spd = safe_get_data(fl_spd_ch)
            fr_spd = safe_get_data(fr_spd_ch)
            front_spd_avg = (fl_spd + fr_spd) / 2.0
            
            rl_spd = safe_get_data(rl_spd_ch)
            rr_spd = safe_get_data(rr_spd_ch)
            rear_spd_avg = (rl_spd + rr_spd) / 2.0
            
            thr = safe_get_data(thr_ch)
            brk = safe_get_data(brk_ch)
            gear = safe_get_data(gear_ch)
            
            ans = input(f"\n  Launch telemetry graph for Lap {int(fastest_lap)} ({fastest_time:.3f}s)? (y/n): ").strip().lower()
            if ans == 'y':
                print("  [+] Building interactive telemetry trace... (Close the window to continue)")
                
                if GUI_MODE == 2:
                    fig = make_subplots(rows=6, cols=1, shared_xaxes=True,
                                        vertical_spacing=0.05,
                                        subplot_titles=("Lateral G", "Front Wheel Speed & Ground Speed", "Throttle", "Brake", "Rear Wheel Speed", "Gear"))
                    
                    fig.add_trace(go.Scatter(x=dist, y=lat_g, mode='lines', line=dict(color='cyan', width=1.5)), row=1, col=1)
                    
                    fig.add_trace(go.Scatter(x=dist, y=front_spd_avg, mode='lines', line=dict(color='yellow', width=1.5), name='Avg Front Whl Spd'), row=2, col=1)
                    fig.add_trace(go.Scatter(x=dist, y=speed, mode='lines', line=dict(color='deeppink', width=1.5, dash='dash'), name='Ground Speed'), row=2, col=1)
                    
                    fig.add_trace(go.Scatter(x=dist, y=thr, mode='lines', line=dict(color='lime', width=1.5)), row=3, col=1)
                    
                    fig.add_trace(go.Scatter(x=dist, y=brk, mode='lines', line=dict(color='red', width=1.5)), row=4, col=1)
                    
                    fig.add_trace(go.Scatter(x=dist, y=rear_spd_avg, mode='lines', line=dict(color='orange', width=1.5)), row=5, col=1)
                    
                    fig.add_trace(go.Scatter(x=dist, y=gear, mode='lines', line=dict(color='white', width=1.5, shape='vh')), row=6, col=1)
                    
                    fig.update_layout(
                        title=f"Telemetry Trace - Lap {int(fastest_lap)}<br>{os.path.basename(file_path)}",
                        template="plotly_dark",
                        font=dict(family="Consolas", size=11),
                        height=900,
                        showlegend=False
                    )
                    fig.update_xaxes(title_text="Lap Distance (m)", row=6, col=1)
                    fig.show()

                else:
                    plt.style.use('dark_background')
                    plt.rcParams['font.family'] = 'Consolas'
                    
                    fig, axs = plt.subplots(6, 1, figsize=(14, 10), sharex=True, num='GTEC - Telemetry Viewer')
                    fig.suptitle(f"Telemetry Trace - Lap {int(fastest_lap)}\n{os.path.basename(file_path)}", fontsize=16, fontweight='bold')
                    
                    # 1. Lateral G
                    axs[0].plot(dist, lat_g, color='cyan', linewidth=1.5)
                    axs[0].set_ylabel("Lat G", fontsize=11)
                    axs[0].grid(True, linestyle='--', alpha=0.3)
                    
                    # 2. Front Wheel Speed & Ground Speed
                    axs[1].plot(dist, front_spd_avg, color='yellow', linewidth=1.5, label='Avg Front Whl Spd')
                    axs[1].plot(dist, speed, color='deeppink', linewidth=1.5, linestyle='--', label='Ground Speed')
                    axs[1].set_ylabel("Front Spd", fontsize=11)
                    axs[1].legend(loc='upper right', fontsize=9, framealpha=0.5)
                    axs[1].grid(True, linestyle='--', alpha=0.3)
                    
                    # 3. Throttle
                    axs[2].plot(dist, thr, color='lime', linewidth=1.5)
                    axs[2].set_ylabel("Throttle", fontsize=11)
                    axs[2].set_ylim(-5, 105)
                    axs[2].grid(True, linestyle='--', alpha=0.3)
                    
                    # 4. Brake
                    axs[3].plot(dist, brk, color='red', linewidth=1.5)
                    axs[3].set_ylabel("Brake", fontsize=11)
                    axs[3].grid(True, linestyle='--', alpha=0.3)
                    
                    # 5. Rear Wheel Speed
                    axs[4].plot(dist, rear_spd_avg, color='orange', linewidth=1.5)
                    axs[4].set_ylabel("Rear Spd", fontsize=11)
                    axs[4].grid(True, linestyle='--', alpha=0.3)
                    
                    # 6. Gear
                    axs[5].plot(dist, gear, color='white', linewidth=1.5, drawstyle='steps-post')
                    axs[5].set_ylabel("Gear", fontsize=11)
                    axs[5].set_xlabel("Lap Distance (m)", fontsize=13)
                    axs[5].set_yticks(np.arange(0, max(gear)+2, 1))
                    axs[5].grid(True, linestyle='--', alpha=0.3)
                    
                    plt.tight_layout()
                    # Adjust top to fit suptitle
                    plt.subplots_adjust(top=0.92, hspace=0.15)
    
                    if GUI_MODE == 3:
                        show_ctk_graph(fig, "GTEC - Telemetry Viewer")
                    else:
                        plt.show()

        print("\n" + "="*60)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            show_exit_screen()
            sys.exit(0)
        break

def run_fuel_analysis(sessions):
    while True:
        clear_screen()
        print("="*60)
        print(" GteC | Fuel & Setup Correlation Analysis")
        print("="*60)
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            channels = session['channels']
            print(f"\nAnalyzing: {os.path.basename(file_path)}")
            
            # Find Fuel Channel
            fuel_ch = next((ch for ch in ['Fuel Level', 'FuelLevel'] if ch in data), None)
            if not fuel_ch:
                print("  [!] Missing Fuel Level channel.")
                continue

            # Find Tire Temp Channels
            fl_t_chs = [ch for ch in ['Tyre Temp FL Inner', 'Tyre Temp FL Centre', 'Tyre Temp FL Outer', 'LFtempL', 'LFtempM', 'LFtempR'] if ch in data]
            fr_t_chs = [ch for ch in ['Tyre Temp FR Inner', 'Tyre Temp FR Centre', 'Tyre Temp FR Outer', 'RFtempL', 'RFtempM', 'RFtempR'] if ch in data]
            rl_t_chs = [ch for ch in ['Tyre Temp RL Inner', 'Tyre Temp RL Centre', 'Tyre Temp RL Outer', 'LRtempL', 'LRtempM', 'LRtempR'] if ch in data]
            rr_t_chs = [ch for ch in ['Tyre Temp RR Inner', 'Tyre Temp RR Centre', 'Tyre Temp RR Outer', 'RRtempL', 'RRtempM', 'RRtempR'] if ch in data]

            lap_arr = data[channels['lap']].data
            time_arr = data[channels['time']].data
            laps = np.unique(lap_arr)
            lap_data = []

            for lap in laps:
                idx = np.where(lap_arr == lap)[0]
                if len(idx) < 100: continue
                lap_time = time_arr[idx][-1] - time_arr[idx][0]
                
                start_idx = idx[0]
                end_idx = idx[-1]
                
                start_fuel = data[fuel_ch].data[start_idx]
                end_fuel = data[fuel_ch].data[end_idx]
                fuel_used = start_fuel - end_fuel

                # Calculate avg start temp across all 4 tires (if available)
                start_temps = []
                for t_chs in [fl_t_chs, fr_t_chs, rl_t_chs, rr_t_chs]:
                    if t_chs:
                        # Average of Inner, Centre, Outer for this tire at the start index
                        tire_start_temp = np.mean([data[ch].data[start_idx] for ch in t_chs])
                        start_temps.append(tire_start_temp)
                
                avg_start_temp = np.mean(start_temps) if start_temps else 0

                lap_data.append({
                    'lap': int(lap),
                    'time': lap_time,
                    'start_fuel': start_fuel,
                    'fuel_used': fuel_used,
                    'start_temp': avg_start_temp
                })

            if not lap_data:
                print("  [!] No valid lap data found.")
                continue

            # Filter out in/out laps using median time
            median_time = np.median([ld['time'] for ld in lap_data])
            valid_laps = [ld for ld in lap_data if median_time * 0.89 <= ld['time'] <= median_time * 1.11]

            if not valid_laps:
                print("  [!] Not enough valid laps for analysis.")
                continue

            # Identify the top 3 fastest laps
            sorted_valid = sorted(valid_laps, key=lambda x: x['time'])
            fastest_laps = sorted_valid[:3]
            fastest_lap_nums = [ld['lap'] for ld in fastest_laps]

            avg_fuel_use = np.mean([ld['fuel_used'] for ld in valid_laps])

            print(f"\n  [ STINT OVERVIEW ]")
            print(f"  Valid Laps: {len(valid_laps)}")
            print(f"  Avg Fuel Use Per Lap: {avg_fuel_use:.2f} L")
            
            GOLD = '\033[33m'
            RESET = '\033[0m'
            
            print("\n  [ LAP-BY-LAP CORRELATION ]")
            print(f"  {'Lap':<5} | {'Time (s)':<10} | {'Fuel Used':<10} | {'Start Fuel':<12} | {'Start Temp':<10}")
            print("  " + "-" * 65)

            for ld in valid_laps:
                is_fastest = ld['lap'] in fastest_lap_nums
                row_color = GOLD if is_fastest else ""
                reset_color = RESET if is_fastest else ""
                
                print(f"  {row_color}{ld['lap']:<5} | {ld['time']:<10.3f} | {ld['fuel_used']:<8.2f} L | {ld['start_fuel']:<10.2f} L | {ld['start_temp']:<8.1f} °C{reset_color}")

        print("\n" + "="*60)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            show_exit_screen()
            sys.exit(0)
        break

def main():
    global GUI_MODE
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

        clear_screen()
        print("="*60)
        print(" GteC | Session Type Selection")
        print("="*60)
        print("  1. Single File Analysis")
        print("  2. Multi-File Comparison")
        print("  3. Settings")
        print("-" * 60)
        
        session_choice = input("\nSelect session type (number) or 'q' to quit: ").strip().lower()
        if session_choice == 'q':
            show_exit_screen()
            return
        
        if session_choice == '3':
            while True:
                clear_screen()
                print("="*60)
                print(" GteC | Settings")
                print("="*60)
                if GUI_MODE == 1:
                    status = "1 (Legacy Matplotlib)"
                elif GUI_MODE == 2:
                    status = "2 (Plotly Web Beta)"
                else:
                    status = "3 (CustomTkinter Beta)"
                    
                print(f"  1. Cycle GUI Mode    [Current: {status}]")
                print("-" * 60)
                s_choice = input("\nSelect an option to cycle (number) or 'p' to go back: ").strip().lower()
                if s_choice == 'p':
                    break
                elif s_choice == '1':
                    GUI_MODE = GUI_MODE + 1
                    if GUI_MODE > 3:
                        GUI_MODE = 1
                    save_config({'gui_mode': GUI_MODE})
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
            clear_screen()
            print("="*60)
            print(" Gtec | Telemetry Archive")
            print("="*60)
            for i, info in enumerate(file_infos):
                print(f"  {i + 1}. {info}")
            print("-" * 60)
            
            while True:
                choice = input("\nSelect a file to analyze (number), 'p' for previous menu, or 'q' to quit: ").strip().lower()
                if choice == 'q':
                    show_exit_screen()
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
                clear_screen()
                print("="*60)
                print(" Gtec | Telemetry Archive (Multi-File)")
                print("="*60)
                for i, info in enumerate(file_infos):
                    print(f"  {i + 1}. {info}")
                print("-" * 60)
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
                    show_exit_screen()
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

        clear_screen()
        sessions = []
        for file_path in selected_files:
            data, limit, channels = load_telemetry(file_path)
            sessions.append({
                'data': data,
                'limit': limit,
                'channels': channels,
                'file_path': file_path
            })
        
        while True:
            clear_screen()
            print("="*60)
            print(" GteC | Analysis Tools")
            print("="*60)
            if len(sessions) == 1:
                print(f" File: {sessions[0]['file_path']}")
            else:
                print(f" Comparing {len(sessions)} files")
            print("-" * 60)
            print("  1. Sector Analysis")
            print("  2. Roll Gradient Analysis")
            print("  3. Static Setup Viewer (alpha)")
            print("  4. Dynamic Aero/Rake Analyzer")
            print("  5. Tire Temperature & Pressure Analysis")
            print("  6. Fuel & Setup Correlation Analysis")
            print("  7. Interactive Line Graph Viewer")
            print("  8. Sector Tire Temp Performance Graph")
            print("-" * 60)
            
            tool_choice = input("\nSelect a tool (number), 'p' for Main Menu, or 'q' to quit: ").strip().lower()
            if tool_choice == 'q':
                show_exit_screen()
                return
            if tool_choice == 'p':
                break
                
            if tool_choice == '1':
                run_sector_analysis(sessions)
            elif tool_choice == '2':
                run_roll_analysis(sessions)
            elif tool_choice == '3':
                run_setup_viewer(sessions)
            elif tool_choice == '4':
                run_rake_analysis(sessions)
            elif tool_choice == '5':
                run_tire_analysis(sessions)
            elif tool_choice == '6':
                run_fuel_analysis(sessions)
            elif tool_choice == '7':
                run_telemetry_viewer(sessions)
            elif tool_choice == '8':
                run_sector_tire_analysis(sessions)
            else:
                print("[!] Invalid selection.")
                input("\nPress Enter to try again...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print("\n" + "!"*60)
        print(" FATAL ERROR DETECTED")
        print("!"*60)
        print(f"\nError: {e}")
        print("\nFull Traceback:")
        traceback.print_exc()
        print("\n" + "!"*60)
        input("\nPlease take a screenshot of this error and press Enter to exit...")
        sys.exit(1)
