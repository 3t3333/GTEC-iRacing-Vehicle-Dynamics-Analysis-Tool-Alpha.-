import os
import sys
import time
import re
import builtins
import matplotlib.pyplot as plt

import ui.splash as splash
from core.config import load_config, save_config, get_gui_mode, set_gui_mode

from analysis.roll_gradient import run_roll_analysis
from analysis.setup_viewer import run_setup_viewer
from analysis.aero_rake import run_rake_analysis
from analysis.tire_performance import run_tire_analysis, run_sector_tire_analysis
from analysis.fuel_correlation import run_fuel_analysis
from analysis.math_sandbox import run_custom_math_graph

def run_automator(sessions):
    original_input = builtins.input
    original_show = plt.show
    original_clear = splash.clear_screen
    
    while True:
        splash.print_header("Preset Automator (Batch Reporting)")
        
        config = load_config()
        presets = config.get('presets', {})
        
        print("  Available Presets:")
        if not presets:
            print("    [No presets found]")
        else:
            for n, preset_val in presets.items():
                tools_str = preset_val if isinstance(preset_val, str) else preset_val.get('tools', '')
                print(f"    - {n}: [{tools_str}]")
                
        print("═" * 64)
        print("  Commands:")
        print("  'run [name]'    : Run a saved preset")
        print("  'new [name]'    : Create a new preset")
        print("  'delete [name]' : Delete a preset")
        print("  'p'             : Back to Tools Menu")
        
        cmd = original_input("\nEnter command: ").strip()
        if cmd.lower() == 'p':
            break
            
        parts = cmd.split(" ", 1)
        action = parts[0].lower()
        name = parts[1].strip() if len(parts) > 1 else ""
        
        if action == 'new' and name:
            print("\n  Available Tools (You can select any of these 9 tools):")
            print("  1: Roll Gradient, 2: Setup Viewer, 3: Aero/Rake")
            print("  4: Tire Temp, 5: Fuel Correlation, 6: Sector Tire Temp")
            print("  7: Custom Sandbox, 8: Preset Automator (N/A), 9: Setup Prediction Engine")
            tools_str = original_input("  Enter tools to run as comma-separated numbers (e.g. '1,4,7' or '1,2,3,4,5,6,7,9'): ").strip()
            valid = True
            for t in tools_str.split(','):
                if t.strip() not in ['1','2','3','4','5','6','7','9']:
                    valid = False
            if valid:
                preset_data = {'tools': tools_str.replace(" ", "")}
                if '9' in preset_data['tools'].split(','):
                    print("\n  [Setup Prediction Engine Selected]")
                    farb_changes = []
                    for i in range(3):
                        c = original_input(f"  Enter FARB change {i+1}/3 (e.g., 'farb +10'): ").strip()
                        farb_changes.append(c)
                    rarb_changes = []
                    for i in range(3):
                        c = original_input(f"  Enter RARB change {i+1}/3 (e.g., 'rarb -5'): ").strip()
                        rarb_changes.append(c)
                    preset_data['setup_changes'] = farb_changes + rarb_changes
                presets[name] = preset_data
                config['presets'] = presets
                save_config(config)
                print(f"  [+] Preset '{name}' saved.")
            else:
                print("  [!] Invalid tool numbers.")
            time.sleep(1)
            continue
            
        elif action == 'delete' and name:
            if name in presets:
                del presets[name]
                config['presets'] = presets
                save_config(config)
                print(f"  [+] Preset '{name}' deleted.")
            else:
                print(f"  [!] Preset '{name}' not found.")
            time.sleep(1)
            continue
            
        elif action == 'run' and name:
            if name not in presets:
                print(f"  [!] Preset '{name}' not found.")
                time.sleep(1)
                continue
                
            preset_val = presets[name]
            if isinstance(preset_val, str):
                tools_to_run = [t.strip() for t in preset_val.split(',')]
                setup_changes = []
            else:
                tools_to_run = [t.strip() for t in preset_val.get('tools', '').split(',')]
                setup_changes = preset_val.get('setup_changes', [])
            
            # Setup Automator Mode
            old_gui_mode = get_gui_mode()
            set_gui_mode(1) # Force Matplotlib for background saving
            
            # Create report directory
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            base_name = os.path.basename(sessions[0]['file_path']).replace('.ld','').replace('.id','')
            report_dir = os.path.join("telemetry", "Reports", f"{base_name}_{timestamp}")
            os.makedirs(report_dir, exist_ok=True)
            
            report_file_path = os.path.join(report_dir, "report.txt")
            report_file = open(report_file_path, "w", encoding='utf-8')
            
            class TeeLogger:
                def __init__(self, file):
                    self.file = file
                    self.terminal = sys.stdout
                def write(self, message):
                    clean_msg = re.sub(r'\033\[[0-9;]*m', '', message)
                    self.file.write(clean_msg)
                    self.terminal.write(message)
                def flush(self):
                    self.file.flush()
                    self.terminal.flush()
                    
            sys.stdout = TeeLogger(report_file)
            
            def automator_clear():
                pass
            splash.clear_screen = automator_clear
            
            def automator_plt_show(*args, **kwargs):
                fig = plt.gcf()
                title = fig.canvas.manager.get_window_title() if fig.canvas.manager else "Graph"
                safe_title = re.sub(r'[^A-Za-z0-9_\-\. ]', '_', title.replace('\n', ' '))
                filename = os.path.join(report_dir, f"{safe_title}_{time.time()}.png")
                plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
                plt.close(fig)

            plt.show = automator_plt_show
            
            automator_state = {}
            current_tool = ""
            
            def automator_input(prompt=""):
                prompt_lower = prompt.lower()
                sys.stdout.write(prompt + "\n")
                
                if 'change:' in prompt_lower:
                    return automator_state.get('current_change', 'p')
                    
                if 'enter window' in prompt_lower:
                    if automator_state.get(f"{current_tool}_window_asked", False):
                        return 'p'
                    automator_state[f"{current_tool}_window_asked"] = True
                    return 'fl'
                    
                if 'enter formula' in prompt_lower:
                    if automator_state.get(f"{current_tool}_formula_asked", False):
                        return 'p'
                    automator_state[f"{current_tool}_formula_asked"] = True
                    return '[Ground Speed]'
                
                if 'launch' in prompt_lower and '(y/n)' in prompt_lower:
                    return 'y'
                    
                return ''
                
            builtins.input = automator_input
            
            print("═"*64)
            print(f" GTEC AUTOMATED REPORT: Preset '{name}'")
            print(f" Generated: {time.ctime()}")
            print("═"*64)
            
            try:
                tool_names = {
                    '1': 'Roll Gradient Analysis',
                    '2': 'Static Setup Viewer',
                    '3': 'Dynamic Aero/Rake Analyzer',
                    '4': 'Tire Temp & Pressure',
                    '5': 'Fuel & Setup Correlation',
                    '6': 'Sector Tire Temp Graph',
                    '7': 'Custom Sandbox',
                    '9': 'Setup Prediction Engine'
                }
                for t in tools_to_run:
                    current_tool = t
                    automator_state.clear()
                    t_name = tool_names.get(t, f'Tool {t}')
                    print(f"\n\n[{t_name}]")
                    print("-" * len(f"[{t_name}]"))
                    if t == '1': run_roll_analysis(sessions)
                    elif t == '2': run_setup_viewer(sessions)
                    elif t == '3': run_rake_analysis(sessions)
                    elif t == '4': run_tire_analysis(sessions)
                    elif t == '5': run_fuel_analysis(sessions)
                    elif t == '6': run_sector_tire_analysis(sessions)
                    elif t == '7': run_custom_math_graph(sessions)
                    elif t == '9':
                        from analysis.setup_prediction import run_setup_prediction_engine
                        if not setup_changes:
                            print("  [!] No setup changes saved in preset. Skipping tool 9.")
                            continue
                        for change in setup_changes:
                            automator_state.clear()
                            print(f"\n--- Applying Prediction Change: {change} ---")
                            automator_state['current_change'] = change
                            run_setup_prediction_engine(sessions)
            except Exception as e:
                print(f"\n[!] Automator Error: {e}")
                
            # Cleanup
            sys.stdout = sys.stdout.terminal
            report_file.close()
            
            builtins.input = original_input
            plt.show = original_show
            splash.clear_screen = original_clear
            set_gui_mode(old_gui_mode)
            
            print(f"\n\n[+] Report complete! Saved to: {report_dir}\n")
            original_input("Press Enter to continue...")
