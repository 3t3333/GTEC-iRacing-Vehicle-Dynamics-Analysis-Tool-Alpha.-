import os
import sys
import yaml
from core.telemetry import get_static_val
import ui.splash as splash
from ui.metadata_printer import print_session_metadata

def format_yaml_value(val):
    if isinstance(val, dict):
        return ""
    if isinstance(val, list):
        return ", ".join(str(v) for v in val)
    return str(val)

def run_setup_viewer(sessions):
    while True:
        splash.print_header("Static Setup Viewer")
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            metadata = session.get('metadata', {})
            
            print(f"\nAnalyzing: {os.path.basename(file_path)}")
            print_session_metadata(data, session['channels'], metadata)
            
            # Check for iRacing YAML Setup
            yaml_str = metadata.get('session_info_yaml', '')
            found_yaml_setup = False
            
            if yaml_str:
                try:
                    # If it's bytes, decode it. We've seen this issue before.
                    if isinstance(yaml_str, bytes):
                        yaml_str = yaml_str.decode('utf-8', errors='ignore')
                        
                    y_data = yaml.safe_load(yaml_str)
                    if y_data and 'CarSetup' in y_data:
                        found_yaml_setup = True
                        setup = y_data['CarSetup']
                        
                        for section_name, section_data in setup.items():
                            if section_name == 'UpdateCount': continue
                            
                            print("\n ┌" + "─" * 55 + "┐")
                            print(" │ " + f"[ {section_name.upper()} ]".ljust(53) + " │")
                            
                            if isinstance(section_data, dict):
                                for k, v in section_data.items():
                                    if isinstance(v, dict):
                                        # Print sub-section header
                                        print(" │ " + f"  {k}:".ljust(53) + " │")
                                        for sub_k, sub_v in v.items():
                                            val_str = format_yaml_value(sub_v)
                                            print(" │ " + f"    {sub_k}: {val_str}".ljust(53) + " │")
                                    else:
                                        val_str = format_yaml_value(v)
                                        print(" │ " + f"  {k}: {val_str}".ljust(53) + " │")
                                        
                            print(" └" + "─" * 55 + "┘")
                except Exception as e:
                    pass
            
            # MoTeC / Traditional Telemetry Fallback
            if not found_yaml_setup:
                # Pressures
                fl_p = get_static_val(data, ['dpLFTireColdPress', 'LFcoldPressure'], multiplier=0.145038, fmt="{:.1f}", unit="psi")
                fr_p = get_static_val(data, ['dpRFTireColdPress', 'RFcoldPressure'], multiplier=0.145038, fmt="{:.1f}", unit="psi")
                rl_p = get_static_val(data, ['dpLRTireColdPress', 'LRcoldPressure'], multiplier=0.145038, fmt="{:.1f}", unit="psi")
                rr_p = get_static_val(data, ['dpRRTireColdPress', 'RRcoldPressure'], multiplier=0.145038, fmt="{:.1f}", unit="psi")
                
                # Ride heights
                fl_rh = get_static_val(data, ['Ride Height FL', 'LFrideHeight'], multiplier=1000, fmt="{:.1f}", unit="mm")
                fr_rh = get_static_val(data, ['Ride Height FR', 'RFrideHeight'], multiplier=1000, fmt="{:.1f}", unit="mm")
                rl_rh = get_static_val(data, ['Ride Height RL', 'LRrideHeight'], multiplier=1000, fmt="{:.1f}", unit="mm")
                rr_rh = get_static_val(data, ['Ride Height RR', 'RRrideHeight'], multiplier=1000, fmt="{:.1f}", unit="mm")
                
                # Brake Bias
                bb = get_static_val(data, ['dcBrakeBias', 'Brake Bias', 'BrakeBias'], fmt="{:.2f}", unit="%")
                
                # Compound
                comp = get_static_val(data, ['PlayerTireCompound', 'PitSvTireCompound'], fmt="{}", unit="")
                if comp == "0.0": comp = "Dry"
                elif comp == "1.0": comp = "Wet"

                # Try to get wing, camber, spring if they exist
                wing = get_static_val(data, ['RearWing', 'Rear Wing', 'WingAngle', 'RearWingAngle'], fmt="{:.1f}", unit="")
                fl_camb = get_static_val(data, ['Camber FL', 'LFcamber'], fmt="{:.2f}", unit="deg")
                fl_spring = get_static_val(data, ['Spring FL', 'LFspring'], fmt="{:.1f}", unit="N/mm")

                print("\n ┌" + "─" * 55 + "┐")
                print(" │ " + "[ TIRES & PRESSURES ]".ljust(53) + " │")
                print(" │ " + f"Compound:        {comp}".ljust(53) + " │")
                print(" │ " + f"Cold Pressures:  FL: {fl_p:<10} | FR: {fr_p}".ljust(53) + " │")
                print(" │ " + f"                 RL: {rl_p:<10} | RR: {rr_p}".ljust(53) + " │")
                print(" └" + "─" * 55 + "┘")
                print(" ┌" + "─" * 55 + "┐")
                print(" │ " + "[ AERODYNAMICS & CHASSIS ]".ljust(53) + " │")
                print(" │ " + f"Ride Heights:    FL: {fl_rh:<10} | FR: {fr_rh}".ljust(53) + " │")
                print(" │ " + f"                 RL: {rl_rh:<10} | RR: {rr_rh}".ljust(53) + " │")
                print(" │ " + f"Rear Wing:       {wing}".ljust(53) + " │")
                print(" └" + "─" * 55 + "┘")
                print(" ┌" + "─" * 55 + "┐")
                print(" │ " + "[ SUSPENSION & BRAKES ]".ljust(53) + " │")
                print(" │ " + f"Spring Rates:    {fl_spring}".ljust(53) + " │")
                print(" │ " + f"Camber:          {fl_camb}".ljust(53) + " │")
                print(" │ " + f"Brake Bias:      {bb}".ljust(53) + " │")
                print(" └" + "─" * 55 + "┘")

        print("\n" + "─"*100)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break
