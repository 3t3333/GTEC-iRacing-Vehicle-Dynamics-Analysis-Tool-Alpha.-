import datetime
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ui.splash as splash
from ui.metadata_printer import print_session_metadata
from ui.graphing import show_ctk_graph
from core.config import get_gui_mode

def run_tire_energy_profiler(sessions, headless=False, headless_config=None):
    while True:
        splash.print_header("Tire Energy & Work Profiler")
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            channels = session['channels']
            print(f"\nAnalyzing: {os.path.basename(file_path)}")
            print_session_metadata(data, channels, session.get('metadata', {}))
            
            # Find required channels
            lat_g_ch = channels.get('lat')
            long_g_ch = channels.get('long')
            dist_ch = channels.get('dist')
            lap_ch = channels.get('lap')
            time_ch = channels.get('time')
            
            speed_ch = None
            for ch in ['Speed', 'Ground Speed', 'Velocity', 'virt_body_v']:
                if ch in data: speed_ch = ch; break
                
            fl_load, fr_load = 'Suspension Load FL', 'Suspension Load FR'
            rl_load, rr_load = 'Suspension Load RL', 'Suspension Load RR'

            required = [speed_ch, lat_g_ch, long_g_ch, fl_load, fr_load, rl_load, rr_load, dist_ch, lap_ch, time_ch]
            missing = [ch for ch in required if ch is None or ch not in data]
            
            if missing:
                print(f"  [!] Missing required channels for Tire Work Profiler: {missing}")
                print("\nPress Enter to return...")
                input()
                continue
                
            # Load Data
            speed_raw = data[speed_ch].data
            if np.max(speed_raw) > 150: # km/h
                speed_ms = speed_raw / 3.6
            elif np.max(speed_raw) < 100 and "m/s" in data[speed_ch].unit.lower(): # m/s
                speed_ms = speed_raw
            else: # mph ? 
                speed_ms = speed_raw * 0.44704
                
            lat_g = data[lat_g_ch].data
            long_g = data[long_g_ch].data
            combined_g = np.sqrt(lat_g**2 + long_g**2)
            
            fl_l = data[fl_load].data
            fr_l = data[fr_load].data
            rl_l = data[rl_load].data
            rr_l = data[rr_load].data
            
            dist_arr = data[dist_ch].data
            lap_arr = data[lap_ch].data
            time_arr = data[time_ch].data
            
            # Filter valid laps
            laps = np.unique(lap_arr)
            lap_times = []
            for lap in laps:
                idx = np.where(lap_arr == lap)[0]
                if len(idx) < 100: continue
                lap_times.append((lap, time_arr[idx][-1] - time_arr[idx][0], idx))
                
            if not lap_times:
                print("  [!] No valid laps found.")
                continue
                
            median_time = np.median([t[1] for t in lap_times])
            valid_laps = [t for t in lap_times if median_time * 0.89 <= t[1] <= median_time * 1.11]
            if not valid_laps:
                valid_laps = lap_times # Fallback
                
            # Find fastest lap
            fastest_lap_info = min(valid_laps, key=lambda x: x[1])
            lap_num, lap_time, lap_idx = fastest_lap_info
            
            # Proxy Work Rate (Power in kW): (Load [N] * Combined G) * Speed [m/s] / 1000
            # Note: A scaling factor is applied to keep numbers readable. 
            # In real physics, slip factor reduces this by ~90%, so we multiply by 0.1 to estimate actual tire heat generation.
            SLIP_FACTOR = 0.1 
            wr_fl = (fl_l[lap_idx] * combined_g[lap_idx] * speed_ms[lap_idx] * SLIP_FACTOR) / 1000.0
            wr_fr = (fr_l[lap_idx] * combined_g[lap_idx] * speed_ms[lap_idx] * SLIP_FACTOR) / 1000.0
            wr_rl = (rl_l[lap_idx] * combined_g[lap_idx] * speed_ms[lap_idx] * SLIP_FACTOR) / 1000.0
            wr_rr = (rr_l[lap_idx] * combined_g[lap_idx] * speed_ms[lap_idx] * SLIP_FACTOR) / 1000.0
            
            dt = np.gradient(time_arr[lap_idx])
            
            # Integral of Power over time = Energy (Joules -> kJ)
            energy_fl = np.sum(wr_fl * dt)
            energy_fr = np.sum(wr_fr * dt)
            energy_rl = np.sum(wr_rl * dt)
            energy_rr = np.sum(wr_rr * dt)
            
            total_energy = energy_fl + energy_fr + energy_rl + energy_rr
            front_pct = ((energy_fl + energy_fr) / total_energy) * 100
            rear_pct = ((energy_rl + energy_rr) / total_energy) * 100
            
            def create_bar(val, max_val, width=10):
                fill = int((val / max_val) * width)
                return "█" * fill + "-" * (width - fill)

            max_e = max(energy_fl, energy_fr, energy_rl, energy_rr)

            PINK = '\033[95m'
            CYAN = '\033[96m'
            RESET = "\033[0m"
            
            print("\n  ┌" + "─" * 98 + "┐")
            print("  │ " + f"[ TIRE ENERGY EXPENDITURE - LAP {int(lap_num)} ]".ljust(92) + " │")
            print("  │ " + f"FL: [{create_bar(energy_fl, max_e)}] {energy_fl:6.0f} kJ".ljust(92) + " │")
            print("  │ " + f"FR: [{create_bar(energy_fr, max_e)}] {energy_fr:6.0f} kJ".ljust(92) + " │")
            print("  │ " + f"RL: [{create_bar(energy_rl, max_e)}] {energy_rl:6.0f} kJ".ljust(92) + " │")
            print("  │ " + f"RR: [{create_bar(energy_rr, max_e)}] {energy_rr:6.0f} kJ".ljust(92) + " │")
            print("  │ " + f" ".ljust(92) + " │")
            print("  │ " + f"ABUSE BIAS: {CYAN}{front_pct:.1f}% Front{RESET} / {PINK}{rear_pct:.1f}% Rear{RESET}".ljust(47 + len(PINK) + len(CYAN) + len(RESET)*2) + " │")
            print("  └" + "─" * 98 + "┘")

            md = session.get('metadata', {})
            car_name = md.get('car', 'UNKNOWN')
            file_basename = os.path.basename(file_path)

            l1_preview = f"""
        L1: TIRE WORK RATE (DYNAMIC)                      TOTAL ENERGY EXPENDITURE               
 ┌─────────────────────────────────────────┐   ┌─────────────────────────────────────────┐      
 │                                         │   │ FRONT LEFT:  [████████--] 1420 kJ       │      
 │                                         │   │ FRONT RIGHT: [██████----] 1100 kJ       │      
 │                                         │   │ REAR LEFT:   [█████-----]  980 kJ       │      
 │                                         │   │ REAR RIGHT:  [███████---] 1250 kJ       │      
 │                                         │   │                                         │      
 │                                         │   │  ABUSE BIAS: 54% FRONT / 46% REAR       │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │ [X] AXIS: TRACK DISTANCE (m)            │   │ [BARS]: INTEGRAL OF WORK OVER LAP       │      
 │ [Y] AXIS: WORK RATE (kW)                │   │ [TEXT]: TOTAL JOULES ABSORBED           │      
 │ [L] LINE: FL, FR, RL, RR TIRES          │   │                                         │      
 └─────────────────────────────────────────┘   └─────────────────────────────────────────┘      
 
  FILE: {file_basename}
  VEHICLE: {car_name}
  
  >> [USE CASE]: QUANTIFY TIRE DEGRADATION AND IDENTIFY WHICH SETUP CHANGES ARE OVERWORKING SPECIFIC CORNERS."""
            print(l1_preview)

            _headless_ran = False
            while True:
                if headless:
                    if headless_config.get('_ran'): return
                    headless_config['_ran'] = True
                    ans_raw = f"print {headless_config['layout'].lower()} < {headless_config['project']}"
                else:
                    ans_raw = input(f"\n  Select action ('open L1', 'print L1 < proj', 'p' to go back): ").strip().lower()
                ans = ans_raw.split('<')[0].strip().lower()
                
                if ans == 'p':
                    break
                    
                if ans in ['open l1', 'print l1']:
                    print("  [+] Building Tire Work Profiler Graph...")
                    import matplotx
                    plt.style.use(matplotx.styles.aura['dark'])
                    plt.rcParams['font.family'] = 'Consolas'
                    
                    fig = plt.figure(figsize=(15, 8), num='OpenDAV - Tire Energy & Work Profiler')
                    gs = fig.add_gridspec(2, 2, width_ratios=[2.5, 1], height_ratios=[1, 1])
                    
                    # Left pane: Line plot over distance
                    ax_line = fig.add_subplot(gs[:, 0])
                    lap_dist = dist_arr[lap_idx]
                    
                    # Smooth the lines slightly for readability
                    window = 10
                    sm_fl = np.convolve(wr_fl, np.ones(window)/window, mode='same')
                    sm_fr = np.convolve(wr_fr, np.ones(window)/window, mode='same')
                    sm_rl = np.convolve(wr_rl, np.ones(window)/window, mode='same')
                    sm_rr = np.convolve(wr_rr, np.ones(window)/window, mode='same')
                    
                    ax_line.plot(lap_dist, sm_fl, label='Front Left', color='#2D8AE2', alpha=0.8, linewidth=1.5)
                    ax_line.plot(lap_dist, sm_fr, label='Front Right', color='#63B3ED', alpha=0.8, linewidth=1.5)
                    ax_line.plot(lap_dist, sm_rl, label='Rear Left', color='#FF1493', alpha=0.8, linewidth=1.5)
                    ax_line.plot(lap_dist, sm_rr, label='Rear Right', color='#FF69B4', alpha=0.8, linewidth=1.5)
                    
                    ax_line.set_title(f"Dynamic Tire Work Rate - Lap {int(lap_num)}", fontsize=14, pad=15)
                    ax_line.set_xlabel("Track Distance (m)", fontsize=11)
                    ax_line.set_ylabel("Est. Work Rate (kW)", fontsize=11)
                    ax_line.legend(loc='upper right')
                    ax_line.grid(True, linestyle='--', alpha=0.2)
                    
                    # Right top: Bar Chart
                    ax_bar = fig.add_subplot(gs[0, 1])
                    corners = ['FL', 'FR', 'RL', 'RR']
                    energies = [energy_fl, energy_fr, energy_rl, energy_rr]
                    colors = ['#2D8AE2', '#63B3ED', '#FF1493', '#FF69B4']
                    
                    bars = ax_bar.bar(corners, energies, color=colors, alpha=0.9)
                    ax_bar.set_title("Total Energy Expenditure (kJ)", fontsize=12, pad=10)
                    ax_bar.set_ylabel("Energy (kJ)", fontsize=10)
                    ax_bar.grid(True, axis='y', linestyle='--', alpha=0.2)
                    
                    # Add value labels
                    for bar in bars:
                        yval = bar.get_height()
                        ax_bar.text(bar.get_x() + bar.get_width()/2, yval + (max_e*0.02), f'{int(yval)}', ha='center', va='bottom', fontsize=9, color='white')

                    # Right bottom: Pie Chart (Bias)
                    ax_pie = fig.add_subplot(gs[1, 1])
                    ax_pie.pie([front_pct, rear_pct], labels=['Front', 'Rear'], colors=['#2D8AE2', '#FF1493'],
                               autopct='%1.1f%%', startangle=90, textprops={'color':"w", 'weight':'bold'})
                    ax_pie.set_title("Axle Energy Bias", fontsize=12, pad=10)

                    info_text = (f"File: {file_basename}\n"
                                 f"Car: {car_name}\n"
                                 f"Fastest Lap: {lap_time:.3f}s")
                    plt.figtext(0.02, 0.02, info_text, fontsize=9, color='white', alpha=0.8, va='bottom', ha='left',
                                bbox=dict(facecolor='#1a1a1a', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.5'))

                    plt.tight_layout()

                    if ans == 'open l1':
                        gui_mode = get_gui_mode()
                        if gui_mode == 3: show_ctk_graph(fig, "OpenDAV - Tire Energy Profiler")
                        else: plt.show()
                    else:
                        timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                        file_out = f"TireEnergy_L1_{timestamp}_{file_basename}.png"
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
                    print("  [!] Invalid command. Try 'open L1', 'print L1', or 'p'.")

        if headless: return
        print("\n" + "─"*100)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break
