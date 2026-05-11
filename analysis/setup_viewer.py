import os
import sys
import yaml
import re
from core.telemetry import load_telemetry
import ui.splash as splash
from ui.tui_engine import get_tui_choice

BLUE = '\033[94m'
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'

def extract_flat_setup(y_str):
    if not y_str: return {}
    try:
        if isinstance(y_str, bytes):
            y_str = y_str.decode('utf-8', errors='ignore')
        y = yaml.safe_load(y_str)
        if not y or 'CarSetup' not in y: return {}
        
        setup = y['CarSetup']
        flat = {}
        def recurse(d, prefix=""):
            if isinstance(d, dict):
                for k, v in d.items():
                    if k in ("UpdateCount", "LastTempsOMI", "LastTempsIMO", "TreadRemaining", "CornerWeight"): continue
                    recurse(v, f"{prefix}{k}." if prefix else f"{k}.")
            else: flat[prefix[:-1]] = d
        recurse(setup)
        return flat
    except:
        return {}

def get_raw_setup_dict(y_str):
    if not y_str: return {}
    try:
        if isinstance(y_str, bytes):
            y_str = y_str.decode('utf-8', errors='ignore')
        y = yaml.safe_load(y_str)
        if not y or 'CarSetup' not in y: return {}
        return y['CarSetup']
    except:
        return {}

def categorize_changes(flat1, flat2):
    changes = []
    diffs = {}
    for k in set(flat1.keys()).union(flat2.keys()):
        v1 = flat1.get(k, None)
        v2 = flat2.get(k, None)
        if str(v1) != str(v2):
            diffs[k] = (v1, v2)
            k_lower = k.lower()
            if any(x in k_lower for x in ['wing', 'aero', 'spoiler', 'splitter', 'downforce', 'flap']):
                changes.append("Aero changes")
            elif any(x in k_lower for x in ['spring', 'shock', 'roll', 'camber', 'toe', 'rideheight', 'arb', 'stiff', 'perch', 'heave']):
                changes.append("Suspension changes")
            elif any(x in k_lower for x in ['tire', 'press', 'compound', 'friction']):
                changes.append("Tire changes")
            elif any(x in k_lower for x in ['brake', 'bias', 'pad']):
                changes.append("Brake changes")
            elif any(x in k_lower for x in ['fuel', 'engine', 'diff', 'gear', 'preload']):
                changes.append("Drivetrain changes")
            else:
                changes.append("Chassis changes")
                
    return list(set(changes)), diffs

def extract_num(s):
    if s is None: return None
    match = re.search(r'-?\d+\.?\d*', str(s))
    if match: return float(match.group())
    return None

def format_delta(k, v1, v2):
    n1 = extract_num(v1)
    n2 = extract_num(v2)
    short_k = k.split('.')[-1]
    if n1 is not None and n2 is not None:
        diff = n2 - n1
        if diff > 0:
            return f"{short_k}: {v1} -> {v2} {GREEN}(+{diff:g}){RESET}"
        elif diff < 0:
            return f"{short_k}: {v1} -> {v2} {RED}({diff:g}){RESET}"
    return f"{short_k}: {v1} -> {v2} {BLUE}(Changed){RESET}"

def dict_to_lines(d, diffs, prefix="", indent=0):
    lines = []
    for k, v in d.items():
        if k in ("UpdateCount", "LastTempsOMI", "LastTempsIMO", "TreadRemaining", "CornerWeight"): continue
        full_key = f"{prefix}{k}" if prefix else k
        
        if isinstance(v, dict):
            lines.append(" " * indent + f"{k}:")
            lines.extend(dict_to_lines(v, diffs, f"{full_key}.", indent + 2))
        else:
            if isinstance(v, list):
                v_str = ", ".join(str(x) for x in v)
            else:
                v_str = str(v)
                
            if full_key in diffs:
                lines.append(" " * indent + f"{k}: {BLUE}{v_str}{RESET}")
            else:
                lines.append(" " * indent + f"{k}: {v_str}")
    return lines

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def pad_line(line, width):
    plen = len(strip_ansi(line))
    if plen < width:
        return line + " " * (width - plen)
    return line

