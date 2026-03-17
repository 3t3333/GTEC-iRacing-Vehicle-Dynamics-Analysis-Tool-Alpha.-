import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.abspath('ldparser'))
from ldparser import ldData

def build_lap_dataframe(data, target_lap):
    lap_ch = 'Lap' if 'Lap' in data else 'Lap Number'
    lap_data = data[lap_ch].data
    
    # Get indices for the target lap
    idx = np.where(lap_data == target_lap)[0]
    if len(idx) == 0:
        raise ValueError(f"Lap {target_lap} not found.")
        
    time_ch = 'SessionTime'
    base_time = data[time_ch].data[idx]
    
    channels_to_extract = {
        'Distance': 'Lap Distance' if 'Lap Distance' in data else 'LapDist',
        'Speed': 'Speed',
        'LongG': 'G Force Long' if 'G Force Long' in data else 'LongAccel',
        'LatG': 'G Force Lat' if 'G Force Lat' in data else 'LatAccel',
        'Steer': 'Steering Wheel Angle' if 'Steering Wheel Angle' in data else 'SteeringWheelAngle'
    }
    
    df_dict = {'Time': base_time}
    for col_name, ch_name in channels_to_extract.items():
        if ch_name not in data:
            print(f"Warning: Channel {ch_name} not found.")
            continue
            
        ch_data = data[ch_name].data
        ch_time = np.linspace(0, len(ch_data)/data[ch_name].freq, len(ch_data))
        # Usually channels are sync'd to the same length/time, but to be safe we can just 
        # slice if they are exactly the same length.
        if len(ch_data) == len(data[time_ch].data):
            df_dict[col_name] = ch_data[idx]
        else:
            print(f"Interpolating {ch_name} due to length mismatch...")
            # We assume time array spans 0 to End.
            session_time_full = data[time_ch].data
            df_dict[col_name] = np.interp(base_time, session_time_full, ch_data)
            
    return pd.DataFrame(df_dict)

def detect_corners(df):
    corners = []
    in_corner = False
    start_idx = 0
    
    for i in range(len(df)):
        long_g = df['LongG'].iloc[i]
        lat_g = df['LatG'].iloc[i]
        steer = df['Steer'].iloc[i]
        
        # Entry logic: braking or steering or lat G
        is_entry = long_g < -0.2 or abs(steer) > 10 or abs(lat_g) > 0.2
        
        # Exit logic: back on throttle, steering straight, lat G low
        is_exit = long_g > 0.1 and abs(steer) < 5 and abs(lat_g) < 0.15
        
        if not in_corner and is_entry:
            in_corner = True
            start_idx = i
        elif in_corner and is_exit:
            # check if corner was long enough (e.g. at least 1 second -> 60 samples at 60Hz)
            if i - start_idx > 30: 
                corners.append((start_idx, i))
            in_corner = False
            
    # Handle case where corner ends at the finish line
    if in_corner and len(df) - start_idx > 30:
        corners.append((start_idx, len(df)-1))
        
    return corners

def analyze_corners(df, corners, max_combined_g):
    results = []
    
    for i, (start, end) in enumerate(corners):
        corner_df = df.iloc[start:end].copy()
        
        # Combined G
        corner_df['CombinedG'] = np.sqrt(corner_df['LatG']**2 + corner_df['LongG']**2)
        corner_df['GripUtil'] = (corner_df['CombinedG'] / max_combined_g) * 100
        
        # Subdivide phases
        # Entry: Start to peak braking (min LongG)
        peak_brake_idx = corner_df['LongG'].idxmin()
        
        # Mid: Peak brake to Peak steering/LatG (we'll use max absolute LatG)
        # Using idxmax on absolute values
        peak_lat_idx = corner_df['LatG'].abs().idxmax()
        
        # Ensure logical order
        if peak_lat_idx < peak_brake_idx:
            peak_lat_idx = peak_brake_idx
            
        entry_df = df.loc[start:peak_brake_idx] if peak_brake_idx >= start else corner_df
        mid_df = df.loc[peak_brake_idx:peak_lat_idx] if peak_lat_idx >= peak_brake_idx else corner_df
        exit_df = df.loc[peak_lat_idx:end] if end >= peak_lat_idx else corner_df
        
        # Calculate utils
        # Use .max() to see how close they got to the limit in that phase
        def get_max_util(phase_df):
            if phase_df.empty: return 0.0
            cg = np.sqrt(phase_df['LatG']**2 + phase_df['LongG']**2)
            return (cg.max() / max_combined_g) * 100
            
        results.append({
            'Turn': i + 1,
            'Start_Dist': corner_df['Distance'].iloc[0],
            'End_Dist': corner_df['Distance'].iloc[-1],
            'Entry_Util': get_max_util(entry_df),
            'Mid_Util': get_max_util(mid_df),
            'Exit_Util': get_max_util(exit_df),
            'Corner_DF': corner_df
        })
        
    return results

