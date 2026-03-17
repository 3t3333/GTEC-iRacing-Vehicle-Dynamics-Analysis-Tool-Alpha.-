import sys
import os

sys.path.insert(0, os.path.abspath('ldparser'))
from ldparser import ldData
import pandas as pd

def main():
    file_path = "Fastlap.ld"
    data = ldData.fromfile(file_path)
    
    channels = list(data)
    with open('all_channels.txt', 'w') as f:
        for ch in sorted(channels):
            f.write(f"{ch}\n")

if __name__ == "__main__":
    main()
