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
    
    # 1. Prepare Data for a specific lap (Lap 25 is the fastest)
    target_lap = 25
    lap_ch = 'Lap' if 'Lap' in data else 'Lap Number'
    lap_mask = data[lap_ch].data == target_lap
    
    # Required channels
    dist_ch = 'Lap Distance' if 'Lap Distance' in data else 'LapDist'
    long_g_ch = 'G Force Long' if 'G Force Long' in data else 'LongAccel'
    lat_g_ch = 'G Force Lat' if 'G Force Lat' in data else 'LatAccel'
    speed_ch = 'Speed'
    
    # Extract data for the lap
    distances = data[dist_ch].data[lap_mask]
    long_gs = data[long_g_ch].data[lap_mask]
    lat_gs = data[lat_g_ch].data[lap_mask]
    speeds = data[speed_ch].data[lap_mask]
    
    # 2. Calculate Combined G for every point in the lap
    # Combined_G = sqrt((Lat G)^2 + (Long G)^2)
    combined_gs = np.sqrt(lat_gs**2 + long_gs**2)
    
    # 3. Establish the Baseline (Max Combined G achieved)
    # Using the max from this specific lap as the peak potential
    max_combined_g = np.max(combined_gs)
    print(f"Empirical Tire Limit (Max Combined G): {max_combined_g:.3f} G")
    
    # 4. Isolate the User's specific window: 142m to 316m
    window_mask = (distances >= 142) & (distances <= 316)
    w_dist = distances[window_mask]
    w_long = long_gs[window_mask]
    w_lat = lat_gs[window_mask]
    w_combined = combined_gs[window_mask]
    w_speed = speeds[window_mask]
    
    # 5. Calculate Grip Utilization % for the window
    utilization = (w_combined / max_combined_g) * 100
    avg_util = np.mean(utilization)
    max_util = np.max(utilization)
    
    print(f"\n--- Analysis for Window: 142m to 316m ---")
    print(f"Average Grip Utilization: {avg_util:.1f}%")
    print(f"Peak Grip Utilization:    {max_util:.1f}%")
    
    # 6. Visualization
    plt.figure(figsize=(12, 6))
    
    # Subplot 1: G-G Diagram (Friction Circle)
    plt.subplot(1, 2, 1)
    # Background: All points from the lap in grey
    plt.scatter(lat_gs, long_gs, color='grey', alpha=0.1, label='Full Lap', s=1)
    # Foreground: The selected window in color
    plt.scatter(w_lat, w_long, c=utilization, cmap='RdYlGn_r', s=10, label='142m-316m')
    
    # Draw the theoretical circle limit
    theta = np.linspace(0, 2*np.pi, 100)
    plt.plot(max_combined_g * np.cos(theta), max_combined_g * np.sin(theta), 'r--', alpha=0.5, label='Empirical Limit')
    
    plt.axhline(0, color='black', lw=0.5)
    plt.axvline(0, color='black', lw=0.5)
    plt.xlabel('Lateral G')
    plt.ylabel('Longitudinal G')
    plt.title('Friction Circle Utilization')
    plt.legend(loc='lower right')
    plt.axis('equal')
    
    # Subplot 2: Utilization Trace over Distance
    plt.subplot(1, 2, 2)
    ax1 = plt.gca()
    ax2 = ax1.twinx()
    
    ax1.plot(w_dist, w_speed, 'b-', label='Speed', alpha=0.7)
    ax2.plot(w_dist, utilization, 'r-', label='Utilization %', linewidth=2)
    
    ax1.set_xlabel('Distance (meters)')
    ax1.set_ylabel('Speed', color='b')
    ax2.set_ylabel('Grip Utilization %', color='r')
    ax2.set_ylim(0, 110)
    plt.title('Grip Utilization vs. Distance (142m-316m)')
    
    plt.tight_layout()
    plt.savefig('custom_window_analysis.png')
    print(f"\nAnalysis complete. Plot saved to 'custom_window_analysis.png'.")

if __name__ == "__main__":
    main()
