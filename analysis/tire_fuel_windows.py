import os
import sys
import re
import numpy as np
import ui.splash as splash
from ui.metadata_printer import print_session_metadata

def run_tire_fuel_windows(sessions):
    while True:
        splash.print_header("Tire & Fuel Windows")
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            channels = session['channels']
            print(f"\nAnalyzing: {os.path.basename(file_path)}")
            print_session_metadata(data, channels, session.get('metadata', {}))
            
            # Lap and Time
            if 'lap' not in channels or 'time' not in channels:
                print("  [!] Missing Lap or Time channels.")
                continue
            lap_arr = data[channels['lap']].data
            time_arr = data[channels['time']].data

            # Fuel
            fuel_ch = next((ch for ch in ['Fuel Level', 'FuelLevel'] if ch in data), None)

            # Tire Temps
            fl_t_chs = [ch for ch in ['Tyre Temp FL Inner', 'Tyre Temp FL Centre', 'Tyre Temp FL Outer', 'LFtempL', 'LFtempM', 'LFtempR'] if ch in data]
            fr_t_chs = [ch for ch in ['Tyre Temp FR Inner', 'Tyre Temp FR Centre', 'Tyre Temp FR Outer', 'RFtempL', 'RFtempM', 'RFtempR'] if ch in data]
            rl_t_chs = [ch for ch in ['Tyre Temp RL Inner', 'Tyre Temp RL Centre', 'Tyre Temp RL Outer', 'LRtempL', 'LRtempM', 'LRtempR'] if ch in data]
            rr_t_chs = [ch for ch in ['Tyre Temp RR Inner', 'Tyre Temp RR Centre', 'Tyre Temp RR Outer', 'RRtempL', 'RRtempM', 'RRtempR'] if ch in data]

            # Tire Pressures
            fl_p_ch = next((ch for ch in ['Tyre Pres FL', 'LFpressure', 'dpLFTireColdPress'] if ch in data), None)
            fr_p_ch = next((ch for ch in ['Tyre Pres FR', 'RFpressure', 'dpRFTireColdPress'] if ch in data), None)
            rl_p_ch = next((ch for ch in ['Tyre Pres RL', 'LRpressure', 'dpLRTireColdPress'] if ch in data), None)
            rr_p_ch = next((ch for ch in ['Tyre Pres RR', 'RRpressure', 'dpRRTireColdPress'] if ch in data), None)

            # Laps calc
            laps = np.unique(lap_arr)
            lap_times = []
            for lap in laps:
                idx = np.where(lap_arr == lap)[0]
                if len(idx) < 100: continue
                lap_time = time_arr[idx][-1] - time_arr[idx][0]
                lap_times.append((lap, lap_time, idx))

            if not lap_times:
                print("  [!] No valid laps found.")
                continue

            median_time = np.median([t[1] for t in lap_times])
            valid_laps = [t for t in lap_times if median_time * 0.89 <= t[1] <= median_time * 1.11]

            if not valid_laps:
                print("  [!] No laps within valid time threshold.")
                continue

            fastest_lap, fastest_time, f_idx = min(valid_laps, key=lambda x: x[1])

            # Calcs
            start_fuel = "N/A"
            if fuel_ch:
                start_fuel = f"{data[fuel_ch].data[f_idx][0]:.2f} L"

            def get_avg_temp(chs):
                if not chs: return "N/A"
                temps = []
                for ch in chs:
                    temps.extend(data[ch].data[f_idx])
                return f"{np.mean(temps):.1f} °C"

            def get_avg_press(ch):
                if not ch: return "N/A"
                val = np.mean(data[ch].data[f_idx])
                if 'kPa' in data[ch].unit or 'kpa' in data[ch].unit.lower() or val > 100:
                    val *= 0.145038
                return f"{val:.1f} psi"

            avg_t_fl = get_avg_temp(fl_t_chs)
            avg_t_fr = get_avg_temp(fr_t_chs)
            avg_t_rl = get_avg_temp(rl_t_chs)
            avg_t_rr = get_avg_temp(rr_t_chs)

            avg_p_fl = get_avg_press(fl_p_ch)
            avg_p_fr = get_avg_press(fr_p_ch)
            avg_p_rl = get_avg_press(rl_p_ch)
            avg_p_rr = get_avg_press(rr_p_ch)

            PINK = '\033[95m'
            CYAN = '\033[96m'
            GOLD = '\033[38;2;255;215;0m'
            RESET = '\033[0m'

            # 1. Primary Window Box
            print("\n ┌" + "─" * 49 + "┐")
            print(" │ " + f"[ TIRE & FUEL WINDOWS ]".ljust(47) + " │")
            print(" │ " + f"Fastest Lap:  {GOLD}Lap {int(fastest_lap)}{RESET} ({fastest_time:.3f} s)".ljust(47 + len(GOLD) + len(RESET)) + " │")
            print(" │ " + f"Start Fuel:   {start_fuel}".ljust(47) + " │")
            print(" ├" + "─" * 49 + "┤")
            print(" │ " + f"{CYAN}Average Tire Temperatures{RESET}".ljust(47 + len(CYAN) + len(RESET)) + " │")
            print(" │ " + f"  FL: {avg_t_fl:<10} | FR: {avg_t_fr}".ljust(47) + " │")
            print(" │ " + f"  RL: {avg_t_rl:<10} | RR: {avg_t_rr}".ljust(47) + " │")
            print(" ├" + "─" * 49 + "┤")
            print(" │ " + f"{CYAN}Average Tire Pressures{RESET}".ljust(47 + len(CYAN) + len(RESET)) + " │")
            print(" │ " + f"  FL: {avg_p_fl:<10} | FR: {avg_p_fr}".ljust(47) + " │")
            print(" │ " + f"  RL: {avg_p_rl:<10} | RR: {avg_p_rr}".ljust(47) + " │")
            print(" └" + "─" * 49 + "┘")

            # 2. Detailed Stint & Correlation (Merging old logic)
            stint_data = []
            corner_stats = {'FL': [], 'FR': [], 'RL': [], 'RR': []}
            
            for lap, l_time, l_idx in valid_laps:
                ld = {'lap': lap, 'time': l_time}

                # Fuel Used
                if fuel_ch:
                    f_start = data[fuel_ch].data[l_idx][0]
                    f_end = data[fuel_ch].data[l_idx][-1]
                    ld['fuel_used'] = f_start - f_end
                    ld['start_fuel'] = f_start
                else:
                    ld['fuel_used'] = 0.0
                    ld['start_fuel'] = 0.0

                # Avg Temp and Per-Corner Stats
                lap_all_temps = []
                for c_name, chs in [('FL', fl_t_chs), ('FR', fr_t_chs), ('RL', rl_t_chs), ('RR', rr_t_chs)]:
                    c_vals = []
                    for ch in chs:
                        c_vals.extend(data[ch].data[l_idx])
                    if c_vals:
                        corner_stats[c_name].extend(c_vals)
                        lap_all_temps.extend(c_vals)
                
                ld['avg_temp'] = np.mean(lap_all_temps) if lap_all_temps else 0.0
                stint_data.append(ld)

            avg_fuel_per_lap = np.mean([ld['fuel_used'] for ld in stint_data]) if fuel_ch else 0.0

            # Calculate Final Corner Summary
            final_corner_readout = []
            for c_name in ['FL', 'FR', 'RL', 'RR']:
                vals = corner_stats[c_name]
                if vals:
                    readout = f"{c_name}: [{np.min(vals):>4.1f} to {np.max(vals):>4.1f} C] Avg: {np.mean(vals):.1f} C"
                else:
                    readout = f"{c_name}: [DATA MISSING]"
                final_corner_readout.append(readout)

            print("\n ┌" + "─" * 49 + "┐")
            print(" │ " + "[ STINT OVERVIEW ]".ljust(47) + " │")
            print(" │ " + f"Valid Laps: {len(stint_data)}".ljust(47) + " │")
            print(" │ " + f"Avg Fuel Use Per Lap: {avg_fuel_per_lap:.2f} L".ljust(47) + " │")
            print(" └" + "─" * 49 + "┘")

            # 3. Side-by-Side Table Layout
            print("\n  [ LAP-BY-LAP CORRELATION ]".ljust(68) + "[ TIRE STINT PERFORMANCE ]")
            print("  " + "─" * 65 + "   " + "─" * 45)
            
            # Prepare rows for both sides
            left_rows = []
            for ld in stint_data:
                row_color = GOLD if ld['lap'] == fastest_lap else ""
                reset_color = RESET if ld['lap'] == fastest_lap else ""
                fuel_used_str = f"{ld['fuel_used']:.2f} L" if fuel_ch else "N/A"
                start_fuel_str = f"{ld['start_fuel']:.2f} L" if fuel_ch else "N/A"
                temp_str = f"{ld['avg_temp']:.1f} °C" if ld['avg_temp'] > 0 else "N/A"
                left_rows.append(f"{row_color}{int(ld['lap']):<5} | {ld['time']:<10.3f} | {fuel_used_str:<10} | {start_fuel_str:<12} | {temp_str:<10}{reset_color}")

            # Combine them
            max_rows = max(len(left_rows), len(final_corner_readout) + 1)
            header_left = f"{'Lap':<5} | {'Time (s)':<10} | {'Fuel Used':<10} | {'Start Fuel':<12} | {'Avg Temp':<10}"
            
            # Print Headers
            print(f"  {header_left:<66}   Summary (Min/Max/Avg):")
            
            for i in range(max_rows):
                l_part = left_rows[i] if i < len(left_rows) else " " * 65
                r_part = final_corner_readout[i-1] if (0 < i <= len(final_corner_readout)) else ""
                
                # Check for color codes in l_part when calculating padding
                raw_l_len = len(re.sub(r'\033\[[0-9;]*m', '', l_part))
                padding = 68 - raw_l_len
                print(f"  {l_part}{' ' * padding}{r_part}")

        print("\n" + "─"*100)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break