import sys
import os

sys.path.insert(0, os.path.abspath('ldparser'))
from ldparser import ldData
import numpy as np
import pandas as pd

def main():
    file_path = "telemetry/Fastlap.ld"
    print(f"Loading {file_path}...\n")
    data = ldData.fromfile(file_path)
    
    # Identify the correct channels for lap and fuel
    lap_channel_name = 'Lap' if 'Lap' in data else 'Lap Number'
    fuel_channel_name = 'Fuel Level' if 'Fuel Level' in data else 'FuelLevel'
    
    lap_data = data[lap_channel_name].data
    fuel_data = data[fuel_channel_name].data
    
    print(f"Using channels: '{lap_channel_name}' and '{fuel_channel_name}'")
    
    # Frequencies
    lap_freq = data[lap_channel_name].freq
    fuel_freq = data[fuel_channel_name].freq
    print(f"Lap freq: {lap_freq}Hz, Fuel freq: {fuel_freq}Hz")
    
    if lap_freq != fuel_freq:
        print("Frequencies differ, logic needs to account for this. But assuming 60Hz for both based on preview.")
    
    # We want data for Lap 3.
    # We find all indices where lap == 3. 
    # Usually 'Lap' is 1-indexed (1, 2, 3...)
    
    unique_laps = np.unique(lap_data)
    if len(unique_laps) < 3:
        print("Not enough laps in the data to find the 3rd lap.")
        return
        
    target_lap = unique_laps[2] # 0-indexed, so 2 is the 3rd lap in the file
    
    # Get all indices for the target lap
    lap_3_indices = np.where(lap_data == target_lap)[0]
    
    if len(lap_3_indices) == 0:
        print(f"Could not find any data points for Lap {target_lap}. Available laps are:")
        print(np.unique(lap_data))
        return
        
    start_idx = lap_3_indices[0]
    end_idx = lap_3_indices[-1]
    
    start_fuel = fuel_data[start_idx]
    end_fuel = fuel_data[end_idx]
    fuel_used = start_fuel - end_fuel
    
    print(f"\n--- Lap {target_lap} Fuel Analysis ---")
    print(f"Start Index: {start_idx}, End Index: {end_idx}")
    print(f"Starting Fuel: {start_fuel:.2f} liters")
    print(f"Ending Fuel:   {end_fuel:.2f} liters")
    print(f"Fuel Used:     {fuel_used:.2f} liters")

if __name__ == "__main__":
    main()
