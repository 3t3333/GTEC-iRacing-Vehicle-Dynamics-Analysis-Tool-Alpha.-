import os
import sys
import json
import time
import datetime
import yaml
import shutil
import ui.splash as splash
from ui.tui_engine import get_tui_choice
from ui.splash import C_ACTION, C_INFO, C_SUCCESS, C_WARNING, C_DANGER, C_GOLD, OpenDAV_RESET

PROJECTS_DIR = "projects"
STAGING_DIR = "telemetry"

def run_project_manager():
    if not os.path.exists(PROJECTS_DIR): os.makedirs(PROJECTS_DIR)
    if not os.path.exists(STAGING_DIR): os.makedirs(STAGING_DIR)
        
    while True:
        menu = [
            (1, "Create New Project Repo", "Initialize a new SimGit repository"),
            (2, "Open Existing Repository", "Manage and analyze tracked setups"),
            (3, "Global Workbook Management", "Edit automated analysis sequences"),
            (4, "Browse & Pull from Cloud", "Sync team projects from Supabase"),
            ('p', "Back", "Return to main menu")
        ]
        choice = get_tui_choice(menu)
        if choice == 'p': break
        elif choice == '1': create_project()
        elif choice == '2': list_projects()
        elif choice == '3':
            from analysis.workflow_engine import manage_workbooks
            manage_workbooks()
        elif choice == '4': browse_and_pull()

def create_project():
    name = input("\nEnter Project Name: ").strip().replace(" ", "_")
    if not name: return
    path = os.path.join(PROJECTS_DIR, name)
    if os.path.exists(path):
        print(f"[!] Project '{name}' already exists."); input(); return
    os.makedirs(path); os.makedirs(os.path.join(path, "telemetry")); os.makedirs(os.path.join(path, "setups"))
    os.makedirs(os.path.join(path, "lapfiles")); os.makedirs(os.path.join(path, "exports")); os.makedirs(os.path.join(path, "reports"))
    state = {"name": name, "created": str(datetime.datetime.now()), "linked_files": [], "baseline": None}
    with open(os.path.join(path, "project_state.json"), "w") as f: json.dump(state, f, indent=4)
    print(f"\n[+] Project Repository '{name}' initialized."); input()

def list_projects():
    projects = [d for d in os.listdir(PROJECTS_DIR) if os.path.isdir(os.path.join(PROJECTS_DIR, d))]
    if not projects: print("  [!] No local projects found."); input(); return
    while True:
        menu = [(i+1, p, "Open project workspace") for i, p in enumerate(projects)]
        menu.append(('p', "Back", "Return to project manager"))
        choice = get_tui_choice(menu)
        if choice == 'p': break
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(projects): manage_project(projects[idx])
        except ValueError: pass

def manage_project(name):
    path = os.path.join(PROJECTS_DIR, name)
    while True:
        try:
            with open(os.path.join(path, "project_state.json"), "r") as f: state = json.load(f)
        except Exception as e: print(f"[!] Error: {e}"); return
        splash.print_header(f"Workspace: {name}", path="SimGit")
        sto_count = len(os.listdir(os.path.join(path, "setups")))
        baseline = os.path.basename(state['baseline']) if state['baseline'] else "None"
        model_status = f"{C_SUCCESS}LOADED{OpenDAV_RESET}" if os.path.exists(os.path.join(path, "vehicle_model.json")) else f"{C_WARNING}MISSING{OpenDAV_RESET}"
        
        print(f"  {C_INFO}Repository Status:{OpenDAV_RESET}")
        print(f"    Telemetry: {len(state['linked_files']):2} files | Setups: {sto_count:2} files | Model: {model_status}")
        print(f"    Baseline:  {C_SUCCESS}{baseline}{OpenDAV_RESET}")
        print("  " + "─" * 98)
        menu = [
            (1, "Commit New Files", "Link staged telemetry to baseline"),
            (2, "Individual Analysis", "Run math tools on specific files"),
            (3, "Run Automated Workbook", "Batch process all tracked telemetry"),
            (4, "View Setup Timeline", "Review setup changes over time"),
            (5, "Install to iRacing", "Export setup to sim folder"),
            (6, "Change Baseline File", "Switch active setup context"),
            (7, "Push to Team Cloud", "Upload project to Supabase"),
            (8, "Confirm Vehicle Parameters", "Edit physics constants & Spring Rates"),
            ('p', "Back", "Return to project list")
        ]
        choice = get_tui_choice(menu)
        if choice == 'p': break
        if choice == '1': commit_files(name, path, state)
        elif choice == '2': run_manual_analysis(name, state)
        elif choice == '3':
            from analysis.workflow_engine import execute_workflow
            execute_workflow(name, state); input()
        elif choice == '4': show_history(name)
        elif choice == '5': install_to_iracing(name, path)
        elif choice == '6': set_baseline(name, path, state)
        elif choice == '7':
            from core.cloud import OpenDAVCloud
            cloud = OpenDAVCloud(); cloud.push_project(name, path); input()
        elif choice == '8': confirm_vehicle_parameters(name, path, state)

