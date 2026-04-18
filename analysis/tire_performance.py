import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import ui.splash as splash
from ui.metadata_printer import print_session_metadata
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
            print_session_metadata(data, channels, session.get('metadata', {}))
            
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
            
            if not (fl_t_chs or fr_t_chs or rl_t_chs or rr_t_chs):
                print("  [!] Missing required tire temperature channels.")
                continue

            def get_stats(chs):
                if not chs: return "N/A", "N/A", "N/A"
                temps = []
                for ch in chs:
                    temps.extend(data[ch].data)
                return np.min(temps), np.max(temps), np.mean(temps)

            def get_p_stats(ch):
                if not ch: return "N/A", "N/A", "N/A"
                vals = data[ch].data
                if 'kPa' in data[ch].unit or 'kpa' in data[ch].unit.lower() or np.mean(vals) > 100:
                    vals = vals * 0.145038 # convert to psi
                return np.min(vals), np.max(vals), np.mean(vals)

            fl_min, fl_max, fl_avg = get_stats(fl_t_chs)
            fr_min, fr_max, fr_avg = get_stats(fr_t_chs)
            rl_min, rl_max, rl_avg = get_stats(rl_t_chs)
            rr_min, rr_max, rr_avg = get_stats(rr_t_chs)

            fl_p_min, fl_p_max, fl_p_avg = get_p_stats(fl_p_ch)
            fr_p_min, fr_p_max, fr_p_avg = get_p_stats(fr_p_ch)
            rl_p_min, rl_p_max, rl_p_avg = get_p_stats(rl_p_ch)
            rr_p_min, rr_p_max, rr_p_avg = get_p_stats(rr_p_ch)

            PINK = '\033[95m'
            CYAN = '\033[96m'
            RESET = '\033[0m'
            
            print("\n ┌" + "─" * 58 + "┐")
            print(" │ " + "[ TIRE TEMPERATURES (°C) ]".ljust(56) + " │")
            
            def format_t_line(name, cmin, cmax, cavg):
                if cmin == "N/A": return f"{name}: [MISSING]".ljust(56)
                return f"{name}: [{cmin:>4.1f} to {cmax:>4.1f}]  Avg: {CYAN}{cavg:.1f}{RESET}".ljust(56 + len(CYAN) + len(RESET))
                
            print(" │ " + format_t_line("Front Left ", fl_min, fl_max, fl_avg) + " │")
            print(" │ " + format_t_line("Front Right", fr_min, fr_max, fr_avg) + " │")
            print(" │ " + format_t_line("Rear Left  ", rl_min, rl_max, rl_avg) + " │")
            print(" │ " + format_t_line("Rear Right ", rr_min, rr_max, rr_avg) + " │")
            print(" └" + "─" * 58 + "┘")

            if fl_p_min != "N/A":
                print(" ┌" + "─" * 58 + "┐")
                print(" │ " + "[ TIRE PRESSURES (psi) ]".ljust(56) + " │")
                
                def format_p_line(name, pmin, pmax, pavg):
                    if pmin == "N/A": return f"{name}: [MISSING]".ljust(56)
                    return f"{name}: [{pmin:>4.1f} to {pmax:>4.1f}]  Avg: {PINK}{pavg:.1f}{RESET}".ljust(56 + len(PINK) + len(RESET))
                    
                print(" │ " + format_p_line("Front Left ", fl_p_min, fl_p_max, fl_p_avg) + " │")
                print(" │ " + format_p_line("Front Right", fr_p_min, fr_p_max, fr_p_avg) + " │")
                print(" │ " + format_p_line("Rear Left  ", rl_p_min, rl_p_max, rl_p_avg) + " │")
                print(" │ " + format_p_line("Rear Right ", rr_p_min, rr_p_max, rr_p_avg) + " │")
                print(" └" + "─" * 58 + "┘")

        print("\n" + "─"*100)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break

