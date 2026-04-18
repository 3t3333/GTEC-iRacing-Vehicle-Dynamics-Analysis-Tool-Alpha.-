import sys
import os
import numpy as np

# Ensure ldparser is accessible
if not getattr(sys, 'frozen', False):
    ld_path = os.path.join(os.getcwd(), 'ldparser')
    if ld_path not in sys.path:
        sys.path.insert(0, ld_path)

try:
    from ldparser import ldData, ldHead
except ImportError as e:
    print(f"\n[!] ERROR: Failed to import ldparser modules: {e}")
    print(f"    Check that you built the EXE using: pyinstaller --onefile --paths \"ldparser\" opendav.py")
    input("\nPress Enter to exit...")
    sys.exit(1)

def load_telemetry(file_path):
    print(f"[*] Loading {file_path}...")
    try:
        if file_path.lower().endswith('.ibt'):
            from core import ibt_adapter
            data = ibt_adapter.fromfile(file_path)
        else:
            data = ldData.fromfile(file_path)
        
        # Identify standard channels
        lap_ch = 'Lap' if 'Lap' in data else 'Lap Number'
        dist_ch = 'Lap Distance' if 'Lap Distance' in data else 'LapDist'
        long_g_ch = 'G Force Long' if 'G Force Long' in data else 'LongAccel'
        lat_g_ch = 'G Force Lat' if 'G Force Lat' in data else 'LatAccel'
        time_ch = 'SessionTime'
        
        # Calculate Global Limit
        comb_g_all = np.sqrt(data[long_g_ch].data**2 + data[lat_g_ch].data**2)
        global_limit = np.max(comb_g_all)
        
        # Extract metadata
        metadata = {'driver': 'Unknown', 'car': 'Unknown', 'venue': 'Unknown', 'fastest_lap': 'N/A', 'laps_count': 0}
        
        if file_path.lower().endswith('.ibt'):
            metadata['driver'] = getattr(data.head, 'driver', 'iRacing User')
            metadata['car'] = getattr(data.head, 'vehicleid', 'iRacing Car')
            metadata['venue'] = getattr(data.head, 'venue', 'iRacing Track')
            
            yaml_raw = getattr(data.head, 'session_info_yaml', '')
            if isinstance(yaml_raw, bytes):
                yaml_raw = yaml_raw.decode('utf-8', errors='ignore')
            metadata['session_info_yaml'] = yaml_raw
        else:
            try:
                with open(file_path, 'rb') as f_obj:
                    h = ldHead.fromfile(f_obj)
                    metadata['driver'] = str(getattr(h, 'driver', '')).strip() or 'Unknown'
                    metadata['car'] = str(getattr(h, 'vehicleid', '')).strip() or 'Unknown'
                    metadata['venue'] = str(getattr(h, 'venue', '')).strip() or 'Unknown'
            except Exception:
                pass

        # Calculate fastest lap and laps count
        if lap_ch in data and time_ch in data:
            lap_arr = data[lap_ch].data
            time_arr = data[time_ch].data
            laps = np.unique(lap_arr)
            metadata['laps_count'] = len(laps)
            
            lap_times = []
            for lap in laps:
                idx = np.where(lap_arr == lap)[0]
                if len(idx) < 100: continue
                lap_times.append((lap, time_arr[idx][-1] - time_arr[idx][0]))
            
            if lap_times:
                median_time = np.median([t[1] for t in lap_times])
                valid_times = [t for t in lap_times if t[1] >= median_time * 0.89]
                if valid_times:
                    fastest = min(valid_times, key=lambda x: x[1])
                    metadata['fastest_lap'] = f"{fastest[1]:.3f} s (Lap {int(fastest[0])})"
        
        return data, global_limit, {
            'lap': lap_ch, 'dist': dist_ch, 'long': long_g_ch, 
            'lat': lat_g_ch, 'time': time_ch
        }, metadata
    except Exception as e:
        print(f"[!] Error loading file: {e}")
        # print(traceback.format_exc()) # Debug
        sys.exit(1)

def get_static_val(data, possible_names, multiplier=1.0, fmt="{:.1f}", unit=""):
    for name in possible_names:
        if name in data:
            val = data[name].data[0] * multiplier
            return f"{fmt.format(val)} {unit}".strip()
    return "N/A (Not logged)"
