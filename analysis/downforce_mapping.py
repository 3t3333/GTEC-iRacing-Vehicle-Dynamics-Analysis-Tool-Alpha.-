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

def run_downforce_mapping(sessions, headless=False, headless_config=None):
    while True:
        splash.print_header("Downforce Mapping Module")
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            channels = session['channels']
            print(f"\nAnalyzing: {os.path.basename(file_path)}")
            print_session_metadata(data, channels, session.get('metadata', {}))
            
            # Find required channels
            speed_ch = None
            for ch in ['virt_body_v', 'Speed', 'Ground Speed', 'Velocity']:
                if ch in data: speed_ch = ch; break
                
            air_dens_ch = None
            for ch in ['air_density', 'AirDensity', 'Air Density']:
                if ch in data: air_dens_ch = ch; break

            fl_ch, fr_ch = 'Ride Height FL', 'Ride Height FR'
            rl_ch, rr_ch = 'Ride Height RL', 'Ride Height RR'
            
            fl_load, fr_load = 'Suspension Load FL', 'Suspension Load FR'
            rl_load, rr_load = 'Suspension Load RL', 'Suspension Load RR'

            lat_g_ch = channels.get('lat')
            long_g_ch = channels.get('long')

            required = [speed_ch, fl_ch, fr_ch, rl_ch, rr_ch, fl_load, fr_load, rl_load, rr_load, lat_g_ch, long_g_ch]
            missing = [ch for ch in required if ch is None or ch not in data]
            if missing:
                print(f"  [!] Missing required channels for Downforce Mapping: {missing}")
                print("      Note: This tool requires Suspension Load channels.")
                print("\nPress Enter to return...")
                input()
                continue

            # Load Data
            speed_raw = data[speed_ch].data
            # Convert to km/h if it's in m/s (iRacing virt_body_v is usually m/s)
            if np.max(speed_raw) > 150:
                speed_kmh = speed_raw 
            else:
                speed_kmh = speed_raw * 3.6 

            fl_rh = data[fl_ch].data * 1000
            fr_rh = data[fr_ch].data * 1000
            rl_rh = data[rl_ch].data * 1000
            rr_rh = data[rr_ch].data * 1000

            fl_l = data[fl_load].data
            fr_l = data[fr_load].data
            rl_l = data[rl_load].data
            rr_l = data[rr_load].data
            
            lat_g = data[lat_g_ch].data
            long_g = data[long_g_ch].data

            # 1. Establish Static Loads
            static_mask = (speed_kmh < 15) & (np.abs(lat_g) < 0.1) & (np.abs(long_g) < 0.1)
            if np.any(static_mask):
                static_fl = np.median(fl_l[static_mask])
                static_fr = np.median(fr_l[static_mask])
                static_rl = np.median(rl_l[static_mask])
                static_rr = np.median(rr_l[static_mask])
            else:
                static_fl = np.median(fl_l) * 0.4
                static_fr = static_fl
                static_rl = np.median(rl_l) * 0.6
                static_rr = static_rl

            static_weight = static_fl + static_fr + static_rl + static_rr

            # 2. Filter for v > 100 km/h
            aero_mask = (speed_kmh > 100.0)
            
            f_rh = ((fl_rh + fr_rh) / 2.0)[aero_mask]
            r_rh = ((rl_rh + rr_rh) / 2.0)[aero_mask]
            
            total_front_load = (fl_l + fr_l)[aero_mask]
            total_rear_load = (rl_l + rr_l)[aero_mask]
            v_filtered = speed_kmh[aero_mask] / 3.6 # Back to m/s for CL calculation
            
            total_load = total_front_load + total_rear_load
            total_downforce = total_load - static_weight

            # Filter out extreme anomalies just in case
            valid_df_mask = total_downforce > 0
            f_rh = f_rh[valid_df_mask]
            r_rh = r_rh[valid_df_mask]
            total_downforce = total_downforce[valid_df_mask]
            v_filtered = v_filtered[valid_df_mask]
            
            if len(f_rh) == 0:
                print("  [!] Downforce values were negative or insufficient data > 100 km/h.")
                continue

            cl_text = ""
            if air_dens_ch:
                rho = data[air_dens_ch].data[aero_mask][valid_df_mask]
                A = 2.0 # Fixed Frontal Area Approximation
                safe_v = np.where(v_filtered == 0, 0.001, v_filtered)
                # CL = 2 * L / (rho * v^2 * A)  (downforce is L)
                cl_vals = (2 * total_downforce) / (rho * (safe_v**2) * A)
                avg_cl = np.median(cl_vals)
                cl_line = f"Avg Est. CL (A=2.0m²): {avg_cl:.3f}"
                cl_text = f" │ {cl_line.ljust(92)} │"

            # CLI Output
            raw_max_df = np.max(total_downforce)
            avg_df = np.median(total_downforce)
            min_df = np.min(total_downforce)
            
            # Stage 1: Calculate "Real" Peak Downforce (RBF Kernel Density -> 98th Percentile)
            try:
                from scipy.stats import gaussian_kde
                # Apply an RBF kernel to every downforce data point to create a concentrated, rounded distribution
                kde = gaussian_kde(total_downforce)
                df_space = np.linspace(min_df, raw_max_df, 2000)
                density = kde.evaluate(df_space)
                
                # Calculate the CDF to find the top 98% of this new smoothed dataset (eliminating outlier spikes)
                cdf = np.cumsum(density)
                cdf = cdf / cdf[-1]
                max_df = df_space[np.searchsorted(cdf, 0.98)]
            except Exception:
                max_df = np.percentile(total_downforce, 98)
            
            # Golden Box Calculation (75% to 90% of the Real Peak)
            gb_top = max_df * 0.90
            gb_bottom = max_df * 0.75
            
            # Stage 2: Target Golden Pose (Highest Density Mode using RBF/KDE)
            mask_gb = (total_downforce >= gb_bottom) & (total_downforce <= gb_top)
            f_gb = f_rh[mask_gb]
            r_gb = r_rh[mask_gb]
            
            target_frh, target_rrh = None, None
            target_pose_text = "Target Golden Pose: N/A"
            if len(f_gb) > 20:
                try:
                    from scipy.stats import gaussian_kde
                    values = np.vstack([f_gb, r_gb])
                    kernel = gaussian_kde(values)
                    densities = kernel.evaluate(values)
                    max_idx = np.argmax(densities)
                    target_frh = f_gb[max_idx]
                    target_rrh = r_gb[max_idx]
                    target_pose_text = f"Target Golden Pose: FRH {target_frh:.1f}mm | RRH {target_rrh:.1f}mm"
                except Exception:
                    pass

            PINK = '\033[95m'
            CYAN = '\033[96m'
            GOLD = '\033[38;2;255;215;0m' # Professional Gold RGB
            RESET = "\033[0m"
            
            print("\n  ┌" + "─" * 98 + "┐")
            print("  │ " + "[ TOTAL DOWNFORCE (v > 100 km/h) ]".ljust(92) + " │")
            print("  │ " + f"Max Downforce: {PINK}{max_df:.1f} N{RESET}".ljust(47 + len(PINK) + len(RESET)) + " │")
            print("  │ " + f"Golden Box:    {GOLD}{gb_bottom:.1f} to {gb_top:.1f} N{RESET}".ljust(47 + len(GOLD) + len(RESET)) + " │")
            print("  │ " + f"{GOLD}{target_pose_text}{RESET}".ljust(47 + len(GOLD) + len(RESET)) + " │")
            print("  │ " + f"Avg Downforce: {CYAN}{avg_df:.1f} N{RESET}".ljust(47 + len(CYAN) + len(RESET)) + " │")
            print("  │ " + f"Min Downforce: {min_df:.1f} N".ljust(92) + " │")
            if cl_text:
                print(cl_text)
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
 │ [Z] AXIS: TOTAL LOAD (N)                │   │ [C] MAP:  LOAD DENSITY                  │      
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
 │ [C] MAP:  TOTAL DOWNFORCE (N)           │   │ [C] MAP:  TOTAL DOWNFORCE (N)           │      
 └─────────────────────────────────────────┘   └─────────────────────────────────────────┘      
 
  >> [USE CASE]: DIRECTLY COMPARE AERODYNAMIC TOPOGRAPHY SHIFTS BETWEEN TWO SETUP ITERATIONS."""
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
                    ans_raw = input(f"\n  Select action ('open L1', 'print L1', 'open L2', 'print L2', 'p' to go back < proj): ").strip().lower()
                ans = ans_raw.split('<')[0].strip().lower()
                
                if ans == 'p':
                    break
                    
                if ans == 'open l1':
                    print("  [+] Building interactive simulation dashboard... (Close the window to continue)")
                    import matplotx
                    import matplotlib.tri as mtri
                    from mpl_toolkits.mplot3d import Axes3D

                    plt.style.use(matplotx.styles.aura['dark'])
                    fig = plt.figure(figsize=(16, 8), num='OpenDAV - 3D Downforce Simulation')
                    
                    if len(f_rh) > 3000:
                        idx = np.linspace(0, len(f_rh)-1, 3000, dtype=int)
                        f_sim, r_sim, z_sim = f_rh[idx], r_rh[idx], total_downforce[idx]
                    else:
                        f_sim, r_sim, z_sim = f_rh, r_rh, total_downforce

                    ax3d = fig.add_subplot(1, 2, 1, projection='3d')
                    triang = mtri.Triangulation(f_sim, r_sim)
                    c_x = np.mean(f_sim[triang.triangles], axis=1)
                    c_y = np.mean(r_sim[triang.triangles], axis=1)
                    centers = np.column_stack((c_x, c_y))
                    tree = cKDTree(np.column_stack((f_sim, r_sim)))
                    distances, _ = tree.query(centers)
                    threshold = max(max(f_sim) - min(f_sim), max(r_sim) - min(r_sim)) * 0.05
                    triang.set_mask(distances > threshold)

                    ax3d.scatter(f_sim, r_sim, z_sim, c=z_sim, cmap=opendav_cmap, s=5, alpha=0.8, edgecolors='none')
                    ax3d.set_title("3D Total Downforce Platform", fontsize=14, pad=20)
                    ax3d.set_xlabel("Front RH (mm)")
                    ax3d.set_ylabel("Rear RH (mm)")
                    ax3d.set_zlabel("Downforce (N)")
                    ax3d.view_init(elev=30, azim=225, vertical_axis='z')

                    ax2d = fig.add_subplot(1, 2, 2)
                    cf = ax2d.tricontourf(triang, z_sim, levels=20, cmap=opendav_cmap, extend='both', alpha=0.9)
                    lines = ax2d.tricontour(triang, z_sim, levels=10, colors='white', linewidths=0.5, alpha=0.3)
                    ax2d.clabel(lines, inline=True, fontsize=8, fmt='%d N')
                    ax2d.scatter(f_sim, r_sim, c='white', s=2, alpha=0.2)
                    ax2d.set_title("2D Load Topography", fontsize=14, pad=20)
                    ax2d.set_xlabel("Front Ride Height (mm)")
                    ax2d.set_ylabel("Rear Ride Height (mm)")
                    from scipy.spatial import cKDTree
                    lookup_tree_sim = cKDTree(np.column_stack((f_sim, r_sim)))
                    def format_coord_sim(x, y):
                        dist, idx = lookup_tree_sim.query([x, y])
                        if dist > 5.0: return f'x={x:.1f}, y={y:.1f}'
                        return f'x={x:.1f}, y={y:.1f}, Load={z_sim[idx]:.1f} N'
                    ax2d.format_coord = format_coord_sim
                    plt.colorbar(cf, ax=ax2d, label='Total Downforce (N)')
                    plt.tight_layout()

                    gui_mode = get_gui_mode()
                    if gui_mode == 3:
                        show_ctk_graph(fig, "OpenDAV - 3D Downforce Simulation")
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
                            levels = np.linspace(0, 100, 20) if ' N' == '%' else 20
                            contourf = plt.tricontourf(triang, z_s, levels=levels, cmap=opendav_cmap, extend='both', alpha=0.9)
                            lines = plt.tricontour(triang, z_s, levels=10, cmap=opendav_cmap, linewidths=1.5, alpha=0.8)
                            plt.clabel(lines, inline=True, fontsize=9, fmt='%.1f N', colors='white')
                            plt.colorbar(contourf, label='Load ( N)' if ' N' == '%' else 'Load')
                            plt.scatter(f_s, r_s, c='white', s=3, alpha=0.4, edgecolors='black', linewidths=0.2)
                            ax = plt.gca()
                            
                            # Enable Z-value coordinate display
                            lookup_tree = cKDTree(np.column_stack((f_s, r_s)))
                            def format_coord(x, y):
                                dist, idx = lookup_tree.query([x, y])
                                if dist > 5.0: return f'x={x:.1f}, y={y:.1f}'
                                return f'x={x:.1f}, y={y:.1f}, Load={z_s[idx]:.1f} N'
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
                        export_dir = f"exports/L1_{timestamp}"
                        os.makedirs(export_dir, exist_ok=True)
                        main_filename = os.path.join(export_dir, f"DownforceMap_{file_basename}.png")
                        generate_2d_plot(f_rh, r_rh, total_downforce, f"2D Total Downforce Heatmap\n{file_basename}", main_filename)
                        
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
                                            generate_2d_plot(f_rh[s_mask], r_rh[s_mask], total_downforce[s_mask], f"Total DF - Sector {i+1}\n{file_basename}", os.path.join(export_dir, f"S{i+1}.png"))
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
                                            generate_2d_plot(f_rh[c_mask], r_rh[c_mask], total_downforce[c_mask], f"Total DF - Corner {i+1}\n{file_basename}", os.path.join(export_dir, f"algocorr{i+1}.png"))
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
                    for ch in ['virt_body_v', 'Speed', 'Ground Speed', 'Velocity']:
                        if ch in ref_data: r_speed_ch = ch; break
                        
                    r_req = [r_speed_ch, 'Ride Height FL', 'Ride Height FR', 'Ride Height RL', 'Ride Height RR',
                             'Suspension Load FL', 'Suspension Load FR', 'Suspension Load RL', 'Suspension Load RR']
                    if any(ch not in ref_data for ch in r_req if ch is not None):
                        print("  [!] Reference file missing required channels.")
                        continue
                        
                    r_speed_raw = ref_data[r_speed_ch].data
                    if np.max(r_speed_raw) > 150:
                        r_speed = r_speed_raw 
                    else:
                        r_speed = r_speed_raw * 3.6 
                    
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
                    
                    r_static_mask = (r_speed < 15) & (np.abs(r_lat_g) < 0.1) & (np.abs(r_long_g) < 0.1)
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
                        
                    r_static_weight = r_s_fl + r_s_fr + r_s_rl + r_s_rr
                        
                    r_aero_mask = (r_speed > 100.0)
                    r_f_rh = ((r_fl_rh + r_fr_rh) / 2.0)[r_aero_mask]
                    r_r_rh = ((r_rl_rh + r_rr_rh) / 2.0)[r_aero_mask]
                    
                    r_total_f = (r_fl_l + r_fr_l)[r_aero_mask]
                    r_total_r = (r_rl_l + r_rr_l)[r_aero_mask]
                    
                    r_total_load = r_total_f + r_total_r
                    r_total_df = r_total_load - r_static_weight
                    
                    r_valid = r_total_df > 0
                    r_f_rh = r_f_rh[r_valid]
                    r_r_rh = r_r_rh[r_valid]
                    r_total_df = r_total_df[r_valid]
                    
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
                    fig = plt.figure(figsize=(20, 9), num='OpenDAV - L2 Downforce Comparison')
                    
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
                        
                        levels = np.linspace(0, 100, 20) if ' N' == '%' else 20
                        cf = ax.tricontourf(triang, z_s, levels=levels, cmap=opendav_cmap, extend='both', alpha=0.9)
                        lines = ax.tricontour(triang, z_s, levels=10, cmap=opendav_cmap, linewidths=1.5, alpha=0.8)
                        ax.clabel(lines, inline=True, fontsize=9, fmt='%.1f N', colors='white')
                        ax.scatter(f_s, r_s, c='white', s=3, alpha=0.4, edgecolors='black', linewidths=0.2)
                        
                        # Enable Z-value coordinate display
                        lookup_tree = cKDTree(np.column_stack((f_s, r_s)))
                        def format_coord(x, y):
                            dist, idx = lookup_tree.query([x, y])
                            if dist > 5.0: return f'x={x:.1f}, y={y:.1f}'
                            return f'x={x:.1f}, y={y:.1f}, Load={z_s[idx]:.1f} N'
                        ax.format_coord = format_coord
                        
                        ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
                        ax.yaxis.set_major_locator(ticker.MultipleLocator(20))
                        ax.grid(True, which='both', linestyle='--', alpha=0.1, color='white')
                        
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
                    cf1 = plot_2d_ax(ax1, f_rh, r_rh, total_downforce, "PRIMARY", p_subtitle)
                    
                    ax2 = fig.add_subplot(1, 2, 2)
                    cf2 = plot_2d_ax(ax2, r_f_rh, r_r_rh, r_total_df, "REFERENCE", r_subtitle)
                    
                    cbar = plt.colorbar(cf2, ax=[ax1, ax2], location='bottom', aspect=40, pad=0.1)
                    cbar.set_label('Total Downforce (N)', fontsize=12)
                    
                    if ans == 'open l2':
                        gui_mode = get_gui_mode()
                        if gui_mode == 3:
                            show_ctk_graph(fig, "OpenDAV - L2 Downforce Comparison")
                        else:
                            plt.show()
                    elif ans == 'print l2':
                        timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                        file_out = f"L2_Downforce_{file_basename}_vs_{os.path.basename(ref_path)}.png"
                        if '<' in ans_raw:
                            project_name = ans_raw.split('<')[1].strip().replace('[', '').replace(']', '').strip()
                            from analysis.projects import save_to_project
                            subf = headless_config.get('run_folder') if headless else None
                            save_to_project(fig, project_name, file_out, subfolder=subf)
                            plt.close(fig)
                            if headless: break
                        else:
                            export_dir = f"exports/L2_{timestamp}"
                            os.makedirs(export_dir, exist_ok=True)
                            export_path = os.path.join(export_dir, file_out)
                            plt.savefig(export_path, dpi=300, bbox_inches='tight')
                            plt.close(fig)
                            print(f"  [+] Saved L2 Layout to {export_path}")
                        if headless: break

                else:
                    print("  [!] Invalid command. Try 'open L1/L2', 'print L1/L2', or 'p'.")

        if headless: return
        print("\n" + "─"*100)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break
