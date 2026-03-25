import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import ui.splash as splash
from ui.graphing import show_ctk_graph
from core.config import get_gui_mode

def run_tire_analysis(sessions):
    while True:
        splash.print_header("Tire Temperature & Pressure Analysis")
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            channels = session['channels']
            print(f"\nAnalyzing: {os.path.basename(file_path)}")
            
            # Find Tire Temp Channels
            fl_t_chs = [ch for ch in ['Tyre Temp FL Inner', 'Tyre Temp FL Centre', 'Tyre Temp FL Outer', 'LFtempL', 'LFtempM', 'LFtempR'] if ch in data]
            fr_t_chs = [ch for ch in ['Tyre Temp FR Inner', 'Tyre Temp FR Centre', 'Tyre Temp FR Outer', 'RFtempL', 'RFtempM', 'RFtempR'] if ch in data]
            rl_t_chs = [ch for ch in ['Tyre Temp RL Inner', 'Tyre Temp RL Centre', 'Tyre Temp RL Outer', 'LRtempL', 'LRtempM', 'LRtempR'] if ch in data]
            rr_t_chs = [ch for ch in ['Tyre Temp RR Inner', 'Tyre Temp RR Centre', 'Tyre Temp RR Outer', 'RRtempL', 'RRtempM', 'RRtempR'] if ch in data]
            
            # Find Tire Pressure Channels
            fl_p_ch = next((ch for ch in ['Tyre Pres FL', 'LFpressure', 'dpLFTireColdPress'] if ch in data), None)
            fr_p_ch = next((ch for ch in ['Tyre Pres FR', 'RFpressure', 'dpRFTireColdPress'] if ch in data), None)
            rl_p_ch = next((ch for ch in ['Tyre Pres RL', 'LRpressure', 'dpLRTireColdPress'] if ch in data), None)
            rr_p_ch = next((ch for ch in ['Tyre Pres RR', 'RRpressure', 'dpRRTireColdPress'] if ch in data), None)

            if not (fl_t_chs and fr_t_chs and rl_t_chs and rr_t_chs):
                print("  [!] Missing required tire temperature channels.")
                continue

            lap_arr = data[channels['lap']].data
            time_arr = data[channels['time']].data
            laps = np.unique(lap_arr)
            lap_data = []

            def get_temp_stats(chs, idx):
                temps = np.mean([data[ch].data[idx] for ch in chs], axis=0)
                return np.mean(temps), np.max(temps)

            for lap in laps:
                idx = np.where(lap_arr == lap)[0]
                if len(idx) < 100: continue
                lap_time = time_arr[idx][-1] - time_arr[idx][0]
                
                fl_t_avg, fl_t_peak = get_temp_stats(fl_t_chs, idx)
                fr_t_avg, fr_t_peak = get_temp_stats(fr_t_chs, idx)
                rl_t_avg, rl_t_peak = get_temp_stats(rl_t_chs, idx)
                rr_t_avg, rr_t_peak = get_temp_stats(rr_t_chs, idx)

                avg_temp = np.mean([fl_t_avg, fr_t_avg, rl_t_avg, rr_t_avg])
                peak_temp = np.max([fl_t_peak, fr_t_peak, rl_t_peak, rr_t_peak])
                
                fl_p = np.mean(data[fl_p_ch].data[idx]) if fl_p_ch else 0
                fr_p = np.mean(data[fr_p_ch].data[idx]) if fr_p_ch else 0
                rl_p = np.mean(data[rl_p_ch].data[idx]) if rl_p_ch else 0
                rr_p = np.mean(data[rr_p_ch].data[idx]) if rr_p_ch else 0
                
                avg_press = np.mean([fl_p, fr_p, rl_p, rr_p])
                if avg_press > 100:  # Assuming kPa and converting to psi
                    avg_press *= 0.145038

                lap_data.append({
                    'lap': int(lap),
                    'time': lap_time,
                    'avg_temp': avg_temp,
                    'peak_temp': peak_temp,
                    'avg_press': avg_press
                })

            if not lap_data:
                print("  [!] No valid lap data found.")
                continue

            # Identify valid laps
            median_time = np.median([ld['time'] for ld in lap_data])
            valid_laps = [ld for ld in lap_data if median_time * 0.89 <= ld['time'] <= median_time * 1.11]

            if not valid_laps:
                print("  [!] Not enough valid laps to determine optimal settings.")
                continue

            valid_laps.sort(key=lambda x: x['time'])
            fastest_lap = valid_laps[0]

            PINK = '\033[95m'
            RESET = '\033[0m'
            
            print("\n ┌" + "─" * 49 + "┐")
            print(" │ " + f"{PINK}[ OPTIMAL SETUP (Based on fastest lap {fastest_lap['lap']}) ]{RESET}".ljust(47 + len(PINK) + len(RESET)) + " │")
            print(" │ " + f"Fastest Time:     {fastest_lap['time']:.3f} s".ljust(47) + " │")
            print(" │ " + f"Optimal Avg Temp: {fastest_lap['avg_temp']:.1f}°C".ljust(47) + " │")
            print(" │ " + f"Optimal Peak Temp:{fastest_lap['peak_temp']:.1f}°C".ljust(47) + " │")
            print(" │ " + f"Optimal Avg Press:{fastest_lap['avg_press']:.1f} psi".ljust(47) + " │")
            print(" └" + "─" * 49 + "┘")

            print("\n  [ TEMPERATURE SPREAD ACROSS ALL LAPS ]")
            print(f"  {'Lap':<5} | {'Time (s)':<10} | {'Avg Temp':<10} | {'Peak Temp':<10} | {'Avg Press':<10}")
            print("  " + "─" * 60)
            
            times = [ld['time'] for ld in valid_laps]
            min_t, max_t = min(times), max(times)
            range_t = max_t - min_t if max_t != min_t else 1

            for ld in valid_laps:
                ratio = (ld['time'] - min_t) / range_t
                if ratio < 0.33:
                    color = '\033[92m' # Green
                elif ratio < 0.66:
                    color = '\033[93m' # Yellow
                else:
                    color = '\033[91m' # Red
                
                print(f"  {color}{ld['lap']:<5} | {ld['time']:<10.3f} | {ld['avg_temp']:<8.1f}°C | {ld['peak_temp']:<8.1f}°C | {ld['avg_press']:<8.1f} psi{RESET}")

        print("\n" + "═"*64)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break

