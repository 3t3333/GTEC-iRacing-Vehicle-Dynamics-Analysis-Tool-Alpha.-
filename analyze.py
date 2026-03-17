import sys
import os

# Add the cloned ldparser repo to the path
sys.path.insert(0, os.path.abspath('ldparser'))

import pandas as pd
from ldparser import ldData

def main():
    file_path = "Fastlap.ld"
    print(f"Loading {file_path}...")
    
    try:
        data = ldData.fromfile(file_path)
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    print("\n--- Metadata ---")
    # Access metadata from the head object
    print(f"Driver: {getattr(data.head, 'driver', 'N/A')}")
    print(f"Vehicle ID: {getattr(data.head, 'vehicleid', 'N/A')}")
    print(f"Venue: {getattr(data.head, 'venue', 'N/A')}")
    print(f"Short Comment: {getattr(data.head, 'shortcomment', 'N/A')}")

    print("\n--- Available Channels ---")
    channels = list(data)
    print(f"Found {len(channels)} total channels.")
    print("First 10 channels for preview:")
    for channel_name in channels[:10]:
        ch = data[channel_name]
        print(f" - {channel_name:20} | Freq: {ch.freq:>4}Hz | Unit: {ch.unit}")

    print("\n--- Data Sample (First 5 rows of first 3 channels) ---")
    sample_channels = channels[:3]
    try:
        # Check if they have the same length for a quick preview
        lengths = [len(data[ch].data) for ch in sample_channels]
        if len(set(lengths)) == 1:
            df_dict = {ch: data[ch].data for ch in sample_channels}
            df = pd.DataFrame(df_dict)
            print(df.head())
        else:
            print("Note: Sample channels have different lengths/frequencies. Printing first values:")
            for ch in sample_channels:
                print(f" - {ch}: {data[ch].data[:5]} ...")
    except Exception as e:
        print(f"Could not preview data table: {e}")

if __name__ == "__main__":
    main()
