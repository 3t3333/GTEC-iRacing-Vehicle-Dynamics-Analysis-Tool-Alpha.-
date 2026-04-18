import os
from core import ibt_adapter
import numpy as np

file_path = 'webanalysisfeature/lap.ibt'
data = ibt_adapter.fromfile(file_path, meta_only=False)

for ch in ['AirTemp', 'TrackTemp', 'AirDensity']:
    if ch in data:
        val = np.median(data[ch].data)
        print(f"Channel {ch}: {val}")
    else:
         print(f"Channel {ch} not found")

