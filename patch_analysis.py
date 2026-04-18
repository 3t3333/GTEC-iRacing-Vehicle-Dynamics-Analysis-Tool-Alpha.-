import re
import os

files = ['analysis/tire_energy.py', 'analysis/aero_rake.py', 'analysis/aero_mapping.py', 'analysis/downforce_mapping.py']

for f_name in files:
    with open(f_name, 'r') as f:
        content = f.read()

    # 1. Update signature
    sig_search = r"def run_[a-z_]+\(sessions\):"
    match = re.search(sig_search, content)
    if match:
        old_sig = match.group(0)
        new_sig = old_sig.replace("(sessions):", "(sessions, headless=False, headless_config=None):")
        content = content.replace(old_sig, new_sig)

    # 2. Update ans_raw input logic
    if f_name == 'analysis/tire_energy.py':
        old_ans = """                ans_raw = input(f"\\n  Select action ('open L1', 'print L1 < proj', 'p' to go back): ").strip().lower()
                ans = ans_raw.split('<')[0].strip()"""
        new_ans = """                if headless:
                    ans_raw = f"print {headless_config['layout']} < {headless_config['project']}"
                else:
                    ans_raw = input(f"\\n  Select action ('open L1', 'print L1 < proj', 'p' to go back): ").strip().lower()
                ans = ans_raw.split('<')[0].strip()"""
        content = content.replace(old_ans, new_ans)
    else:
        old_ans = """                ans_raw = input(f"\\n  Select action ('open L1', 'print L1', 'open L2', 'print L2', 'p' to go back < proj): ").strip().lower()
                ans = ans_raw.split('<')[0].strip()"""
        new_ans = """                if headless:
                    ans_raw = f"print {headless_config['layout'].lower()} < {headless_config['project']}"
                else:
                    ans_raw = input(f"\\n  Select action ('open L1', 'print L1', 'open L2', 'print L2', 'p' to go back < proj): ").strip().lower()
                ans = ans_raw.split('<')[0].strip()"""
        content = content.replace(old_ans, new_ans)

    # 3. Update L2 reference logic
    if f_name != 'analysis/tire_energy.py':
        if f_name == 'analysis/aero_rake.py':
            old_ref = """                    telemetry_dir = "telemetry"
                    ld_files = [f for f in os.listdir(telemetry_dir) if f.lower().endswith(('.ld', '.ibt'))]
                    ld_files.sort()
                    
                    print("\\n  Select Reference File:")
                    for i, lf in enumerate(ld_files): print(f"    {i+1}. {lf}")
                    ref_choice = input("  Selection (number): ").strip()
                    try:
                        ref_idx = int(ref_choice) - 1
                        ref_path = os.path.join(telemetry_dir, ld_files[ref_idx])
                        r_data, _, r_channels, r_metadata = load_telemetry(ref_path)
                    except:
                        print("  [!] Invalid selection.")
                        continue"""
            
            new_ref = """                    if headless:
                        ref_path = headless_config['ref_path']
                        try:
                            r_data, _, r_channels, r_metadata = load_telemetry(ref_path)
                        except Exception as e:
                            print(f"  [!] Error loading reference file: {e}")
                            break
                    else:
                        telemetry_dir = "telemetry"
                        ld_files = [f for f in os.listdir(telemetry_dir) if f.lower().endswith(('.ld', '.ibt'))]
                        ld_files.sort()
                        
                        print("\\n  Select Reference File:")
                        for i, lf in enumerate(ld_files): print(f"    {i+1}. {lf}")
                        ref_choice = input("  Selection (number): ").strip()
                        try:
                            ref_idx = int(ref_choice) - 1
                            ref_path = os.path.join(telemetry_dir, ld_files[ref_idx])
                            r_data, _, r_channels, r_metadata = load_telemetry(ref_path)
                        except:
                            print("  [!] Invalid selection.")
                            continue"""
            content = content.replace(old_ref, new_ref)
        else: # aero_mapping & downforce_mapping
            # These two have slightly different ref loading
            old_ref = """                    telemetry_dir = "telemetry"
                    if not os.path.exists(telemetry_dir):
                        print(f"  [!] Directory '{telemetry_dir}' not found.")
                        continue
                        
                    ld_files = [f for f in os.listdir(telemetry_dir) if f.lower().endswith(('.ld', '.ibt'))]
                    ld_files.sort()
                    
                    if not ld_files:
                        print("  [!] No files found in telemetry directory.")
                        continue
                        
                    print("\\n  Select Reference File:")
                    for i, lf in enumerate(ld_files):
                        print(f"    {i+1}. {lf}")
                    print("  ─" * 20)
                    ref_choice = input("  Selection (number): ").strip()
                    try:
                        ref_idx = int(ref_choice) - 1
                        if not (0 <= ref_idx < len(ld_files)):
                            raise ValueError()
                    except ValueError:
                        print("  [!] Invalid selection.")
                        continue
                        
                    ref_path = os.path.join(telemetry_dir, ld_files[ref_idx])
                    print(f"  [*] Loading Reference: {os.path.basename(ref_path)}")
                    
                    try:
                        ref_data, _, ref_channels, ref_metadata = load_telemetry(ref_path)
                    except Exception as e:
                        print(f"  [!] Error loading reference file: {e}")
                        continue"""

            new_ref = """                    if headless:
                        ref_path = headless_config['ref_path']
                        try:
                            ref_data, _, ref_channels, ref_metadata = load_telemetry(ref_path)
                        except Exception as e:
                            print(f"  [!] Error loading reference file: {e}")
                            break
                    else:
                        telemetry_dir = "telemetry"
                        if not os.path.exists(telemetry_dir):
                            print(f"  [!] Directory '{telemetry_dir}' not found.")
                            continue
                            
                        ld_files = [f for f in os.listdir(telemetry_dir) if f.lower().endswith(('.ld', '.ibt'))]
                        ld_files.sort()
                        
                        if not ld_files:
                            print("  [!] No files found in telemetry directory.")
                            continue
                            
                        print("\\n  Select Reference File:")
                        for i, lf in enumerate(ld_files):
                            print(f"    {i+1}. {lf}")
                        print("  ─" * 20)
                        ref_choice = input("  Selection (number): ").strip()
                        try:
                            ref_idx = int(ref_choice) - 1
                            if not (0 <= ref_idx < len(ld_files)):
                                raise ValueError()
                        except ValueError:
                            print("  [!] Invalid selection.")
                            continue
                            
                        ref_path = os.path.join(telemetry_dir, ld_files[ref_idx])
                        print(f"  [*] Loading Reference: {os.path.basename(ref_path)}")
                        
                        try:
                            ref_data, _, ref_channels, ref_metadata = load_telemetry(ref_path)
                        except Exception as e:
                            print(f"  [!] Error loading reference file: {e}")
                            continue"""
            content = content.replace(old_ref, new_ref)

    # 4. Handle extended report prompt in print L1 (only for aero_mapping & downforce_mapping)
    if f_name in ['analysis/aero_mapping.py', 'analysis/downforce_mapping.py']:
        content = content.replace("ans_ext = input(\"  Print extended report (Sectors/Corners)? (y/n): \").strip().lower()", 
                                  "ans_ext = 'n' if headless else input(\"  Print extended report (Sectors/Corners)? (y/n): \").strip().lower()")

    # 5. Break the loops if headless
    if f_name == 'analysis/tire_energy.py':
        content = content.replace("print(f\"  [+] Saved to {export_path}\")", "print(f\"  [+] Saved to {export_path}\")\n                        if headless: break")
    elif f_name == 'analysis/aero_rake.py':
        content = content.replace("print(f\"  [+] Saved to {export_path}\")", "print(f\"  [+] Saved to {export_path}\")\n                        if headless: break")
        content = content.replace("print(f\"  [+] Saved to {ep}\")", "print(f\"  [+] Saved to {ep}\")\n                        if headless: break")
    else: # aero/downforce
        content = content.replace("print(f\"      [+] Exported {base_name}\")", "print(f\"      [+] Exported {base_name}\")") # Keep this untouched as it's a loop
        content = content.replace("print(f\"  [!] Failed to generate report: {e}\")", "print(f\"  [!] Failed to generate report: {e}\")\n                        if headless: break")
        content = content.replace("print(f\"  [+] Saved L2 Layout to {export_path}\")", "print(f\"  [+] Saved L2 Layout to {export_path}\")\n                        if headless: break")
        content = content.replace("print(\"      [!] Distance channel required for extended report.\")", "print(\"      [!] Distance channel required for extended report.\")\n                        if headless: break")

    # 6. Finally break the main loop at the very end
    end_block = """        print("\\n" + "─"*100)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break"""
    new_end_block = """        if headless: return
        print("\\n" + "─"*100)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break"""
    content = content.replace(end_block, new_end_block)

    with open(f_name, 'w') as f:
        f.write(content)

