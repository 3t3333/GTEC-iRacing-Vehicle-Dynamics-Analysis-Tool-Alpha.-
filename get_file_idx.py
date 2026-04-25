import os
files = [f for f in os.listdir("telemetry") if f.endswith(".ibt")]
for i, f in enumerate(files):
    if "porsche992rgt3_indianapolis" in f:
        print("FOUND", f, "at index", i+1) # wait, it's sorted by display name.