def confirm_vehicle_parameters(name, path, state):
    model_path = os.path.join(path, "vehicle_model.json")
    
    # Default/Fallback model
    model = {
        "spring_rate_npm": {"FL": 1000000.0, "FR": 1000000.0, "RL": 1000000.0, "RR": 1000000.0},
        "motion_ratios": {"FL": 1.0, "FR": 1.0, "RL": 1.0, "RR": 1.0}
    }
    
    if os.path.exists(model_path):
        try:
            with open(model_path, "r") as f:
                loaded_model = json.load(f)
                if "physics_model" in loaded_model:
                    model = loaded_model["physics_model"]
                else:
                    model = loaded_model # Backward compatibility
        except Exception:
            pass

    # Try to auto-detect from the most recent baseline telemetry if available
    detected_springs = {}
    if state.get('baseline') and os.path.exists(state['baseline']):
        try:
            print(f"\n  [*] Scanning baseline telemetry for known parameters...")
            from core.telemetry import load_telemetry
            data, _, _, _ = load_telemetry(state['baseline'])
            for corner in ['FL', 'FR', 'RL', 'RR']:
                ch_name = f'SpringRate{corner}'
                if ch_name in data.channels:
                    # iRacing usually stores this in N/mm in the YAML
                    detected_springs[corner] = data.channels[ch_name].data[0] 
        except Exception:
            pass

    splash.print_header(f"Confirm Vehicle Parameters: {name}", path="SimGit > Setup")
    print(f"  {C_INFO}Please confirm or update the fundamental vehicle physics constants.{OpenDAV_RESET}")
    print(f"  {C_GOLD}These values are used to calculate precise aerodynamic loads.{OpenDAV_RESET}")
    print("  " + "─" * 98)

    # 1. Spring Rates
    print(f"\n  {C_ACTION}[ 1. Spring Rates (N/mm) ]{OpenDAV_RESET}")
    for corner in ['FL', 'FR', 'RL', 'RR']:
        current_val = model['spring_rate_npm'].get(corner, 1000000.0) / 1000.0 # Convert back to N/mm for display
        detected_val = detected_springs.get(corner)
        
        prompt_suffix = f"(Detected: {detected_val:.1f})" if detected_val else f"(Current: {current_val:.1f})"
        
        while True:
            inp = input(f"    {corner} Spring Rate {prompt_suffix}: ").strip()
            if not inp:
                # Use detected if available, otherwise keep current
                val = detected_val if detected_val else current_val
                model['spring_rate_npm'][corner] = val * 1000.0 # Store as N/m
                break
            try:
                val = float(inp)
                model['spring_rate_npm'][corner] = val * 1000.0 # Store as N/m
                break
            except ValueError:
                print(f"    {C_DANGER}[!] Invalid number. Please enter a valid float (e.g. 260.0).{OpenDAV_RESET}")

    # 2. Motion Ratios
    print(f"\n  {C_ACTION}[ 2. Motion Ratios (Shock Travel / Wheel Travel) ]{OpenDAV_RESET}")
    print(f"  {C_INFO}Hint: If unknown, leave as 1.0. For modern GTs/Prototypes, usually 0.7 - 0.95.{OpenDAV_RESET}")
    for corner in ['FL', 'FR', 'RL', 'RR']:
        current_mr = model['motion_ratios'].get(corner, 1.0)
        while True:
            inp = input(f"    {corner} Motion Ratio (Current: {current_mr:.3f}): ").strip()
            if not inp:
                model['motion_ratios'][corner] = current_mr
                break
            try:
                val = float(inp)
                if val <= 0 or val > 5:
                    print(f"    {C_DANGER}[!] Invalid ratio. Usually between 0.1 and 2.0.{OpenDAV_RESET}")
                    continue
                model['motion_ratios'][corner] = val
                break
            except ValueError:
                print(f"    {C_DANGER}[!] Invalid number.{OpenDAV_RESET}")


    # 3. Static Mass
    print(f"\n  {C_ACTION}[ 3. Static Mass Calibration (kg) ]{OpenDAV_RESET}")
    print(f"  {C_INFO}Used to normalize shock sensor zeros. Enter car dry weight + driver + fuel.{OpenDAV_RESET}")
    current_mass = model.get('actual_mass_kg', 1350.0)
    while True:
        inp = input(f"    Total Static Mass (Current: {current_mass:.1f} kg): ").strip()
        if not inp:
            model['actual_mass_kg'] = current_mass
            break
        try:
            val = float(inp)
            if val < 500 or val > 5000:
                print(f"    {C_DANGER}[!] Unrealistic mass.{OpenDAV_RESET}")
                continue
            model['actual_mass_kg'] = val
            break
        except ValueError:
            print(f"    {C_DANGER}[!] Invalid number.{OpenDAV_RESET}")

    # Save the updated model
    full_model = {"physics_model": model}
    with open(model_path, "w") as f:
        json.dump(full_model, f, indent=4)
        
    print(f"\n  {C_SUCCESS}[✔] Vehicle parameters saved and applied to project!{OpenDAV_RESET}")
    input("\nPress Enter to return...")

