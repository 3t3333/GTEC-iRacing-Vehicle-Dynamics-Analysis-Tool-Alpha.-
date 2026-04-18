import re

with open('opendav.py', 'r') as f:
    content = f.read()

# Make sure analysis package is registered in sys.path or explicitly imported
if "sys.path.insert(0, base_path)" not in content:
    content = content.replace("base_path = getattr(sys, '_MEIPASS', os.getcwd())",
                              "base_path = getattr(sys, '_MEIPASS', os.getcwd())\nsys.path.insert(0, base_path)")
                              
with open('opendav.py', 'w') as f:
    f.write(content)
