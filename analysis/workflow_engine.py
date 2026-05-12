import os
import json
import ui.splash as splash

WORKBOOKS_FILE = "workbooks.json"

def load_workbooks():
    if os.path.exists(WORKBOOKS_FILE):
        with open(WORKBOOKS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_workbooks(wbs):
    with open(WORKBOOKS_FILE, 'w') as f:
        json.dump(wbs, f, indent=4)

def manage_workbooks():
    while True:
        splash.print_header("Manage Workbooks")
        print("  1. Create New Workbook")
        print("  2. View Existing Workbooks")
        print("  3. Delete Workbook")
        print("  p. Back")
        print("─" * 100)
        
        choice = input("\nSelect an option: ").strip().lower()
        if choice == 'p': break
        elif choice == '1': create_workbook()
        elif choice == '2': view_workbooks()
        elif choice == '3': delete_workbook()

def create_workbook():
    name = input("\nEnter Workbook Name (e.g. Aero_Suite_L2): ").strip().replace(" ", "_")
    if not name: return
    
    wbs = load_workbooks()
    if name in wbs:
        print("[!] Workbook already exists.")
        input("\nPress Enter to continue...")
        return
        
    tasks = []
    features_map = {
        '1': ('Tire Energy & Work Profiler', ['L1', 'L2', 'L3', 'L4']),
        '2': ('Dynamic Aero/Rake Analyzer', ['L1', 'L2']),
        '3': ('Tire & Fuel Windows', ['L1']),
        '4': ('Tire Temp/Load Map', ['L1']),
        '5': ('Custom Math Sandbox', ['L1']),
        '6': ('Empirical Aero Map Generator', ['L1', 'L2', 'L3']),
        '7': ('Downforce Mapping Module', ['L1', 'L2', 'L3', 'L4']),
        '8': ('Pitch Kinematics & Platform Analyzer', ['L1', 'L2']),
        '9': ('Yaw Kinematics & Handling Analyzer', ['L1', 'L2']),
        '10': ('Total Lateral Load Transfer (TLLTD)', ['L1']),
        '11': ('Compression Rates', ['L1', 'L2', 'L3', 'L4', 'L5', 'L6'])
    }
    
    while True:
        splash.print_header(f"Building Workbook: {name}")
        if tasks:
            print("  Current Tasks:")
            for i, t in enumerate(tasks):
                fname = features_map[t['feature']][0]
                print(f"    {i+1}. {fname} ({t['layout']})")
            print("─" * 100)
            
        print("  Available Features:")
        for k, v in features_map.items():
            print(f"    {k}. {v[0]}")
        print("\n  Enter feature number to add, 'd' when done, or 'c' to cancel.")
        
        f_choice = input("\nChoice: ").strip().lower()
        if f_choice == 'c':
            return
        if f_choice == 'd':
            if not tasks:
                print("[!] No tasks added. Discarding workbook.")
                input("\nPress Enter to continue...")
                return
            wbs[name] = tasks
            save_workbooks(wbs)
            print(f"\n[+] Workbook '{name}' saved successfully.")
            input("Press Enter to continue...")
            break
            
        if f_choice in features_map:
            valid_layouts = features_map[f_choice][1]
            import os
                # Try to extract previews dynamically
                module_map = {
                    '1': 'tire_energy.py', '2': 'aero_rake.py', '3': 'tire_fuel_windows.py',
                    '4': 'tire_performance.py', '5': 'math_sandbox.py', '6': 'aero_mapping.py',
                    '7': 'downforce_mapping.py', '8': 'pitch_kinematics.py', '9': 'yaw_kinematics.py',
                    '10': 'load_transfer.py', '11': 'compression_rates.py'
                }
                mod_file = module_map.get(f_choice)
                if mod_file and os.path.exists(os.path.join('analysis', mod_file)):
                    with open(os.path.join('analysis', mod_file), 'r') as mf:
                        m_content = mf.read()
                        
                        import re
                        # Look for variable assignments like l1_preview = f"""..."""
                        previews = re.findall(r'[l|f]\w*_preview\s*=\s*(?:f)?"""(.*?)"""', m_content, re.DOTALL)
                        
                        if previews:
                            print("\n" + "─"*80)
                            for p in previews:
                                print(p)
                            print("─"*80)
                        else:
                            # Fallback if variable wasn't found, look for direct print(f"""...""")
                            raw_prints = re.findall(r'print\(\s*(?:f)?"""(.*?)"""\s*\)', m_content, re.DOTALL)
                            if raw_prints:
                                print("\n" + "─"*80)
                                for p in raw_prints:
                                    print(p)
                                print("─"*80)
                                
            if len(valid_layouts) == 1:
                print(f"\n  [+] Auto-selected {valid_layouts[0]} (Only 1 layout available).")
                layout = valid_layouts[0]
            else:
                print(f"\n  [ ADD LAYOUT ]: Type 'Add L1', 'Add L2', etc. from the options: {', '.join(valid_layouts)}")
                ans = input("  Selection: ").strip().lower()
                
                if ans.startswith('add '):
                    layout = ans.split(' ')[1].upper()
                else:
                    layout = ans.upper() # Fallback just in case they just typed 'L2'
                    
                if layout not in valid_layouts:
                    print("  [!] Invalid layout.")
                    continue
            tasks.append({'feature': f_choice, 'layout': layout})
            print(f"  [+] Added Feature {f_choice} -> {layout} to workbook.")
        else:
            print("  [!] Invalid selection.")
            import time
            time.sleep(1)

def view_workbooks():
    wbs = load_workbooks()
    if not wbs:
        print("[!] No workbooks found.")
        input("\nPress Enter to continue...")
        return
    splash.print_header("Existing Workbooks")
    for k, v in wbs.items():
        print(f"  ■ {k}")
        for t in v:
            fname = {"1": "Tire Energy", "2": "Rake Analyzer", "3": "Tire/Fuel Windows", "4": "Sector Tires", "5": "Math Sandbox", "6": "Aero Map", "7": "Downforce Map", "8": "Pitch Analyzer", "9": "Yaw Analyzer", "10": "TLLTD", "11": "Compression Rates"}.get(t['feature'], f"Feature {t['feature']}")
            print(f"      - {fname} ({t['layout']})")
    input("\nPress Enter to continue...")

def delete_workbook():
    wbs = load_workbooks()
    if not wbs:
        print("[!] No workbooks to delete.")
        input("\nPress Enter to continue...")
        return
    splash.print_header("Delete Workbook")
    names = list(wbs.keys())
    for i, n in enumerate(names):
        print(f"  {i+1}. {n}")
    print("─" * 100)
    choice = input("\nEnter number to delete (or 'c' to cancel): ").strip()
    if choice == 'c': return
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(names):
            del wbs[names[idx]]
            save_workbooks(wbs)
            print(f"[+] Deleted workbook '{names[idx]}'.")
    except ValueError:
        print("[!] Invalid input.")
    input("\nPress Enter to continue...")

def execute_workflow(project_name, state):
    wbs = load_workbooks()
    if not wbs:
        print("[!] No workbooks available. Create one first via the main Automation menu.")
        return
        
    if not state['linked_files']:
        print("[!] No telemetry files linked to this project.")
        return
        
    splash.print_header(f"Run Automation - Project: {project_name}")
    names = list(wbs.keys())
    for i, n in enumerate(names):
        print(f"  {i+1}. {n}")
    print("  c. Cancel")
    print("─" * 100)
    
    choice = input("\nSelect Workbook: ").strip().lower()
    if choice == 'c': return
    
    try:
        idx = int(choice) - 1
        if not (0 <= idx < len(names)):
            print("[!] Invalid selection.")
            return
        wb_name = names[idx]
        tasks = wbs[wb_name]
    except ValueError:
        print("[!] Invalid input.")
        return
    
    needs_ref = any(t['layout'] == 'L2' for t in tasks)
    ref_path = None
    
    if needs_ref:
        print(f"\n[*] This workbook '{wb_name}' requires a Reference File for L2 comparisons.")
        baseline_name = os.path.basename(state['baseline']) if state['baseline'] else 'None'
        print(f"    Project Baseline: {baseline_name}")
        ans = input("    Use project baseline as reference? (y/n): ").strip().lower()
        if ans == 'y' and state['baseline']:
            ref_path = state['baseline']
        else:
            print("\n  Select a linked file as Reference:")
            for i, f in enumerate(state['linked_files']):
                print(f"    {i+1}. {os.path.basename(f)}")
            r_choice = input("  Selection: ").strip()
            try:
                r_idx = int(r_choice) - 1
                ref_path = state['linked_files'][r_idx]
            except ValueError:
                print("[!] Invalid selection. Aborting workflow.")
                return
                
    primary_path = state['linked_files'][-1]
    print(f"\n[*] Starting Workflow: {wb_name}")
    print(f"    Primary: {os.path.basename(primary_path)}")
    if ref_path:
        print(f"    Reference: {os.path.basename(ref_path)}")
        
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
    run_folder_name = f"{project_name}_{timestamp}"
    print(f"    Export Directory: /exports/{run_folder_name}/")
    
    print("\n    Loading primary telemetry...")
    from core.telemetry import load_telemetry
    data, limit, channels, metadata = load_telemetry(primary_path)
    sessions = [{'data': data, 'limit': limit, 'channels': channels, 'metadata': metadata, 'file_path': primary_path}]
    
    from analysis.tire_energy import run_tire_energy_profiler
    from analysis.aero_rake import run_rake_analysis
    from analysis.aero_mapping import run_aero_mapping
    from analysis.downforce_mapping import run_downforce_mapping
    from analysis.pitch_kinematics import run_pitch_analyzer
    from analysis.yaw_kinematics import run_yaw_analyzer
    from analysis.load_transfer import run_tlltd_analyzer
    
    for i, task in enumerate(tasks):
        f_id = task['feature']
        layout = task['layout']
        print(f"\n  [{i+1}/{len(tasks)}] Executing Feature {f_id} -> {layout}")
        
        config = {'layout': layout, 'project': project_name, 'ref_path': ref_path, 'run_folder': run_folder_name}
        
        try:
            if f_id == '1':
                run_tire_energy_profiler(sessions, headless=True, headless_config=config)
            elif f_id == '2':
                run_rake_analysis(sessions, headless=True, headless_config=config)
            elif f_id == '3':
                from analysis.tire_fuel_windows import run_tire_fuel_windows
                run_tire_fuel_windows(sessions, headless=True, headless_config=config)
            elif f_id == '4':
                from analysis.tire_performance import run_sector_tire_analysis
                run_sector_tire_analysis(sessions, headless=True, headless_config=config)
            elif f_id == '5':
                from analysis.math_sandbox import run_custom_math_graph
                run_custom_math_graph(sessions, headless=True, headless_config=config)
            elif f_id == '6':
                run_aero_mapping(sessions, headless=True, headless_config=config)
            elif f_id == '7':
                run_downforce_mapping(sessions, headless=True, headless_config=config)
            elif f_id == '8':
                run_pitch_analyzer(sessions, headless=True, headless_config=config)
            elif f_id == '9':
                run_yaw_analyzer(sessions, headless=True, headless_config=config)
            elif f_id == '10':
                run_tlltd_analyzer(sessions, headless=True, headless_config=config)
            elif f_id == '11':
                from analysis.compression_rates import run_compression_rates
                run_compression_rates(sessions, headless=True, headless_config=config)
        except Exception as e:
            print(f"      [!] Error executing task: {e}")
            import traceback
            traceback.print_exc()
            
    print(f"\n[+] Workflow '{wb_name}' completed. All reports saved to project exports.")
    input("\nPress Enter to return to Project Dashboard...")