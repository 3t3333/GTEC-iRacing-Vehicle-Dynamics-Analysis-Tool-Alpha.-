import sys
import os

sys.path.insert(0, os.path.abspath('ldparser'))
from ldparser import ldData

def main():
    file_path = "Fastlap.ld"
    data = ldData.fromfile(file_path)
    
    channels = list(data)
    
    print("\n--- Channels related to Sectors / Splits ---")
    for ch in channels:
        if 'sect' in ch.lower() or 'split' in ch.lower() or 'time' in ch.lower():
            print(f" - {ch:30} | Freq: {data[ch].freq:>4}Hz | Unit: {data[ch].unit}")

if __name__ == "__main__":
    main()
