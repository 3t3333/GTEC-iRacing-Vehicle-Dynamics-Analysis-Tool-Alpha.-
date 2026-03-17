import sys
import os

sys.path.insert(0, os.path.abspath('ldparser'))
from ldparser import ldData

def main():
    file_path = "Fastlap.ld"
    print(f"Loading {file_path}...")
    data = ldData.fromfile(file_path)
    
    channels = list(data)
    
    print("\n--- Channels related to Distance ---")
    for ch in channels:
        if 'dist' in ch.lower() or 'lap' in ch.lower() or 'fuel' in ch.lower() or 'beac' in ch.lower():
            print(f" - {ch:30} | Freq: {data[ch].freq:>4}Hz | Unit: {data[ch].unit}")

if __name__ == "__main__":
    main()
