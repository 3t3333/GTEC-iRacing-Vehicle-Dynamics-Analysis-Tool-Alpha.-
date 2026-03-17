import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.abspath('ldparser'))
from ldparser import ldData

def main():
    file_path = "Fastlap.ld"
    print(f"Loading {file_path}...")
    data = ldData.fromfile(file_path)
    
    # Configuration
    s1_dist_threshold = 1041.0
    window_start = 142.0
    window_end = 316.0
    
    # Identify channels
    lap_ch = 'Lap' if 'Lap' in data else 'Lap Number'
    dist_ch = 'Lap Distance' if 'Lap Distance' in data else 'LapDist'
    long_g_ch = 'G Force Long' if 'G Force Long' in data else 'LongAccel'
    lat_g_ch = 'G Force Lat' if 'G Force Lat' in data else 'LatAccel'
    time_ch = 'SessionTime'
    
    lap_data = data[lap_ch].data
    dist_data = data[dist_ch].data
    long_g_data = data[long_g_ch].data
    lat_g_data = data[lat_g_ch].data
    time_data = data[time_ch].data
    
    # 1. Global Max Combined G (The limit baseline across the whole session)
    combined_g_all = np.sqrt(long_g_data**2 + lat_g_data**2)
    global_max_g = np.max(combined_g_all)
    print(f"Global Empirical Limit: {global_max_g:.3f} G\n")
    
    laps = np.unique(lap_data)
    lap_stats = []

    for lap in laps:
        idx = np.where(lap_data == lap)[0]
        if len(idx) < 100: continue # Skip partial data
        
        l_dist = dist_data[idx]
        l_time = time_data[idx]
        l_comb = combined_g_all[idx]
        
        # Calculate Sector 1 Time
        # Find start of lap
        start_idx = np.argmax(l_dist >= 0)
        t_start = l_time[start_idx]
        
        # Find end of Sector 1
        s1_end_idx_in_lap = np.argmax(l_dist >= s1_dist_threshold)
        if s1_end_idx_in_lap == 0 and l_dist[0] < s1_dist_threshold:
            continue # S1 not completed in this lap
            
        t_s1 = l_time[s1_end_idx_in_lap]
        s1_duration = t_s1 - t_start
        
        # Calculate Max Utilization in the specific window (142m - 316m)
        window_mask = (l_dist >= window_start) & (l_dist <= window_end)
        if not np.any(window_mask):
            continue
            
        window_max_g = np.max(l_comb[window_mask])
        utilization = (window_max_g / global_max_g) * 100
        
        lap_stats.append({
            'Lap': int(lap),
            'S1_Time': s1_duration,
            'Window_Util%': utilization
        })

    # Create Summary Table
    df_stats = pd.DataFrame(lap_stats)
    df_stats = df_stats.sort_values('S1_Time') # Sort by fastest S1
    
    print("--- Efficiency vs. Performance Correlation ---")
    print(f"Target Window: {window_start}m - {window_end}m")
    print("-" * 45)
    print(f"{'Lap':<5} | {'S1 Time':<10} | {'Window Max Util%':<15}")
    print("-" * 45)
    for _, row in df_stats.iterrows():
        print(f"{int(row['Lap']):<5} | {row['S1_Time']:<10.3f} | {row['Window_Util%']:<15.1f}%")

    # Quick Correlation Analysis
    correlation = df_stats['S1_Time'].corr(df_stats['Window_Util%'])
    print("-" * 45)
    print(f"Correlation (S1 Time vs. Util%): {correlation:.3f}")
    print("Note: A negative correlation means higher utilization leads to lower (faster) lap times.")

    # Visualization
    plt.figure(figsize=(8, 6))
    plt.scatter(df_stats['Window_Util%'], df_stats['S1_Time'], color='blue')
    for i, txt in enumerate(df_stats['Lap']):
        plt.annotate(f"L{txt}", (df_stats['Window_Util%'].iloc[i], df_stats['S1_Time'].iloc[i]))
    
    plt.title(f'S1 Performance vs. Corner Utilization ({window_start}m-{window_end}m)')
    plt.xlabel('Max Grip Utilization %')
    plt.ylabel('Sector 1 Time (s)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.savefig('performance_correlation.png')
    print("\nSaved correlation plot to 'performance_correlation.png'")

if __name__ == "__main__":
    main()
