import os
import sys
import json
import time
import datetime
import yaml
import shutil
import ui.splash as splash
from ui.splash import C_ACTION, C_INFO, C_SUCCESS, C_WARNING, C_DANGER, C_GOLD, OpenDAV_RESET

PROJECTS_DIR = "projects"
STAGING_DIR = "telemetry"  # Global drop folder for new files

def run_project_manager():
    if not os.path.exists(PROJECTS_DIR):
        os.makedirs(PROJECTS_DIR)
    if not os.path.exists(STAGING_DIR):
        os.makedirs(STAGING_DIR)
        
    while True:
        splash.print_header("SimGit Project Manager")
        print(f"  {C_INFO}[ LOCAL WORKSPACE ]{OpenDAV_RESET}")
        print(f"    {C_ACTION}1.{OpenDAV_RESET} Create New Project Repo")
        print(f"    {C_ACTION}2.{OpenDAV_RESET} Open Existing Repository")
        print(f"    {C_ACTION}3.{OpenDAV_RESET} Global Workbook Management")
        print(f"\n  {C_INFO}[ TEAM SYNC ]{OpenDAV_RESET}")
        print(f"    {C_ACTION}4.{OpenDAV_RESET} Browse & Pull from Cloud")
        print("  " + "─" * 98)
        
        choice = input(f"\n  Select an option ({C_ACTION}number{OpenDAV_RESET}), or '{C_ACTION}p{OpenDAV_RESET}' to go back: ").strip().lower()
        
        if choice == 'p': break
        elif choice == '1': create_project()
        elif choice == '2': list_projects()
        elif choice == '3':
            from analysis.workflow_engine import manage_workbooks
            manage_workbooks()
        elif choice == '4':
            browse_and_pull()
        else:
            print("[!] Invalid selection.")
            time.sleep(1)

def create_project():
    name = input("\nEnter Project Name (e.g. Daytona_Setup_Week): ").strip().replace(" ", "_")
    if not name: return
    
    path = os.path.join(PROJECTS_DIR, name)
    if os.path.exists(path):
        print(f"[!] Project '{name}' already exists.")
        input("\nPress Enter to continue...")
        return
        
    # Build Git-like directory structure
    os.makedirs(path)
    os.makedirs(os.path.join(path, "telemetry")) # Tracked .ibt
    os.makedirs(os.path.join(path, "setups"))    # Tracked .sto
    os.makedirs(os.path.join(path, "lapfiles"))  # Tracked .blap / .olap
    os.makedirs(os.path.join(path, "exports"))
    os.makedirs(os.path.join(path, "reports"))
    
    state = {
        "name": name,
        "created": str(datetime.datetime.now()),
        "linked_files": [], # Pointers to local tracked telemetry
        "baseline": None
    }
    
    with open(os.path.join(path, "project_state.json"), "w") as f:
        json.dump(state, f, indent=4)
        
    with open(os.path.join(path, "setup_history.md"), "w") as f:
        f.write(f"# Setup History: {name}\n\n")
        f.write("| Date | File | Type | Changes / Notes |\n")
        f.write("|------|------|------|-----------------|\n")
        
    print(f"\n[+] Project Repository '{name}' initialized successfully.")
    input("Press Enter to continue...")

def list_projects():
    projects = [d for d in os.listdir(PROJECTS_DIR) if os.path.isdir(os.path.join(PROJECTS_DIR, d))]
    if not projects:
        print("  [!] No local projects found.")
        input("\n  Press Enter to continue...")
        return
        
    while True:
        splash.print_header("Select Project Repository")
        print(f"    {'ID':3} | {'REPOSITORY NAME':40}")
        print(f"    {'─'*3}─┼─{'─'*40}")
        for i, p in enumerate(projects):
            print(f"    {C_ACTION}{i+1:2}.{OpenDAV_RESET} | {C_GOLD}{p.ljust(40)}{OpenDAV_RESET}")
        
        print("  " + "─" * 98)
        
        choice = input(f"\n  Selection ({C_ACTION}number{OpenDAV_RESET}), or '{C_ACTION}p{OpenDAV_RESET}' to go back: ").strip().lower()
        if choice == 'p': break
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(projects):
                manage_project(projects[idx])
            else:
                print("  [!] Invalid index.")
                import time
                time.sleep(1)
        except ValueError:
            print("  [!] Invalid selection.")
            import time
            time.sleep(1)

