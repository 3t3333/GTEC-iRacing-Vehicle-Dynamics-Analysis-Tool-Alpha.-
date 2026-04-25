import subprocess
import os

commands = [
    "1",
    r"D:\gtec\telemetry\porsche992rgt3_indianapolis 2022 road 2025-08-24 12-30-03.ibt",
    "7",
    "print l3",
    "45.0",
    "p",
    "p",
    "q"
]

proc = subprocess.Popen(["python3", "opendav.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
stdout, stderr = proc.communicate(input="\n".join(commands) + "\n")
print(stdout[-1000:])
if stderr:
    print("ERRORS:", stderr)