def run_sector_tire_analysis(sessions):
    while True:
        splash.print_header("Sector Tire Temp Performance Graph")
        
        try:
            inp = input("\nEnter window (e.g., '142-316' or 'fl' for full lap), 'p' for Tools Menu, or 'q' to quit: ").strip().lower()
            if inp == 'q':
                splash.show_exit_screen()
                sys.exit(0)
            if inp == 'p':
                break
            
            is_full_lap = False
            if inp == 'fl':
                is_full_lap = True
                start_m, end_m = 0.0, 0.0 # placeholders
            elif '-' not in inp:
                print("[!] Invalid format. Use 'Start-End' or 'fl'.")
                input("\nPress Enter to try again...")
                continue
            else:
                start_m, end_m = map(float, inp.split('-'))
            
            for session in sessions:
                data = session['data']
                channels = session['channels']
                file_path = session['file_path']
                
                print(f"\nAnalyzing: {os.path.basename(file_path)}")
                
                # Find Tire Temp Channels
                fl_t_chs = [ch for ch in ['Tyre Temp FL Inner', 'Tyre Temp FL Centre', 'Tyre Temp FL Outer', 'LFtempL', 'LFtempM', 'LFtempR'] if ch in data]
                fr_t_chs = [ch for ch in ['Tyre Temp FR Inner', 'Tyre Temp FR Centre', 'Tyre Temp FR Outer', 'RFtempL', 'RFtempM', 'RFtempR'] if ch in data]
                rl_t_chs = [ch for ch in ['Tyre Temp RL Inner', 'Tyre Temp RL Centre', 'Tyre Temp RL Outer', 'LRtempL', 'LRtempM', 'LRtempR'] if ch in data]
                rr_t_chs = [ch for ch in ['Tyre Temp RR Inner', 'Tyre Temp RR Centre', 'Tyre Temp RR Outer', 'RRtempL', 'RRtempM', 'RRtempR'] if ch in data]
                
                all_t_chs = fl_t_chs + fr_t_chs + rl_t_chs + rr_t_chs
                
                if not all_t_chs:
                    print("  [!] Missing required tire temperature channels.")
                    continue

                lap_arr = data[channels['lap']].data
                dist_arr = data[channels['dist']].data
                time_arr = data[channels['time']].data
                
                if is_full_lap:
                    start_m = 0.0
                    end_m = float(np.max(dist_arr))
                laps = np.unique(lap_arr)
                lap_data = []

                for lap in laps:
                    idx = np.where(lap_arr == lap)[0]
                    if len(idx) < 100: continue
                    
                    l_dist = dist_arr[idx]
                    
                    # Window Mask
                    mask = (l_dist >= start_m) & (l_dist <= end_m)
                    if not np.any(mask): continue
                    
                    w_time = time_arr[idx][mask]
                    duration = w_time[-1] - w_time[0]
                    
                    # Get average tire temperature in the sector across all available sensors
                    temps = []
                    for ch in all_t_chs:
                        ch_data = data[ch].data[idx][mask]
                        temps.append(np.mean(ch_data))
                    
                    avg_temp = np.mean(temps)
                    lap_data.append({
                        'lap': int(lap),
                        'time': duration,
                        'temp': avg_temp
                    })

                if not lap_data:
                    print("  [!] No valid data found for that window.")
                    continue

                # Identify valid laps (filter out heavy traffic/spins)
                median_time = np.median([ld['time'] for ld in lap_data])
                valid_laps = [ld for ld in lap_data if median_time * 0.85 <= ld['time'] <= median_time * 1.15]

                if len(valid_laps) < 3:
                    print("  [!] Not enough valid laps to build a correlation graph.")
                    continue

                temps = np.array([ld['temp'] for ld in valid_laps])
                times = np.array([ld['time'] for ld in valid_laps])
                
                print(f"  [+] Found {len(valid_laps)} valid laps. Ready to graph.")

                ans = input(f"\n  Launch interactive scatter plot for {os.path.basename(file_path)}? (y/n): ").strip().lower()
                if ans == 'y':
                    print("  [+] Building interactive graph... (Close the graph window to continue)")
                    gui_mode = get_gui_mode()
                    if gui_mode == 2:
                        fig = go.Figure()
                        
                        fig.add_trace(go.Scatter(x=temps, y=times, mode='markers',
                                                 marker=dict(color='cyan', size=10, opacity=0.8),
                                                 name='Lap Data'))
                                                 
                        # Empirical Optimal Temp
                        sorted_indices = np.argsort(times)
                        top_n = min(3, len(times))
                        fastest_laps_idx = sorted_indices[:top_n]
                        
                        emp_opt_temp = np.mean(temps[fastest_laps_idx])
                        emp_opt_time = np.mean(times[fastest_laps_idx])
                        
                        fig.add_trace(go.Scatter(x=[emp_opt_temp], y=[emp_opt_time], mode='markers',
                                                 marker=dict(color='yellow', size=20, symbol='star'),
                                                 name=f'Optimal (Top {top_n} Avg): {emp_opt_temp:.1f}°C'))
                        
                        fig.add_vline(x=emp_opt_temp, line=dict(color='yellow', dash='dot'), opacity=0.5)

                        try:
                            coeffs = np.polyfit(temps, times, 2)
                            p = np.poly1d(coeffs)
                            
                            x_curve = np.linspace(min(temps), max(temps), 100)
                            y_curve = p(x_curve)
                            
                            a, b, c = coeffs
                            eq_str = f"y = {a:.4f}x² + {b:.4f}x + {c:.4f}"
                            fig.add_trace(go.Scatter(x=x_curve, y=y_curve, mode='lines',
                                                     line=dict(color='deeppink', width=3),
                                                     name=f'Trend Fit<br>{eq_str}'))
                        except Exception as e:
                            print(f"  [!] Could not fit curve: {e}")

                        fig.update_layout(
                            title=f"Sector Tire Temp vs Performance<br>Sector: {start_m}m to {end_m}m | {os.path.basename(file_path)}",
                            xaxis_title="Average Tire Temperature (°C)",
                            yaxis_title="Sector Time (s)",
                            template="plotly_dark",
                            font=dict(family="Consolas", size=13)
                        )
                        fig.show()

                    else:
                        plt.style.use('dark_background')
                        plt.rcParams['font.family'] = 'Consolas'
                        fig = plt.figure(figsize=(12, 7), num='GTEC - Sector Tire Analysis')
    
                        # Scatter Plot
                        plt.scatter(temps, times, alpha=0.8, color='cyan', s=40, label='Lap Data')
    
                        # Empirical Optimal Temp (Average temp of the fastest laps)
                        # This finds where the car is empirically fastest, regardless of curve fit skew
                        sorted_indices = np.argsort(times)
                        top_n = min(3, len(times))  # Top 3 fastest laps
                        fastest_laps_idx = sorted_indices[:top_n]
                        
                        emp_opt_temp = np.mean(temps[fastest_laps_idx])
                        emp_opt_time = np.mean(times[fastest_laps_idx])
                        
                        plt.scatter([emp_opt_temp], [emp_opt_time], color='yellow', marker='*', s=200, zorder=5, label=f'Optimal (Top {top_n} Avg): {emp_opt_temp:.1f}°C')
                        plt.axvline(x=emp_opt_temp, color='yellow', linestyle=':', alpha=0.5)
    
                        # Polynomial Curve Fitting (Quadratic/Parabola)
                        # We still draw the curve to show the general U-shape trend
                        try:
                            coeffs = np.polyfit(temps, times, 2)
                            p = np.poly1d(coeffs)
                            
                            x_curve = np.linspace(min(temps), max(temps), 100)
                            y_curve = p(x_curve)
                            
                            a, b, c = coeffs
                            eq_str = f"y = {a:.4f}x² + {b:.4f}x + {c:.4f}"
                            plt.plot(x_curve, y_curve, color='deeppink', linewidth=2, label=f'Trend Fit\n{eq_str}')
                        except Exception as e:
                            print(f"  [!] Could not fit curve: {e}")
    
                        # Styling
                        plt.title(f"Sector Tire Temp vs Performance\nSector: {start_m}m to {end_m}m | {os.path.basename(file_path)}", fontsize=16, fontweight='bold', pad=20)
                        plt.xlabel("Average Tire Temperature (°C)", fontsize=13)
                        plt.ylabel("Sector Time (s)", fontsize=13)
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
                            show_ctk_graph(fig, "GTEC - Sector Tire Analysis")
                        else:
                            plt.show()

        except ValueError:
            print("[!] Please enter valid numbers.")
            input("\nPress Enter to try again...")
        except KeyboardInterrupt:
            sys.exit(0)
