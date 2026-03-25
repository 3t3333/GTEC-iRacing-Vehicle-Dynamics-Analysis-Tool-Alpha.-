import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ui.splash as splash
from ui.graphing import show_ctk_graph
from core.config import get_gui_mode

def run_rake_analysis(sessions):
    while True:
        splash.print_header("Dynamic Aero/Rake Analyzer")
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            print(f"\nAnalyzing: {os.path.basename(file_path)}")
            
            # Find speed channel
            speed_ch = None
            for ch in ['Speed', 'Ground Speed']:
                if ch in data:
                    speed_ch = ch
                    break
                    
            if not speed_ch:
                print("  [!] Could not find Speed channel.")
                continue

            # Ride height channels
            fl_ch, fr_ch = 'Ride Height FL', 'Ride Height FR'
            rl_ch, rr_ch = 'Ride Height RL', 'Ride Height RR'
            
            required = [fl_ch, fr_ch, rl_ch, rr_ch]
            missing = [ch for ch in required if ch not in data]
            if missing:
                print(f"  [!] Missing required channels: {missing}")
                continue
                
            # Lat/Long G to filter
            lat_g_ch, long_g_ch = None, None
            for ch in ['G Force Lat', 'LatAccel', 'LatG']:
                if ch in data: lat_g_ch = ch; break
            for ch in ['G Force Long', 'LongAccel', 'LongG']:
                if ch in data: long_g_ch = ch; break

            if not lat_g_ch or not long_g_ch:
                print("  [!] Missing G channels for filtering.")
                continue

            # Convert speed to mph
            max_speed_raw = np.max(data[speed_ch].data)
            if max_speed_raw > 150: # Assume km/h
                speed = data[speed_ch].data * 0.621371
            else: # Assume m/s
                speed = data[speed_ch].data * 2.23694
                
            fl = data[fl_ch].data * 1000
            fr = data[fr_ch].data * 1000
            rl = data[rl_ch].data * 1000
            rr = data[rr_ch].data * 1000
            
            lat_g = data[lat_g_ch].data
            long_g = data[long_g_ch].data

            front_rh = (fl + fr) / 2.0
            rear_rh = (rl + rr) / 2.0
            rake = rear_rh - front_rh

            # Filter for straights (Lat G near 0, Long G relatively steady, not heavy braking)
            mask = (np.abs(lat_g) < 0.2) & (long_g > -0.5) & (speed > 40)
            
            if not np.any(mask):
                print("  [!] Not enough straight line data to calculate dynamic rake.")
                continue
                
            straight_speed = speed[mask]
            straight_rake = rake[mask]

            # Perform linear regression to get mm/mph
            rake_m, rake_c = np.polyfit(straight_speed, straight_rake, 1)

            print(f"  Max Speed: {np.max(speed):.1f} mph")
            
            PINK = '\033[95m'
            RESET = '\033[0m'
            print(f"  {PINK}Rake Adjustment: {rake_m:+.4f} mm/mph{RESET}")
            
            fastest_lap_info = session.get('metadata', {}).get('fastest_lap', 'N/A')
            if fastest_lap_info != 'N/A':
                print(f"  {PINK}Fastest Lap: {fastest_lap_info}{RESET}")
            
            print("\n ┌" + "─" * 39 + "┐")
            print(" │ " + "Modeled Rake at speeds:".ljust(37) + " │")
            for s in [50, 100, 150, np.max(speed)]:
                r = rake_m * s + rake_c
                if s == np.max(speed):
                    print(" │ " + f"@ {s:3.0f} mph (Max): {r:5.1f} mm".ljust(37) + " │")
                else:
                    print(" │ " + f"@ {s:3} mph:       {r:5.1f} mm".ljust(37) + " │")
            print(" └" + "─" * 39 + "┘")
            
            # Interactive Graphing Feature
            ans = input("\n  Launch interactive scatter plot for this session? (y/n): ").strip().lower()
            if ans == 'y':
                print("  [+] Building interactive graph... (Close the graph window to continue)")
                gui_mode = get_gui_mode()
                # We style it to match the splash screen aesthetic
                if gui_mode == 2:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=straight_speed, y=straight_rake, mode='markers',
                                             marker=dict(color='cyan', size=4, opacity=0.4),
                                             name='Telemetry Data'))
                    x_vals = np.array([min(straight_speed), max(straight_speed)])
                    y_vals = rake_m * x_vals + rake_c
                    fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines',
                                             line=dict(color='deeppink', width=3),
                                             name=f'Trend: {rake_m:+.4f} mm/mph'))
                    
                    fig.update_layout(
                        title=f"Dynamic Aero/Rake Correlation<br>{os.path.basename(file_path)}",
                        xaxis_title="Speed (mph)",
                        yaxis_title="Rake (mm) [Rear - Front]",
                        template="plotly_dark",
                        font=dict(family="Consolas", size=13)
                    )
                    fig.show()
                else:
                    plt.style.use('dark_background')
                    plt.rcParams['font.family'] = 'Consolas'
                    fig = plt.figure(figsize=(12, 7), num='GTEC - Dynamic Rake Analyzer')
    
                    # Scatter the raw straightaway data
                    plt.scatter(straight_speed, straight_rake, alpha=0.4, label='Telemetry Data', color='cyan', s=4)
    
                    # Plot the linear regression trend line
                    x_vals = np.array([min(straight_speed), max(straight_speed)])
                    y_vals = rake_m * x_vals + rake_c
                    plt.plot(x_vals, y_vals, color='deeppink', linewidth=1, label=f'Trend: {rake_m:+.4f} mm/mph')
    
                    # Styling
                    plt.title(f"Dynamic Aero/Rake Correlation\n{os.path.basename(file_path)}", fontsize=16, fontweight='bold', pad=20)
                    plt.xlabel("Speed (mph)", fontsize=13)
                    plt.ylabel("Rake (mm) [Rear - Front]", fontsize=13)
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
                        show_ctk_graph(fig, "GTEC - Dynamic Rake Analyzer")
                    else:
                        plt.show()
        print("\n" + "═"*64)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break
