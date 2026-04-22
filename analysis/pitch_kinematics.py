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

def run_pitch_analyzer(sessions, headless=False, headless_config=None):
    while True:
        if not headless:
            splash.print_header("Pitch Kinematics & Platform Analyzer")
            
        _headless_ran = False
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            channels = session['channels']
            
            if not headless:
                print(f"\nAnalyzing: {os.path.basename(file_path)}")
                print_session_metadata(data, channels, session.get('metadata', {}))
            
            # Find channels
            speed_ch = None
            for ch in ['Speed', 'Ground Speed', 'Velocity', 'virt_body_v']:
                if ch in data: speed_ch = ch; break
                
            lat_g_ch, long_g_ch = None, None
            for ch in ['G Force Lat', 'LatAccel', 'LatG', 'lat']:
                if ch in data or ch in channels.values(): lat_g_ch = ch; break
            for ch in ['G Force Long', 'LongAccel', 'LongG', 'long']:
                if ch in data or ch in channels.values(): long_g_ch = ch; break

            fl_ch, fr_ch = 'Ride Height FL', 'Ride Height FR'
            rl_ch, rr_ch = 'Ride Height RL', 'Ride Height RR'
            
            required = [fl_ch, fr_ch, rl_ch, rr_ch]
            if not speed_ch or not lat_g_ch or not long_g_ch:
                if not headless: print("  [!] Missing Speed/G channels for Pitch filtering.")
                continue
            missing = [ch for ch in required if ch not in data]
            if missing:
                if not headless: print(f"  [!] Missing ride height channels: {missing}")
                continue

            # Data prep
            speed_raw = data[speed_ch].data
            if np.max(speed_raw) > 150: # km/h
                speed = speed_raw 
            elif np.max(speed_raw) < 100 and "m/s" in data[speed_ch].unit.lower(): # m/s
                speed = speed_raw * 3.6
            else: # mph
                speed = speed_raw * 1.60934
                
            fl = data[fl_ch].data * 1000
            fr = data[fr_ch].data * 1000
            rl = data[rl_ch].data * 1000
            rr = data[rr_ch].data * 1000
            
            lat_g = data[channels.get('lat', lat_g_ch)].data
            long_g = data[channels.get('long', long_g_ch)].data

            f_rh = (fl + fr) / 2.0
            r_rh = (rl + rr) / 2.0
            
            # Apply a Low-Pass Filter (Moving Average) to smooth out suspension high-frequency noise (e.g. curb strikes)
            # This ensures we are measuring the true mechanical chassis platform pitch, not track surface bumps.
            window = 10
            f_rh = np.convolve(f_rh, np.ones(window)/window, mode='same')
            r_rh = np.convolve(r_rh, np.ones(window)/window, mode='same')
            long_g_smooth = np.convolve(long_g, np.ones(window)/window, mode='same')
            
            rake = r_rh - f_rh
            
            # 1. Establish Static Rake
            static_mask = (speed < 15) & (np.abs(lat_g) < 0.1) & (np.abs(long_g) < 0.1)
            if np.any(static_mask):
                static_rake = np.median(rake[static_mask])
            else:
                static_rake = np.median(rake)

            # Dynamic Rake Delta (Positive = Pitching Forward/Diving)
            dyn_rake_delta = rake - static_rake

            # 2. Filter for Pure Longitudinal Events (low lat G) and mid-speed (reduce extreme aero)
            # 40 to 140 km/h to capture mechanical pitch without massive aero squat
            mask = (speed > 40) & (speed < 140) & (np.abs(lat_g) < 0.15)
            
            if not np.any(mask):
                if not headless: print("  [!] Not enough straight-line braking/acceleration data.")
                continue
                
            valid_long_g = long_g_smooth[mask]
            valid_pitch = dyn_rake_delta[mask]
            
            # 3. Split into Braking and Acceleration
            mask_brake = valid_long_g < -0.2
            mask_accel = valid_long_g > 0.2
            
            brake_g = valid_long_g[mask_brake]
            brake_pitch = valid_pitch[mask_brake]
            brake_speed = speed[mask][mask_brake]
            
            accel_g = valid_long_g[mask_accel]
            accel_pitch = valid_pitch[mask_accel]
            accel_speed = speed[mask][mask_accel]
            
            # Linear regressions (We force it through 0,0 conceptually, or just standard polyfit)
            brake_m, brake_c = 0, 0
            if len(brake_g) > 10:
                brake_m, brake_c = np.polyfit(brake_g, brake_pitch, 1)
                
            accel_m, accel_c = 0, 0
            if len(accel_g) > 10:
                accel_m, accel_c = np.polyfit(accel_g, accel_pitch, 1)
            def get_r2(x, y, m, c):
                if len(x) < 2: return 0
                y_pred = m * x + c
                ss_res = np.sum((y - y_pred)**2)
                ss_tot = np.sum((y - np.mean(y))**2)
                return 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

            brake_r2 = get_r2(brake_g, brake_pitch, brake_m, brake_c) if len(brake_g) > 10 else 0
            accel_r2 = get_r2(accel_g, accel_pitch, accel_m, accel_c) if len(accel_g) > 10 else 0


            from matplotlib.colors import LinearSegmentedColormap
            opendav_colors = ["#2D8AE2", "#FF1493", "#D2751D"] # Blue -> Pink -> Orange
            opendav_cmap = LinearSegmentedColormap.from_list("opendav_pitch", opendav_colors, N=256)

            PINK = '\033[95m'
            CYAN = '\033[96m'
            RESET = "\033[0m"
            
            if not headless:
                print("\n ┌" + "─" * 49 + "┐")
                print(" │ " + "[ PITCH KINEMATICS & STIFFNESS ]".ljust(47) + " │")
                print(" │ " + f"Brake Dive: {PINK}{abs(brake_m):.2f} mm/G{RESET} (R²: {brake_r2:.3f})".ljust(47 + len(PINK) + len(RESET)) + " │")
                print(" │ " + f"Accel Squat: {CYAN}{abs(accel_m):.2f} mm/G{RESET} (R²: {accel_r2:.3f})".ljust(47 + len(CYAN) + len(RESET)) + " │")
                print(" │ " + f"Static Rake (0G): {static_rake:.1f} mm".ljust(47) + " │")
                print(" └" + "─" * 49 + "┘")
            
            md = session.get('metadata', {})
            car_name = md.get('car', 'UNKNOWN')
            file_basename = os.path.basename(file_path)

            l1_preview = f"""
        L1: LONGITUDINAL PITCH (RAW)                      PITCH GRADIENT (MODELED)               
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
 │ [X] AXIS: LONGITUDINAL G-FORCE          │   │ [X] AXIS: LONGITUDINAL G-FORCE          │      
 │ [Y] AXIS: DYNAMIC RAKE DELTA (MM)       │   │ [Y] AXIS: DYNAMIC RAKE DELTA (MM)       │      
 │ [L] LINE: BRAKE vs ACCEL GRADIENT       │   │ [L] LINE: BRAKE vs ACCEL GRADIENT       │      
 └─────────────────────────────────────────┘   └─────────────────────────────────────────┘      
 
  FILE: {file_basename}
  VEHICLE: {car_name}
  
  >> [USE CASE]: QUANTIFY AERODYNAMIC PLATFORM STABILITY UNDER HEAVY BRAKING AND ACCELERATION."""
  
            l2_preview = f"""
        L2: PITCH KINEMATICS (PRIMARY)                    PITCH KINEMATICS (REFERENCE)               
 ┌─────────────────────────────────────────┐   ┌─────────────────────────────────────────┐      
 │                                         │   │ SETUP SHIFT: Fr Spring [120->140]       │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │ [X] AXIS: LONGITUDINAL G-FORCE          │   │ [X] AXIS: LONGITUDINAL G-FORCE          │      
 │ [Y] AXIS: DYNAMIC RAKE DELTA (MM)       │   │ [Y] AXIS: DYNAMIC RAKE DELTA (MM)       │      
 │ [L] LINE: BRAKE vs ACCEL GRADIENT       │   │ [L] LINE: BRAKE vs ACCEL GRADIENT       │      
 └─────────────────────────────────────────┘   └─────────────────────────────────────────┘      
 
  >> [USE CASE]: DIRECTLY COMPARE CHASSIS PITCH STIFFNESS / ANTI-DIVE BETWEEN TWO SETUP ITERATIONS."""

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
                    if not headless: print("  [+] Building Pitch Kinematics Graph...")
                    import matplotx
                    plt.style.use(matplotx.styles.aura['dark'])
                    plt.rcParams['font.family'] = 'Consolas'
                    fig = plt.figure(figsize=(12, 7), num='OpenDAV - Pitch Kinematics Analyzer')
    
                    sc_b = plt.scatter(brake_g, brake_pitch, c=brake_speed, cmap=opendav_cmap, alpha=0.6, s=15, edgecolors='none', vmin=40, vmax=140)
                    sc_a = plt.scatter(accel_g, accel_pitch, c=accel_speed, cmap=opendav_cmap, alpha=0.6, s=15, edgecolors='none', vmin=40, vmax=140)
                    cbar = plt.colorbar(sc_b, pad=0.02)
                    cbar.set_label('Speed (km/h)', fontsize=11)
                    
                    # Invisible scatter points just for the legend
                    plt.scatter([], [], color='#FF1493', s=15, label='Braking Telemetry')
                    plt.scatter([], [], color='#2D8AE2', s=15, label='Accel Telemetry')
                    
                    if len(brake_g) > 10:
                        x_b = np.array([min(brake_g), 0])
                        plt.plot(x_b, brake_m * x_b + brake_c, color='#FF1493', linewidth=3, label=f'Brake Dive: {abs(brake_m):.2f} mm/G (R²: {brake_r2:.3f})')
                    if len(accel_g) > 10:
                        x_a = np.array([0, max(accel_g)])
                        plt.plot(x_a, accel_m * x_a + accel_c, color='#2D8AE2', linewidth=3, label=f'Accel Squat: {abs(accel_m):.2f} mm/G (R²: {accel_r2:.3f})')
    
                    
                    # Enable Speed display in the Matplotlib status bar
                    # Combine Brake and Accel data for the lookup tree
                    all_g = np.concatenate([brake_g, accel_g])
                    all_p = np.concatenate([brake_pitch, accel_pitch])
                    all_s = np.concatenate([brake_speed, accel_speed])
                    lookup_tree = cKDTree(np.column_stack((all_g, all_p)))
                    def format_coord(x, y):
                        dist, idx = lookup_tree.query([x, y])
                        if dist > 0.5: return f'LongG={x:.3f}, RakeDelta={y:.1f}mm'
                        val = all_s[idx]
                        return f'LongG={x:.3f}, RakeDelta={y:.1f}mm, Speed={val:.1f}km/h'
                    plt.gca().format_coord = format_coord

                    plt.axvline(0, color='white', linewidth=1, alpha=0.5, linestyle='--')
                    plt.axhline(0, color='white', linewidth=1, alpha=0.5, linestyle='--')
                    
                    plt.title(f"Dynamic Pitch Stiffness\n{file_basename}", fontsize=16, fontweight='bold', pad=20)
                    plt.xlabel("Longitudinal G-Force (Negative = Braking)", fontsize=13)
                    plt.ylabel("Rake Delta (mm) [Positive = Diving Forward]", fontsize=13)
                    plt.legend(fontsize=11)
                    plt.grid(True, linestyle='--', alpha=0.2)
                    
                    info_text = (f"Driver: {md.get('driver', 'N/A')}\nCar: {md.get('car', 'N/A')}\nVenue: {md.get('venue', 'N/A')}")
                    plt.figtext(0.02, 0.02, info_text, fontsize=9, color='white', alpha=0.8, va='bottom', ha='left',
                                bbox=dict(facecolor='#1a1a1a', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.5'))
                    plt.tight_layout()

                    if ans == 'open l1':
                        gui_mode = get_gui_mode()
                        if gui_mode == 3: show_ctk_graph(fig, "OpenDAV - Pitch Kinematics")
                        else: plt.show()
                    else:
                        import datetime
                        timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                        file_out = f"Pitch_L1_{timestamp}_{file_basename}.png"
                        if '<' in ans_raw:
                            project_name = ans_raw.split('<')[1].strip()
                            from analysis.projects import save_to_project
                            save_to_project(fig, project_name, file_out)
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
                            
                    # Process Reference
                    r_speed_raw = r_data[speed_ch].data
                    r_speed = r_speed_raw if np.max(r_speed_raw) > 150 else (r_speed_raw * 3.6 if "m/s" in r_data[speed_ch].unit.lower() else r_speed_raw * 1.609)
                    
                    r_f_rh = (r_data[fl_ch].data + r_data[fr_ch].data) / 2.0 * 1000
                    r_r_rh = (r_data[rl_ch].data + r_data[rr_ch].data) / 2.0 * 1000
                    
                    window = 10
                    r_f_rh = np.convolve(r_f_rh, np.ones(window)/window, mode='same')
                    r_r_rh = np.convolve(r_r_rh, np.ones(window)/window, mode='same')
                    
                    r_rake = r_r_rh - r_f_rh
                    
                    r_lat_g = r_data[r_channels.get('lat', lat_g_ch)].data
                    r_long_g = r_data[r_channels.get('long', long_g_ch)].data
                    r_long_g_smooth = np.convolve(r_long_g, np.ones(window)/window, mode='same')
                    
                    r_static_mask = (r_speed < 15) & (np.abs(r_lat_g) < 0.1) & (np.abs(r_long_g) < 0.1)
                    r_static_rake = np.median(r_rake[r_static_mask]) if np.any(r_static_mask) else np.median(r_rake)
                    r_dyn_rake = r_rake - r_static_rake
                    
                    r_mask = (r_speed > 40) & (r_speed < 140) & (np.abs(r_lat_g) < 0.15)
                    r_valid_g = r_long_g_smooth[r_mask]
                    r_valid_pitch = r_dyn_rake[r_mask]
                    
                    r_b_m, r_b_c = 0, 0
                    r_brake_speed = r_speed[r_mask][r_valid_g < -0.2]
                    if len(r_valid_g[r_valid_g < -0.2]) > 10:
                        r_b_m, r_b_c = np.polyfit(r_valid_g[r_valid_g < -0.2], r_valid_pitch[r_valid_g < -0.2], 1)
                        
                    r_a_m, r_a_c = 0, 0
                    r_accel_speed = r_speed[r_mask][r_valid_g > 0.2]
                    if len(r_valid_g[r_valid_g > 0.2]) > 10:
                        r_a_m, r_a_c = np.polyfit(r_valid_g[r_valid_g > 0.2], r_valid_pitch[r_valid_g > 0.2], 1)
                    def get_r2(x, y, m, c):
                        if len(x) < 2: return 0
                        y_pred = m * x + c
                        ss_res = np.sum((y - y_pred)**2)
                        ss_tot = np.sum((y - np.mean(y))**2)
                        return 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

                    r_brake_r2 = get_r2(r_valid_g[r_valid_g < -0.2], r_valid_pitch[r_valid_g < -0.2], r_b_m, r_b_c) if len(r_valid_g[r_valid_g < -0.2]) > 10 else 0
                    r_accel_r2 = get_r2(r_valid_g[r_valid_g > 0.2], r_valid_pitch[r_valid_g > 0.2], r_a_m, r_a_c) if len(r_valid_g[r_valid_g > 0.2]) > 10 else 0


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
                    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8), num='OpenDAV - L2 Pitch Comparison')
                    
                    for i_ax, (ax, b_g, b_p, b_s, a_g, a_p, a_s, bm, bc, am, ac, tit, subt) in enumerate([
                        (ax1, brake_g, brake_pitch, brake_speed, accel_g, accel_pitch, accel_speed, brake_m, brake_c, accel_m, accel_c, "PRIMARY", f"{file_basename}"),
                        (ax2, r_valid_g[r_valid_g < -0.2], r_valid_pitch[r_valid_g < -0.2], r_brake_speed, r_valid_g[r_valid_g > 0.2], r_valid_pitch[r_valid_g > 0.2], r_accel_speed, r_b_m, r_b_c, r_a_m, r_a_c, "REFERENCE", f"{delta_title}")
                    ]):
                        sc_b = ax.scatter(b_g, b_p, c=b_s, cmap=opendav_cmap, alpha=0.6, s=15, edgecolors='none', vmin=40, vmax=140)
                        sc_a = ax.scatter(a_g, a_p, c=a_s, cmap=opendav_cmap, alpha=0.6, s=15, edgecolors='none', vmin=40, vmax=140)
                        
                        # Only add colorbar on the second plot to save space, or a shared one below.
                        if i_ax == 1:
                            cbar = plt.colorbar(sc_b, ax=[ax1, ax2], location='bottom', aspect=40, pad=0.1)
                            cbar.set_label('Speed (km/h)', fontsize=12)
                        
                        if len(b_g) > 10:
                            xb = np.array([min(b_g), 0])
                            ax.plot(xb, bm*xb+bc, color='#FF1493', lw=3, label=f'Brake Dive: {abs(bm):.2f} mm/G (R²: {brake_r2 if tit == "PRIMARY" else r_brake_r2:.3f})')
                        if len(a_g) > 10:
                            xa = np.array([0, max(a_g)])
                            ax.plot(xa, am*xa+ac, color='#2D8AE2', lw=3, label=f'Accel Squat: {abs(am):.2f} mm/G (R²: {accel_r2 if tit == "PRIMARY" else r_accel_r2:.3f})')
                            
                                                # Enable Speed display in the Matplotlib status bar
                        all_g_l2 = np.concatenate([b_g, a_g])
                        all_p_l2 = np.concatenate([b_p, a_p])
                        all_s_l2 = np.concatenate([b_s, a_s])
                        lookup_tree_l2 = cKDTree(np.column_stack((all_g_l2, all_p_l2)))
                        def format_coord_l2(x, y):
                            dist, idx = lookup_tree_l2.query([x, y])
                            if dist > 0.5: return f'LongG={x:.3f}, RakeDelta={y:.1f}mm'
                            val = all_s_l2[idx]
                            return f'LongG={x:.3f}, RakeDelta={y:.1f}mm, Speed={val:.1f}km/h'
                        ax.format_coord = format_coord_l2

                        ax.axvline(0, color='white', linewidth=1, alpha=0.5, linestyle='--')
                        ax.axhline(0, color='white', linewidth=1, alpha=0.5, linestyle='--')
                        
                        import textwrap
                        subt_wrapped = "\\n".join(textwrap.wrap(subt, 60))
                        ax.set_title(f"{tit}\n{subt_wrapped}", fontsize=11)
                        ax.set_xlabel("Longitudinal G-Force")
                        ax.set_ylabel("Rake Delta (mm)")
                        ax.legend()
                        ax.grid(True, alpha=0.2)
                    
                    plt.tight_layout()
                    if ans == 'open l2':
                        if get_gui_mode() == 3: show_ctk_graph(fig, "OpenDAV - L2 Pitch Comparison")
                        else: plt.show()
                    elif ans == 'print l2':
                        import datetime
                        ts = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                        file_out = f"Pitch_L2_{ts}_{file_basename}.png"
                        if '<' in ans_raw:
                            project_name = ans_raw.split('<')[1].strip()
                            from analysis.projects import save_to_project
                            save_to_project(fig, project_name, file_out)
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
