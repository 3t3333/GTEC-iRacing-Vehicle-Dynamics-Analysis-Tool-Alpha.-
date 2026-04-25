import os
import sys
import datetime
import numpy as np
import yaml
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from scipy.interpolate import Rbf
from scipy.spatial import ConvexHull, cKDTree
from matplotlib.path import Path
import ui.splash as splash
from ui.metadata_printer import print_session_metadata
from ui.graphing import show_ctk_graph
from core.config import get_gui_mode

def run_aero_mapping(sessions, headless=False, headless_config=None):
    while True:
        splash.print_header("Empirical Aero Map Generator")
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            channels = session['channels']
            print(f"\nAnalyzing: {os.path.basename(file_path)}")
            print_session_metadata(data, channels, session.get('metadata', {}))
            
            # Find required channels
            lat_g_ch = channels['lat']
            long_g_ch = channels['long']
            
            speed_ch = None
            for ch in ['Speed', 'Ground Speed']:
                if ch in data: speed_ch = ch; break
                
            fl_ch, fr_ch = 'Ride Height FL', 'Ride Height FR'
            rl_ch, rr_ch = 'Ride Height RL', 'Ride Height RR'
            
            fl_load, fr_load = 'Suspension Load FL', 'Suspension Load FR'
            rl_load, rr_load = 'Suspension Load RL', 'Suspension Load RR'

            required = [speed_ch, fl_ch, fr_ch, rl_ch, rr_ch, fl_load, fr_load, rl_load, rr_load]
            missing = [ch for ch in required if ch not in data]
            if missing:
                print(f"  [!] Missing required channels for Aero Mapping: {missing}")
                print("      Note: This tool requires Suspension Load or Shock Deflection channels (usually available in iRacing Open Wheel/Prototypes).")
                print("\nPress Enter to return...")
                input()
                continue

            # Load Data
            speed = data[speed_ch].data * 2.23694 # Assume m/s to mph for now. Better check max speed later.
            if np.max(data[speed_ch].data) > 150: speed = data[speed_ch].data * 0.621371 # km/h to mph

            fl_rh = data[fl_ch].data * 1000
            fr_rh = data[fr_ch].data * 1000
            rl_rh = data[rl_ch].data * 1000
            rr_rh = data[rr_ch].data * 1000

            fl_l = data[fl_load].data
            fr_l = data[fr_load].data
            rl_l = data[rl_load].data
            rr_l = data[rr_load].data
            
            long_g = data[long_g_ch].data
            lat_g = data[lat_g_ch].data

            # 1. Isolate the "Coast-Down" Calibration Zones
            # High speed (> 100mph), Zero Lat G (< 0.1), Zero Long G (+- 0.1 from drag deceleration)
            print("  [*] Running Coast-Down auto-calibration...")
            
            coast_mask = (speed > 100) & (np.abs(lat_g) < 0.1) & (np.abs(long_g) < 0.15)
            if not np.any(coast_mask):
                print("  [!] Could not find clear Coast-Down zones (Zero-G straightaways) to auto-calibrate base loads.")
                continue

            # 2. Establish Static Loads (Approximation from very low speeds)
            static_mask = (speed < 10) & (np.abs(lat_g) < 0.1) & (np.abs(long_g) < 0.1)
            if np.any(static_mask):
                static_fl = np.median(fl_l[static_mask])
                static_fr = np.median(fr_l[static_mask])
                static_rl = np.median(rl_l[static_mask])
                static_rr = np.median(rr_l[static_mask])
            else:
                print("  [!] No pit-lane/low-speed data to find static weights. Assuming symmetric start weights.")
                static_fl = np.median(fl_l) * 0.4 # Rough guess for prototyping
                static_fr = static_fl
                static_rl = np.median(rl_l) * 0.6
                static_rr = static_rl

            # 3. Filter for High-Speed Stable Corners & Straights to build the map
            # We want areas where aerodynamics are working (Speed > 80mph)
            aero_mask = (speed > 80)
            
            filtered_speed = speed[aero_mask]
            f_rh = ((fl_rh + fr_rh) / 2.0)[aero_mask]
            r_rh = ((rl_rh + rr_rh) / 2.0)[aero_mask]
            
            total_front_load = (fl_l + fr_l)[aero_mask]
            total_rear_load = (rl_l + rr_l)[aero_mask]
            
            # Simple Mechanical Subtraction (Ignoring Pitch transfer for the simplified V1 Map)
            # In V2, we will use Wheelbase and CG Height to remove Longitudinal Transfer exactly.
            aero_front = total_front_load - (static_fl + static_fr)
            aero_rear = total_rear_load - (static_rl + static_rr)
            
            # Ensure we don't divide by zero or negative total downforce. 
            # The threshold is lowered to 50 for robust IBT mock fallback functionality.
            valid_df_mask = (aero_front + aero_rear) > 50 
            
            f_rh = f_rh[valid_df_mask]
            r_rh = r_rh[valid_df_mask]
            aero_front = aero_front[valid_df_mask]
            aero_rear = aero_rear[valid_df_mask]
            
            if len(f_rh) == 0:
                print("  [!] Insufficient downforce generated to build a reliable Aero Map.")
                continue

            aero_balance = (aero_front / (aero_front + aero_rear)) * 100.0
            # Clamp strictly between 0% and 100% to block extreme noise/sensor errors
            aero_balance = np.clip(aero_balance, 0.0, 100.0)
            rake_angle = r_rh - f_rh
            
            # Binning for the Terminal Output
            median_ab = np.median(aero_balance)
            max_ab = np.max(aero_balance)
            min_ab = np.min(aero_balance)

            PINK = '\033[95m'
            CYAN = '\033[96m'
            RESET = "\033[0m"
            
            print("\n  ┌" + "─" * 98 + "┐")
            print("  │ " + "[ EMPIRICAL AERO BALANCE ]".ljust(92) + " │")
            print("  │ " + f"Average High-Speed AB: {CYAN}{median_ab:.1f}% Front{RESET}".ljust(96 + len(CYAN) + len(RESET)) + " │")
            print("  │ " + f"Peak Pitch AB (Braking): {PINK}{max_ab:.1f}% Front{RESET}".ljust(96 + len(PINK) + len(RESET)) + " │")
            print("  │ " + f"Minimum AB (Accel):      {min_ab:.1f}% Front".ljust(92) + " │")
            print("  └" + "─" * 98 + "┘")

            md = session.get('metadata', {})
            car_name = md.get('car', 'UNKNOWN')
            file_basename = os.path.basename(file_path)

            l1_preview = f"""
        L1: 3D SCATTERPLOT (RAW)                          2D INTERPOLATION (MODELED)               
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
 │ [X] AXIS: FRONT RIDE HEIGHT             │   │ [X] AXIS: FRONT RIDE HEIGHT             │      
 │ [Y] AXIS: REAR RIDE HEIGHT              │   │ [Y] AXIS: REAR RIDE HEIGHT              │      
 │ [Z] AXIS: AERO BALANCE %                │   │ [C] MAP:  AB % DENSITY                  │      
 └─────────────────────────────────────────┘   └─────────────────────────────────────────┘      
 
  FILE: {file_basename}
  VEHICLE: {car_name}
  
  >> [USE CASE]: VIEW RAW DATA FIDELITY SIDE-BY-SIDE WITH THE MATHEMATICAL SURFACE MODEL."""
            print(l1_preview)
            l2_preview = f"""
        L2: 2D INTERPOLATION (PRIMARY)                    2D INTERPOLATION (REFERENCE)               
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
 │ [X] AXIS: FRONT RIDE HEIGHT             │   │ [X] AXIS: FRONT RIDE HEIGHT             │      
 │ [Y] AXIS: REAR RIDE HEIGHT              │   │ [Y] AXIS: REAR RIDE HEIGHT              │      
 │ [C] MAP:  AB % DENSITY                  │   │ [C] MAP:  AB % DENSITY                  │      
 └─────────────────────────────────────────┘   └─────────────────────────────────────────┘      
 
  >> [USE CASE]: DIRECTLY COMPARE AERODYNAMIC TOPOGRAPHY SHIFTS BETWEEN TWO SETUP ITERATIONS.

        L3: TARGET DELTA ANALYZER (MIGRATION & STABILITY)
 ┌───────────────────────────────────────────────────────────────────────────────────────┐
 │        [ SHADED LINE CHART ] DYNAMIC AERO BALANCE OVER TRACK DISTANCE                 │
 │       [ RED SHADING ] = MIGRATION SPIKE (OVERSTEER / LINE OF DEATH CROSSED)           │
 │       [ BLUE SHADING ] = SAFE ZONE (UNDERSTEER / CENTER OF PRESSURE BEHIND COG)       │
 └───────────────────────────────────────────────────────────────────────────────────────┘
 ┌─────────────────────────────────────────┐   ┌─────────────────────────────────────────┐      
 │     [ SCATTER ] RIDE HEIGHT ENVELOPE    │   │      [ LINE ] PITCH KINEMATICS          │
 │       VERIFY MECHANICAL PLATFORM        │   │        VERIFY BRAKING STABILITY         │
 └─────────────────────────────────────────┘   └─────────────────────────────────────────┘
  
  >> [USE CASE]: DIAGNOSE IF AERO VARIANCE IS CAUSED BY MECHANICAL PLATFORM FAILURE OR PITCH SENSITIVITY.
"""
            print(l2_preview)

            _headless_ran = False

            # Define Custom OpenDAV Colormap for all plots in this module
            from matplotlib.colors import LinearSegmentedColormap
            opendav_colors = ["#2D8AE2", "#FF1493", "#D2751D"] # Blue -> Pink -> Orange
            opendav_cmap = LinearSegmentedColormap.from_list("opendav_aero", opendav_colors, N=256)

            while True:
                if headless:
                    if headless_config.get('_ran'): return
                    headless_config['_ran'] = True
                    ans_raw = f"print {headless_config['layout'].lower()} < {headless_config['project']}"
                else:
                    ans_raw = input(f"\n  Select action ('open L1/L2/L3', 'print L1/L2/L3', 'p' to go back < proj): ").strip().lower()
                ans = ans_raw.split('<')[0].strip().lower()
                
                if ans == 'p':
                    break
                    
                if ans == 'open l1':
                    print("  [+] Building interactive simulation dashboard... (Close the window to continue)")
                    import matplotx
                    import matplotlib.tri as mtri
                    from mpl_toolkits.mplot3d import Axes3D

                    plt.style.use(matplotx.styles.aura['dark'])
                    fig = plt.figure(figsize=(16, 8), num='OpenDAV - 3D Aero Simulation')
                    
                    if len(f_rh) > 3000:
                        idx = np.linspace(0, len(f_rh)-1, 3000, dtype=int)
                        f_sim, r_sim, z_sim = f_rh[idx], r_rh[idx], aero_balance[idx]
                    else:
                        f_sim, r_sim, z_sim = f_rh, r_rh, aero_balance

                    ax3d = fig.add_subplot(1, 2, 1, projection='3d')
                    triang = mtri.Triangulation(f_sim, r_sim)
                    centers = np.column_stack((np.mean(f_sim[triang.triangles], axis=1), np.mean(r_sim[triang.triangles], axis=1)))
                    tree = cKDTree(np.column_stack((f_sim, r_sim)))
                    distances, _ = tree.query(centers)
                    threshold = max(max(f_sim) - min(f_sim), max(r_sim) - min(r_sim)) * 0.05
                    triang.set_mask(distances > threshold)

                    ax3d.scatter(f_sim, r_sim, z_sim, c=z_sim, cmap=opendav_cmap, s=5, alpha=0.8, edgecolors='none', rasterized=True)
                    ax3d.set_title("3D Aero Balance Platform", fontsize=14, pad=20)
                    ax3d.set_xlabel("Front RH (mm)")
                    ax3d.set_ylabel("Rear RH (mm)")
                    ax3d.set_zlabel("AB %")
                    ax3d.view_init(elev=30, azim=225, vertical_axis='z')

                    ax2d = fig.add_subplot(1, 2, 2)
                    levels = np.linspace(0, 100, 20)
                    cf = ax2d.tricontourf(triang, z_sim, levels=levels, cmap=opendav_cmap, extend='both', alpha=0.9)
                    lines = ax2d.tricontour(triang, z_sim, levels=10, colors='white', linewidths=0.5, alpha=0.3)
                    ax2d.clabel(lines, inline=True, fontsize=8, fmt='%.1f%%')
                    ax2d.scatter(f_sim, r_sim, c='white', s=2, alpha=0.2, rasterized=True)
                    ax2d.set_title("2D Platform Topography", fontsize=14, pad=20)
                    ax2d.set_xlabel("Front Ride Height (mm)")
                    ax2d.set_ylabel("Rear Ride Height (mm)")
                    lookup_tree_sim = cKDTree(np.column_stack((f_sim, r_sim)))
                    def format_coord_sim(x, y):
                        dist, idx = lookup_tree_sim.query([x, y])
                        if dist > 5.0: return f'x={x:.1f}, y={y:.1f}'
                        return f'x={x:.1f}, y={y:.1f}, AB={z_sim[idx]:.1f}%'
                    ax2d.format_coord = format_coord_sim
                    plt.colorbar(cf, ax=ax2d, label='Aero Balance (% Front)')
                    plt.tight_layout()

                    gui_mode = get_gui_mode()
                    if gui_mode == 3:
                        show_ctk_graph(fig, "OpenDAV - 3D Aero Simulation")
                    else:
                        plt.show()

                elif ans == 'print l1':
                    print("  [+] Generating 2D Interpolation Exports...")
                    
                    def generate_2d_plot(f_data, r_data, z_data, title, filename):
                        base_name = os.path.basename(filename)
                        if len(f_data) < 15: 
                            print(f"      [-] Skipped {base_name}: Insufficient high-speed data ({len(f_data)} pts).")
                            return
                        if len(f_data) > 2000:
                            idx = np.linspace(0, len(f_data)-1, 2000, dtype=int)
                            f_s, r_s, z_s = f_data[idx], r_data[idx], z_data[idx]
                        else:
                            f_s, r_s, z_s = f_data, r_data, z_data
                        try:
                            import matplotlib.ticker as ticker
                            import matplotx
                            import matplotlib.tri as mtri
                            plt.style.use(matplotx.styles.aura['dark'])
                            plt.figure(figsize=(10, 8))
                            triang = mtri.Triangulation(f_s, r_s)
                            c_x = np.mean(f_s[triang.triangles], axis=1)
                            c_y = np.mean(r_s[triang.triangles], axis=1)
                            centers = np.column_stack((c_x, c_y))
                            tree = cKDTree(np.column_stack((f_s, r_s)))
                            distances, _ = tree.query(centers)
                            threshold = max(max(f_s) - min(f_s), max(r_s) - min(r_s)) * 0.04
                            triang.set_mask(distances > threshold)
                            levels = np.linspace(0, 100, 20) if '%' == '%' else 20
                            contourf = plt.tricontourf(triang, z_s, levels=levels, cmap=opendav_cmap, extend='both', alpha=0.9)
                            lines = plt.tricontour(triang, z_s, levels=10, cmap=opendav_cmap, linewidths=1.5, alpha=0.8)
                            plt.clabel(lines, inline=True, fontsize=9, fmt='%.1f%%', colors='white')
                            plt.colorbar(contourf, label='AB (%)' if '%' == '%' else 'AB')
                            plt.scatter(f_s, r_s, c='white', s=3, alpha=0.4, edgecolors='black', linewidths=0.2, rasterized=True)
                            ax = plt.gca()
                            
                            # Enable Z-value coordinate display
                            lookup_tree = cKDTree(np.column_stack((f_s, r_s)))
                            def format_coord(x, y):
                                dist, idx = lookup_tree.query([x, y])
                                if dist > 5.0: return f'x={x:.1f}, y={y:.1f}'
                                return f'x={x:.1f}, y={y:.1f}, AB={z_s[idx]:.1f}%'
                            ax.format_coord = format_coord
                            
                            ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
                            ax.yaxis.set_major_locator(ticker.MultipleLocator(20))
                            plt.grid(True, which='both', linestyle='--', alpha=0.1, color='white')
                            plt.title(title)
                            plt.xlabel("Front Ride Height (mm)")
                            plt.ylabel("Rear Ride Height (mm)")
                            plt.savefig(filename, dpi=300, bbox_inches='tight')
                            plt.close()
                            print(f"      [+] Exported {base_name}")
                        except Exception as e:
                            print(f"      [-] Skipped {base_name}: Math error ({e}).")

                    try:
                        timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                        export_dir = f"exports/F2L1_{timestamp}"
                        os.makedirs(export_dir, exist_ok=True)
                        main_filename = os.path.join(export_dir, f"F2L1_{file_basename}.png")
                        generate_2d_plot(f_rh, r_rh, aero_balance, f"2D Aero Balance Heatmap\n{file_basename}", main_filename)
                        
                        ans_ext = 'n' if headless else input("  Print extended report (Sectors/Corners)? (y/n): ").strip().lower()
                        if ans_ext == 'y':
                            dist_ch = channels.get('dist')
                            if dist_ch and dist_ch in data:
                                dist_raw = data[dist_ch].data
                                lap_arr = data[channels['lap']].data
                                filtered_dist = dist_raw[aero_mask][valid_df_mask]
                                filtered_lap = lap_arr[aero_mask][valid_df_mask]
                                laps = np.unique(filtered_lap)
                                target_lap = laps[len(laps)//2] if len(laps) > 0 else 0
                                lap_mask = (filtered_lap == target_lap)
                                l_dist = filtered_dist[lap_mask]
                                if len(l_dist) > 0:
                                    total_lap_dist = np.max(l_dist) - np.min(l_dist)
                                    # 1. Sector Maps
                                    yaml_str = md.get('session_info_yaml', '')
                                    sectors = []
                                    try:
                                        y_data = yaml.safe_load(yaml_str)
                                        if y_data and 'SplitTimeInfo' in y_data and 'Sectors' in y_data['SplitTimeInfo']:
                                            for s in y_data['SplitTimeInfo']['Sectors']:
                                                pct = s.get('SectorStartPct', -1)
                                                if pct >= 0: sectors.append(pct)
                                    except: pass
                                    if sectors:
                                        sectors.append(1.0)
                                        for i in range(len(sectors)-1):
                                            start_m = np.min(l_dist) + (sectors[i] * total_lap_dist)
                                            end_m = np.min(l_dist) + (sectors[i+1] * total_lap_dist)
                                            s_mask = (filtered_dist >= start_m) & (filtered_dist < end_m)
                                            generate_2d_plot(f_rh[s_mask], r_rh[s_mask], aero_balance[s_mask], f"AB - Sector {i+1}\n{file_basename}", os.path.join(export_dir, f"S{i+1}.png"))
                                    # 2. Corner Maps
                                    if 'LatAccel' in data:
                                        lap_idx = np.where(data[channels['lap']].data == target_lap)[0]
                                        d_lap_dist = data[dist_ch].data[lap_idx]
                                        d_lat = data['LatAccel'].data[lap_idx] / 9.81
                                        window = 20
                                        smooth_lat = np.convolve(d_lat, np.ones(window)/window, mode='same')
                                        is_corner = np.abs(smooth_lat) > 0.25
                                        corners = []; in_c = False; start_i = 0
                                        for i in range(len(is_corner)):
                                            if is_corner[i] and not in_c: in_c = True; start_i = i
                                            elif not is_corner[i] and in_c: in_c = False; corners.append({'start': start_i, 'end': i})
                                        merged_corners = []
                                        if corners:
                                            curr = corners[0]
                                            for nxt in corners[1:]:
                                                if (d_lap_dist[nxt['start']] - d_lap_dist[curr['end']]) < 30: curr['end'] = nxt['end']
                                                else: merged_corners.append(curr); curr = nxt
                                            merged_corners.append(curr)
                                        alg_corners = [c for c in merged_corners if (d_lap_dist[c['end']] - d_lap_dist[c['start']]) >= 15]
                                        for i, c in enumerate(alg_corners):
                                            start_m = d_lap_dist[c['start']]; end_m = d_lap_dist[c['end']]
                                            c_mask = (filtered_dist >= start_m) & (filtered_dist <= end_m)
                                            generate_2d_plot(f_rh[c_mask], r_rh[c_mask], aero_balance[c_mask], f"AB - Corner {i+1}\n{file_basename}", os.path.join(export_dir, f"algocorr{i+1}.png"))
                            else: print("      [!] Could not isolate distance tracking.")
                        else: print("      [!] Distance channel required for extended report.")
                        if headless: break
                    except Exception as e:
                        print(f"  [!] Failed to generate report: {e}")
                        if headless: break
                
                elif ans in ['open l2', 'print l2']:
                    from core.telemetry import load_telemetry
                    
                    if headless:
                        ref_path = headless_config['ref_path']
                        try:
                            ref_data, _, ref_channels, ref_metadata = load_telemetry(ref_path)
                        except Exception as e:
                            print(f"  [!] Error loading reference file: {e}")
                            break
                    else:
                        telemetry_dir = "telemetry"
                        if not os.path.exists(telemetry_dir):
                            print(f"  [!] Directory '{telemetry_dir}' not found.")
                            continue
                            
                        ld_files = [f for f in os.listdir(telemetry_dir) if f.lower().endswith(('.ld', '.ibt'))]
                        ld_files.sort()
                        
                        if not ld_files:
                            print("  [!] No files found in telemetry directory.")
                            continue
                            
                        print("\n  Select Reference File:")
                        for i, lf in enumerate(ld_files):
                            print(f"    {i+1}. {lf}")
                        print("  ─" * 20)
                        ref_choice = input("  Selection (number): ").strip()
                        try:
                            ref_idx = int(ref_choice) - 1
                            if not (0 <= ref_idx < len(ld_files)):
                                raise ValueError()
                        except ValueError:
                            print("  [!] Invalid selection.")
                            continue
                            
                        ref_path = os.path.join(telemetry_dir, ld_files[ref_idx])
                        print(f"  [*] Loading Reference: {os.path.basename(ref_path)}")
                        
                        try:
                            ref_data, _, ref_channels, ref_metadata = load_telemetry(ref_path)
                        except Exception as e:
                            print(f"  [!] Error loading reference file: {e}")
                            continue
                        
                    # Process Reference File
                    r_lat_g_ch = ref_channels.get('lat')
                    r_long_g_ch = ref_channels.get('long')
                    
                    r_speed_ch = None
                    for ch in ['Speed', 'Ground Speed']:
                        if ch in ref_data: r_speed_ch = ch; break
                        
                    r_req = [r_speed_ch, 'Ride Height FL', 'Ride Height FR', 'Ride Height RL', 'Ride Height RR',
                             'Suspension Load FL', 'Suspension Load FR', 'Suspension Load RL', 'Suspension Load RR']
                    if any(ch not in ref_data for ch in r_req if ch is not None):
                        print("  [!] Reference file missing required channels.")
                        continue
                        
                    r_speed = ref_data[r_speed_ch].data * 2.23694
                    if np.max(ref_data[r_speed_ch].data) > 150: r_speed = ref_data[r_speed_ch].data * 0.621371
                    
                    r_fl_rh = ref_data['Ride Height FL'].data * 1000
                    r_fr_rh = ref_data['Ride Height FR'].data * 1000
                    r_rl_rh = ref_data['Ride Height RL'].data * 1000
                    r_rr_rh = ref_data['Ride Height RR'].data * 1000
                    
                    r_fl_l = ref_data['Suspension Load FL'].data
                    r_fr_l = ref_data['Suspension Load FR'].data
                    r_rl_l = ref_data['Suspension Load RL'].data
                    r_rr_l = ref_data['Suspension Load RR'].data
                    
                    r_long_g = ref_data[r_long_g_ch].data if r_long_g_ch in ref_data else np.zeros_like(r_speed)
                    r_lat_g = ref_data[r_lat_g_ch].data if r_lat_g_ch in ref_data else np.zeros_like(r_speed)
                    
                    r_static_mask = (r_speed < 10) & (np.abs(r_lat_g) < 0.1) & (np.abs(r_long_g) < 0.1)
                    if np.any(r_static_mask):
                        r_s_fl = np.median(r_fl_l[r_static_mask])
                        r_s_fr = np.median(r_fr_l[r_static_mask])
                        r_s_rl = np.median(r_rl_l[r_static_mask])
                        r_s_rr = np.median(r_rr_l[r_static_mask])
                    else:
                        r_s_fl = np.median(r_fl_l) * 0.4
                        r_s_fr = r_s_fl
                        r_s_rl = np.median(r_rl_l) * 0.6
                        r_s_rr = r_s_rl
                        
                    r_aero_mask = (r_speed > 80)
                    r_f_rh = ((r_fl_rh + r_fr_rh) / 2.0)[r_aero_mask]
                    r_r_rh = ((r_rl_rh + r_rr_rh) / 2.0)[r_aero_mask]
                    
                    r_total_f = (r_fl_l + r_fr_l)[r_aero_mask] - (r_s_fl + r_s_fr)
                    r_total_r = (r_rl_l + r_rr_l)[r_aero_mask] - (r_s_rl + r_s_rr)
                    
                    r_valid = (r_total_f + r_total_r) > 50
                    r_f_rh = r_f_rh[r_valid]
                    r_r_rh = r_r_rh[r_valid]
                    r_ab = (r_total_f[r_valid] / (r_total_f[r_valid] + r_total_r[r_valid])) * 100.0
                    r_ab = np.clip(r_ab, 0.0, 100.0)
                    
                    if len(r_f_rh) < 15:
                        print("  [!] Insufficient valid data in reference file.")
                        continue
                        
                    # Extract YAML Setup Deltas
                    def extract_setup(y):
                        setup = y.get('CarSetup', {})
                        flat = {}
                        def recurse(d, prefix=""):
                            if isinstance(d, dict):
                                for k, v in d.items():
                                    if k in ("UpdateCount", "LastTempsOMI", "LastTempsIMO", "TreadRemaining", "CornerWeight"):
                                        continue
                                    recurse(v, f"{prefix}{k}." if prefix else f"{k}.")
                            else:
                                flat[prefix[:-1]] = d
                        recurse(setup)
                        return flat
                        
                    y1 = yaml.safe_load(md.get('session_info_yaml', '')) or {}
                    y2 = yaml.safe_load(ref_metadata.get('session_info_yaml', '')) or {}
                    
                    s1 = extract_setup(y1)
                    s2 = extract_setup(y2)
                    
                    deltas = []
                    for k in set(s1.keys()).union(s2.keys()):
                        v1 = s1.get(k, 'N/A')
                        v2 = s2.get(k, 'N/A')
                        if v1 != v2:
                            fk = k.replace('Chassis.', '').replace('Tires.', '')
                            fk = fk.replace('LeftFront.', 'LF ').replace('RightFront.', 'RF ')
                            fk = fk.replace('LeftRear.', 'LR ').replace('RightRear.', 'RR ')
                            fk = fk.replace('Front.', 'F ').replace('Rear.', 'R ').replace('InCarDials.', '')
                            deltas.append(f"{fk} [{v1}->{v2}]")
                            
                    delta_title = "SETUP SHIFTS: " + ", ".join(deltas) if deltas else "SETUP SHIFTS: None Detected"
                    # Wrap title if too long
                    import textwrap
                    delta_title = "\n".join(textwrap.wrap(delta_title, 80))
                    
                    print("  [+] Launching L2 Comparison...")
                    import matplotx
                    import matplotlib.ticker as ticker
                    import matplotlib.tri as mtri
                    
                    plt.style.use(matplotx.styles.aura['dark'])
                    fig = plt.figure(figsize=(20, 9), num='OpenDAV - L2 Aero Comparison')
                    
                    def plot_2d_ax(ax, f_s, r_s, z_s, title, subtitle=""):
                        if len(f_s) > 2000:
                            idx = np.linspace(0, len(f_s)-1, 2000, dtype=int)
                            f_s, r_s, z_s = f_s[idx], r_s[idx], z_s[idx]
                        triang = mtri.Triangulation(f_s, r_s)
                        c_x = np.mean(f_s[triang.triangles], axis=1)
                        c_y = np.mean(r_s[triang.triangles], axis=1)
                        centers = np.column_stack((c_x, c_y))
                        tree = cKDTree(np.column_stack((f_s, r_s)))
                        distances, _ = tree.query(centers)
                        threshold = max(max(f_s) - min(f_s), max(r_s) - min(r_s)) * 0.04
                        triang.set_mask(distances > threshold)
                        
                        levels = np.linspace(0, 100, 20) if '%' == '%' else 20
                        cf = ax.tricontourf(triang, z_s, levels=levels, cmap=opendav_cmap, extend='both', alpha=0.9)
                        lines = ax.tricontour(triang, z_s, levels=10, cmap=opendav_cmap, linewidths=1.5, alpha=0.8)
                        ax.clabel(lines, inline=True, fontsize=9, fmt='%.1f%%', colors='white')
                        ax.scatter(f_s, r_s, c='white', s=3, alpha=0.4, edgecolors='black', linewidths=0.2, rasterized=True)
                        
                        # Enable Z-value coordinate display
                        lookup_tree = cKDTree(np.column_stack((f_s, r_s)))
                        def format_coord(x, y):
                            dist, idx = lookup_tree.query([x, y])
                            if dist > 5.0: return f'x={x:.1f}, y={y:.1f}'
                            return f'x={x:.1f}, y={y:.1f}, AB={z_s[idx]:.1f}%'
                        ax.format_coord = format_coord
                        
                        ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
                        ax.yaxis.set_major_locator(ticker.MultipleLocator(20))
                        ax.grid(True, which='both', linestyle='--', alpha=0.1, color='white')
                        
                        full_title = f"{title}\n{subtitle}" if subtitle else title
                        ax.set_title(full_title, fontsize=12, pad=15)
                        ax.set_xlabel("Front Ride Height (mm)", fontsize=11)
                        ax.set_ylabel("Rear Ride Height (mm)", fontsize=11)
                        
                        return cf
                        
                    p_lap_ch = channels.get('lap')
                    p_laps = len(np.unique(data[p_lap_ch].data[aero_mask][valid_df_mask])) if p_lap_ch and p_lap_ch in data else "Unknown"
                    p_pts = len(f_rh)
                    p_subtitle = f"Laps: {p_laps} | Graphed Data Points: {p_pts}\n{file_basename}"
                    
                    r_lap_ch = ref_channels.get('lap')
                    r_laps = len(np.unique(ref_data[r_lap_ch].data[r_aero_mask][r_valid])) if r_lap_ch and r_lap_ch in ref_data else "Unknown"
                    r_pts = len(r_f_rh)
                    r_subtitle = f"Laps: {r_laps} | Graphed Data Points: {r_pts}\n{delta_title}"

                    ax1 = fig.add_subplot(1, 2, 1)
                    cf1 = plot_2d_ax(ax1, f_rh, r_rh, aero_balance, "PRIMARY", p_subtitle)
                    
                    ax2 = fig.add_subplot(1, 2, 2)
                    cf2 = plot_2d_ax(ax2, r_f_rh, r_r_rh, r_ab, "REFERENCE", r_subtitle)
                    
                    cbar = plt.colorbar(cf2, ax=[ax1, ax2], location='bottom', aspect=40, pad=0.1)
                    cbar.set_label('Aero Balance (% Front)', fontsize=12)
                    
                    if ans == 'open l2':
                        gui_mode = get_gui_mode()
                        if gui_mode == 3:
                            show_ctk_graph(fig, "OpenDAV - L2 Aero Comparison")
                        else:
                            plt.show()
                    elif ans == 'print l2':
                        timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                        file_out = f"F2L2_{file_basename}_vs_{os.path.basename(ref_path)}.png"
                        if '<' in ans_raw:
                            project_name = ans_raw.split('<')[1].strip().replace('[', '').replace(']', '').strip()
                            from analysis.projects import save_to_project
                            subf = headless_config.get('run_folder') if headless else None
                            save_to_project(fig, project_name, file_out, subfolder=subf)
                            plt.close(fig)
                            if headless: break
                        else:
                            export_dir = f"exports/F2L2_{timestamp}"
                            os.makedirs(export_dir, exist_ok=True)
                            export_path = os.path.join(export_dir, file_out)
                            plt.savefig(export_path, dpi=300, bbox_inches='tight')
                            plt.close(fig)
                            print(f"  [+] Saved L2 Layout to {export_path}")
                        if headless: break


                elif ans in ['open l3', 'print l3']:
                    dist_ch = channels.get('dist')
                    if not dist_ch or dist_ch not in data:
                        print("  [!] Distance channel required for L3 Target Delta Analyzer. Aborting.")
                        continue
                    
                    dist_arr = data[dist_ch].data[aero_mask][valid_df_mask]
                    spd_arr = speed[aero_mask][valid_df_mask]
                    
                    # Sort data by distance for line charts
                    sort_idx = np.argsort(dist_arr)
                    d_s = dist_arr[sort_idx]
                    ab_s = aero_balance[sort_idx]
                    f_rh_s = f_rh[sort_idx]
                    r_rh_s = r_rh[sort_idx]
                    spd_s = spd_arr[sort_idx]
                    rake_s = r_rh_s - f_rh_s
                    
                    print(f"  [+] Target CoG (Center of Gravity) defaults to 45.0%.")
                    target_ab_input = "" if headless else input("      Enter Target Aero Balance % (or press Enter for 45.0): ").strip()
                    try:
                        target_ab = float(target_ab_input) if target_ab_input else 45.0
                    except ValueError:
                        target_ab = 45.0
                    
                    print("  [+] Building Target Delta Analyzer Graph (L3)...")
                    import matplotx
                    plt.style.use(matplotx.styles.aura['dark'])
                    plt.rcParams.update({
                        'font.family': ['Consolas', 'DejaVu Sans Mono', 'monospace'],
                        'figure.dpi': 144,
                        'axes.linewidth': 1.2,
                        'grid.alpha': 0.15,
                        'xtick.direction': 'in',
                        'ytick.direction': 'in',
                        'scatter.edgecolors': 'none'
                    })
                    
                    fig = plt.figure(figsize=(18, 10), num='OpenDAV - Aero Delta Analyzer (L3)')
                    gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 1], hspace=0.35, wspace=0.25)
                    
                    # Top Pane: Delta Line Chart
                    ax_delta = fig.add_subplot(gs[0, :])
                    
                    # Smooth AB for plotting readability (15-sample window)
                    window = 15
                    sm_ab = np.convolve(ab_s, np.ones(window)/window, mode='same')
                    
                    ax_delta.plot(d_s, sm_ab, color='white', linewidth=1.5, alpha=0.9, label='Dynamic Aero Balance')
                    ax_delta.axhline(target_ab, color='#FFD700', linestyle='--', linewidth=2, label=f'Target (CoG) = {target_ab}%')
                    
                    # Shading Logic (Milliken Line of Death)
                    ax_delta.fill_between(d_s, sm_ab, target_ab, where=(sm_ab > target_ab), interpolate=True, color='#FF1493', alpha=0.4, label='Danger: Forward Migration (Oversteer)')
                    ax_delta.fill_between(d_s, sm_ab, target_ab, where=(sm_ab <= target_ab), interpolate=True, color='#2D8AE2', alpha=0.4, label='Safe: Rearward Migration (Understeer)')
                    
                    ax_delta.set_title(f"Aerodynamic Migration & Stability Trace\nTarget: {target_ab}%", fontsize=14, pad=15)
                    ax_delta.set_xlabel("Track Distance (m)", fontsize=11)
                    ax_delta.set_ylabel("Aero Balance (%)", fontsize=11)
                    ax_delta.legend(loc='upper right')
                    ax_delta.grid(True, linestyle='--', alpha=0.2)
                    
                    # Bottom Left: Platform Envelope Scatter
                    ax_plat = fig.add_subplot(gs[1, 0])
                    sc = ax_plat.scatter(f_rh_s, r_rh_s, c=spd_s, cmap='plasma', s=4, alpha=0.6, rasterized=True)
                    plt.colorbar(sc, ax=ax_plat, label='Speed')
                    
                    # Draw a bounding box for the target window (approximated by the 25th-75th percentile of AB near target)
                    target_mask = (ab_s >= target_ab - 1.0) & (ab_s <= target_ab + 1.0)
                    if np.any(target_mask):
                        f_min, f_max = np.percentile(f_rh_s[target_mask], 10), np.percentile(f_rh_s[target_mask], 90)
                        r_min, r_max = np.percentile(r_rh_s[target_mask], 10), np.percentile(r_rh_s[target_mask], 90)
                        import matplotlib.patches as patches
                        rect = patches.Rectangle((f_min, r_min), f_max - f_min, r_max - r_min, linewidth=2, edgecolor='#FFD700', facecolor='none', linestyle='--', label='Target Envelope')
                        ax_plat.add_patch(rect)
                        ax_plat.legend(loc='upper right')
                        
                    ax_plat.set_title("Mechanical Platform Attainment", fontsize=12, pad=10)
                    ax_plat.set_xlabel("Front Ride Height (mm)", fontsize=10)
                    ax_plat.set_ylabel("Rear Ride Height (mm)", fontsize=10)
                    ax_plat.grid(True, linestyle='--', alpha=0.2)
                    
                    # Bottom Right: Pitch Kinematics
                    ax_pitch = fig.add_subplot(gs[1, 1])
                    sm_rake = np.convolve(rake_s, np.ones(window)/window, mode='same')
                    ax_pitch.plot(d_s, sm_rake, color='#FF69B4', linewidth=1.5, alpha=0.8, label='Pitch / Rake (mm)')
                    ax_pitch.set_title("Pitch Kinematics (Braking Dive)", fontsize=12, pad=10)
                    ax_pitch.set_xlabel("Track Distance (m)", fontsize=10)
                    ax_pitch.set_ylabel("Rake (RRH - FRH) mm", fontsize=10, color='#FF69B4')
                    ax_pitch.tick_params(axis='y', labelcolor='#FF69B4')
                    
                    ax2 = ax_pitch.twinx()
                    ax2.plot(d_s, spd_s, color='#2D8AE2', linewidth=1.0, alpha=0.5, label='Speed')
                    ax2.set_ylabel("Speed", fontsize=10, color='#2D8AE2')
                    ax2.tick_params(axis='y', labelcolor='#2D8AE2')
                    
                    # Combine legends
                    lines_1, labels_1 = ax_pitch.get_legend_handles_labels()
                    lines_2, labels_2 = ax2.get_legend_handles_labels()
                    ax_pitch.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper right')
                    
                    info_text = (f"File: {file_basename}\nCar: {car_name}\nAvg AB: {median_ab:.1f}%")
                    plt.figtext(0.02, 0.02, info_text, fontsize=9, color='white', alpha=0.8, va='bottom', ha='left',
                                bbox=dict(facecolor='#1a1a1a', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.5'))

                    if ans == 'open l3':
                        gui_mode = get_gui_mode()
                        if gui_mode == 3: show_ctk_graph(fig, "OpenDAV - Aero Delta Analyzer (L3)")
                        else: plt.show()
                    else:
                        timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                        file_out = f"F2L3_{timestamp}_{file_basename}.png"
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

                else:
                    print("  [!] Invalid command. Try 'open L1/L2/L3', 'print L1/L2/L3', or 'p'.")

        if headless: return
        print("\n" + "─"*100)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break