def manage_project(name):
    path = os.path.join(PROJECTS_DIR, name)
    while True:
        try:
            with open(os.path.join(path, "project_state.json"), "r") as f:
                state = json.load(f)
        except Exception as e:
            print(f"[!] Error loading project state: {e}")
            input("\nPress Enter to return...")
            return
            
        splash.print_header(f"Workspace: {name}", path="SimGit")
        
        # Stats Block
        sto_count = len(os.listdir(os.path.join(path, "setups")))
        lap_count = len(os.listdir(os.path.join(path, "lapfiles")))
        baseline = os.path.basename(state['baseline']) if state['baseline'] else "None"
        
        print(f"  {C_INFO}Repository Status:{OpenDAV_RESET}")
        print(f"    Telemetry: {len(state['linked_files']):2} files | Setups: {sto_count:2} files | Ghost Laps: {lap_count:2} files")
        print(f"    Baseline:  {C_SUCCESS}{baseline}{OpenDAV_RESET}")
        print("  " + "─" * 98)
        
        print(f"  {C_INFO}[ DEVELOP ]{OpenDAV_RESET}")
        print(f"    {C_ACTION}1.{OpenDAV_RESET} Commit New Files          {C_ACTION}2.{OpenDAV_RESET} Individual Analysis")
        print(f"    {C_ACTION}3.{OpenDAV_RESET} Run Automated Workbook    {C_ACTION}4.{OpenDAV_RESET} View Setup Timeline")
        print(f"\n  {C_INFO}[ DEPLOY ]{OpenDAV_RESET}")
        print(f"    {C_ACTION}5.{OpenDAV_RESET} Install to iRacing        {C_ACTION}6.{OpenDAV_RESET} Change Baseline File")
        print(f"\n  {C_INFO}[ REMOTE ]{OpenDAV_RESET}")
        print(f"    {C_ACTION}7.{OpenDAV_RESET} Push to Team Cloud (Supabase)")
        print("  " + "─" * 98)
        
        choice = input(f"\n  Selection ({C_ACTION}number{OpenDAV_RESET}), or '{C_ACTION}p{OpenDAV_RESET}' for Repositories: ").strip().lower()
        if choice == 'p': break
        
        if choice == '1': commit_files(name, path, state)
        elif choice == '2': run_manual_analysis(name, state)
        elif choice == '3':
            from analysis.workflow_engine import execute_workflow
            execute_workflow(name, state)
            input("\nPress Enter to continue...")
        elif choice == '4': show_history(name)
        elif choice == '5': install_to_iracing(name, path)
        elif choice == '6': set_baseline(name, path, state)
        elif choice == '7':
            from core.cloud import OpenDAVCloud
            cloud = OpenDAVCloud()
            cloud.push_project(name, path)
            input("\nPress Enter to continue...")
        else:
            print("[!] Invalid selection.")
            time.sleep(1)

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

def run_manual_analysis(project_name, state):
    if not state['linked_files']:
        print("[!] No telemetry files committed to this project.")
        input("\nPress Enter to continue...")
        return
        
    while True:
        splash.print_header(f"Manual Analysis - {project_name}")
        for i, f in enumerate(state['linked_files']):
            print(f"  {i+1}. {os.path.basename(f)}")
        print("  p. Back")
        print("─" * 100)
        
        choice = input("\nSelect Primary Telemetry file: ").strip().lower()
        if choice == 'p': return
        
        try:
            idx = int(choice) - 1
            if not (0 <= idx < len(state['linked_files'])):
                print("[!] Invalid selection.")
                time.sleep(1)
                continue
            primary_path = state['linked_files'][idx]
        except ValueError:
            print("[!] Invalid selection.")
            time.sleep(1)
            continue
            
        print(f"\n[*] Loading {os.path.basename(primary_path)}...")
        from core.telemetry import load_telemetry
        data, limit, channels, metadata = load_telemetry(primary_path)
        sessions = [{'data': data, 'limit': limit, 'channels': channels, 'metadata': metadata, 'file_path': primary_path}]
        
        while True:
            splash.print_header(f"Manual Analysis", path=f"SimGit > {project_name}")
            print(f"  {C_INFO}Analyzing:{OpenDAV_RESET} {os.path.basename(primary_path)}")
            print(f"  {C_GOLD}[HINT]{OpenDAV_RESET} To save locally, use: {C_ACTION}print L1 < {project_name}{OpenDAV_RESET}")
            
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
                (11, "TLLTD Distribution", "Lateral load transfer distribution")
            ]
            
            print("  " + "─" * 98)
            for num, tool_name, desc in tools:
                print(f"    {C_ACTION}{num:2}.{OpenDAV_RESET} {tool_name.ljust(25)} {C_INFO}>> {desc}{OpenDAV_RESET}")
            print("  " + "─" * 98)
            
            tool_choice = input(f"\n  Select tool ({C_ACTION}number{OpenDAV_RESET}), or '{C_ACTION}p{OpenDAV_RESET}' to change file: ").strip().lower()
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
            else:
                print("[!] Invalid selection.")
                time.sleep(1)

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
            # p is just a folder name or project name from the DB
            print(f"    {i+1}. {p}")
        print("─" * 100)
        
        choice = input("\nSelect a project to download (number), or 'p' to go back: ").strip().lower()
        if choice == 'p': break
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(projects):
                target_project = projects[idx]
                
                # Check if it already exists locally
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
