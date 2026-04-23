import os
import sys
import re
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

def run_setup_prediction_engine(sessions):
    while True:
        splash.print_header("Setup Prediction Engine (Alpha) - Roll Stiffness")
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            channels = session['channels']
            print(f"\nAnalyzing Baseline: {os.path.basename(file_path)}")
            
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
                print("  [!] Not enough cornering data to establish baseline.")
                continue
                
            cornering_lat_g = lat_g[mask]
            cornering_front_roll = front_roll_mm[mask]
            cornering_rear_roll = rear_roll_mm[mask]

            # Linear regression to find baseline gradient
            try:
                baseline_front_m, _ = np.polyfit(cornering_lat_g, cornering_front_roll, 1)
                baseline_rear_m, _ = np.polyfit(cornering_lat_g, cornering_rear_roll, 1)
                
                total_gradient = abs(baseline_front_m) + abs(baseline_rear_m)
                if total_gradient == 0:
                    print("  [!] Calculated zero roll baseline.")
                    continue
                    
                baseline_front_dist = (abs(baseline_front_m) / total_gradient) * 100
                baseline_rear_dist = (abs(baseline_rear_m) / total_gradient) * 100
                
            except Exception as e:
                print(f"  [!] Error calculating baseline gradient: {e}")
                continue

            PINK = '\033[95m'
            CYAN = '\033[96m'
            RESET = "\033[0m"

            print("\n ┌" + "─" * 49 + "┐")
            print(" │ " + "[ Baseline Roll Stiffness ]".ljust(96) + " │")
            print(" │ " + f"{CYAN}Front Roll:{RESET} {abs(baseline_front_m):.3f} mm/G ({baseline_front_dist:.1f}%)".ljust(96 + len(CYAN) + len(RESET)) + " │")
            print(" │ " + f"{CYAN}Rear Roll:{RESET}  {abs(baseline_rear_m):.3f} mm/G ({baseline_rear_dist:.1f}%)".ljust(96 + len(CYAN) + len(RESET)) + " │")
            print(" └" + "─" * 49 + "┘")
            
            print("\n  Enter setup change (e.g., 'farb +10%' or 'rarb -5%')")
            print("  Type 'p' to skip to next file/menu, or 'q' to quit.")
            
            cmd = input("\nChange: ").strip().lower()
            if cmd == 'q':
                splash.show_exit_screen()
                sys.exit(0)
            if cmd == 'p':
                break
                
            # Parse command
            match = re.match(r'(farb|rarb)\s*([+-]\d+)', cmd.replace('%', ''))
            if not match:
                print("  [!] Invalid format. Try 'farb +10' or 'rarb -5'.")
                input("\nPress Enter to return...")
                continue
                
            axle = match.group(1)
            percent_change = float(match.group(2))
            multiplier = 1.0 + (percent_change / 100.0)
            
            # Since stiffness is inversely proportional to roll (Roll = Torque / Stiffness)
            # If stiffness increases by 10% (multiplier 1.1), roll decreases by factor of (1/1.1)
            # Wait, user command is conceptually "Stiffen by 10%". So modifier to Roll Gradient is 1/multiplier
            if multiplier <= 0:
                print("  [!] Invalid stiffness change.")
                continue

            roll_modifier = 1.0 / multiplier
            
            if axle == 'farb':
                new_front_m = baseline_front_m * roll_modifier
                new_rear_m = baseline_rear_m # Assuming chassis box rigidity shift is minor for local axle visual
                
                new_total = abs(new_front_m) + abs(new_rear_m)
                new_front_dist = (abs(new_front_m) / new_total) * 100
                new_rear_dist = (abs(new_rear_m) / new_total) * 100
                
                axle_name = "Front"
                old_m = baseline_front_m
                new_m = new_front_m
                
            else: # rarb
                new_front_m = baseline_front_m
                new_rear_m = baseline_rear_m * roll_modifier
                
                new_total = abs(new_front_m) + abs(new_rear_m)
                new_front_dist = (abs(new_front_m) / new_total) * 100
                new_rear_dist = (abs(new_rear_m) / new_total) * 100
                
                axle_name = "Rear"
                old_m = baseline_rear_m
                new_m = new_rear_m

            if axle == 'farb':
                load_shift_pct = ((new_front_dist - baseline_front_dist) / baseline_front_dist) * 100
            else:
                load_shift_pct = ((new_rear_dist - baseline_rear_dist) / baseline_rear_dist) * 100
                
            load_msg = f"Est. Outside Tire Load Change: {load_shift_pct:+.1f}%"

            print("\n ┌" + "─" * 49 + "┐")
            print(" │ " + "[ PREDICTION RESULTS ]".ljust(96) + " │")
            print(" │ " + f"{axle_name} Roll Gradient: {abs(old_m):.3f} -> {PINK}{abs(new_m):.3f} mm/G{RESET}".ljust(96 + len(PINK) + len(RESET)) + " │")
            print(" │ " + f"New Roll Balance: Front {new_front_dist:.1f}% | Rear {new_rear_dist:.1f}%".ljust(96) + " │")
            print(" │ " + load_msg.ljust(96) + " │")
            print(" └" + "─" * 49 + "┘")

            # Sector visualization
            print("\n  Enter track window to simulate the ghost setup")
            inp = input("  (e.g., '142-316' or 'fl' for full lap): ").strip().lower()
            
            is_full_lap = False
            if inp == 'fl':
                is_full_lap = True
                start_m, end_m = 0.0, 0.0
            elif '-' not in inp:
                print("  [!] Invalid format. Use 'Start-End' or 'fl'.")
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
                
            fastest_lap, fastest_time = min(valid_laps, key=lambda x: x[1])
            idx = np.where(lap_arr == fastest_lap)[0]
            
            l_dist = dist_arr[idx]
            mask = (l_dist >= start_m) & (l_dist <= end_m)
            
            if not np.any(mask):
                print("  [!] No data inside that window for the fastest lap.")
                continue
            
            x_data = l_dist[mask]
            actual_lat_g = lat_g[idx][mask]
            
            if axle == 'farb':
                actual_roll = front_roll_mm[idx][mask]
                # Predicted Roll = True G * new_m
                predicted_roll = actual_lat_g * new_front_m
            else:
                actual_roll = rear_roll_mm[idx][mask]
                predicted_roll = actual_lat_g * new_rear_m

            ans = input(f"\n  Launch simulation graph for Sector {start_m}m to {end_m}m? (y/n): ").strip().lower()
            if ans == 'y':
                print("  [+] Building graph... (Close the window to continue)")
                
                GUI_MODE = get_gui_mode()
                
                title_text = f"Predicted Setup {axle_name} Roll (Lap {int(fastest_lap)})<br>{os.path.basename(file_path)}"
                title_text_plt = f"Predicted Setup {axle_name} Roll (Lap {int(fastest_lap)})\n{os.path.basename(file_path)}"
                
                if GUI_MODE == 2:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=x_data, y=actual_roll, mode='lines', line=dict(color='cyan', width=2), name='Actual Roll'))
                    fig.add_trace(go.Scatter(x=x_data, y=predicted_roll, mode='lines', line=dict(color='deeppink', width=2, dash='dash'), name=f'Predicted (Ghost) {axle_name} Roll'))
                    
                    fig.update_layout(
                        title=title_text,
                        xaxis_title="Distance (m)",
                        yaxis_title="Roll (mm)",
                        template="plotly_dark",
                        font=dict(family="Consolas", size=13)
                    )
                    fig.show()

                else:
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
                    fig = plt.figure(figsize=(12, 7), num='OpenDAV - Setup Prediction Engine')

                    plt.plot(x_data, actual_roll, color='cyan', linewidth=2, label='Actual Roll')
                    plt.plot(x_data, predicted_roll, color='deeppink', linewidth=2, linestyle='--', label=f'Predicted (Ghost) {axle_name} Roll')
                    
                    plt.title(title_text_plt, fontsize=16, fontweight='bold', pad=20)
                    plt.xlabel("Distance (m)", fontsize=13)
                    plt.ylabel("Roll (mm)", fontsize=13)
                    plt.xticks(fontsize=11)
                    plt.yticks(fontsize=11)
                    plt.legend(fontsize=11, frameon=True, shadow=True)
                    plt.grid(True, linestyle='--', alpha=0.3)

                    md = session.get('metadata', {})
                    info_text = (f"Driver: {md.get('driver', 'N/A')}\n"
                                 f"Car: {md.get('car', 'N/A')}\n"
                                 f"Venue: {md.get('venue', 'N/A')}\n"
                                 f"Fastest Lap: {md.get('fastest_lap', 'N/A')}\n"
                                 f"Laps: {md.get('laps_count', 0)}")
                    plt.figtext(0.02, 0.02, info_text, fontsize=9, color='white',
                                alpha=0.8, va='bottom', ha='left',
                                bbox=dict(facecolor='#1a1a1a', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.5'))

                    plt.tight_layout()
                    
                    if GUI_MODE == 3:
                        show_ctk_graph(fig, "OpenDAV - Setup Prediction Engine")
                    else:
                        plt.show()

        print("\n" + "─"*100)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break
