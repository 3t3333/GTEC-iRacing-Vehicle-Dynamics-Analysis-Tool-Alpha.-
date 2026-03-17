import sys
import os
import time
sys.path.insert(0, os.path.abspath('ldparser'))
from ldparser import ldData

start = time.time()
ld_files = [f for f in os.listdir('telemetry') if f.lower().endswith(('.ld', '.id'))]
for f in ld_files:
    f_path = os.path.join('telemetry', f)
    data = ldData.fromfile(f_path)
    h = data.head
    print(f"{h.driver} - {h.vehicleid} - {h.venue}")
print(f"Total time: {time.time() - start:.3f}s")
