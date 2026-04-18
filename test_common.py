import numpy as np

def get_session_info(data, channels):
    info = []
    
    # 1. Lap Count
    if 'lap' in channels and channels['lap'] in data:
        laps = np.unique(data[channels['lap']].data)
        info.append(f"Laps: {len(laps)}")
        
    # 2. Air Temp
    for ch in ['AirTemp', 'Air Temp']:
        if ch in data:
            val = np.median(data[ch].data)
            info.append(f"Air Temp: {val:.1f}°C")
            break
            
    # 3. Track Temp
    for ch in ['TrackTemp', 'Track Temp']:
        if ch in data:
            val = np.median(data[ch].data)
            info.append(f"Track Temp: {val:.1f}°C")
            break
            
    # 4. Air Density
    for ch in ['AirDensity', 'Air Density', 'air_density']:
        if ch in data:
            val = np.median(data[ch].data)
            info.append(f"Air Density: {val:.3f} kg/m³")
            break
            
    return " | ".join(info)

# Mock data test
class MockCh:
    def __init__(self, data): self.data = data
data = {'AirTemp': MockCh([26.9]), 'TrackTemp': MockCh([38.8]), 'AirDensity': MockCh([1.18]), 'Lap': MockCh([1,1,2,2,3])}
channels = {'lap': 'Lap'}

print(get_session_info(data, channels))
