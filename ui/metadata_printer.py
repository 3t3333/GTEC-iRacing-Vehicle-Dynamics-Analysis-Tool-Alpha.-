import numpy as np
import yaml

def print_session_metadata(data, channels, metadata=None):
    """
    Extracts and prints standard session metadata directly below the "Analyzing:" line.
    Requires data dictionary, channels mapping, and optional metadata dict (for YAML).
    """
    info = []
    
    # 1. Lap Count
    if 'lap' in channels and channels['lap'] in data:
        laps = np.unique(data[channels['lap']].data)
        info.append(f"Laps: {len(laps)}")
        
    # 2. Air Temp
    found_air = False
    for ch in ['AirTemp', 'Air Temp']:
        if ch in data:
            val = np.median(data[ch].data)
            info.append(f"Air: {val:.1f}°C")
            found_air = True
            break
            
    # 3. Track Temp
    found_track = False
    for ch in ['TrackTemp', 'Track Temp']:
        if ch in data:
            val = np.median(data[ch].data)
            info.append(f"Track: {val:.1f}°C")
            found_track = True
            break
            
    # 4. Air Density
    found_dens = False
    for ch in ['AirDensity', 'Air Density', 'air_density']:
        if ch in data:
            val = np.median(data[ch].data)
            info.append(f"Air Density: {val:.3f} kg/m³")
            found_dens = True
            break
            
    # 5. YAML Fallback (if channels are missing)
    if metadata and metadata.get('session_info_yaml'):
        try:
            y_data = yaml.safe_load(metadata['session_info_yaml'])
            if y_data and 'WeekendInfo' in y_data:
                wi = y_data['WeekendInfo']
                if not found_air and 'TrackAirTemp' in wi:
                    # Strip ' C' if present
                    val_str = str(wi['TrackAirTemp']).replace(' C', '').strip()
                    try:
                        info.append(f"Air: {float(val_str):.1f}°C")
                    except ValueError:
                         pass
                if not found_track and 'TrackSurfaceTemp' in wi:
                    val_str = str(wi['TrackSurfaceTemp']).replace(' C', '').strip()
                    try:
                         info.append(f"Track: {float(val_str):.1f}°C")
                    except ValueError:
                         pass
                if not found_dens and 'TrackAirPressure' in wi:
                     val_str = str(wi['TrackAirPressure']).replace(' Hg', '').strip()
                     try:
                          info.append(f"Pressure: {float(val_str):.2f} Hg")
                     except ValueError:
                          pass
        except Exception:
            pass

    if info:
        print(f"             ({ ' | '.join(info) })")
