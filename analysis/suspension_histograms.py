import os
import sys
import numpy as np
from scipy.spatial import cKDTree
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ui.splash as splash
from ui.metadata_printer import print_session_metadata
from ui.graphing import show_ctk_graph
from core.config import get_gui_mode

def get_susp_travel(data, corner):
    """
    Search for suspension travel channels for a specific corner.
    Returns (data_array, channel_name, is_estimate)
    """
    # iRacing / Standard Mappings
    mappings = {
        'FL': ['Damper Pos FL', 'Susp Pos FL', 'Suspension Travel FL', 'LFshockDefl', 'LF shock deflection'],
        'FR': ['Damper Pos FR', 'Susp Pos FR', 'Suspension Travel FR', 'RFshockDefl', 'RF shock deflection'],
        'RL': ['Damper Pos RL', 'Susp Pos RL', 'Suspension Travel RL', 'LRshockDefl', 'LR shock deflection'],
        'RR': ['Damper Pos RR', 'Susp Pos RR', 'Suspension Travel RR', 'RRshockDefl', 'RR shock deflection']
    }
    
    for ch in mappings[corner]:
        if ch in data:
            try:
                # Some files have channels listed but with corrupt/unknown data types
                # Typically, Damper Pos is logged in meters. We need to convert it to millimeters.
                raw_data = data[ch].data
                if np.max(np.abs(raw_data)) < 0.5: # If max travel is less than half a meter, it's almost certainly logged in meters
                    return raw_data * 1000, ch, False
                return raw_data, ch, False
            except ValueError:
                continue
            
    # Fallback to Ride Heights (Estimating travel from height changes)
    rh_mappings = {
        'FL': ['Ride Height FL', 'LFrideHeight'],
        'FR': ['Ride Height FR', 'RFrideHeight'],
        'RL': ['Ride Height RL', 'LRrideHeight'],
        'RR': ['Ride Height RR', 'RRrideHeight']
    }
    
    for ch in rh_mappings[corner]:
        if ch in data:
            try:
                raw_h = data[ch].data * 1000 # convert to mm
                static_h = np.mean(raw_h[:10]) # Rough static baseline
                # Susp compression = Static - Current (roughly)
                travel = static_h - raw_h
                return travel, ch, True
            except ValueError:
                continue
            
    return None, None, False

