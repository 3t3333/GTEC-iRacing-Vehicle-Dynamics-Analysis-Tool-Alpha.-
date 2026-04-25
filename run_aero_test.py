import sys
import os

from core.telemetry import load_telemetry
from analysis.aero_mapping import run_aero_mapping

file_path = "telemetry/porsche992rgt3_indianapolis 2022 road 2025-08-24 12-30-03.ibt"

print("Loading telemetry...")
sessions = []
data, global_limit, channels, metadata = load_telemetry(file_path)
if data is not None:
    sessions.append({
        'file_path': file_path,
        'data': data,
        'channels': channels,
        'metadata': metadata
    })
    
    print("Running aero mapping test...")
    headless_config = {
        'project': 'test',
        'layout': 'L3',
        'run_folder': 'test_folder'
    }
    
    run_aero_mapping(sessions, headless=True, headless_config=headless_config)
    print("Done")
else:
    print("Failed to load telemetry")
