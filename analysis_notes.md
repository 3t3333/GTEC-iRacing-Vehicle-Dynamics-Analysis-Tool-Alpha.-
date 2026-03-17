# Telemetry Data Analysis Notes

This document contains important context, tooling details, and track information gathered during the analysis of MoTeC telemetry data (`.ld` files) for sim racing.

## Data Source
- **Format:** MoTeC `.ld` (binary telemetry data) and `.ldx` (XML metadata).
- **Driver:** Arturo Gomez
- **Vehicle:** Porsche 992 Cup (`porsche9922cup`)
- **Track:** Hockenheim GP
- **Logging Frequency:** 60Hz (Standard for most channels)

## Python Environment & Tooling
The environment requires a custom parser to read the proprietary `.ld` binary format.
- **Parser Library:** `ldparser` (by gotzl). Since it is not on PyPI, it must be cloned directly: `git clone https://github.com/gotzl/ldparser.git`.
- **Dependencies:** `pandas`, `numpy`, `matplotlib`.
- **Initialization Snippet:**
  ```python
  import sys, os
  sys.path.insert(0, os.path.abspath('ldparser'))
  from ldparser import ldData
  
  # Load data
  data = ldData.fromfile("Fastlap.ld")
  
  # Access channels (ldData uses a custom iterator, not .keys())
  channels = list(data)
  
  # Access specific channel data array
  throttle = data['Throttle'].data
  lap_dist = data['Lap Distance'].data
  ```

## Key Telemetry Channels
There are over 360 channels in the dataset. Some of the most important for lap and location analysis include:
- **`Lap` / `Lap Number`:** The current lap integer (1-indexed, though often starts higher depending on the session structure).
- **`LapDist` / `Lap Distance`:** The distance traveled in the current lap in meters. Resets at the start/finish line. Essential for plotting corner data.
- **`SessionTime`:** The elapsed time in seconds. Used for calculating sector and lap times.
- **`Fuel Level` / `FuelLevel`:** The remaining fuel in liters. Useful for consumption calculations.
- **`Brake Pedal Position` / `Brake`:** Braking input (percentage).
- **`Throttle`:** Throttle input (percentage).
- **`Steering Wheel Angle`:** Steering input.

## Hockenheim GP Track Data
When analyzing sector times, the standard FIA/iRacing track splits must be manually calculated using the `Lap Distance` channel, as the telemetry is a continuous stream.

- **Total Track Length:** 4,574 meters
- **Sector 1:** Ends at 1,041 meters (Just before Turn 5 entry).
- **Sector 2:** Length 2,142 meters. Ends at 3,183 meters total distance (Just before Sachs-Kurve entry).
- **Sector 3:** Length 1,391 meters. Ends at 4,574 meters (Start/Finish line).

### Sector Calculation Logic
Because data is logged at a fixed frequency (e.g., 60Hz), the exact distance of the sector line might fall between two data points. The most robust way to calculate sector times in Python is to find the timestamp of the first data point *after* the sector distance threshold is crossed:

```python
# Find S1 time (when dist >= 1041m)
s1_idx = np.argmax(lap_dist >= 1041.0)
time_at_s1 = lap_time[s1_idx]
```

## Known Quirks
- **Lap Numbering:** The laps in a single file might not start at 1. For example, a session file might only contain data for Laps 17 through 26. Always use `np.unique(data['Lap'].data)` to see the available laps.
- **Array Lengths:** If different channels have different logging frequencies (e.g., 60Hz vs 5Hz), their data arrays will have different lengths. You cannot easily bundle them into a single Pandas DataFrame without resampling or aligning them against a common `SessionTime` or `Lap Distance` axis first.