with open('analysis/aero_mapping.py', 'r') as f:
    content = f.read()

content = content.replace(
    'target_ab_input = input("      Enter Target Aero Balance % (or press Enter for 45.0): ").strip()',
    'target_ab_input = "" if headless else input("      Enter Target Aero Balance % (or press Enter for 45.0): ").strip()'
)

with open('analysis/aero_mapping.py', 'w') as f:
    f.write(content)