def run_manual_analysis(project_name, state):
    from ui.tui_engine import get_tui_choice
    from ui.tui_multi import get_multi_lap_choice
    from ui.tui_sector import get_sector_choice
    import json
    
    if not state['linked_files']:
        print("[!] No telemetry files committed.")
        input("\nPress Enter to continue...")
        return
        
    while True:
        splash.print_header(f"Manual Analysis - {project_name}")
        
        file_menu = []
        for i, f in enumerate(state['linked_files']):
            file_menu.append((i+1, os.path.basename(f), f"Tracked file {i+1}"))
        file_menu.append(('p', "Back", "Return to workspace"))
        
        choice = get_tui_choice(file_menu)
        if choice == 'p': return
        
        try:
            primary_path = state['linked_files'][int(choice)-1]
        except:
            continue
        
        # Load the Model Overrides!
        overrides = {}
        model_path = os.path.join(PROJECTS_DIR, project_name, "vehicle_model.json")
        if os.path.exists(model_path):
            try:
                with open(model_path, "r") as f:
                    loaded_model = json.load(f)
                    if "physics_model" in loaded_model:
                        overrides = loaded_model
                    else:
                        overrides = {"physics_model": loaded_model}
            except Exception: pass

        from core.telemetry import load_telemetry
        try:
            data, limit, channels, metadata = load_telemetry(primary_path, overrides=overrides)
        except Exception as e:
            print(f"[!] Error loading file: {e}")
            import time; time.sleep(2)
            continue
            
        sessions = []
        
        # --- LAP BROWSER INJECTION ---
        lap_data = metadata.get('lap_browser_data', [])
        selected_laps = []
        if lap_data:
            car = metadata.get('car', 'Unknown Car')
            venue = metadata.get('venue', 'Unknown Venue')
            laps_to_analyze = get_multi_lap_choice(lap_data, f"[ SIM-GIT SESSION BROWSER ] : {car} @ {venue}", f"File: {os.path.basename(primary_path)}")
            
            if not laps_to_analyze:
                continue
                
            selected_laps = [l['lap_num'] for l in laps_to_analyze]
            
            # --- SECTOR SLIDER INJECTION ---
            import yaml
            sectors_pct = []
            try:
                y_data = yaml.safe_load(metadata.get('session_info_yaml', ''))
                if y_data and 'SplitTimeInfo' in y_data and 'Sectors' in y_data['SplitTimeInfo']:
                    for s in y_data['SplitTimeInfo']['Sectors']:
                        pct = s.get('SectorStartPct', -1)
                        if pct >= 0: sectors_pct.append(pct)
            except: pass
            
            import numpy as np
            max_dist = 5000.0 
            if channels.get('dist') and channels['dist'] in data:
                dist_raw = data[channels['dist']].data
                lap_arr = data[channels['lap']].data
                if len(dist_raw) > 0 and len(lap_arr) > 0:
                    first_lap = selected_laps[0] if selected_laps else np.unique(lap_arr)[0]
                    lap_mask = (lap_arr == first_lap)
                    if np.any(lap_mask):
                        max_dist = np.max(dist_raw[lap_mask]) - np.min(dist_raw[lap_mask])

            distance_bounds = get_sector_choice(max_dist, sectors_pct)
            if distance_bounds is None:
                continue
                
            metadata['selected_laps'] = selected_laps
            sessions.append({
                'file_path': primary_path,
                'data': data,
                'limit': limit,
                'channels': channels,
                'metadata': metadata,
                'distance_bounds': distance_bounds
            })
        else:
            sessions.append({
                'file_path': primary_path,
                'data': data,
                'limit': limit,
                'channels': channels,
                'metadata': metadata
            })
        
        while True:
            splash.print_header(f"Manual Analysis", path=f"SimGit > {project_name}")
            
            tools = [
                (1, "Tire Energy Profiler", "Physical work and abuse bias"),
                (2, "Static Setup Viewer", "YAML mechanical state"),
                (3, "Dynamic Rake Analyzer", "Attitude vs Speed trend"),
                (4, "Tire & Fuel Windows", "Stint performance tracking"),
                (5, "Tire Temp/Load Map", "Sector grip performance"),
                (6, "Custom Math Sandbox", "User-defined telemetry plots"),
                (7, "Empirical Aero Map", "3D Balance & Rake Topography"),
                (8, "Downforce Mapping", "Total Load & Aero Efficiency"),
                (9, "Pitch & Platform", "Braking dive and squat stiffness"),
                (10, "Handling Analyzer", "Yaw Error (Understeer/Oversteer)"),
                (11, "TLLTD Distribution", "Lateral load transfer distribution"),
                ('p', "Back", "Return to file selection")
            ]
            
            tool_choice = get_tui_choice(tools)
            if tool_choice == 'p': break
            
            if tool_choice == '1':
                from analysis.tire_energy import run_tire_energy_profiler
                run_tire_energy_profiler(sessions)
            elif tool_choice == '2':
                from analysis.setup_viewer import run_setup_viewer
                run_setup_viewer(sessions)
            elif tool_choice == '3':
                from analysis.aero_rake import run_rake_analysis
                run_rake_analysis(sessions)
            elif tool_choice == '4':
                from analysis.tire_fuel_windows import run_tire_fuel_windows
                run_tire_fuel_windows(sessions)
            elif tool_choice == '5':
                from analysis.tire_performance import run_sector_tire_analysis
                run_sector_tire_analysis(sessions)
            elif tool_choice == '6':
                from analysis.math_sandbox import run_custom_math_graph
                run_custom_math_graph(sessions)
            elif tool_choice == '7':
                from analysis.aero_mapping import run_aero_mapping
                run_aero_mapping(sessions)
            elif tool_choice == '8':
                from analysis.downforce_mapping import run_downforce_mapping
                run_downforce_mapping(sessions)
            elif tool_choice == '9':
                from analysis.pitch_kinematics import run_pitch_analyzer
                run_pitch_analyzer(sessions)
            elif tool_choice == '10':
                from analysis.yaw_kinematics import run_yaw_analyzer
                run_yaw_analyzer(sessions)
            elif tool_choice == '11':
                from analysis.load_transfer import run_tlltd_analyzer
                run_tlltd_analyzer(sessions)

