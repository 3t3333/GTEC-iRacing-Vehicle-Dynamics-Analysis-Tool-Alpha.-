with open('analysis/aero_mapping.py', 'r') as f:
    content = f.read()

content = content.replace('export_dir = f"exports/L1_{timestamp}"', 'export_dir = f"exports/F2L1_{timestamp}"')
content = content.replace('f"AeroMap_{file_basename}.png"', 'f"F2L1_{file_basename}.png"')
content = content.replace('export_dir = f"exports/L2_{timestamp}"', 'export_dir = f"exports/F2L2_{timestamp}"')
content = content.replace('f"L2_Aero_{file_basename}_vs_{os.path.basename(ref_path)}.png"', 'f"F2L2_{file_basename}_vs_{os.path.basename(ref_path)}.png"')

with open('analysis/aero_mapping.py', 'w') as f:
    f.write(content)
