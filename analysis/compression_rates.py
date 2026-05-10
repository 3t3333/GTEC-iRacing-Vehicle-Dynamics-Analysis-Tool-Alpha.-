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
            # We want mm / kmh -> slope = d(CRH) / d(Speed)
            # Ensure valid data
            valid_idx = np.isfinite(s_speed) & np.isfinite(crh_smooth)
            if np.sum(valid_idx) < 10:
                print("  [!] Not enough stable data for regression.")
                continue
                
            m, b = np.polyfit(s_speed[valid_idx], crh_smooth[valid_idx], 1)
            
            print(f"  [+] Sector Analyzed.")
            print(f"      Compression Rate: {m:.4f} mm / (km/h)")
            
            ans_raw = input(f"\n  Select action ('open L1/L2', 'print L1/L2', 'p' to go back < proj): ").strip().lower()
            ans = ans_raw.split('<')[0].strip().lower()
            
            if ans == 'p':
                break
                
                        if ans in ['open l2', 'print l2']:
                try:
                    # 1. DISTANCE RESAMPLING (For Smooth Animation)
                    d_min, d_max = s_dist[0], s_dist[-1]
                    d_grid = np.arange(d_min, d_max, 2.0) # 2-meter spatial steps
                    
                    # Interpolate data onto grid
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
                    
                    # PRE-PLOT STATIC ELEMENTS
                    # Regression Background
                    ax_reg.scatter(s_speed, crh_smooth, c='white', s=5, alpha=0.1, edgecolors='none')
                    x_line = np.array([np.min(s_speed), np.max(s_speed)])
                    y_line = m * x_line + b
                    ax_reg.plot(x_line, y_line, c='#0ea5e9', lw=2.0, alpha=0.5, label=f"Trend: {m:.4f} mm/kmh")
                    reg_dot, = ax_reg.plot([], [], 'o', color='white', markersize=10, zorder=10)
                    ax_reg.set_title("Compression Rate Trend", fontsize=11)
                    ax_reg.set_xlabel("Speed (km/h)"); ax_reg.set_ylabel("Center RH (mm)")
                    
                    # Distance Background
                    d_plot = d_grid - d_grid[0]
                    ax_dist.plot(d_plot, df_res, c='#A020F0', lw=1.5, alpha=0.4, label="Downforce")
                    ax_dist.set_ylabel("Downforce (N)", color='#A020F0')
                    ax_dist.set_xlabel("Sector Distance (m)")
                    
                    ax_spd = ax_dist.twinx()
                    ax_spd.plot(d_plot, spd_res, c='#32CD32', lw=1.5, alpha=0.4, label="Speed")
                    ax_spd.set_ylabel("Speed (km/h)", color='#32CD32')
                    
                    playhead = ax_dist.axvline(0, color='white', lw=2, zorder=10)
                    df_dot, = ax_dist.plot([], [], 'o', color='white', markersize=8, zorder=11)
                    
                    # Map Limits
                    f_min_lim, f_max_lim = np.min(f_rh_res)-2, np.max(f_rh_res)+2
                    r_min_lim, r_max_lim = np.min(r_rh_res)-2, np.max(r_rh_res)+2
                    
                    fig.suptitle(f"OpenDAV F12L2: {file_basename}", fontsize=15, color='white', y=0.97)
                    plt.tight_layout()
                    fig.subplots_adjust(top=0.9)
                    
                    window_size = 75 # 150m window
                    
                    def update(frame):
                        # 1. Update Map (Rolling Window)
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
                        
                        # 2. Update Regression Dot
                        reg_dot.set_data([spd_res[frame]], [crh_res[frame]])
                        
                        # 3. Update Playhead
                        playhead.set_xdata([d_plot[frame], d_plot[frame]])
                        df_dot.set_data([d_plot[frame]], [df_res[frame]])
                        
                        return ax_map, reg_dot, playhead, df_dot

                    ani = animation.FuncAnimation(fig, update, frames=len(d_grid), blit=False)
                    
                    if ans == 'open l2':
                        if get_gui_mode() == 3: show_ctk_graph(fig, "OpenDAV - Animated Compression")
                        else: plt.show()
                    elif ans == 'print l2':
                        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                        out_dir = os.path.join("exports", f"F12L2_{ts}")
                        os.makedirs(out_dir, exist_ok=True)
                        out_file = os.path.join(out_dir, f"L2_Animation_{file_basename}.mp4")
                        print(f"      Rendering MP4 ({len(d_grid)} frames @ 30fps)...")
                        ani.save(out_file, writer='ffmpeg', fps=30, dpi=120)
                        print(f"  [+] Saved Animation to: {out_file}")
                        
                    plt.close(fig)
                except Exception as e:
                    print(f"  [!] Animation Error: {e}")
                    import traceback; traceback.print_exc()

            if ans in ['open l1', 'print l1']:
                print("  [+] Building Compression Rates Layout (L1)...")
                plt.style.use(matplotx.styles.aura['dark'])
                fig = plt.figure(figsize=(16, 10), num='OpenDAV - Compression Rates')
                gs = GridSpec(2, 2, height_ratios=[1, 1], figure=fig)
                
                # Top Left: Downforce Contour
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
                    
                # Top Right: Regression Plot
                ax_reg = fig.add_subplot(gs[0, 1])
                ax_reg.scatter(s_speed, crh_smooth, c='white', s=10, alpha=0.6, edgecolors='none', label="Smoothed Center RH")
                
                # Regression line
                x_line = np.array([np.min(s_speed), np.max(s_speed)])
                y_line = m * x_line + b
                ax_reg.plot(x_line, y_line, c='#0ea5e9', lw=2.5, label=f"Trend: {m:.4f} mm/kmh")
                
                ax_reg.set_title("Compression Rate vs Speed", fontsize=12, pad=10)
                ax_reg.set_xlabel("Speed (km/h)")
                ax_reg.set_ylabel("Center Ride Height (mm)")
                ax_reg.grid(True, alpha=0.1)
                ax_reg.legend(loc='upper right', frameon=False)
                
                # Bottom: Distance Line Chart (Speed and DF)
                ax_dist = fig.add_subplot(gs[1, :])
                d_plot = s_dist - s_dist[0]
                
                ax_dist.plot(d_plot, s_df, c='#A020F0', lw=1.5, label="Total Downforce")
                ax_dist.set_ylabel("Downforce (N)", color='#A020F0')
                ax_dist.tick_params(axis='y', labelcolor='#A020F0')
                ax_dist.set_xlabel("Sector Distance (m)")
                
                ax_spd = ax_dist.twinx()
                ax_spd.plot(d_plot, s_speed, c='#32CD32', lw=1.5, label="Speed", alpha=0.8)
                ax_spd.set_ylabel("Speed (km/h)", color='#32CD32')
                ax_spd.tick_params(axis='y', labelcolor='#32CD32')
                
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
                    export_dir = "exports"
                    os.makedirs(export_dir, exist_ok=True)
                    out = os.path.join(export_dir, f"F12L1_{ts}_{file_basename}.png")
                    plt.savefig(out, dpi=300, bbox_inches='tight')
                    print(f"  [+] Saved to {out}")
                    plt.close(fig)
                    
        print("\n" + "─"*100)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break