def commit_files(name, path, state):
    while True:
        if not os.path.exists(STAGING_DIR):
            os.makedirs(STAGING_DIR)

        staged_files = [f for f in os.listdir(STAGING_DIR) if f.lower().endswith(('.ibt', '.ld', '.sto', '.blap', '.olap'))]
        if not staged_files:
            print(f"\n[!] No files found in the global '{STAGING_DIR}' staging folder.")
            print("    Drop your .ibt, .sto, or .blap files there first to commit them.")
            input("\nPress Enter to continue...")
            break

        splash.print_header(f"Commit Files to '{name}'")
        print("  Untracked Files in Staging Area:")
        for i, f in enumerate(staged_files):
            print(f"    {i+1}. {f}")
        print("─" * 100)

        while True:
            choice = input("\nSelect files to commit (e.g. '1,3,4'), 'all', or 'c' to cancel: ").strip().lower()

            if choice == 'c': return

            to_commit = []
            if choice == 'all':
                to_commit = staged_files
            else:
                try:
                    indices = [int(x.strip()) - 1 for x in choice.split(',')]
                    for idx in indices:
                        if 0 <= idx < len(staged_files):
                            to_commit.append(staged_files[idx])
                        else:
                            print(f"[!] Invalid selection: {idx+1}")
                            time.sleep(1)

                    if not to_commit: continue
                except ValueError:
                    print("[!] Invalid selection. Use numbers separated by commas.")
                    time.sleep(1)
                    continue

            commit_msg = input("Enter a commit message / notes for these files: ").strip()
            if not commit_msg:
                commit_msg = "Added new file(s)"

            break

        for file_name in to_commit:
            src = os.path.join(STAGING_DIR, file_name)
            ext = file_name.split('.')[-1].lower()

            if ext in ['ibt', 'ld']:
                dest_dir = os.path.join(path, "telemetry")
                file_type = "Telemetry"
            elif ext == 'sto':
                dest_dir = os.path.join(path, "setups")
                file_type = "Setup"
            elif ext in ['blap', 'olap']:
                dest_dir = os.path.join(path, "lapfiles")
                file_type = "Ghost Lap"
            else:
                continue

            dest = os.path.join(dest_dir, file_name)
            shutil.copy2(src, dest)

            diff_text = commit_msg

            # If telemetry, analyze mechanical setup diff
            if ext in ['ibt', 'ld']:
                from core.telemetry import load_telemetry
                print(f"\n[*] Analyzing mechanical setup of {file_name}...")
                try:
                    _, _, _, metadata = load_telemetry(dest)
                    last_file = state['linked_files'][-1] if state['linked_files'] else None

                    if last_file and os.path.exists(last_file):
                        _, _, _, last_metadata = load_telemetry(last_file)

                        def extract_setup(m):
                            y = yaml.safe_load(m.get('session_info_yaml', '')) or {}
                            setup = y.get('CarSetup', {})
                            flat = {}
                            def recurse(d, prefix=""):
                                if isinstance(d, dict):
                                    for k, v in d.items():
                                        if k in ("UpdateCount", "LastTempsOMI", "LastTempsIMO", "TreadRemaining", "CornerWeight"): continue
                                        recurse(v, f"{prefix}{k}." if prefix else f"{k}.")
                                else: flat[prefix[:-1]] = d
                            recurse(setup)
                            return flat

                        s1 = extract_setup(last_metadata)
                        s2 = extract_setup(metadata)

                        deltas = []
                        for k in set(s1.keys()).union(s2.keys()):
                            if s1.get(k) != s2.get(k):
                                fk = k.replace('Chassis.', '').replace('Tires.', '').replace('Front.', 'F ').replace('Rear.', 'R ')
                                deltas.append(f"{fk} [{s1.get(k)} -> {s2.get(k)}]")

                        if deltas:
                            diff_text += f" | Setup Shift: {', '.join(deltas)}"
                except Exception as e:
                    print(f"[!] Error parsing telemetry setup: {e}")

                state['linked_files'].append(dest)
                if not state['baseline']:
                    state['baseline'] = dest

            # Log to history
            with open(os.path.join(path, "setup_history.md"), "a") as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                f.write(f"| {timestamp} | {file_name} | {file_type} | {diff_text} |\n")

            print(f"[+] Committed '{file_name}' to {file_type} repository.")

        with open(os.path.join(path, "project_state.json"), "w") as f:
            json.dump(state, f, indent=4)

        ans = input("\nPress Enter to commit more files, or 'c' to return to dashboard: ").strip().lower()
        if ans == 'c':
            break

