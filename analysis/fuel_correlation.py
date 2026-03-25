import os
import sys
import numpy as np
import ui.splash as splash

def run_fuel_analysis(sessions):
    while True:
        splash.print_header("Fuel & Setup Correlation Analysis")
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            channels = session['channels']
            print(f"\nAnalyzing: {os.path.basename(file_path)}")
            
            # Find Fuel Channel
            fuel_ch = next((ch for ch in ['Fuel Level', 'FuelLevel'] if ch in data), None)
            if not fuel_ch:
                print("  [!] Missing Fuel Level channel.")
                continue

            # Find Tire Temp Channels
            fl_t_chs = [ch for ch in ['Tyre Temp FL Inner', 'Tyre Temp FL Centre', 'Tyre Temp FL Outer', 'LFtempL', 'LFtempM', 'LFtempR'] if ch in data]
            fr_t_chs = [ch for ch in ['Tyre Temp FR Inner', 'Tyre Temp FR Centre', 'Tyre Temp FR Outer', 'RFtempL', 'RFtempM', 'RFtempR'] if ch in data]
            rl_t_chs = [ch for ch in ['Tyre Temp RL Inner', 'Tyre Temp RL Centre', 'Tyre Temp RL Outer', 'LRtempL', 'LRtempM', 'LRtempR'] if ch in data]
            rr_t_chs = [ch for ch in ['Tyre Temp RR Inner', 'Tyre Temp RR Centre', 'Tyre Temp RR Outer', 'RRtempL', 'RRtempM', 'RRtempR'] if ch in data]

            lap_arr = data[channels['lap']].data
            time_arr = data[channels['time']].data
            laps = np.unique(lap_arr)
            lap_data = []

            for lap in laps:
                idx = np.where(lap_arr == lap)[0]
                if len(idx) < 100: continue
                lap_time = time_arr[idx][-1] - time_arr[idx][0]
                
                start_idx = idx[0]
                end_idx = idx[-1]
                
                start_fuel = data[fuel_ch].data[start_idx]
                end_fuel = data[fuel_ch].data[end_idx]
                fuel_used = start_fuel - end_fuel

                # Calculate avg start temp across all 4 tires (if available)
                start_temps = []
                for t_chs in [fl_t_chs, fr_t_chs, rl_t_chs, rr_t_chs]:
                    if t_chs:
                        # Average of Inner, Centre, Outer for this tire at the start index
                        tire_start_temp = np.mean([data[ch].data[start_idx] for ch in t_chs])
                        start_temps.append(tire_start_temp)
                
                avg_start_temp = np.mean(start_temps) if start_temps else 0

                lap_data.append({
                    'lap': int(lap),
                    'time': lap_time,
                    'start_fuel': start_fuel,
                    'fuel_used': fuel_used,
                    'start_temp': avg_start_temp
                })

            if not lap_data:
                print("  [!] No valid lap data found.")
                continue

            # Filter out in/out laps using median time
            median_time = np.median([ld['time'] for ld in lap_data])
            valid_laps = [ld for ld in lap_data if median_time * 0.89 <= ld['time'] <= median_time * 1.11]

            if not valid_laps:
                print("  [!] Not enough valid laps for analysis.")
                continue

            # Identify the top 3 fastest laps
            sorted_valid = sorted(valid_laps, key=lambda x: x['time'])
            fastest_laps = sorted_valid[:3]
            fastest_lap_nums = [ld['lap'] for ld in fastest_laps]

            avg_fuel_use = np.mean([ld['fuel_used'] for ld in valid_laps])

            print("\n ┌" + "─" * 39 + "┐")
            print(" │ " + "[ STINT OVERVIEW ]".ljust(37) + " │")
            print(" │ " + f"Valid Laps: {len(valid_laps)}".ljust(37) + " │")
            print(" │ " + f"Avg Fuel Use Per Lap: {avg_fuel_use:.2f} L".ljust(37) + " │")
            print(" └" + "─" * 39 + "┘")
            
            GOLD = '\033[33m'
            RESET = '\033[0m'
            
            print("\n  [ LAP-BY-LAP CORRELATION ]")
            print(f"  {'Lap':<5} | {'Time (s)':<10} | {'Fuel Used':<10} | {'Start Fuel':<12} | {'Start Temp':<10}")
            print("  " + "─" * 65)

            for ld in valid_laps:
                is_fastest = ld['lap'] in fastest_lap_nums
                row_color = GOLD if is_fastest else ""
                reset_color = RESET if is_fastest else ""
                
                print(f"  {row_color}{ld['lap']:<5} | {ld['time']:<10.3f} | {ld['fuel_used']:<8.2f} L | {ld['start_fuel']:<10.2f} L | {ld['start_temp']:<8.1f} °C{reset_color}")

        print("\n" + "═"*64)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break
