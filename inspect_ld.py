import sys
import os
sys.path.insert(0, os.path.abspath('ldparser'))
from ldparser import ldData

data = ldData.fromfile('telemetry/Fastlap.ld')
print("Head Attributes:")
for k in dir(data.head):
    if not k.startswith('_'):
        print(f"{k}: {getattr(data.head, k)}")