def install_to_iracing(name, path):
    splash.print_header(f"Install to iRacing - {name}")
    
    # Gather installable assets
    setups = os.listdir(os.path.join(path, "setups"))
    lapfiles = os.listdir(os.path.join(path, "lapfiles"))
    
    assets = []
    for s in setups: assets.append(("Setup", os.path.join(path, "setups", s), s))
    for l in lapfiles: assets.append(("Ghost Lap", os.path.join(path, "lapfiles", l), l))
    
    if not assets:
        print("[!] No .sto setups or .blap ghost laps committed to this project.")
        input("\nPress Enter to return...")
        return
        
    for i, (atype, _, fname) in enumerate(assets):
        print(f"  {i+1}. [{atype}] {fname}")
    print("─" * 100)
    
    choice = input("\nSelect asset to install to iRacing (number): ").strip()
    try:
        idx = int(choice) - 1
        if not (0 <= idx < len(assets)):
            raise ValueError()
    except ValueError:
        print("[!] Invalid selection.")
        input("\nPress Enter to return...")
        return
        
    asset_type, asset_path, asset_name = assets[idx]
    
    print("\n[*] Searching for local iRacing installation...")
    iracing_path = ""
    
    if os.name == 'nt':
        base = os.path.expanduser("~")
        iracing_path = os.path.join(base, "Documents", "iRacing")
    else:
        iracing_path = "" 
            
    if not os.path.exists(iracing_path):
        print("[!] Could not automatically locate iRacing Documents folder.")
        iracing_path = input("    Please manually paste the path to your iRacing folder: ").strip()
        if not os.path.exists(iracing_path):
            print("[!] Path does not exist. Aborting.")
            input("\nPress Enter to return...")
            return
            
    if asset_type == "Setup":
        print(f"\n    Detected Setup File. You must specify the car folder (e.g. 'porsche992cup').")
        car_folders = [d for d in os.listdir(os.path.join(iracing_path, "setups")) if os.path.isdir(os.path.join(iracing_path, "setups", d))]
        
        # Try to guess car folder from filename (basic heuristic)
        from core.config import get_auto_import
        auto_install = get_auto_import()
        
        guessed_car = ""
        for c in car_folders:
            if c.lower().replace(" ", "") in asset_name.lower().replace(" ", ""):
                guessed_car = c
                break
                
        if auto_install and guessed_car:
            print(f"\n    [Auto-Install] Detected Car Folder: {guessed_car}")
            car_folder = guessed_car
        else:
            car_folder = input(f"    Enter Target Car Folder (Detected: {guessed_car}): ").strip()
            if not car_folder: car_folder = guessed_car
        
        dest_dir = os.path.join(iracing_path, "setups", car_folder)
        
    else:
        print(f"\n    Detected Ghost Lap. You must specify the track folder (e.g. 'daytona').")
        track_folders = [d for d in os.listdir(os.path.join(iracing_path, "lapfiles")) if os.path.isdir(os.path.join(iracing_path, "lapfiles", d))]
        
        guessed_track = ""
        for t in track_folders:
            if t.lower().replace(" ", "") in asset_name.lower().replace(" ", ""):
                guessed_track = t
                break
                
        from core.config import get_auto_import
        auto_install = get_auto_import()
        
        if auto_install and guessed_track:
            print(f"\n    [Auto-Install] Detected Track Folder: {guessed_track}")
            track_folder = guessed_track
        else:
            track_folder = input(f"    Enter Target Track Folder (Detected: {guessed_track}): ").strip()
            if not track_folder: track_folder = guessed_track
        
        dest_dir = os.path.join(iracing_path, "lapfiles", track_folder)
        
    if not os.path.exists(dest_dir):
        print(f"\n[!] Target directory does not exist: {dest_dir}")
        ans = input("    Create it anyway? (y/n): ").strip().lower()
        if ans == 'y':
            os.makedirs(dest_dir)
        else:
            print("    Aborted.")
            input("\nPress Enter to return...")
            return
            
    try:
        dest_file = os.path.join(dest_dir, asset_name)
        shutil.copy2(asset_path, dest_file)
        print(f"\n[+] SUCCESS: Installed {asset_name} to {dest_dir}")
    except Exception as e:
        print(f"\n[!] Error copying file: {e}")
        
    input("\nPress Enter to continue...")

