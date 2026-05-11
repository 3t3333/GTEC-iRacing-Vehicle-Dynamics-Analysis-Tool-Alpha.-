import os
import sys
import datetime
import numpy as np
import yaml
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib.tri as mtri
import matplotx
from scipy.spatial import cKDTree
from scipy.signal import savgol_filter
from core.config import get_gui_mode
from ui.graphing import show_ctk_graph
from ui.metadata_printer import print_session_metadata
import ui.splash as splash

from matplotlib.colors import LinearSegmentedColormap
opendav_colors = ["#2D8AE2", "#FF1493", "#D2751D"]
opendav_cmap = LinearSegmentedColormap.from_list("opendav_aero", opendav_colors, N=256)

def run_compression_rates(sessions, headless=False, headless_config=None):
    while True:
        splash.print_header("Compression Rates Analyzer")
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            channels = session['channels']
            md = session.get('metadata', {})
            file_basename = os.path.basename(file_path).replace('.ibt', '')
            
            print(f"\nAnalyzing: {file_basename}")
            
            # Find required channels
            speed_ch = next((ch for ch in ['Speed', 'virt_body_v', 'Ground Speed'] if ch in data), None)
            fl_ch, fr_ch = 'Ride Height FL', 'Ride Height FR'
            rl_ch, rr_ch = 'Ride Height RL', 'Ride Height RR'
            fl_load, fr_load = 'Suspension Load FL', 'Suspension Load FR'
            rl_load, rr_load = 'Suspension Load RL', 'Suspension Load RR'
            dist_ch = channels.get('dist')

            required = [speed_ch, fl_ch, fr_ch, rl_ch, rr_ch, fl_load, fr_load, rl_load, rr_load, dist_ch]
            if not all(ch in data for ch in required if ch):
                print(f"  [!] Missing required channels.")
                input("\nPress Enter to return...")
                continue

            # Load Data
            speed_raw = data[speed_ch].data
            speed_kmh = speed_raw if np.max(speed_raw) > 150 else speed_raw * 3.6
            
            fl_rh = data[fl_ch].data * 1000
            fr_rh = data[fr_ch].data * 1000
            rl_rh = data[rl_ch].data * 1000
            rr_rh = data[rr_ch].data * 1000
            
            fl_l = data[fl_load].data
            fr_l = data[fr_load].data
            rl_l = data[rl_load].data
            rr_l = data[rr_load].data
            
            dist_raw = data[dist_ch].data
            
            # 1. Establish Static Loads
            lat_g_ch = channels.get('lat')
            long_g_ch = channels.get('long')
            
            lat_g = data[lat_g_ch].data if lat_g_ch and lat_g_ch in data else np.zeros_like(speed_kmh)
            long_g = data[long_g_ch].data if long_g_ch and long_g_ch in data else np.zeros_like(speed_kmh)
            
            vert_g = data['VertAccel'].data / 9.80665 if 'VertAccel' in data else np.ones_like(lat_g)
            
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
            calc_mass = static_weight / 9.80665
            
            # MASS CALIBRATION SCALAR
            overrides = getattr(data, 'overrides', {})
            phys_model = overrides.get('physics_model', {}) if overrides else {}
            actual_mass = phys_model.get('actual_mass_kg', 1350.0) 
            scale_factor = 1.0
            
            if calc_mass > 1800 or calc_mass < 800:
                scale_factor = actual_mass / calc_mass
                fl_l *= scale_factor
                fr_l *= scale_factor
                rl_l *= scale_factor
                rr_l *= scale_factor
                static_weight *= scale_factor
                
            total_load = fl_l + fr_l + rl_l + rr_l
            total_downforce = total_load - (static_weight * vert_g)
            
            # Apply Distance Bounds (Sector Isolation)
            if 'distance_bounds' not in session or not session['distance_bounds']:
                print("  [!] This tool requires a sector to be isolated.")
                continue
                
            b_min, b_max = session['distance_bounds']
            lap_mask = np.ones_like(dist_raw, dtype=bool)
            if 'selected_laps' in md and md['selected_laps'] and 'lap' in channels and channels['lap'] in data:
                lap_mask = np.isin(data[channels['lap']].data, md['selected_laps'])
                
            sector_mask = (dist_raw >= b_min) & (dist_raw <= b_max) & lap_mask
            
            if not np.any(sector_mask):
                print("  [!] No data found in the selected sector.")
                continue
                
            s_speed = speed_kmh[sector_mask]
            s_dist = dist_raw[sector_mask]
            s_df = total_downforce[sector_mask]
            
            s_fl_rh = fl_rh[sector_mask]
            s_fr_rh = fr_rh[sector_mask]
            s_rl_rh = rl_rh[sector_mask]
            s_rr_rh = rr_rh[sector_mask]
            
            s_f_rh = (s_fl_rh + s_fr_rh) / 2.0
            s_r_rh = (s_rl_rh + s_rr_rh) / 2.0
            
            # 1. Center Ride Height
            crh_raw = (s_fl_rh + s_fr_rh + s_rl_rh + s_rr_rh) / 4.0
            
            # 2. Savitzky-Golay Smoothing
            window = min(31, len(crh_raw) // 2 * 2 + 1)
            if window > 3:
                crh_smooth = savgol_filter(crh_raw, window_length=window, polyorder=3)
            else:
                crh_smooth = crh_raw

            # 3. Linear Regression (Speed vs CRH)
            valid_idx = np.isfinite(s_speed) & np.isfinite(crh_smooth)
            if np.sum(valid_idx) < 10:
                print("  [!] Not enough stable data for regression.")
                continue
                
            m, b = np.polyfit(s_speed[valid_idx], crh_smooth[valid_idx], 1)
            
            print(f"  [+] Sector Analyzed.")
            print(f"      Compression Rate: {m:.4f} mm / (km/h)")
            
            f12_preview = """
    >> [USE CASE]: ANALYZE STRAIGHT-LINE AERODYNAMIC EFFICIENCY AND SUSPENSION COMPRESSION.

        L1: STATIC COMPRESSION RATES                  L2: ANIMATED COMPRESSION RATES
 ┌─────────────────────────────────────────┐   ┌─────────────────────────────────────────┐
 │                                         │   │                                         │
 │                                         │   │                                         │
 │                                         │   │                                         │
 │ [X/Y] MAP:  FRONT RH / REAR RH          │   │ [X/Y] MAP:  FRONT RH / REAR RH          │
 │ [C] CONTR:  SECTOR DOWNFORCE CONTOUR    │   │ [C] CONTR:  ROLLING DOWNFORCE CONTOUR   │
 │ [L] TREND:  SPEED VS CENTER RH SLOPE    │   │ [L] TREND:  DYNAMIC REGRESSION PLAYHEAD │
 │ [E] ENVEL:  DOWNFORCE/SPEED VS DISTANCE │   │ [E] ENVEL:  SYNCHRONIZED DISTANCE TRACE │
 └─────────────────────────────────────────┘   └─────────────────────────────────────────┘

        L3/L4: 2-SETUP TRADE-OFF COMPARISON           L5/L6: 3-SETUP TRADE-OFF COMPARISON
 ┌─────────────────────────────────────────┐   ┌─────────────────────────────────────────┐
 │ L3: STATIC MAPS      L4: ANIMATED MAPS  │   │ L5: STATIC MAPS      L6: ANIMATED MAPS  │
 │                                         │   │                                         │
 │                                         │   │                                         │
 │ [2x MAPS] BASELINE VS 1 ALT SETUP       │   │ [3x MAPS] BASELINE VS 2 ALT SETUPS      │
 │ [2x LINES] REGRESSION TREND COMPARISONS │   │ [3x LINES] REGRESSION TREND COMPARISONS │
 │ [TITLE] AUTOMATIC SETUP DELTA DIFFING   │   │ [TITLE] AUTOMATIC SETUP DELTA DIFFING   │
 │                                         │   │                                         │
 └─────────────────────────────────────────┘   └─────────────────────────────────────────┘"""
            print(f12_preview)
            
            ans_raw = input(f"\n  Select action ('open L1..L6', 'print L1..L6', 'p' to go back < proj): ").strip().lower()
            ans = ans_raw.split('<')[0].strip().lower()
            
            if ans == 'p':
                break
                
            if ans in ['open l2', 'print l2']:
                try:
                    # 1. DISTANCE RESAMPLING
                    d_min, d_max = s_dist[0], s_dist[-1]
                    d_grid = np.arange(d_min, d_max, 2.0)
                    
                    f_rh_res = np.interp(d_grid, s_dist, s_f_rh)
                    r_rh_res = np.interp(d_grid, s_dist, s_r_rh)
                    crh_res = np.interp(d_grid, s_dist, crh_smooth)
                    spd_res = np.interp(d_grid, s_dist, s_speed)
                    df_res = np.interp(d_grid, s_dist, s_df)
                    
                    print(f"  [+] Resampled {len(s_dist)} points to {len(d_grid)} spatial frames.")
                    print("  [+] Building Animated Compression Analysis (L2)...")
                    
                    import matplotlib.animation as animation
                    plt.style.use(matplotx.styles.aura['dark'])
                    fig = plt.figure(figsize=(16, 10), num='OpenDAV - Animated Compression Rates')
                    gs = GridSpec(2, 2, height_ratios=[1, 1], figure=fig)
                    
                    ax_map = fig.add_subplot(gs[0, 0])
                    ax_reg = fig.add_subplot(gs[0, 1])
                    ax_dist = fig.add_subplot(gs[1, :])
                    
                    ax_reg.scatter(s_speed, crh_smooth, c='white', s=5, alpha=0.1, edgecolors='none')
                    x_line = np.array([np.min(s_speed), np.max(s_speed)])
                    y_line = m * x_line + b
                    ax_reg.plot(x_line, y_line, c='#0ea5e9', lw=2.0, alpha=0.5, label=f"Trend: {m:.4f} mm/kmh")
                    reg_dot, = ax_reg.plot([], [], 'o', color='white', markersize=10, zorder=10)
                    ax_reg.set_title("Compression Rate Trend", fontsize=11)
                    ax_reg.set_xlabel("Speed (km/h)"); ax_reg.set_ylabel("Center RH (mm)")
                    
                    d_plot = d_grid - d_grid[0]
                    ax_dist.plot(d_plot, df_res, c='#A020F0', lw=1.5, alpha=0.4, label="Downforce")
                    ax_dist.set_ylabel("Downforce (N)", color='#A020F0')
                    ax_dist.set_xlabel("Sector Distance (m)")
                    
                    ax_spd = ax_dist.twinx()
                    ax_spd.plot(d_plot, spd_res, c='#32CD32', lw=1.5, alpha=0.4, label="Speed")
                    ax_spd.set_ylabel("Speed (km/h)", color='#32CD32')
                    
                    playhead = ax_dist.axvline(0, color='white', lw=2, zorder=10)
                    df_dot, = ax_dist.plot([], [], 'o', color='white', markersize=8, zorder=11)
                    
                    f_min_lim, f_max_lim = np.min(f_rh_res)-2, np.max(f_rh_res)+2
                    r_min_lim, r_max_lim = np.min(r_rh_res)-2, np.max(r_rh_res)+2
                    
                    fig.suptitle(f"OpenDAV F11L2: {file_basename}", fontsize=15, color='white', y=0.97)
                    plt.tight_layout()
                    fig.subplots_adjust(top=0.9)
                    
                    window_size = 75 
                    
                    def update(frame):
                        start_idx = max(0, frame - window_size)
                        end_idx = frame + 1
                        ax_map.clear()
                        ax_map.set_xlim(f_max_lim, f_min_lim)
                        ax_map.set_ylim(r_max_lim, r_min_lim)
                        ax_map.set_title(f"Dynamic Aero Map (Window: {window_size*2}m)", fontsize=11)
                        ax_map.set_xlabel("Front RH (mm)"); ax_map.set_ylabel("Rear RH (mm)")
                        
                        w_f = f_rh_res[start_idx:end_idx]
                        w_r = r_rh_res[start_idx:end_idx]
                        w_z = df_res[start_idx:end_idx]
                        
                        if len(w_f) > 5:
                            try:
                                triang = mtri.Triangulation(w_f, w_r)
                                c_xy = np.column_stack((np.mean(w_f[triang.triangles], axis=1), np.mean(w_r[triang.triangles], axis=1)))
                                tree = cKDTree(np.column_stack((w_f, w_r)))
                                dist, _ = tree.query(c_xy)
                                triang.set_mask(dist > (np.max(w_f)-np.min(w_f)) * 0.15)
                                ax_map.tricontourf(triang, w_z, levels=10, cmap=opendav_cmap, extend='both', alpha=0.9)
                                ax_map.scatter(w_f, w_r, c='white', s=2, alpha=0.3)
                            except: pass
                        
                        ax_map.scatter(f_rh_res[frame], r_rh_res[frame], c='red', s=60, edgecolors='white', zorder=10)
                        reg_dot.set_data([spd_res[frame]], [crh_res[frame]])
                        playhead.set_xdata([d_plot[frame], d_plot[frame]])
                        df_dot.set_data([d_plot[frame]], [df_res[frame]])
                        return ax_map, reg_dot, playhead, df_dot

                    ani = animation.FuncAnimation(fig, update, frames=len(d_grid), blit=False)
                    
                    if ans == 'open l2':
                        if get_gui_mode() == 3: show_ctk_graph(fig, "OpenDAV - Animated Compression")
                        else: plt.show()
                    elif ans == 'print l2':
                        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                        print(f"      Rendering MP4 ({len(d_grid)} frames @ 30fps)...")
                        if '<' in ans_raw:
                            project_name = ans_raw.split('<')[1].strip().replace('[', '').replace(']', '').strip()
                            from analysis.projects import save_to_project
                            subf = os.path.join(headless_config.get('run_folder', ''), f"F11L2_{ts}") if headless else f"F11L2_{ts}"
                            save_to_project(fig, project_name, f"L2_Animation_{file_basename}.mp4", subfolder=subf, is_video=True, ani=ani)
                        else:
                            out_dir = os.path.join("exports", f"F11L2_{ts}")
                            os.makedirs(out_dir, exist_ok=True)
                            out_file = os.path.join(out_dir, f"L2_Animation_{file_basename}.mp4")
                            ani.save(out_file, writer='ffmpeg', fps=30, dpi=120)
                            print(f"  [+] Saved Animation to: {out_file}")
                    plt.close(fig)
                except Exception as e:
                    print(f"  [!] Animation Error: {e}")
                    import traceback; traceback.print_exc()

            if ans in ['open l3', 'print l3', 'open l4', 'print l4', 'open l5', 'print l5', 'open l6', 'print l6']:
                from ui.tui_ref_selector import select_reference_file
                from core.telemetry import load_telemetry
                import textwrap
                
                print("\n  [+] Select Reference Setup 1")
                res1 = select_reference_file(file_path, project_files=session.get('project_files'), project_name=session.get('project_name'))
                if not res1 or not res1[0]: continue
                r1_path, r1_laps, r1_data, r1_channels, r1_md = res1
                
                r2_path, r2_laps, r2_data, r2_channels, r2_md = None, None, None, None, None
                is_3_setup = ans in ['open l5', 'print l5', 'open l6', 'print l6']
                
                if is_3_setup:
                    print("\n  [+] Select Reference Setup 2")
                    res2 = select_reference_file(file_path, project_files=session.get('project_files'), project_name=session.get('project_name'))
                    if not res2 or not res2[0]: continue
                    r2_path, r2_laps, r2_data, r2_channels, r2_md = res2
                
                def extract_setup(y):
                    setup = y.get('CarSetup', {})
                    flat = {}
                    def recurse(d, prefix=""):
                        if isinstance(d, dict):
                            for k, v in d.items():
                                if k in ("UpdateCount", "LastTempsOMI", "LastTempsIMO", "TreadRemaining", "CornerWeight"): continue
                                recurse(v, f"{prefix}{k}." if prefix else f"{k}.")
                        else: flat[prefix[:-1]] = d
                    recurse(setup)
                    return flat

                def get_delta_title(y1_str, y2_str, fname):
                    y1 = yaml.safe_load(y1_str or '') or {}
                    y2 = yaml.safe_load(y2_str or '') or {}
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
                    delta_str = ", ".join(deltas) if deltas else "No Setup Changes"
                    return f"{os.path.basename(fname).replace('.ibt','')}\n{textwrap.shorten(delta_str, 50)}"

                title_base = f"BASELINE: {file_basename}"
                title_r1 = get_delta_title(md.get('session_info_yaml', ''), r1_md.get('session_info_yaml', ''), r1_path)
                title_r2 = get_delta_title(md.get('session_info_yaml', ''), r2_md.get('session_info_yaml', ''), r2_path) if is_3_setup else "" 

                def process_ref(r_data, r_ch, r_laps, bounds):
                    s_ch = next((c for c in ['Speed', 'virt_body_v', 'Ground Speed'] if c in r_data), None)
                    if not s_ch or 'dist' not in r_ch: return None
                    
                    spd = r_data[s_ch].data
                    spd_k = spd if np.max(spd) > 150 else spd * 3.6
                    fl = r_data['Ride Height FL'].data * 1000
                    fr = r_data['Ride Height FR'].data * 1000
                    rl = r_data['Ride Height RL'].data * 1000
                    rr = r_data['Ride Height RR'].data * 1000
                    fl_l = r_data['Suspension Load FL'].data
                    fr_l = r_data['Suspension Load FR'].data
                    rl_l = r_data['Suspension Load RL'].data
                    rr_l = r_data['Suspension Load RR'].data
                    
                    lat_g_ch = r_ch.get('lat')
                    long_g_ch = r_ch.get('long')
                    lat_g = r_data[lat_g_ch].data if lat_g_ch and lat_g_ch in r_data else np.zeros_like(spd_k)
                    long_g = r_data[long_g_ch].data if long_g_ch and long_g_ch in r_data else np.zeros_like(spd_k)
                    vert_g = r_data['VertAccel'].data / 9.80665 if 'VertAccel' in r_data else np.ones_like(spd_k)
                    
                    st_mask = (spd_k < 15) & (np.abs(lat_g) < 0.1) & (np.abs(long_g) < 0.1)
                    if np.any(st_mask):
                        st_w = np.median(fl_l[st_mask]) + np.median(fr_l[st_mask]) + np.median(rl_l[st_mask]) + np.median(rr_l[st_mask])
                    else:
                        st_w = np.median(fl_l)*0.4 + np.median(fr_l)*0.4 + np.median(rl_l)*0.6 + np.median(rr_l)*0.6
                        
                    c_mass = st_w / 9.80665
                    overrides = getattr(r_data, 'overrides', {})
                    phys = overrides.get('physics_model', {}) if overrides else {}
                    a_mass = phys.get('actual_mass_kg', 1350.0)
                    sf = a_mass / c_mass if (c_mass > 1800 or c_mass < 800) else 1.0
                    
                    tot_df = (fl_l*sf + fr_l*sf + rl_l*sf + rr_l*sf) - (st_w*sf * vert_g)
                    
                    d_raw = r_data[r_ch['dist']].data
                    lap_raw = r_data[r_ch['lap']].data if 'lap' in r_ch else np.zeros_like(d_raw)
                    b_min, b_max = bounds
                    l_mask = np.ones_like(d_raw, dtype=bool)
                    if r_laps: l_mask = np.isin(lap_raw, r_laps)
                    s_mask = (d_raw >= b_min) & (d_raw <= b_max) & l_mask
                    
                    if not np.any(s_mask): return None
                    
                    crh = (fl + fr + rl + rr)[s_mask] / 4.0
                    window = min(31, len(crh) // 2 * 2 + 1)
                    crh_s = savgol_filter(crh, window, 3) if window > 3 else crh
                    
                    s_spd = spd_k[s_mask]
                    v_idx = np.isfinite(s_spd) & np.isfinite(crh_s)
                    if np.sum(v_idx) < 10: return None
                    m, b = np.polyfit(s_spd[v_idx], crh_s[v_idx], 1)
                    
                    return {
                        'spd': s_spd, 'crh': crh_s, 'df': tot_df[s_mask], 
                        'f_rh': ((fl+fr)/2.0)[s_mask], 'r_rh': ((rl+rr)/2.0)[s_mask],
                        'dist': d_raw[s_mask], 'm': m, 'b': b
                    }

                r1_res = process_ref(r1_data, r1_channels, r1_laps, session['distance_bounds'])
                r2_res = process_ref(r2_data, r2_channels, r2_laps, session['distance_bounds']) if is_3_setup else None
                
                if not r1_res or (is_3_setup and not r2_res):
                    print("  [!] Failed to extract valid overlapping sector from reference files.")
                    continue
                    
                base_res = {'spd': s_speed, 'crh': crh_smooth, 'df': s_df, 'f_rh': s_f_rh, 'r_rh': s_r_rh, 'dist': s_dist, 'm': m, 'b': b}
                datasets = [base_res, r1_res, r2_res] if is_3_setup else [base_res, r1_res]
                titles = [title_base, title_r1, title_r2] if is_3_setup else [title_base, title_r1]
                
                plt.style.use(matplotx.styles.aura['dark'])
                
                if ans in ['open l3', 'print l3', 'open l5', 'print l5']:
                    print(f"  [+] Building Static Trade-off Comparison ({ans.split()[1].upper()})...")
                    fig = plt.figure(figsize=(18, 10), num='OpenDAV - Trade-off Comparison')
                    gs = GridSpec(2, len(datasets), height_ratios=[1.2, 1], figure=fig)
                    
                    for i, (ds, title) in enumerate(zip(datasets, titles)):
                        ax_map = fig.add_subplot(gs[0, i])
                        ax_reg = fig.add_subplot(gs[1, i])
                        
                        f_tri, r_tri, z_tri = ds['f_rh'], ds['r_rh'], ds['df']
                        if len(f_tri) > 3000:
                            idx = np.linspace(0, len(f_tri)-1, 3000, dtype=int)
                            f_tri, r_tri, z_tri = f_tri[idx], r_tri[idx], z_tri[idx]
                        try:
                            triang = mtri.Triangulation(f_tri, r_tri)
                            c_xy = np.column_stack((np.mean(f_tri[triang.triangles], axis=1), np.mean(r_tri[triang.triangles], axis=1)))
                            tree = cKDTree(np.column_stack((f_tri, r_tri)))
                            dist_v, _ = tree.query(c_xy)
                            triang.set_mask(dist_v > (np.max(f_tri)-np.min(f_tri)) * 0.1)
                            cf = ax_map.tricontourf(triang, z_tri, levels=15, cmap=opendav_cmap, extend='both', alpha=0.9)
                            ax_map.scatter(f_tri, r_tri, c='white', s=1, alpha=0.1)
                        except: pass
                        
                        ax_map.invert_xaxis()
                        ax_map.invert_yaxis()
                        ax_map.set_title(title, fontsize=10, color='white', loc='left')
                        ax_map.set_xlabel("Front RH (mm)"); ax_map.set_ylabel("Rear RH (mm)")
                        
                        ax_reg.scatter(ds['spd'], ds['crh'], c='white', s=5, alpha=0.4, edgecolors='none')
                        xl = np.array([np.min(ds['spd']), np.max(ds['spd'])])
                        yl = ds['m'] * xl + ds['b']
                        ax_reg.plot(xl, yl, c='#0ea5e9', lw=2.5, label=f"CR: {ds['m']:.4f} mm/kmh")
                        ax_reg.set_xlabel("Speed (km/h)"); ax_reg.set_ylabel("Center RH (mm)")
                        ax_reg.grid(True, alpha=0.1)
                        ax_reg.legend(loc='upper right', frameon=False)
                        
                    plt.tight_layout()
                    if ans in ['open l3', 'open l5']:
                        if get_gui_mode() == 3: show_ctk_graph(fig, "OpenDAV - Trade-off Comparison")
                        else: plt.show()
                    else:
                        l_name = ans.split()[1].upper()
                        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                        if '<' in ans_raw:
                            project_name = ans_raw.split('<')[1].strip().replace('[', '').replace(']', '').strip()
                            from analysis.projects import save_to_project
                            subf = headless_config.get('run_folder') if headless else None
                            save_to_project(fig, project_name, f"F11{l_name}_{ts}_Tradeoff.png", subfolder=subf)
                        else:
                            out = os.path.join("exports", f"F11{l_name}_{ts}_Tradeoff.png")
                            plt.savefig(out, dpi=300, bbox_inches='tight')
                            print(f"  [+] Saved {l_name} to {out}")
                    plt.close(fig)
                    
                elif ans in ['open l4', 'print l4', 'open l6', 'print l6']:
                    l_name = ans.split()[1].upper()
                    print(f"  [+] Building Animated Trade-off Comparison ({l_name})...")
                    fig = plt.figure(figsize=(18, 10), num='OpenDAV - Animated Trade-off')
                    gs = GridSpec(2, len(datasets), height_ratios=[1.2, 1], figure=fig)
                    
                    # Common Grid
                    if is_3_setup:
                        min_d = min(base_res['dist'][0], r1_res['dist'][0], r2_res['dist'][0])
                        max_d = max(base_res['dist'][-1], r1_res['dist'][-1], r2_res['dist'][-1])
                    else:
                        min_d = min(base_res['dist'][0], r1_res['dist'][0])
                        max_d = max(base_res['dist'][-1], r1_res['dist'][-1])
                    d_grid = np.arange(min_d, max_d, 2.0)
                    
                    resampled = []
                    for ds in datasets:
                        s_idx = np.argsort(ds['dist'])
                        d_sort = ds['dist'][s_idx]
                        r_f = np.interp(d_grid, d_sort, ds['f_rh'][s_idx])
                        r_r = np.interp(d_grid, d_sort, ds['r_rh'][s_idx])
                        r_z = np.interp(d_grid, d_sort, ds['df'][s_idx])
                        r_s = np.interp(d_grid, d_sort, ds['spd'][s_idx])
                        r_c = np.interp(d_grid, d_sort, ds['crh'][s_idx])
                        resampled.append({'f': r_f, 'r': r_r, 'z': r_z, 'spd': r_s, 'crh': r_c, 'm': ds['m'], 'b': ds['b']})
                        
                    axs_map = [fig.add_subplot(gs[0, i]) for i in range(len(datasets))]
                    axs_reg = [fig.add_subplot(gs[1, i]) for i in range(len(datasets))]
                    reg_dots = []
                    
                    for i, (ds, rds, title) in enumerate(zip(datasets, resampled, titles)):
                        axs_reg[i].scatter(ds['spd'], ds['crh'], c='white', s=5, alpha=0.1, edgecolors='none')
                        xl = np.array([np.min(ds['spd']), np.max(ds['spd'])])
                        yl = ds['m'] * xl + ds['b']
                        axs_reg[i].plot(xl, yl, c='#0ea5e9', lw=2.0, alpha=0.5, label=f"CR: {ds['m']:.4f}")
                        rd, = axs_reg[i].plot([], [], 'o', color='white', markersize=10, zorder=10)
                        reg_dots.append(rd)
                        axs_reg[i].set_title(title, fontsize=10, loc='left')
                        axs_reg[i].legend(loc='upper right', frameon=False)
                        
                    plt.tight_layout()
                    w_size = 75
                    
                    def update(frame):
                        s_idx = max(0, frame - w_size)
                        e_idx = frame + 1
                        
                        ret = []
                        for i in range(len(datasets)):
                            rds = resampled[i]
                            axs_map[i].clear()
                            axs_map[i].set_xlim(np.max(rds['f'])+2, np.min(rds['f'])-2)
                            axs_map[i].set_ylim(np.max(rds['r'])+2, np.min(rds['r'])-2)
                            
                            w_f = rds['f'][s_idx:e_idx]
                            w_r = rds['r'][s_idx:e_idx]
                            w_z = rds['z'][s_idx:e_idx]
                            
                            if len(w_f) > 5:
                                try:
                                    triang = mtri.Triangulation(w_f, w_r)
                                    c_xy = np.column_stack((np.mean(w_f[triang.triangles], axis=1), np.mean(w_r[triang.triangles], axis=1)))
                                    tree = cKDTree(np.column_stack((w_f, w_r)))
                                    dist_v, _ = tree.query(c_xy)
                                    triang.set_mask(dist_v > (np.max(w_f)-np.min(w_f)) * 0.15)
                                    axs_map[i].tricontourf(triang, w_z, levels=10, cmap=opendav_cmap, extend='both', alpha=0.9)
                                except: pass
                            axs_map[i].scatter(rds['f'][frame], rds['r'][frame], c='red', s=60, edgecolors='white', zorder=10)
                            reg_dots[i].set_data([rds['spd'][frame]], [rds['crh'][frame]])
                            ret.extend([axs_map[i], reg_dots[i]])
                        return ret
                        
                    ani = animation.FuncAnimation(fig, update, frames=len(d_grid), blit=False)
                    if ans == 'open l4':
                        if get_gui_mode() == 3: show_ctk_graph(fig, "OpenDAV - Animated Trade-off")
                        else: plt.show()
                    else:
                        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                        print(f"      Rendering MP4 ({len(d_grid)} frames)...")
                        if '<' in ans_raw:
                            project_name = ans_raw.split('<')[1].strip().replace('[', '').replace(']', '').strip()
                            from analysis.projects import save_to_project
                            subf = os.path.join(headless_config.get('run_folder', ''), f"F11L4_{ts}") if headless else f"F11L4_{ts}"
                            save_to_project(fig, project_name, f"L4_Tradeoff_{file_basename}.mp4", subfolder=subf, is_video=True, ani=ani)
                        else:
                            out_dir = os.path.join("exports", f"F11L4_{ts}")
                            os.makedirs(out_dir, exist_ok=True)
                            out_file = os.path.join(out_dir, f"L4_Tradeoff_{file_basename}.mp4")
                            ani.save(out_file, writer='ffmpeg', fps=30, dpi=120)
                            print(f"  [+] Saved Animation to: {out_file}")
                    plt.close(fig)


            if ans in ['open l1', 'print l1']:
                print("  [+] Building Compression Rates Layout (L1)...")
                plt.style.use(matplotx.styles.aura['dark'])
                fig = plt.figure(figsize=(16, 10), num='OpenDAV - Compression Rates')
                gs = GridSpec(2, 2, height_ratios=[1, 1], figure=fig)
                
                ax_map = fig.add_subplot(gs[0, 0])
                try:
                    f_tri, r_tri, z_tri = s_f_rh, s_r_rh, s_df
                    if len(f_tri) > 5000:
                        idx = np.linspace(0, len(f_tri)-1, 5000, dtype=int)
                        f_tri, r_tri, z_tri = f_tri[idx], r_tri[idx], z_tri[idx]
                        
                    triang = mtri.Triangulation(f_tri, r_tri)
                    c_xy = np.column_stack((np.mean(f_tri[triang.triangles], axis=1), np.mean(r_tri[triang.triangles], axis=1)))
                    tree = cKDTree(np.column_stack((f_tri, r_tri)))
                    dist, _ = tree.query(c_xy)
                    triang.set_mask(dist > (np.max(f_tri)-np.min(f_tri)) * 0.1)
                    
                    cf = ax_map.tricontourf(triang, z_tri, levels=15, cmap=opendav_cmap, extend='both', alpha=0.9)
                    ax_map.scatter(f_tri, r_tri, c='white', s=2, alpha=0.2)
                    ax_map.invert_xaxis()
                    ax_map.invert_yaxis()
                    ax_map.set_title("Sector Downforce Contour", fontsize=12, pad=10)
                    ax_map.set_xlabel("Front RH (mm)")
                    ax_map.set_ylabel("Rear RH (mm)")
                    plt.colorbar(cf, ax=ax_map, label="Downforce (N)")
                except Exception as e:
                    ax_map.text(0.5, 0.5, f"Map Error: {e}", color='red', ha='center')
                    
                ax_reg = fig.add_subplot(gs[0, 1])
                ax_reg.scatter(s_speed, crh_smooth, c='white', s=10, alpha=0.6, edgecolors='none', label="Smoothed Center RH")
                x_line = np.array([np.min(s_speed), np.max(s_speed)])
                y_line = m * x_line + b
                ax_reg.plot(x_line, y_line, c='#0ea5e9', lw=2.5, label=f"Trend: {m:.4f} mm/kmh")
                ax_reg.set_title("Compression Rate vs Speed", fontsize=12, pad=10)
                ax_reg.set_xlabel("Speed (km/h)")
                ax_reg.set_ylabel("Center Ride Height (mm)")
                ax_reg.grid(True, alpha=0.1)
                ax_reg.legend(loc='upper right', frameon=False)
                
                ax_dist = fig.add_subplot(gs[1, :])
                d_plot = s_dist - s_dist[0]
                ax_dist.plot(d_plot, s_df, c='#A020F0', lw=1.5, label="Total Downforce")
                ax_dist.set_ylabel("Downforce (N)", color='#A020F0')
                ax_dist.set_xlabel("Sector Distance (m)")
                ax_spd = ax_dist.twinx()
                ax_spd.plot(d_plot, s_speed, c='#32CD32', lw=1.5, label="Speed", alpha=0.8)
                ax_spd.set_ylabel("Speed (km/h)", color='#32CD32')
                ax_dist.set_title("Downforce & Speed Envelope", fontsize=12, pad=10)
                ax_dist.grid(True, alpha=0.1)
                
                fig.suptitle(f"OpenDAV Compression Rates: {file_basename}", fontsize=15, color='white', y=0.96)
                plt.tight_layout()
                fig.subplots_adjust(top=0.88)
                
                if ans == 'open l1':
                    if get_gui_mode() == 3: show_ctk_graph(fig, "OpenDAV - Compression Rates")
                    else: plt.show()
                elif ans == 'print l1':
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                    if '<' in ans_raw:
                        project_name = ans_raw.split('<')[1].strip().replace('[', '').replace(']', '').strip()
                        from analysis.projects import save_to_project
                        subf = headless_config.get('run_folder') if headless else None
                        save_to_project(fig, project_name, f"F11L1_{ts}_{file_basename}.png", subfolder=subf)
                    else:
                        export_dir = "exports"
                        os.makedirs(export_dir, exist_ok=True)
                        out = os.path.join(export_dir, f"F11L1_{ts}_{file_basename}.png")
                        plt.savefig(out, dpi=300, bbox_inches='tight')
                        print(f"  [+] Saved to {out}")
                    plt.close(fig)
                    
        print("\n" + "─"*100)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break