def run_sector_tire_analysis(sessions):
    while True:
        splash.print_header("Sector Tire Temp Performance Graph")
        print("\n  This tool analyzes how cornering tire temperatures correlate with lap times.")
        print("  It plots empirical data and mathematically estimates the optimal temperature window.")
        
        print("\n  Enter track distance window (e.g. '140-300') or 'fl' for Full Lap.")
        inp = input("  Window: ").strip().lower()
        
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        if inp == 'p':
            break
            
        is_full_lap = False
        if inp == 'fl':
            is_full_lap = True
            start_m, end_m = 0, 0
        else:
            if '-' not in inp:
                print("  [!] Invalid format. Try 'Start-End' or 'fl'.")
                input("\nPress Enter to return...")
                continue
                
            try:
                start_m, end_m = map(float, inp.split('-'))
            except ValueError:
                print("  [!] Invalid format. Must be numbers.")
                input("\nPress Enter to return...")
                continue
            
        scope_text = "FULL LAP" if is_full_lap else f"SECTOR {start_m}m to {end_m}m"
            
        for session in sessions:
            data = session['data']
            channels = session['channels']
            file_path = session['file_path']
            
            print(f"\nAnalyzing: {os.path.basename(file_path)}")
            print_session_metadata(data, channels, session.get('metadata', {}))
            
            # Find Tire Temp Channels
            fl_t_chs = [ch for ch in ['Tyre Temp FL Inner', 'Tyre Temp FL Centre', 'Tyre Temp FL Outer', 'LFtempL', 'LFtempM', 'LFtempR'] if ch in data]
            fr_t_chs = [ch for ch in ['Tyre Temp FR Inner', 'Tyre Temp FR Centre', 'Tyre Temp FR Outer', 'RFtempL', 'RFtempM', 'RFtempR'] if ch in data]
            rl_t_chs = [ch for ch in ['Tyre Temp RL Inner', 'Tyre Temp RL Centre', 'Tyre Temp RL Outer', 'LRtempL', 'LRtempM', 'LRtempR'] if ch in data]
            rr_t_chs = [ch for ch in ['Tyre Temp RR Inner', 'Tyre Temp RR Centre', 'Tyre Temp RR Outer', 'RRtempL', 'RRtempM', 'RRtempR'] if ch in data]
            
            all_t_chs = fl_t_chs + fr_t_chs + rl_t_chs + rr_t_chs
            
            if not all_t_chs:
                print("  [!] Missing required tire temperature channels.")
                continue
                
            dist_arr = data[channels['dist']].data
            lap_arr = data[channels['lap']].data
            time_arr = data[channels['time']].data
            
            laps = np.unique(lap_arr)
            
            lap_metrics = [] # (lap_time, avg_sector_temp)
            
            # Get valid laps first to find median
            temp_lap_times = []
            for lap in laps:
                idx = np.where(lap_arr == lap)[0]
                if len(idx) < 100: continue
                temp_lap_times.append((lap, time_arr[idx][-1] - time_arr[idx][0], idx))
                
            if not temp_lap_times: continue
            
            median_time = np.median([t[1] for t in temp_lap_times])
            valid_laps = [t for t in temp_lap_times if median_time * 0.89 <= t[1] <= median_time * 1.11]
            
            for lap, lap_time, l_idx in valid_laps:
                l_dist = dist_arr[l_idx]
                if is_full_lap:
                    mask = np.ones_like(l_dist, dtype=bool)
                else:
                    mask = (l_dist >= start_m) & (l_dist <= end_m)
                
                if not np.any(mask): continue
                
                sector_temps = []
                for ch in all_t_chs:
                    sector_temps.extend(data[ch].data[l_idx][mask])
                    
                if sector_temps:
                    avg_temp = np.mean(sector_temps)
                    lap_metrics.append((lap_time, avg_temp))
                    
            if len(lap_metrics) < 3:
                print("  [!] Not enough valid laps to build a correlation graph.")
                continue
                
            times = np.array([m[0] for m in lap_metrics])
            temps = np.array([m[1] for m in lap_metrics])
            
            # Fit polynomial curve (Quadratic)
            coeffs = np.polyfit(temps, times, 2)
            p = np.poly1d(coeffs)
            
            # Calculate optimal temp using Derivative F'(x) = 0
            # For quadratic y = ax^2 + bx + c, the derivative is 2ax + b.
            # Setting 2ax + b = 0 gives x = -b / (2a)
            # We want the minimum lap time, which is the vertex of a U-shaped parabola (a > 0).
            if coeffs[0] > 0:
                optimal_temp = -coeffs[1] / (2 * coeffs[0])
            else:
                # If a <= 0, it's an inverted parabola. Fall back to the absolute fastest lap temp.
                optimal_temp = temps[np.argmin(times)]
            
            PINK = '\033[95m'
            RESET = '\033[0m'
            print(" ┌" + "─" * 49 + "┐")
            print(" │ " + f"[ {scope_text} PERFORMANCE ]".ljust(47) + " │")
            print(" │ " + f"Analyzed {len(lap_metrics)} valid laps.".ljust(47) + " │")
            print(" │ " + f"Calculated Optimal Temp: {PINK}{optimal_temp:.1f} °C{RESET}".ljust(47 + len(PINK) + len(RESET)) + " │")
            print(" └" + "─" * 49 + "┘")
            
            md = session.get('metadata', {})
            car_name = md.get('car', 'UNKNOWN')
            file_basename = os.path.basename(file_path)

            l3_preview = f"""
        L3: TIRE TEMP VS LAP TIME (QUADRATIC) 
 ┌─────────────────────────────────────────┐
 │                                         │
 │                                         │
 │                                         │
 │                                         │
 │                                         │
 │                                         │
 │                                         │
 │                                         │
 │                                         │
 │ [X] AXIS: AVG TIRE TEMP (°C)            │
 │ [Y] AXIS: LAP TIME (s)                  │
 │ [L] LINE: QUADRATIC TREND               │
 └─────────────────────────────────────────┘
 
  FILE: {file_basename}
  VEHICLE: {car_name}
  
  >> [USE CASE]: IDENTIFY THE THERMAL OPTIMAL WINDOW BY CORRELATING TIRE HEAT TO LAP PACING."""
            print(l3_preview)

            while True:
                ans = input(f"\n  Select action ('open L3', 'print L3', 'p' to go back): ").strip().lower()
                
                if ans == 'p':
                    break
                    
                if ans in ['open l3', 'print l3']:
                    t_min = np.min(temps) - 2
                    t_max = np.max(temps) + 2
                    t_curve = np.linspace(t_min, t_max, 100)
                    time_curve = p(t_curve)
                    
                    title_scope = f"{scope_text} Correlation"
                    
                    if ans == 'open l3':
                        print("  [+] Building correlation graph... (Close the window to continue)")
                        GUI_MODE = get_gui_mode()
                        if GUI_MODE == 2:
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=temps, y=times, mode='markers', marker=dict(size=8, color='cyan'), name='Lap Data'))
                            fig.add_trace(go.Scatter(x=t_curve, y=time_curve, mode='lines', line=dict(color='deeppink', dash='dash'), name='Trend Curve'))
                            fig.add_vline(x=optimal_temp, line_width=2, line_dash="dash", line_color="gold", annotation_text="Optimal Window")
                            fig.update_layout(
                                title=f"Tire Temperature vs Lap Time<br>{title_scope}<br>{file_basename}",
                                xaxis_title=f"Avg {scope_text.capitalize()} Tire Temp (°C)",
                                yaxis_title="Lap Time (s)",
                                template="plotly_dark",
                                font=dict(family="Consolas", size=13)
                            )
                            fig.show()
                        else:
                            import matplotx
                            plt.style.use(matplotx.styles.aura['dark'])
                            plt.rcParams['font.family'] = 'Consolas'
                            fig = plt.figure(figsize=(12, 7), num='OpenDAV - Sector Tire Analysis')
                            plt.scatter(temps, times, alpha=0.8, color='cyan', s=40, label='Lap Data')
                            plt.plot(t_curve, time_curve, color='deeppink', linestyle='--', linewidth=2, label='Performance Trend')
                            plt.axvline(x=optimal_temp, color='gold', linestyle='-', linewidth=2, label=f'Calculated Optimal ({optimal_temp:.1f}°C)')
                            plt.title(f"Tire Temperature vs Lap Time\n{title_scope}\n{file_basename}", fontsize=16, fontweight='bold', pad=20)
                            plt.xlabel(f"Average {scope_text.capitalize()} Tire Temp (°C)", fontsize=13)
                            plt.ylabel("Lap Time (s)", fontsize=13)
                            plt.xticks(fontsize=11)
                            plt.yticks(fontsize=11)
                            plt.legend(fontsize=11, frameon=True, shadow=True)
                            plt.grid(True, linestyle='--', alpha=0.3)
                            info_text = (f"Driver: {md.get('driver', 'N/A')}\n"
                                         f"Car: {md.get('car', 'N/A')}\n"
                                         f"Venue: {md.get('venue', 'N/A')}")
                            plt.figtext(0.02, 0.02, info_text, fontsize=9, color='white',
                                        alpha=0.8, va='bottom', ha='left',
                                        bbox=dict(facecolor='#1a1a1a', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.5'))
                            plt.tight_layout()
                            
                            if GUI_MODE == 3:
                                show_ctk_graph(fig, "OpenDAV - Sector Tire Analysis")
                            else:
                                plt.show()
                                
                    elif ans == 'print l3':
                        import datetime
                        print("  [+] Exporting L3 Layout...")
                        timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                        export_dir = f"exports/L3_{timestamp}"
                        os.makedirs(export_dir, exist_ok=True)
                        
                        safe_scope = scope_text.replace(' ', '_').replace('.', '_')
                        export_path = os.path.join(export_dir, f"L3_{safe_scope}_{file_basename}.png")
                        
                        import matplotx
                        plt.style.use(matplotx.styles.aura['dark'])
                        plt.rcParams['font.family'] = 'Consolas'
                        fig = plt.figure(figsize=(12, 7))
                        plt.scatter(temps, times, alpha=0.8, color='cyan', s=40, label='Lap Data')
                        plt.plot(t_curve, time_curve, color='deeppink', linestyle='--', linewidth=2, label='Performance Trend')
                        plt.axvline(x=optimal_temp, color='gold', linestyle='-', linewidth=2, label=f'Calculated Optimal ({optimal_temp:.1f}°C)')
                        plt.title(f"Tire Temperature vs Lap Time\n{title_scope}\n{file_basename}", fontsize=16, fontweight='bold', pad=20)
                        plt.xlabel(f"Average {scope_text.capitalize()} Tire Temp (°C)", fontsize=13)
                        plt.ylabel("Lap Time (s)", fontsize=13)
                        plt.xticks(fontsize=11)
                        plt.yticks(fontsize=11)
                        plt.legend(fontsize=11, frameon=True, shadow=True)
                        plt.grid(True, linestyle='--', alpha=0.3)
                        info_text = (f"Driver: {md.get('driver', 'N/A')}\n"
                                     f"Car: {md.get('car', 'N/A')}\n"
                                     f"Venue: {md.get('venue', 'N/A')}")
                        plt.figtext(0.02, 0.02, info_text, fontsize=9, color='white',
                                    alpha=0.8, va='bottom', ha='left',
                                    bbox=dict(facecolor='#1a1a1a', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.5'))
                        plt.tight_layout()
                        plt.savefig(export_path, dpi=300, bbox_inches='tight')
                        plt.close(fig)
                        print(f"  [+] Saved to {export_path}")
                else:
                    print("  [!] Invalid command. Try 'open L3', 'print L3', or 'p'.")

        print("\n" + "─"*100)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break