def show_history(name):
    path = os.path.join(PROJECTS_DIR, name, "setup_history.md")
    splash.print_header(f"Setup History Log: {name}")
    try:
        with open(path, "r") as f:
            print(f.read())
    except Exception as e:
        print(f"[!] Error reading history: {e}")
    input("\nPress Enter to return...")

def set_baseline(name, path, state):
    if not state['linked_files']:
        print("[!] No telemetry files committed yet.")
        input("\nPress Enter to continue...")
        return
        
    splash.print_header("Set Baseline Telemetry")
    for i, f in enumerate(state['linked_files']):
        print(f"  {i+1}. {os.path.basename(f)}")
    print("─" * 100)
    
    choice = input("\nSelect baseline file: ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(state['linked_files']):
            state['baseline'] = state['linked_files'][idx]
            with open(os.path.join(path, "project_state.json"), "w") as f:
                json.dump(state, f, indent=4)
            print(f"[+] Baseline set to {os.path.basename(state['baseline'])}")
        else:
            print("[!] Invalid selection.")
    except ValueError:
        print("[!] Invalid selection.")
    input("\nPress Enter to continue...")

def save_to_project(fig, project_name, filename, subfolder=None):
    path = os.path.join(PROJECTS_DIR, project_name)
    if not os.path.exists(path):
        print(f"[!] Project '{project_name}' not found. Saving to global exports instead.")
        os.makedirs("exports", exist_ok=True)
        export_path = os.path.join("exports", filename)
    else:
        if subfolder:
            export_dir = os.path.join(path, "exports", subfolder)
            os.makedirs(export_dir, exist_ok=True)
            export_path = os.path.join(export_dir, filename)
        else:
            export_path = os.path.join(path, "exports", filename)
        
    fig.savefig(export_path, dpi=300, bbox_inches='tight')
    print(f"  [+] Saved to {export_path}")

def browse_and_pull():
    from core.cloud import OpenDAVCloud
    cloud = OpenDAVCloud()
    if not cloud.is_logged_in():
        print("\n[!] You must be logged in to pull projects from SimGit.")
        input("\nPress Enter to return...")
        return
        
    print("\n[*] Connecting to SimGit Database to fetch available projects...")
    projects = cloud.list_available_projects()
    
    if not projects:
        input("\nPress Enter to return...")
        return
        
    while True:
        splash.print_header("SimGit Cloud Repository")
        print("  Available Projects on Server:")
        for i, p in enumerate(projects):
            print(f"    {i+1}. {p}")
        print("─" * 100)
        
        choice = input("\nSelect a project to download (number), or 'p' to go back: ").strip().lower()
        if choice == 'p': break
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(projects):
                target_project = projects[idx]
                
                local_path = os.path.join(PROJECTS_DIR, target_project)
                if os.path.exists(local_path):
                    print(f"\n[!] Project '{target_project}' already exists locally.")
                    ans = input("    Do you want to overwrite/sync it anyway? (y/n): ").strip().lower()
                    if ans != 'y': continue
                    
                cloud.pull_project(target_project)
                input("\nPress Enter to return...")
                break
            else:
                print("  [!] Invalid selection.")
                import time
                time.sleep(1)
        except ValueError:
            print("  [!] Invalid selection.")
            import time
            time.sleep(1)
