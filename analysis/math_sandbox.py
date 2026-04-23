import os
import sys
import re
import numpy as np
from scipy.spatial import cKDTree
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import ui.splash as splash
from ui.metadata_printer import print_session_metadata
from ui.graphing import show_ctk_graph
from core.config import get_gui_mode

def run_custom_math_graph(sessions):
    while True:
        splash.print_header("Custom Math Graphing Tool (Sandbox)")
        
        print("  Create a custom formula using channel names in brackets.")
        print("  Example: ([Wheel Speed FL] + [Wheel Speed FR]) / 2")
        print("  (Type 'c' to view all available channels in the first session)")
        formula = input("\nEnter formula, 'p' for Tools Menu, or 'q' to quit: ").strip()
        
        if formula.lower() == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        if formula.lower() == 'p':
            break
        if formula.lower() == 'c':
            if sessions:
                data = sessions[0]['data']
                names = sorted([ch.name for ch in getattr(data, 'channs', []) if hasattr(ch, 'name')])
                print("\n--- Available Channels ---")
                for i in range(0, len(names), 3):
                    print("  " + ", ".join(names[i:i+3]))
            input("\nPress Enter to return...")
            continue
            
        if not formula:
            continue

        channels_in_formula = re.findall(r'\[([^\]]+)\]', formula)
        if not channels_in_formula:
            print("  [!] No channels detected. Make sure to use [Brackets] around channel names.")
            input("\nPress Enter to try again...")
            continue

        try:
            inp = input("Enter window (e.g., '142-316', 'fl' for full lap, or 'fs' for full stint): ").strip().lower()
            
            is_full_lap = False
            is_full_stint = False
            if inp == 'fl':
                is_full_lap = True
                start_m, end_m = 0.0, 0.0 # placeholders
            elif inp == 'fs':
                is_full_stint = True
                start_m, end_m = 0.0, 0.0 # placeholders
            elif '-' not in inp:
                print("[!] Invalid format. Use 'Start-End', 'fl', or 'fs'.")
                input("\nPress Enter to try again...")
                continue
            else:
                start_m, end_m = map(float, inp.split('-'))
            
            for session in sessions:
                data = session['data']
                channels = session['channels']
                file_path = session['file_path']
                
                print(f"\nAnalyzing: {os.path.basename(file_path)}")
                print_session_metadata(data, channels, session.get('metadata', {}))
                
                missing = [ch for ch in channels_in_formula if ch not in data]
                if missing:
                    print(f"  [!] Missing channels in this file: {missing}")
                    continue
                
                lap_arr = data[channels['lap']].data
                dist_arr = data[channels['dist']].data
                time_arr = data[channels['time']].data
                
                fastest_lap = None
                
                if is_full_stint:
                    # Use time for the X-axis across the whole stint
                    x_data = time_arr
                    x_label = "Time (s)"
                    title_scope = "Full Stint"
                    
                    local_vars = {}
                    eval_str = formula
                    for i, ch_name in enumerate(channels_in_formula):
                        var_name = f"var_{i}"
                        local_vars[var_name] = data[ch_name].data
                        eval_str = eval_str.replace(f"[{ch_name}]", var_name)
                        
                else:
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
                    x_label = "Distance (m)"
                    title_scope = f"Lap {int(fastest_lap)} | {start_m}m to {end_m}m"
                    
                    # Evaluate formula
                    local_vars = {}
                    eval_str = formula
                    for i, ch_name in enumerate(channels_in_formula):
                        var_name = f"var_{i}"
                        local_vars[var_name] = data[ch_name].data[idx][mask]
                        eval_str = eval_str.replace(f"[{ch_name}]", var_name)
                
                try:
                    y_data = eval(eval_str, {"np": np, "abs": abs, "max": max, "min": min}, local_vars)
                    
                    # If the formula was just a constant or single value, broadcast it
                    if not isinstance(y_data, np.ndarray):
                        y_data = np.full_like(x_data, y_data)
                except Exception as e:
                    print(f"  [!] Math Error: {e}")
                    continue
                
                prompt_scope = "Full Stint" if is_full_stint else f"Lap {int(fastest_lap)}"
                ans = input(f"\n  Launch Custom Math Graph for {prompt_scope}? (y/n): ").strip().lower()
                if ans == 'y':
                    print("  [+] Building custom interactive graph... (Close the window to continue)")
                    gui_mode = get_gui_mode()
                    if gui_mode == 2:
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=x_data, y=y_data, mode='lines', line=dict(color='cyan', width=2), name='Custom Math'))
                        
                        fig.update_layout(
                            title=f"Custom Sandbox: {formula}<br>{title_scope}<br>{os.path.basename(file_path)}",
                            xaxis_title=x_label,
                            yaxis_title="Result",
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
                        fig = plt.figure(figsize=(12, 7), num='OpenDAV - Custom Sandbox Graph')
    
                        plt.plot(x_data, y_data, color='cyan', linewidth=2, label='Custom Math')
                        
                        plt.title(f"Custom Sandbox: {formula}\n{title_scope}\n{os.path.basename(file_path)}", fontsize=16, fontweight='bold', pad=20)
                        plt.xlabel(x_label, fontsize=13)
                        plt.ylabel("Result", fontsize=13)
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
                        
                        if gui_mode == 3:
                            show_ctk_graph(fig, "OpenDAV - Custom Sandbox Graph")
                        else:
                            plt.show()

        except ValueError:
            print("[!] Please enter valid numbers.")
            input("\nPress Enter to try again...")
        except KeyboardInterrupt:
            sys.exit(0)