def main():
    file_path = "Fastlap.ld"
    print(f"Loading {file_path}...")
    data = ldData.fromfile(file_path)
    
    target_lap = 25 # The fastest lap identified earlier
    print(f"Building DataFrame for Lap {target_lap}...")
    df = build_lap_dataframe(data, target_lap)
    
    # Calculate Max Combined G from the entire lap (or session)
    # Using lap 25 for simplicity, though session max is better
    lap_combined_g = np.sqrt(df['LatG']**2 + df['LongG']**2)
    max_combined_g = lap_combined_g.max()
    print(f"Max Historical Combined G: {max_combined_g:.2f} G")
    
    print("\nDetecting corners...")
    corners = detect_corners(df)
    print(f"Found {len(corners)} corners.")
    
    print("\nAnalyzing Tire Utilization...")
    analysis = analyze_corners(df, corners, max_combined_g)
    
    print("\n--- The Corner Summary Table ---")
    print(f"{'Turn':<5} | {'Start Dist(m)':<15} | {'Entry Util%':<12} | {'Mid Util%':<10} | {'Exit Util%':<10}")
    print("-" * 65)
    for res in analysis:
        print(f"{res['Turn']:<5} | {res['Start_Dist']:<15.1f} | {res['Entry_Util']:<11.1f}% | {res['Mid_Util']:<9.1f}% | {res['Exit_Util']:<9.1f}%")

    # Plot Turn 1 G-G Diagram
    if len(analysis) > 0:
        t1 = analysis[0]
        c_df = t1['Corner_DF']
        
        plt.figure(figsize=(10, 5))
        
        # Subplot 1: G-G Diagram
        plt.subplot(1, 2, 1)
        plt.scatter(c_df['LatG'].to_numpy(), c_df['LongG'].to_numpy(), c=c_df['Distance'].to_numpy(), cmap='viridis')
        plt.colorbar(label='Distance (m)')
        plt.title(f"Turn 1 G-G Diagram")
        plt.xlabel("Lat G")
        plt.ylabel("Long G")
        plt.axhline(0, color='black', lw=0.5)
        plt.axvline(0, color='black', lw=0.5)
        # Add friction circle boundary
        theta = np.linspace(0, 2*np.pi, 100)
        plt.plot(max_combined_g * np.cos(theta), max_combined_g * np.sin(theta), 'r--', alpha=0.5)
        plt.xlim(-max_combined_g*1.2, max_combined_g*1.2)
        plt.ylim(-max_combined_g*1.2, max_combined_g*1.2)

        # Subplot 2: Distance Trace
        plt.subplot(1, 2, 2)
        ax1 = plt.gca()
        ax2 = ax1.twinx()
        
        ax1.plot(c_df['Distance'].to_numpy(), c_df['Speed'].to_numpy(), 'b-', label='Speed')
        ax2.plot(c_df['Distance'].to_numpy(), c_df['GripUtil'].to_numpy(), 'r-', label='Grip Util %')
        
        ax1.set_xlabel('Distance (m)')
        ax1.set_ylabel('Speed', color='b')
        ax2.set_ylabel('Grip Util %', color='r')
        plt.title('Turn 1 Distance Trace')
        
        plt.tight_layout()
        plt.savefig("turn1_analysis.png")
        print("\nSaved Turn 1 analysis plot to 'turn1_analysis.png'")

if __name__ == "__main__":
    main()
