from scipy.spatial import cKDTree
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yaml
import ui.splash as splash
from ui.metadata_printer import print_session_metadata
from ui.graphing import show_ctk_graph
from core.config import get_gui_mode
from core.car_db import get_car_spec, update_car_spec

def run_yaw_analyzer(sessions, headless=False, headless_config=None):
    while True:
        if not headless:
            splash.print_header("Yaw Kinematics & Handling Analyzer")
            
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            channels = session['channels']
            metadata = session.get('metadata', {})
            car_name = metadata.get('car', 'UNKNOWN')
            
            if not headless:
                print(f"\nAnalyzing: {os.path.basename(file_path)}")
                print_session_metadata(data, channels, metadata)
            
            # 1. Get Car Specs
            specs = get_car_spec(car_name)
            if not specs and not headless:
                print(f"\n  [!] Unknown car detected: {car_name}")
                try:
                    wb = float(input("      Enter Wheelbase (meters): ").strip())
                    sr = float(input("      Enter Steering Ratio (e.g. 14.5): ").strip())
                    update_car_spec(car_name, wb, sr)
                    specs = {"wheelbase": wb, "steering_ratio": sr}
                except ValueError:
                    print("  [!] Invalid input. Skipping file.")
                    continue
            elif not specs and headless:
                # Default fallback for headless if unknown
                specs = {"wheelbase": 2.6, "steering_ratio": 14.0}
            
            wheelbase = specs['wheelbase']
            steering_ratio = specs['steering_ratio']

            # 2. Find Required Channels
            speed_ch = None
            for ch in ['Speed', 'Ground Speed', 'Velocity', 'virt_body_v']:
                if ch in data: speed_ch = ch; break
            
            yaw_ch = None
            for ch in ['YawRate', 'Yaw']:
                if ch in data: yaw_ch = ch; break
                
            steer_ch = None
            for ch in ['SteeringWheelAngle', 'SteerWheelAngle']:
                if ch in data: steer_ch = ch; break
                
            lat_g_ch = None
            for ch in ['LatAccel', 'LatG', 'G Force Lat', 'lat']:
                if ch in data or ch in channels.values(): lat_g_ch = ch; break

            if not all([speed_ch, yaw_ch, steer_ch, lat_g_ch]):
                if not headless: print(f"  [!] Missing channels for Yaw analysis. Need Speed, YawRate, Steer, LatAccel.")
                continue

            # 3. Load and Calculate
            # Speed (m/s)
            v_ms = data[speed_ch].data
            if np.max(v_ms) > 150: v_ms = v_ms / 3.6 # km/h fallback
            elif np.max(v_ms) > 100: v_ms = v_ms * 0.44704 # mph fallback
            
            # Steering Wheel Angle (rad)
            swa_rad = data[steer_ch].data
            # Actual Yaw Rate (rad/s)
            actual_yaw = data[yaw_ch].data
            # Lat Accel (G)
            lat_g = data[channels.get('lat', lat_g_ch)].data
            if np.max(np.abs(lat_g)) > 10: lat_g = lat_g / 9.81 # m/s^2 fallback

            # Front Wheel Angle (delta)
            # swa_rad is usually absolute rads from center. 
            # delta_rad = swa_rad / steering_ratio
            fwa_rad = swa_rad / steering_ratio
            
            # Kinematic Yaw Rate = (V / L) * tan(delta)
            # For small angles, tan(delta) approx delta
            kinematic_yaw = (v_ms / wheelbase) * np.tan(fwa_rad)
            
            # Yaw Error (rad/s)
            # Positive = Actual > Kinematic = Oversteer
            # Negative = Actual < Kinematic = Understeer
            yaw_error = actual_yaw - kinematic_yaw
            
            # Convert to deg/s for readability
            yaw_error_deg = np.degrees(yaw_error)
            
            # 4. Filter for cornering data
            # Speed > 40 km/h, LatG > 0.3G
            mask = (v_ms > 11.1) & (np.abs(lat_g) > 0.3)
            
            if not np.any(mask):
                if not headless: print("  [!] Not enough cornering data to establish baseline.")
                continue
                
            plot_lat_g = lat_g[mask]
            plot_yaw_err = yaw_error_deg[mask]
            
            # Subtitles
            file_basename = os.path.basename(file_path)
            lap_ch = channels.get('lap')
            laps = len(np.unique(data[lap_ch].data[mask])) if lap_ch and lap_ch in data else "Unknown"
            pts = len(plot_lat_g)
            
            PINK = '\033[95m'
            CYAN = '\033[96m'
            RESET = "\033[0m"

            # Terminal Stats
            median_err = np.median(plot_yaw_err)
            bias_str = f"{CYAN}Understeer{RESET}" if median_err < 0 else f"{PINK}Oversteer{RESET}"
            
            if not headless:
                print("\n  ┌" + "─" * 98 + "┐")
                print("  │ " + "[ YAW KINEMATICS & BALANCE ]".ljust(92) + " │")
                print("  │ " + f"Median Yaw Error: {abs(median_err):.2f} deg/s ({bias_str})".ljust(47 + len(PINK) + len(RESET)) + " │")
                print("  │ " + f"Wheelbase: {wheelbase:.3f} m | Ratio: {steering_ratio:.1f}".ljust(92) + " │")
                print("  └" + "─" * 98 + "┘")

            l1_preview = f"""
        L1: YAW ERROR SCATTER (RAW)                       HANDLING BALANCE MAP               
 ┌─────────────────────────────────────────┐   ┌─────────────────────────────────────────┐      
 │                                         │   │ OVERSTEER BIAS (RED)                    │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │          [ TELEMETRY DOTS ]             │   │----------------- NEUTRAL LINE ----------│      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │ UNDERSTEER BIAS (BLUE)                  │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │ [X] AXIS: LATERAL G-FORCE               │   │ [X] AXIS: LATERAL G-FORCE               │      
 │ [Y] AXIS: YAW ERROR (DEG/S)             │   │ [Y] AXIS: YAW ERROR (DEG/S)             │      
 │ [C] COLOR: BLUE (US) / RED (OS)         │   │ [L] LINE: HANDLING TREND                │      
 └─────────────────────────────────────────┘   └─────────────────────────────────────────┘      
 
  FILE: {file_basename}
  VEHICLE: {car_name}
  
  >> [USE CASE]: PROVE UNDERSTEER/OVERSTEER BALANCE AT DIFFERENT SPEEDS AND CORNER PHASES."""

            l2_preview = f"""
        L2: HANDLING TREND (PRIMARY)                      HANDLING TREND (REFERENCE)               
 ┌─────────────────────────────────────────┐   ┌─────────────────────────────────────────┐      
 │                                         │   │ SETUP SHIFT: Rear ARB [4->2]            │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │ [X] AXIS: LATERAL G-FORCE               │   │ [X] AXIS: LATERAL G-FORCE               │      
 │ [Y] AXIS: YAW ERROR (DEG/S)             │   │ [Y] AXIS: YAW ERROR (DEG/S)             │      
 │ [L] LINE: HANDLING TREND                │   │ [L] LINE: HANDLING TREND                │      
 └─────────────────────────────────────────┘   └─────────────────────────────────────────┘      
 
  >> [USE CASE]: DIRECTLY COMPARE HANDLING BALANCE SHIFTS BETWEEN TWO SETUP ITERATIONS."""

            if not headless:
                print(l1_preview)
                print(l2_preview)

            while True:
                if headless:
                    if headless_config.get('_ran'): return
                    headless_config['_ran'] = True
                    ans_raw = f"print {headless_config['layout'].lower()} < {headless_config['project']}"
                else:
                    ans_raw = input(f"\n  Select action ('open L1', 'print L1', 'open L2', 'print L2', 'p' to go back < proj): ").strip().lower()
                
                ans = ans_raw.split('<')[0].strip().lower()
                
                if ans == 'p':
                    break
                    
                if ans in ['open l1', 'print l1']:
                    if not headless: print("  [+] Building Handling Balance Graph...")
                    import matplotx
                    plt.style.use(matplotx.styles.aura['dark'])
                    plt.rcParams['font.family'] = 'Consolas'
                    fig = plt.figure(figsize=(12, 7), num='OpenDAV - Handling Balance')

                    # Separate OS and US for coloring
                    os_mask = plot_yaw_err > 0
                    us_mask = plot_yaw_err <= 0
                    
                    plt.scatter(plot_lat_g[us_mask], plot_yaw_err[us_mask], alpha=0.3, color='#2D8AE2', s=5, label='Understeer')
                    plt.scatter(plot_lat_g[os_mask], plot_yaw_err[os_mask], alpha=0.3, color='#FF1493', s=5, label='Oversteer')
                    
                    # Trend line (Handling Gradient)
                    if len(plot_lat_g) > 20:
                        m, c = np.polyfit(plot_lat_g, plot_yaw_err, 1)
                        x_trend = np.array([min(plot_lat_g), max(plot_lat_g)])
                        plt.plot(x_trend, m * x_trend + c, color='white', linewidth=2, linestyle='--', label=f'Trend: {m:+.2f} deg/s/G')

                    
                    # Enable Yaw Error display in the Matplotlib status bar
                    lookup_tree = cKDTree(np.column_stack((plot_lat_g, plot_yaw_err)))
                    def format_coord(x, y):
                        dist, idx = lookup_tree.query([x, y])
                        if dist > 0.5: return f'LatG={x:.3f}, YawErr={y:.1f}deg/s'
                        val = plot_yaw_err[idx]
                        return f'LatG={x:.3f}, YawErr={y:.1f}deg/s' # Standard display is fine here since Y is the value
                    plt.gca().format_coord = format_coord

                    plt.axhline(0, color='white', linewidth=1, alpha=0.5)
                    plt.title(f"Handling Balance Analysis (Actual vs Kinematic Yaw)\n{file_basename}", fontsize=15, fontweight='bold', pad=20)
                    plt.xlabel("Lateral Acceleration (G)", fontsize=12)
                    plt.ylabel("Yaw Error (deg/s) [Positive = Oversteer]", fontsize=12)
                    plt.legend(loc='upper right')
                    plt.grid(True, alpha=0.1)

                    info_text = (f"Driver: {metadata.get('driver', 'N/A')}\nCar: {car_name}\nLaps: {laps} | Points: {pts}")
                    plt.figtext(0.02, 0.02, info_text, fontsize=9, color='white', alpha=0.8, va='bottom', ha='left',
                                bbox=dict(facecolor='#1a1a1a', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.5'))
                    plt.tight_layout()

                    if ans == 'open l1':
                        gui_mode = get_gui_mode()
                        if gui_mode == 3: show_ctk_graph(fig, "OpenDAV - Handling Balance")
                        else: plt.show()
                    else:
                        import datetime
                        timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                        file_out = f"Yaw_L1_{timestamp}_{file_basename}.png"
                        if '<' in ans_raw:
                            project_name = ans_raw.split('<')[1].strip().replace('[', '').replace(']', '').strip()
                            from analysis.projects import save_to_project
                            subf = headless_config.get('run_folder') if headless else None
                            save_to_project(fig, project_name, file_out, subfolder=subf)
                            plt.close(fig)
                        else:
                            os.makedirs("exports", exist_ok=True)
                            export_path = f"exports/{file_out}"
                            plt.savefig(export_path, dpi=300, bbox_inches='tight')
                            plt.close(fig)
                            if not headless: print(f"  [+] Saved to {export_path}")

                elif ans in ['open l2', 'print l2']:
                    from core.telemetry import load_telemetry
                    if headless:
                        ref_path = headless_config['ref_path']
                        try:
                            r_data, _, r_channels, r_metadata = load_telemetry(ref_path)
                        except Exception as e:
                            print(f"  [!] Error loading reference file: {e}")
                            break
                    else:
                        telemetry_dir = "telemetry"
                        ld_files = [f for f in os.listdir(telemetry_dir) if f.lower().endswith(('.ld', '.ibt'))]
                        ld_files.sort()
                        
                        print("\n  Select Reference File:")
                        for i, lf in enumerate(ld_files): print(f"    {i+1}. {lf}")
                        ref_choice = input("  Selection (number): ").strip()
                        try:
                            ref_idx = int(ref_choice) - 1
                            ref_path = os.path.join(telemetry_dir, ld_files[ref_idx])
                            r_data, _, r_channels, r_metadata = load_telemetry(ref_path)
                        except:
                            print("  [!] Invalid selection.")
                            continue

                    # Process Reference Specs
                    r_car = r_metadata.get('car', 'UNKNOWN')
                    r_specs = get_car_spec(r_car) or {"wheelbase": 2.6, "steering_ratio": 14.0}
                    
                    # Process Reference Data (Same logic as primary)
                    r_speed_raw = r_data[speed_ch].data
                    r_v_ms = r_speed_raw if np.max(r_speed_raw) < 100 else r_speed_raw / 3.6
                    r_swa = r_data[steer_ch].data
                    r_yaw = r_data[yaw_ch].data
                    r_lat_g_raw = r_data[r_channels.get('lat', lat_g_ch)].data
                    r_lat_g = r_lat_g_raw if np.max(np.abs(r_lat_g_raw)) < 10 else r_lat_g_raw / 9.81
                    
                    r_kin_yaw = (r_v_ms / r_specs['wheelbase']) * np.tan(r_swa / r_specs['steering_ratio'])
                    r_err_deg = np.degrees(r_yaw - r_kin_yaw)
                    
                    r_mask = (r_v_ms > 11.1) & (np.abs(r_lat_g) > 0.3)
                    r_plot_g = r_lat_g[r_mask]
                    r_plot_err = r_err_deg[r_mask]

                    # YAML Diff
                    from analysis.projects import extract_setup # Actually I need to re-implement or import
                    def extract_setup_local(m):
                        y = yaml.safe_load(m.get('session_info_yaml', '')) or {}
                        setup = y.get('CarSetup', {})
                        flat = {}
                        def recurse(d, prefix=""):
                            if isinstance(d, dict):
                                for k, v in d.items():
                                    if k in ("UpdateCount", "LastTempsOMI", "LastTempsIMO", "TreadRemaining", "CornerWeight"): continue
                                    recurse(v, f"{prefix}{k}." if prefix else f"{k}.")
                            else: flat[prefix[:-1]] = d
                        recurse(setup); return flat
                    s1 = extract_setup_local(metadata)
                    s2 = extract_setup_local(r_metadata)
                    deltas = [f"{k.split('.')[-1]} [{s1[k]}->{s2[k]}]" for k in set(s1.keys()) if s1.get(k) != s2.get(k)]
                    delta_title = "SETUP SHIFTS: " + ", ".join(deltas[:4]) + ("..." if len(deltas)>4 else "")

                    import matplotx
                    plt.style.use(matplotx.styles.aura['dark'])
                    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8), num='OpenDAV - L2 Handling Comparison')
                    
                    for ax, g_data, err_data, tit, subt in [
                        (ax1, plot_lat_g, plot_yaw_err, "PRIMARY", f"Laps: {laps} | Pts: {pts}\n{file_basename}"),
                        (ax2, r_plot_g, r_plot_err, "REFERENCE", f"Laps: {len(np.unique(r_data[r_channels.get('lap')].data[r_mask])) if r_channels.get('lap') in r_data else '?'} | Pts: {len(r_plot_g)}\n{delta_title}")
                    ]:
                        # OS/US coloring
                        os_m = err_data > 0
                        us_m = err_data <= 0
                        ax.scatter(g_data[us_m], err_data[us_m], alpha=0.3, color='#2D8AE2', s=4)
                        ax.scatter(g_data[os_m], err_data[os_m], alpha=0.3, color='#FF1493', s=4)
                        
                        if len(g_data) > 20:
                            m, c = np.polyfit(g_data, err_data, 1)
                            xv = np.array([min(g_data), max(g_data)])
                            ax.plot(xv, m*xv+c, color='white', lw=3, ls='--', label=f'Gradient: {m:+.2f} deg/s/G')
                        
                        ax.axhline(0, color='white', lw=1, alpha=0.5)
                        import textwrap
                        subt_wrapped = "\n".join(textwrap.wrap(subt, 60))
                        ax.set_title(f"{tit}\n{subt_wrapped}", fontsize=11)
                        ax.set_xlabel("Lateral Acceleration (G)")
                        ax.set_ylabel("Yaw Error (deg/s)")
                        ax.legend()
                        ax.grid(True, alpha=0.1)
                    
                    plt.tight_layout()
                    if ans == 'open l2':
                        if get_gui_mode() == 3: show_ctk_graph(fig, "OpenDAV - L2 Handling Comparison")
                        else: plt.show()
                    elif ans == 'print l2':
                        import datetime
                        ts = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                        file_out = f"Yaw_L2_{ts}_{file_basename}.png"
                        if '<' in ans_raw:
                            project_name = ans_raw.split('<')[1].strip().replace('[', '').replace(']', '').strip()
                            from analysis.projects import save_to_project
                            subf = headless_config.get('run_folder') if headless else None
                            save_to_project(fig, project_name, file_out, subfolder=subf)
                            plt.close(fig)
                        else:
                            os.makedirs("exports", exist_ok=True)
                            ep = f"exports/{file_out}"
                            plt.savefig(ep, dpi=300); plt.close(fig)
                            if not headless: print(f"  [+] Saved to {ep}")
                else: 
                    if not headless: print("  [!] Invalid command.")
                    
        if headless: return
        print("\n" + "─"*100)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break
