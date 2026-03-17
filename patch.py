import re

with open('/mnt/d/gtec/gtecsectortool.py', 'r') as f:
    content = f.read()

# Replace run_sector_analysis
old_rsa = """def run_sector_analysis(data, limit, channels, file_path):
    while True:
        clear_screen()
        print("="*60)
        print(f" GteC | Limit: {limit:.3f}G")
        print("="*60)
        print(f" File: {file_path}")
        print(f" Tool: Sector Analysis")
        print("-" * 60)
        
        try:
            inp = input("\\nEnter window (e.g., '142-316'), 'p' for Tools Menu, or 'q' to quit: ").strip().lower()
            if inp == 'q':
                show_exit_screen()
                sys.exit(0)
            if inp == 'p':
                break
            
            if '-' not in inp:
                print("[!] Invalid format. Use 'Start-End'.")
                input("\\nPress Enter to try again...")
                continue
                
            start_m, end_m = map(float, inp.split('-'))
            
            results = perform_analysis(data, limit, channels, start_m, end_m)
            
            if not results:
                print(f"\\n[!] No data found for range {start_m}m to {end_m}m.")
            else:
                print(f"\\nRESULTS FOR {start_m}m to {end_m}m:")
                print("-" * 55)
                print(f"{'Lap':<6} | {'Time (s)':<10} | {'Peak Util%':<12} | {'Avg Util%':<10}")
                print("-" * 55)
                
                # Use median to avoid unusually slow laps (spins/traffic) skewing the threshold
                median_time = np.median([r['Time'] for r in results])
                valid_times = [r['Time'] for r in results if r['Time'] >= median_time * 0.89]
                fastest_time = min(valid_times) if valid_times else None
                
                PINK = '\\033[95m'
                RESET = '\\033[0m'
                
                for r in sorted(results, key=lambda x: x['Time']):
                    row_str = f"{r['Lap']:<6} | {r['Time']:<10.3f} | {r['Peak']:<11.1f}% | {r['Avg']:<10.1f}%"
                    if r['Time'] == fastest_time:
                        print(f"{PINK}{row_str} < FASTEST{RESET}")
                    else:
                        print(row_str)
                
            input("\\nPress Enter for a new analysis...")
            
        except ValueError:
            print("[!] Please enter valid numbers.")
            input("\\nPress Enter to try again...")
        except KeyboardInterrupt:
            sys.exit(0)"""

new_rsa = """def run_sector_analysis(sessions):
    while True:
        clear_screen()
        print("="*60)
        if len(sessions) == 1:
            print(f" GteC | Limit: {sessions[0]['limit']:.3f}G")
            print("="*60)
            print(f" File: {sessions[0]['file_path']}")
        else:
            print(f" GteC | Multi-File Sector Analysis")
            print("="*60)
            print(f" Comparing {len(sessions)} files")
        print(f" Tool: Sector Analysis")
        print("-" * 60)
        
        try:
            inp = input("\\nEnter window (e.g., '142-316'), 'p' for Tools Menu, or 'q' to quit: ").strip().lower()
            if inp == 'q':
                show_exit_screen()
                sys.exit(0)
            if inp == 'p':
                break
            
            if '-' not in inp:
                print("[!] Invalid format. Use 'Start-End'.")
                input("\\nPress Enter to try again...")
                continue
                
            start_m, end_m = map(float, inp.split('-'))
            
            for session in sessions:
                data = session['data']
                limit = session['limit']
                channels = session['channels']
                file_path = session['file_path']
                
                results = perform_analysis(data, limit, channels, start_m, end_m)
                
                if not results:
                    print(f"\\n[!] No data found for {os.path.basename(file_path)} in range {start_m}m to {end_m}m.")
                else:
                    print(f"\\nRESULTS FOR {os.path.basename(file_path)} ({start_m}m to {end_m}m):")
                    print("-" * 55)
                    print(f"{'Lap':<6} | {'Time (s)':<10} | {'Peak Util%':<12} | {'Avg Util%':<10}")
                    print("-" * 55)
                    
                    # Use median to avoid unusually slow laps (spins/traffic) skewing the threshold
                    import numpy as np
                    median_time = np.median([r['Time'] for r in results])
                    valid_times = [r['Time'] for r in results if r['Time'] >= median_time * 0.89]
                    fastest_time = min(valid_times) if valid_times else None
                    
                    PINK = '\\033[95m'
                    RESET = '\\033[0m'
                    
                    for r in sorted(results, key=lambda x: x['Time']):
                        row_str = f"{r['Lap']:<6} | {r['Time']:<10.3f} | {r['Peak']:<11.1f}% | {r['Avg']:<10.1f}%"
                        if r['Time'] == fastest_time:
                            print(f"{PINK}{row_str} < FASTEST{RESET}")
                        else:
                            print(row_str)
                
            input("\\nPress Enter for a new analysis...")
            
        except ValueError:
            print("[!] Please enter valid numbers.")
            input("\\nPress Enter to try again...")
        except KeyboardInterrupt:
            sys.exit(0)"""

content = content.replace(old_rsa, new_rsa)

