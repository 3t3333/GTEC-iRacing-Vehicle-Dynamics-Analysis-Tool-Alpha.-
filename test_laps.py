import os
import sys

sys.path.insert(0, os.path.abspath('ldparser'))
from ldparser import ldData, ldHead

telemetry_dir = "telemetry"
ld_files = [f for f in os.listdir(telemetry_dir) if f.lower().endswith(('.ld', '.id'))]

temp_files_info = []
for f in ld_files:
    f_path = os.path.join(telemetry_dir, f)
    display_name = f
    laps_count = 0
    try:
        with open(f_path, 'rb') as f_obj:
            h = ldHead.fromfile(f_obj)
            driver = str(getattr(h, 'driver', '')).strip() or 'Unknown Driver'
            car = str(getattr(h, 'vehicleid', '')).strip() or 'Unknown Car'
            venue = str(getattr(h, 'venue', '')).strip() or 'Unknown Venue'
            display_name = f"{driver} - {car} - {venue}"
        
        # Load data to get laps
        d = ldData.fromfile(f_path)
        if 'Lap' in d:
            laps_count = len(set(d['Lap'].data))
        elif 'Lap Number' in d:
            laps_count = len(set(d['Lap Number'].data))
    except Exception as e:
        print(f"Error on {f}: {e}")
        pass
    
    if laps_count > 0:
        display_name = f"{display_name} ({laps_count} Laps)"
    else:
        display_name = f"{display_name} (Unknown Laps)"
        
    temp_files_info.append((laps_count, f, display_name))
    
temp_files_info.sort(key=lambda x: x[0], reverse=True)

ld_files = [item[1] for item in temp_files_info]
file_infos = [item[2] for item in temp_files_info]

for fi in file_infos:
    print(fi)