def run_suspension_histograms(sessions):
    while True:
        splash.print_header("Suspension Travel Histograms")
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            channels = session['channels']
            metadata = session.get('metadata', {})
            
            print(f"\nAnalyzing: {os.path.basename(file_path)}")
            print_session_metadata(data, channels, session.get('metadata', {}))
            
            # 1. Ask for Sector
            print("\n  Enter track window (e.g., '142-316' or 'fl' for full lap)")
            inp = input("  Window: ").strip().lower()
            
            if inp == 'q':
                splash.show_exit_screen()
                sys.exit(0)
            if inp == 'p':
                break
                
            is_full_lap = False
            if inp == 'fl':
                is_full_lap = True
                start_m, end_m = 0.0, 0.0
            elif '-' not in inp:
                print("  [!] Invalid format. Try 'Start-End' or 'fl'.")
                input("\nPress Enter to return...")
                continue
            else:
                try:
                    start_m, end_m = map(float, inp.split('-'))
                except ValueError:
                    print("  [!] Invalid format.")
                    input("\nPress Enter to return...")
                    continue

            dist_arr = data[channels['dist']].data
            lap_arr = data[channels['lap']].data
            time_arr = data[channels['time']].data

            if is_full_lap:
                start_m = 0.0
                end_m = float(np.max(dist_arr))

            # Find fastest lap in that window
            laps = np.unique(lap_arr)
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
            
            fastest_lap, _ = min(valid_laps, key=lambda x: x[1])
            f_idx = np.where(lap_arr == fastest_lap)[0]
            
            l_dist = dist_arr[f_idx]
            mask = (l_dist >= start_m) & (l_dist <= end_m)
            
            if not np.any(mask):
                print("  [!] No data in that window for fastest lap.")
                continue
                
            # 2. Extract Data for all 4 corners
            corners = ['FL', 'FR', 'RL', 'RR']
            corner_names_long = {
                'FL': 'Front Left',
                'FR': 'Front Right',
                'RL': 'Rear Left',
                'RR': 'Rear Right'
            }
            corner_data = {}
            warnings = []
            
            for c in corners:
                trav, name, is_est = get_susp_travel(data, c)
                if trav is not None:
                    # Clip data to window
                    window_data = trav[f_idx][mask]
                    corner_data[c] = {
                        'vals': window_data,
                        'name': name,
                        'is_estimate': is_est
                    }
                    if is_est:
                        warnings.append(f"[!] {c}: Using Ride Height estimation ({name})")
                else:
                    print(f"  [!] Missing suspension travel for {c}.")

            if not corner_data:
                print("  [!] No suspension data available for any corner.")
                continue

            for w in warnings:
                print(f"  {w}")

            # 3. Calculate Stats for CLI
            stats = {}
            for c, d in corner_data.items():
                v = d['vals']
                # Histogram (1mm bins)
                bins = np.arange(np.floor(np.min(v)), np.ceil(np.max(v)) + 1, 1)
                counts, bin_edges = np.histogram(v, bins=bins)
                
                # Find peak bin
                if len(counts) > 0:
                    peak_idx = np.argmax(counts)
                    peak_range = f"{bin_edges[peak_idx]:.0f}-{bin_edges[peak_idx+1]:.0f}"
                else:
                    peak_range = "N/A"
                
                stats[c] = {
                    'min': np.min(v),
                    'max': np.max(v),
                    'peak': peak_range
                }

            # 4. CLI Output (ASCII BOX)
            PINK = '\033[95m'
            RESET = "\033[0m"
            
            header_str = f"[ SUSPENSION TRAVEL SUMMARY - Lap {int(fastest_lap)} ]"
            print("\n ┌" + "─" * 50 + "┐")
            print(" │ " + header_str.center(48) + " │")
            print(" │ " + " " * 48 + " │")
            for c in corners:
                full_name = corner_names_long[c]
                if c in stats:
                    s = stats[c]
                    data_str = f"{full_name}:  [{s['min']:>4.1f} to {s['max']:>4.1f} mm] Peak @ {s['peak']} mm"
                    print(" │ " + f"{data_str}".ljust(48) + " │")
                else:
                    print(" │ " + f"{full_name}: [MISSING]".ljust(48) + " │")
            print(" └" + "─" * 50 + "┘")

            # 5. Graphing
            ans = input(f"\n  Launch simulation graph for Sector {start_m}m to {end_m}m? (y/n): ").strip().lower()
            if ans == 'y':
                print("  [+] Building histograms... (Close the window to continue)")
                
                GUI_MODE = get_gui_mode()
                
                title_plt = f"Suspension Travel Histograms - Lap {int(fastest_lap)}\n{os.path.basename(file_path)}"
                title_web = f"Suspension Travel Histograms - Lap {int(fastest_lap)} | {os.path.basename(file_path)}"

                if GUI_MODE == 2:
                    # Plotly (2x2)
                    fig = make_subplots(rows=2, cols=2, 
                                        subplot_titles=("Front Left (FL)", "Front Right (FR)", 
                                                        "Rear Left (RL)", "Rear Right (RR)"),
                                        vertical_spacing=0.15)
                    
                    pos_map = {'FL': (1,1), 'FR': (1,2), 'RL': (2,1), 'RR': (2,2)}
                    
                    for c, d in corner_data.items():
                        r, col = pos_map[c]
                        fig.add_trace(go.Histogram(x=d['vals'], xbins=dict(size=1.0),
                                                   marker_color='cyan', opacity=0.7,
                                                   name=c, histnorm='percent'),
                                      row=r, col=col)
                        
                    fig.update_layout(title_text=title_web, template="plotly_dark", 
                                      showlegend=False, font=dict(family="Consolas", size=13))
                    fig.update_xaxes(title_text="Position (mm)")
                    fig.update_yaxes(title_text="Time (%)")
                    fig.show()

                else:
                    # Matplotlib / CTK
                    import matplotx
                    plt.style.use(matplotx.styles.aura['dark'])
                    plt.rcParams.update({
                        'font.family': ['Consolas', 'DejaVu Sans Mono', 'monospace'],
                        'figure.dpi': 144,  # High-DPI Retina rendering
                        'axes.linewidth': 1.2,
                        'grid.alpha': 0.15,
                        'xtick.direction': 'in',
                        'ytick.direction': 'in',
                        'scatter.edgecolors': 'none'
                    })
                    fig, axs = plt.subplots(2, 2, figsize=(14, 9), num='OpenDAV - Suspension Histograms')
                    plt.suptitle(title_plt, fontsize=16, fontweight='bold')
                    
                    pos_map = {'FL': axs[0,0], 'FR': axs[0,1], 'RL': axs[1,0], 'RR': axs[1,1]}
                    
                    for c, d in corner_data.items():
                        ax = pos_map[c]
                        # Histogram
                        counts, bins, patches = ax.hist(d['vals'], bins=np.arange(np.floor(np.min(d['vals'])), np.ceil(np.max(d['vals'])) + 1, 1),
                                                        color='cyan', alpha=0.7, density=True, label='Frequency')
                        
                        # Smooth line (simple moving average over histogram)
                        if len(counts) > 3:
                            smooth_counts = np.convolve(counts, np.ones(3)/3, mode='same')
                            bin_centers = (bins[:-1] + bins[1:]) / 2
                            ax.plot(bin_centers, smooth_counts, color='deeppink', linewidth=2, label='Trend')
                        
                        ax.set_title(f"Corner: {c} ({d['name']})", color='white', fontsize=12)
                        ax.set_xlabel("Position (mm)", fontsize=10)
                        ax.set_ylabel("Probability Density", fontsize=10)
                        ax.grid(True, linestyle=':', alpha=0.3)
                        ax.legend(fontsize=8)

                    # Metadata Box (Bottom Left)
                    md = session.get('metadata', {})
                    info_text = (f"Driver: {md.get('driver', 'N/A')}\n"
                                 f"Car: {md.get('car', 'N/A')}\n"
                                 f"Venue: {md.get('venue', 'N/A')}\n"
                                 f"Fastest Lap: {md.get('fastest_lap', 'N/A')}\n"
                                 f"Laps: {md.get('laps_count', 0)}")
                    plt.figtext(0.02, 0.02, info_text, fontsize=9, color='white',
                                alpha=0.8, va='bottom', ha='left',
                                bbox=dict(facecolor='#1a1a1a', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.5'))

                    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
                    
                    if GUI_MODE == 3:
                        show_ctk_graph(fig, "OpenDAV - Suspension Histograms")
                    else:
                        plt.show()

        print("\n" + "─"*100)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break