def run_setup_history(project_name, state):
    project_files = state.get('linked_files', [])
    if not project_files:
        print("  [!] No files linked to this project.")
        input("\nPress Enter to return...")
        return
        
    print("\n  [*] Loading Setup History...")
    setups_data = []
    
    for fp in project_files:
        try:
            _, _, _, md = load_telemetry(fp, meta_only=True)
            y_str = md.get('session_info_yaml', '')
            flat = extract_flat_setup(y_str)
            raw = get_raw_setup_dict(y_str)
            setups_data.append({
                'file': os.path.basename(fp),
                'flat': flat,
                'raw': raw
            })
        except:
            pass

    if len(setups_data) == 0:
        print("  [!] No valid setup data found.")
        input("\nPress Enter to return...")
        return

    while True:
        splash.print_header("Setup History Viewer", path=f"SimGit > {project_name}")
        
        menu_items = []
        for i, sd in enumerate(setups_data):
            if i == 0:
                menu_items.append((i+1, sd['file'], "Baseline Setup (No previous reference)"))
            else:
                changes, diffs = categorize_changes(setups_data[i-1]['flat'], sd['flat'])
                if changes:
                    desc = ", ".join(changes)
                else:
                    desc = "No changes detected"
                menu_items.append((i+1, sd['file'], desc))
                
        menu_items.append(('p', "Back", "Return to Tools Menu"))
        
        choice = get_tui_choice(menu_items)
        if choice == 'p': break
        
        idx = int(choice) - 1
        
        if idx == 0:
            print(f"\n  [!] '{setups_data[idx]['file']}' is the baseline.")
            print("      Select a later iteration to compare changes.")
            input("\nPress Enter to continue...")
            continue
            
        prev_data = setups_data[idx-1]
        curr_data = setups_data[idx]
        
        changes, diffs = categorize_changes(prev_data['flat'], curr_data['flat'])
        
        splash.clear_screen()
        print("\n" + "═" * 100)
        print(f" SETUP ITERATION COMPARISON".center(100))
        print("═" * 100)
        print(f" Previous: {prev_data['file']}")
        print(f" New:      {curr_data['file']}")
        print("─" * 100)
        
        if not diffs:
            print("\n  [!] No setup changes detected between these two files.")
            input("\nPress Enter to return to History Viewer...")
            continue
            
        print(f"\n {BLUE}[ CHANGED PARAMETERS ]{RESET}")
        for k, (v1, v2) in diffs.items():
            print(f"   • {format_delta(k, v1, v2)}")
            
        print("\n")
        
        left_lines = dict_to_lines(prev_data['raw'], diffs)
        right_lines = dict_to_lines(curr_data['raw'], diffs)
        
        max_lines = max(len(left_lines), len(right_lines))
        
        print(" ┌" + "─" * 43 + "┐     ┌" + "─" * 43 + "┐")
        print(" │ PREVIOUS SETUP" + " " * 27 + "│ ==> │ NEW SETUP" + " " * 32 + "│")
        print(" ├" + "─" * 43 + "┤     ├" + "─" * 43 + "┤")
        
        for i in range(max_lines):
            l_str = left_lines[i] if i < len(left_lines) else ""
            r_str = right_lines[i] if i < len(right_lines) else ""
            
            l_pad = pad_line(l_str, 41)
            r_pad = pad_line(r_str, 41)
            
            print(f" │ {l_pad} │     │ {r_pad} │")
            
        print(" └" + "─" * 43 + "┘     └" + "─" * 43 + "┘")
        
        print("\n" + "─" * 100)
        input("Press Enter to return to History Viewer...")
