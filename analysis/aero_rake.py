import datetime
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ui.splash as splash
from ui.metadata_printer import print_session_metadata
from ui.graphing import show_ctk_graph
from core.config import get_gui_mode

def run_rake_analysis(sessions, headless=False, headless_config=None):
    while True:
        splash.print_header("Dynamic Aero/Rake Analyzer")
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            channels = session['channels']
            print(f"\nAnalyzing: {os.path.basename(file_path)}")
            print_session_metadata(data, channels, session.get('metadata', {}))
            
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
            RESET = "\033[0m"
            print(f"  {PINK}Rake Adjustment: {rake_m:+.4f} mm/mph{RESET}")
            
            fastest_lap_info = session.get('metadata', {}).get('fastest_lap', 'N/A')
            if fastest_lap_info != 'N/A':
                print(f"  {PINK}Fastest Lap: {fastest_lap_info}{RESET}")
            
            print("\n ┌" + "─" * 39 + "┐")
            print(" │ " + "Modeled Rake at speeds:".ljust(37) + " │")
            for s in [50, 100, 150, np.max(speed)]:
                r = rake_m * s + rake_c
                if s == np.max(speed):
                    print(" │ " + f"@ {s:3.0f} mph (Max): {r:5.1f} mm".ljust(37) + " │")
                else:
                    print(" │ " + f"@ {s:3} mph:       {r:5.1f} mm".ljust(37) + " │")
            print(" └" + "─" * 39 + "┘")
            

            md = session.get('metadata', {})
            car_name = md.get('car', 'UNKNOWN')
            file_basename = os.path.basename(file_path)

            l1_preview = f"""
        L1: DYNAMIC RAKE SCATTER (RAW)                    LINEAR REGRESSION (TREND)               
 ┌─────────────────────────────────────────┐   ┌─────────────────────────────────────────┐      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │ [X] AXIS: SPEED (MPH)                   │   │ [X] AXIS: SPEED (MPH)                   │      
 │ [Y] AXIS: RAKE (MM)                     │   │ [Y] AXIS: RAKE (MM)                     │      
 │ [L] LINE: LINEAR FIT                    │   │ [L] LINE: LINEAR FIT                    │      
 └─────────────────────────────────────────┘   └─────────────────────────────────────────┘      
 
  FILE: {file_basename}
  VEHICLE: {car_name}
  
  >> [USE CASE]: ANALYZE HOW THE CAR'S ATTITUDE (RAKE) CHANGES DYNAMICALLY WITH SPEED."""
            
            l2_preview = f"""
        L2: RAKE TREND (PRIMARY)                          RAKE TREND (REFERENCE)               
 ┌─────────────────────────────────────────┐   ┌─────────────────────────────────────────┐      
 │                                         │   │ SETUP SHIFT: Wing [3->5], RH [50->48]   │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │ [X] AXIS: SPEED (MPH)                   │   │ [X] AXIS: SPEED (MPH)                   │      
 │ [Y] AXIS: RAKE (MM)                     │   │ [Y] AXIS: RAKE (MM)                     │      
 │ [L] LINE: LINEAR FIT                    │   │ [L] LINE: LINEAR FIT                    │      
 └─────────────────────────────────────────┘   └─────────────────────────────────────────┘      
 
  >> [USE CASE]: DIRECTLY COMPARE DYNAMIC RAKE SENSITIVITY BETWEEN TWO SETUP ITERATIONS."""
            
            print(l1_preview)
            print(l2_preview)

            _headless_ran = False
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
                    print("  [+] Building Rake Analysis Graph...")
                    import matplotx
                    plt.style.use(matplotx.styles.aura['dark'])
                    plt.rcParams['font.family'] = 'Consolas'
                    fig = plt.figure(figsize=(12, 7), num='OpenDAV - Dynamic Rake Analyzer')
    
                    plt.scatter(straight_speed, straight_rake, alpha=0.4, label='Telemetry Data', color='cyan', s=4)
                    x_vals_line = np.array([min(straight_speed), max(straight_speed)])
                    y_vals_line = rake_m * x_vals_line + rake_c
                    plt.plot(x_vals_line, y_vals_line, color='deeppink', linewidth=2, label=f'Trend: {rake_m:+.4f} mm/mph')
    
                    plt.title(f"Dynamic Aero/Rake Correlation\n{file_basename}", fontsize=16, fontweight='bold', pad=20)
                    plt.xlabel("Speed (mph)", fontsize=13)
                    plt.ylabel("Rake (mm) [Rear - Front]", fontsize=13)
                    plt.legend(fontsize=11)
                    plt.grid(True, linestyle='--', alpha=0.3)
                    
                    info_text = (f"Driver: {md.get('driver', 'N/A')}\nCar: {md.get('car', 'N/A')}\nVenue: {md.get('venue', 'N/A')}")
                    plt.figtext(0.02, 0.02, info_text, fontsize=9, color='white', alpha=0.8, va='bottom', ha='left',
                                bbox=dict(facecolor='#1a1a1a', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.5'))
                    plt.tight_layout()

                    if ans == 'open l1':
                        gui_mode = get_gui_mode()
                        if gui_mode == 3: show_ctk_graph(fig, "OpenDAV - Dynamic Rake Analyzer")
                        else: plt.show()
                    else:
                        timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                        file_out = f"Rake_L1_{timestamp}_{file_basename}.png"
                        if '<' in ans_raw:
                            project_name = ans_raw.split('<')[1].strip().replace('[', '').replace(']', '').strip()
                            from analysis.projects import save_to_project
                            subf = headless_config.get('run_folder') if headless else None
                            save_to_project(fig, project_name, file_out, subfolder=subf)
                            plt.close(fig)
                            if headless: break
                        else:
                            os.makedirs("exports", exist_ok=True)
                            export_path = f"exports/{file_out}"
                            plt.savefig(export_path, dpi=300, bbox_inches='tight')
                            plt.close(fig)
                            print(f"  [+] Saved to {export_path}")
                        if headless: break

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
                        
                    # Process Reference
                    r_speed_ch = None
                    for ch in ['Speed', 'Ground Speed']:
                        if ch in r_data: r_speed_ch = ch; break
                    r_speed_raw = r_data[r_speed_ch].data
                    r_speed = r_speed_raw * 0.621371 if np.max(r_speed_raw) > 150 else r_speed_raw * 2.23694
                    r_f_rh = (r_data['Ride Height FL'].data + r_data['Ride Height FR'].data) / 2.0 * 1000
                    r_r_rh = (r_data['Ride Height RL'].data + r_data['Ride Height RR'].data) / 2.0 * 1000
                    r_rake = r_r_rh - r_f_rh
                    r_lat_g = r_data[r_channels['lat']].data if r_channels['lat'] in r_data else np.zeros_like(r_speed)
                    r_long_g = r_data[r_channels['long']].data if r_channels['long'] in r_data else np.zeros_like(r_speed)
                    r_mask = (np.abs(r_lat_g) < 0.2) & (r_long_g > -0.5) & (r_speed > 40)
                    r_s_speed = r_speed[r_mask]
                    r_s_rake = r_rake[r_mask]
                    r_m, r_c = np.polyfit(r_s_speed, r_s_rake, 1)

                    # YAML Diff
                    def extract_setup(y):
                        setup = y.get('CarSetup', {})
                        flat = {}
                        def recurse(d, prefix=""):
                            if isinstance(d, dict):
                                for k, v in d.items():
                                    if k in ("UpdateCount", "LastTempsOMI", "LastTempsIMO", "TreadRemaining", "CornerWeight"): continue
                                    recurse(v, f"{prefix}{k}." if prefix else f"{k}.")
                            else: flat[prefix[:-1]] = d
                        recurse(setup); return flat
                    s1 = extract_setup(yaml.safe_load(md.get('session_info_yaml', '')) or {})
                    s2 = extract_setup(yaml.safe_load(r_metadata.get('session_info_yaml', '')) or {})
                    deltas = [f"{k.split('.')[-1]} [{s1[k]}->{s2[k]}]" for k in set(s1.keys()) if s1.get(k) != s2.get(k)]
                    delta_title = "SETUP SHIFTS: " + ", ".join(deltas[:4]) + ("..." if len(deltas)>4 else "")

                    import matplotx
                    plt.style.use(matplotx.styles.aura['dark'])
                    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8), num='OpenDAV - L2 Rake Comparison')
                    
                    for ax, spd, rk, m, c, tit, subt in [
                        (ax1, straight_speed, straight_rake, rake_m, rake_c, "PRIMARY", f"Laps: {len(np.unique(data[channels['lap']].data[mask]))} | Pts: {len(straight_speed)}\n{file_basename}"),
                        (ax2, r_s_speed, r_s_rake, r_m, r_c, "REFERENCE", f"Laps: {len(np.unique(r_data[r_channels['lap']].data[r_mask]))} | Pts: {len(r_s_speed)}\n{delta_title}")
                    ]:
                        ax.scatter(spd, rk, alpha=0.3, color='cyan', s=3)
                        xv = np.array([min(spd), max(spd)])
                        ax.plot(xv, m*xv+c, color='deeppink', lw=3, label=f'Trend: {m:+.4f} mm/mph')
                        ax.set_title(f"{tit}\n{subt}", fontsize=11)
                        ax.set_xlabel("Speed (mph)")
                        ax.set_ylabel("Rake (mm)")
                        ax.legend()
                        ax.grid(True, alpha=0.2)
                    
                    plt.tight_layout()
                    if ans == 'open l2':
                        if get_gui_mode() == 3: show_ctk_graph(fig, "OpenDAV - L2 Rake Comparison")
                        else: plt.show()
                    else:
                        ts = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                        os.makedirs("exports", exist_ok=True)
                        ep = f"exports/Rake_L2_{ts}_{file_basename}.png"
                        plt.savefig(ep, dpi=300); plt.close(fig)
                        print(f"  [+] Saved to {ep}")
                        if headless: break
                else: print("  [!] Invalid command.")

        if headless: return
        print("\n" + "─"*100)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break
