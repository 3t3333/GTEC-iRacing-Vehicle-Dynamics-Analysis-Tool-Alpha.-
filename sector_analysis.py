import sys
import os
import numpy as np

sys.path.insert(0, os.path.abspath('ldparser'))
from ldparser import ldData

def main():
    file_path = "Fastlap.ld"
    print(f"Loading {file_path}...\n")
    data = ldData.fromfile(file_path)
    
    lap_ch = 'Lap' if 'Lap' in data else 'Lap Number'
    dist_ch = 'LapDist' if 'LapDist' in data else 'Lap Distance'
    time_ch = 'SessionTime'
    
    if lap_ch not in data or dist_ch not in data or time_ch not in data:
        print("Missing required channels.")
        return
        
    lap_data = data[lap_ch].data
    dist_data = data[dist_ch].data
    time_data = data[time_ch].data
    
    # Hockenheim GP standard sector splits based on track length 4574m
    s1_dist = 1041.0
    s2_dist = 1041.0 + 2142.0  # 3183.0
    
    laps = np.unique(lap_data)
    
    print("--- Hockenheim GP Sector Report ---")
    print("S1 Ends: 1041m | S2 Ends: 3183m | S3 Ends: ~4574m\n")
    print(f"{'Lap':<5} | {'Sector 1':<10} | {'Sector 2':<10} | {'Sector 3':<10} | {'Lap Time':<10}")
    print("-" * 57)
    
    def fmt_time(t):
        if t >= 60:
            m = int(t // 60)
            s = t % 60
            return f"{m}:{s:06.3f}"
        return f"{t:06.3f}"

    for lap in laps:
        idx = np.where(lap_data == lap)[0]
        if len(idx) < 60: # less than 1 sec of data, skip
            continue
            
        # Ensure lap_dist is strictly increasing for interpolation
        lap_dist = dist_data[idx]
        lap_time = time_data[idx]
        
        # Simple check for completeness (is lap > 4500m?)
        if lap_dist[-1] < 4500:
            continue
            
        # To avoid ValueError in np.interp, make sure x is increasing
        # Sometime telemetry drops or pauses, we can just use the first index where dist > threshold
        try:
            # Find exact start time (when dist > 0)
            start_idx = np.argmax(lap_dist >= 0)
            t_start = lap_time[start_idx]
            
            # Find S1 time (when dist >= s1_dist)
            s1_idx = np.argmax(lap_dist >= s1_dist)
            t_s1 = lap_time[s1_idx]
            
            # Find S2 time (when dist >= s2_dist)
            s2_idx = np.argmax(lap_dist >= s2_dist)
            t_s2 = lap_time[s2_idx]
            
            # End time is the last point of the lap before Lap variable changes
            t_end = lap_time[-1]
            
            s1_time = t_s1 - t_start
            s2_time = t_s2 - t_s1
            s3_time = t_end - t_s2
            total_time = t_end - t_start
            
            # Check if lap was invalid or an out lap starting midway
            if t_start == 0 and start_idx != 0:
                continue
                
            print(f"{int(lap):<5} | {fmt_time(s1_time):<10} | {fmt_time(s2_time):<10} | {fmt_time(s3_time):<10} | {fmt_time(total_time):<10}")
        except Exception as e:
            pass

if __name__ == "__main__":
    main()
