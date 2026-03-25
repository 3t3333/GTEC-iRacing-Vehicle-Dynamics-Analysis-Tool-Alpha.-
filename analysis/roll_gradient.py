import os
import sys
import numpy as np
import ui.splash as splash

def run_roll_analysis(sessions):
    while True:
        splash.print_header("Roll Gradient Analysis")
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            print(f"\nAnalyzing: {os.path.basename(file_path)}")
            
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
                print("  [!] Not enough cornering data to calculate roll gradient.")
                continue
                
            cornering_lat_g = lat_g[mask]
            cornering_front_roll = front_roll_mm[mask]
            cornering_rear_roll = rear_roll_mm[mask]

            # Calculate Fastest Lap
            channels = session['channels']
            lap_arr = data[channels['lap']].data
            time_arr = data[channels['time']].data
            laps = np.unique(lap_arr)
            lap_times = []
            for lap in laps:
                idx = np.where(lap_arr == lap)[0]
                if len(idx) < 100: continue
                lap_times.append(time_arr[idx][-1] - time_arr[idx][0])
            
            fastest_str = ""
            if lap_times:
                median_time = np.median(lap_times)
                valid_times = [t for t in lap_times if t >= median_time * 0.89]
                if valid_times:
                    fastest_time = min(valid_times)
                    PINK = '\033[95m'
                    RESET = '\033[0m'
                    fastest_str = f"\n  {PINK}Fastest Lap: {fastest_time:.3f} s{RESET}"

            # Linear regression (y = mx + c) to find gradient
            try:
                front_m, _ = np.polyfit(cornering_lat_g, cornering_front_roll, 1)
                rear_m, _ = np.polyfit(cornering_lat_g, cornering_rear_roll, 1)
                
                total_gradient = abs(front_m) + abs(rear_m)
                if total_gradient == 0:
                    print("  [!] Calculated zero roll (is data valid?).")
                    continue
                    
                front_dist = (abs(front_m) / total_gradient) * 100
                rear_dist = (abs(rear_m) / total_gradient) * 100
                
                print(" ┌" + "─" * 39 + "┐")
                print(" │ " + f"Front Roll Gradient: {abs(front_m):.2f} mm/G".ljust(37) + " │")
                print(" │ " + f"Rear Roll Gradient:  {abs(rear_m):.2f} mm/G".ljust(37) + " │")
                print(" └" + "─" * 39 + "┘")
                print(" ┌" + "─" * 39 + "┐")
                print(" │ " + "Roll Balance (Higher % = Softer end):".ljust(37) + " │")
                print(" │ " + f"Front: {front_dist:.1f}% | Rear: {rear_dist:.1f}%".ljust(37) + " │")
                print(" └" + "─" * 39 + "┘")
                if fastest_str:
                    print(fastest_str)
            except Exception as e:
                print(f"  [!] Error calculating gradient: {e}")

        print("\n" + "═"*64)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break