# Replace main() menu part
old_main_menu = """        clear_screen()
        print("="*60)
        print(" Gtec | Telemetry Archive")
        print("="*60)
        for i, info in enumerate(file_infos):
            print(f"  {i + 1}. {info}")
        print("-" * 60)
        
        file_path = None
        while True:
            choice = input("\\nSelect a file to analyze (number) or 'q' to quit: ").strip().lower()
            if choice == 'q':
                show_exit_screen()
                return
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(ld_files):
                    file_path = os.path.join(telemetry_dir, ld_files[choice_idx])
                    break
                else:
                    print("[!] Invalid selection.")
            except ValueError:
                print("[!] Please enter a valid number.")
                
        clear_screen()
        data, limit, channels = load_telemetry(file_path)
        
        while True:
            clear_screen()
            print("="*60)
            print(" GteC | Analysis Tools")
            print("="*60)
            print(f" File: {file_path}")
            print("-" * 60)
            print("  1. Sector Analysis")
            print("-" * 60)
            
            tool_choice = input("\\nSelect a tool (number), 'p' for Main Menu, or 'q' to quit: ").strip().lower()
            if tool_choice == 'q':
                show_exit_screen()
                return
            if tool_choice == 'p':
                break
                
            if tool_choice == '1':
                run_sector_analysis(data, limit, channels, file_path)
            else:
                print("[!] Invalid selection.")
                input("\\nPress Enter to try again...")"""

new_main_menu = """        clear_screen()
        print("="*60)
        print(" GteC | Session Type Selection")
        print("="*60)
        print("  1. Single File Analysis")
        print("  2. Multi-File Comparison")
        print("-" * 60)
        
        session_choice = input("\\nSelect session type (number) or 'q' to quit: ").strip().lower()
        if session_choice == 'q':
            show_exit_screen()
            return
        if session_choice not in ('1', '2'):
            print("[!] Invalid selection.")
            time.sleep(1)
            continue
            
        is_multi = (session_choice == '2')
        selected_files = []
        
        if not is_multi:
            clear_screen()
            print("="*60)
            print(" Gtec | Telemetry Archive")
            print("="*60)
            for i, info in enumerate(file_infos):
                print(f"  {i + 1}. {info}")
            print("-" * 60)
            
            while True:
                choice = input("\\nSelect a file to analyze (number) or 'q' to quit: ").strip().lower()
                if choice == 'q':
                    show_exit_screen()
                    sys.exit(0)
                try:
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(ld_files):
                        selected_files.append(os.path.join(telemetry_dir, ld_files[choice_idx]))
                        break
                    else:
                        print("[!] Invalid selection.")
                except ValueError:
                    print("[!] Please enter a valid number.")
        else:
            while True:
                clear_screen()
                print("="*60)
                print(" Gtec | Telemetry Archive (Multi-File)")
                print("="*60)
                for i, info in enumerate(file_infos):
                    print(f"  {i + 1}. {info}")
                print("-" * 60)
                if selected_files:
                    print(f"\\nCurrently selected ({len(selected_files)}):")
                    for sf in selected_files:
                        print(f"  - {os.path.basename(sf)}")
                
                print("\\nOptions:")
                print("  [Number] Select file to add")
                print("  [d]      Information sum met (done selecting)")
                print("  [q]      Quit")
                
                choice = input("\\nSelect an option: ").strip().lower()
                if choice == 'q':
                    show_exit_screen()
                    sys.exit(0)
                if choice == 'd':
                    if len(selected_files) < 2:
                        print("[!] Please select at least two files for comparison.")
                        time.sleep(1)
                        continue
                    break
                    
                try:
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(ld_files):
                        file_path = os.path.join(telemetry_dir, ld_files[choice_idx])
                        if file_path not in selected_files:
                            selected_files.append(file_path)
                        else:
                            print("[!] File already selected.")
                            time.sleep(1)
                    else:
                        print("[!] Invalid selection.")
                        time.sleep(1)
                except ValueError:
                    print("[!] Please enter a valid option.")
                    time.sleep(1)

        clear_screen()
        sessions = []
        for file_path in selected_files:
            data, limit, channels = load_telemetry(file_path)
            sessions.append({
                'data': data,
                'limit': limit,
                'channels': channels,
                'file_path': file_path
            })
        
        while True:
            clear_screen()
            print("="*60)
            print(" GteC | Analysis Tools")
            print("="*60)
            if len(sessions) == 1:
                print(f" File: {sessions[0]['file_path']}")
            else:
                print(f" Comparing {len(sessions)} files")
            print("-" * 60)
            print("  1. Sector Analysis")
            print("-" * 60)
            
            tool_choice = input("\\nSelect a tool (number), 'p' for Main Menu, or 'q' to quit: ").strip().lower()
            if tool_choice == 'q':
                show_exit_screen()
                return
            if tool_choice == 'p':
                break
                
            if tool_choice == '1':
                run_sector_analysis(sessions)
            else:
                print("[!] Invalid selection.")
                input("\\nPress Enter to try again...")"""

content = content.replace(old_main_menu, new_main_menu)

with open('/mnt/d/gtec/gtecsectortool.py', 'w') as f:
    f.write(content)
