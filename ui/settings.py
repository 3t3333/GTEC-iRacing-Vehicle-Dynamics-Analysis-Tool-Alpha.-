import sys
import os
import time

from core.config import get_gui_mode, set_gui_mode, get_data_mode, set_data_mode, save_config, load_config
import ui.splash as splash

def show_settings():
    while True:
        splash.clear_screen()
        splash.print_header("Settings")
        
        gui_mode = get_gui_mode()
        data_mode = get_data_mode()
        
        gui_str = "Legacy (Matplotlib)" if gui_mode == 1 else "Plotly (Web Interactive)" if gui_mode == 2 else "CustomTkinter (Desktop)"
        data_str = "Auto-Detect" if data_mode == 1 else "Strict MoTeC (.ld)" if data_mode == 2 else "Strict iRacing (.ibt)"
        
        print(f"  1. GUI Mode: \033[1;36m{gui_str}\033[0m")
        print(f"  2. Data Source Mode: \033[1;36m{data_str}\033[0m")
        print(f"  3. OpenDAV Cloud: Login / Sync")
        print(f"  4. Supabase API Settings")
        print(f"  5. [Admin] Manage SimGit Team Access")
        print("─" * 100)
        
        choice = input("\nSelect a setting to change, or 'b' to go back: ").strip().lower()
        
        if choice == 'b':
            break
            
        elif choice == '1':
            print("\n  [1] Legacy Matplotlib (Dark Theme)")
            print("  [2] Plotly (Interactive HTML)")
            print("  [3] CustomTkinter (Desktop GUI)")
            new_mode = input("  Select GUI Mode: ").strip()
            if new_mode in ['1', '2', '3']:
                set_gui_mode(int(new_mode))
                config = load_config()
                config['gui_mode'] = int(new_mode)
                save_config(config)
                print("  [+] GUI Mode saved.")
                time.sleep(0.5)
                
        elif choice == '2':
            print("\n  [1] Auto-Detect (.ld and .ibt)")
            print("  [2] Strict MoTeC (.ld only)")
            print("  [3] Strict iRacing (.ibt only)")
            new_mode = input("  Select Data Mode: ").strip()
            if new_mode in ['1', '2', '3']:
                set_data_mode(int(new_mode))
                config = load_config()
                config['data_mode'] = int(new_mode)
                save_config(config)
                print("  [+] Data Source Mode saved.")
                time.sleep(0.5)
                
        elif choice == '3':
            from core.cloud import OpenDAVCloud
            cloud = OpenDAVCloud()
            if cloud.is_logged_in():
                print(f"\n  Status: Logged In")
                ans = input("  Would you like to logout? (y/n): ").strip().lower()
                if ans == 'y':
                    cloud.logout()
            else:
                print(f"\n  Status: Not Logged In")
                print("  [1] Login")
                print("  [2] Create New Account")
                print("  [p] Cancel")
                action = input("\n  Action: ").strip().lower()
                
                if action == '1':
                    email = input("  Email: ").strip()
                    password = input("  Password: ").strip()
                    cloud.login(email, password)
                elif action == '2':
                    email = input("  New Email: ").strip()
                    password = input("  New Password (min 6 chars): ").strip()
                    cloud.signup(email, password)
            input("\nPress Enter to continue...")

        elif choice == '4':
            config = load_config()
            print(f"\n  Current Supabase URL: {config.get('supabase_url', 'Not Set')}")
            url = input("  New Supabase URL (Enter to skip): ").strip()
            if url: config['supabase_url'] = url
            
            print(f"  Current Public API Key: {'*' * 20 if config.get('supabase_key') else 'Not Set'}")
            key = input("  New Public API Key (Enter to skip): ").strip()
            if key: config['supabase_key'] = key
            
            save_config(config)
            print("  [+] API Settings saved.")
            time.sleep(1)
        elif choice == '5':
            from core.cloud import OpenDAVCloud
            cloud = OpenDAVCloud()
            if not cloud.is_logged_in():
                print("\n[!] You must be logged in to manage team access.")
                time.sleep(1)
                continue
                
            print("\n[*] Connecting to SimGit Database...")
            import requests
            headers = {"apikey": cloud.anon_key, "Authorization": f"Bearer {cloud.token}"}
            
            # 1. Verify this user is an admin
            try:
                me_res = requests.get(f"{cloud.base_url}/rest/v1/team_members?id=eq.{cloud.user_id}", headers=headers)
                if me_res.status_code == 200 and me_res.json():
                    if me_res.json()[0].get('role') != 'admin':
                        print("[!] Access Denied: You must be a Team Admin to use this menu.")
                        input("\nPress Enter to return...")
                        continue
                else:
                    # If the table doesn't exist or they aren't in it, the SQL script hasn't been run.
                    print("[!] Database Error: Are you sure you ran the 'simgit_setup.sql' script in Supabase?")
                    input("\nPress Enter to return...")
                    continue
            except Exception as e:
                print(f"[!] Network error verifying admin status: {e}")
                time.sleep(1)
                continue
                
            # 2. Fetch all team members
            while True:
                splash.print_header("SimGit Team Management")
                res = requests.get(f"{cloud.base_url}/rest/v1/team_members", headers=headers)
                if res.status_code != 200:
                    print(f"[!] Failed to fetch team members: {res.text}")
                    break
                    
                members = res.json()
                pending = [m for m in members if m['role'] == 'pending']
                approved = [m for m in members if m['role'] in ['approved', 'admin']]
                
                print("  [ PENDING APPROVALS ]")
                if not pending: print("    None.")
                for i, p in enumerate(pending):
                    print(f"    {i+1}. {p['email']} (Status: {p['role']})")
                    
                print("\n  [ ACTIVE TEAM ]")
                if not approved: print("    None.")
                for i, a in enumerate(approved):
                    print(f"    {i+1 + len(pending)}. {a['email']} (Role: {a['role']})")
                    
                print("─" * 100)
                action = input("\nSelect a user to manage (number), or 'p' to go back: ").strip().lower()
                
                if action == 'p': break
                try:
                    idx = int(action) - 1
                    all_users = pending + approved
                    if not (0 <= idx < len(all_users)):
                        print("  [!] Invalid selection.")
                        time.sleep(1)
                        continue
                        
                    target = all_users[idx]
                    
                    if target['id'] == cloud.user_id:
                        print("  [!] You cannot modify your own permissions here.")
                        time.sleep(1)
                        continue
                        
                    print(f"\n  Managing User: {target['email']}")
                    print("  1. Approve Access (Allow Push/Pull)")
                    print("  2. Revoke Access / Set to Pending")
                    print("  3. Delete User entirely")
                    print("  c. Cancel")
                    
                    cmd = input("\n  Action: ").strip().lower()
                    if cmd == 'c': continue
                    
                    if cmd == '1':
                        patch_res = requests.patch(
                            f"{cloud.base_url}/rest/v1/team_members?id=eq.{target['id']}", 
                            headers=headers, 
                            json={"role": "approved"}
                        )
                        if patch_res.status_code in [200, 204]: print("  [+] User approved!")
                        else: print(f"  [!] Error: {patch_res.text}")
                        
                    elif cmd == '2':
                        patch_res = requests.patch(
                            f"{cloud.base_url}/rest/v1/team_members?id=eq.{target['id']}", 
                            headers=headers, 
                            json={"role": "pending"}
                        )
                        if patch_res.status_code in [200, 204]: print("  [+] Access revoked.")
                        else: print(f"  [!] Error: {patch_res.text}")
                        
                    elif cmd == '3':
                        del_res = requests.delete(
                            f"{cloud.base_url}/rest/v1/team_members?id=eq.{target['id']}", 
                            headers=headers
                        )
                        if del_res.status_code in [200, 204]: print("  [+] User deleted.")
                        else: print(f"  [!] Error: {del_res.text}")
                        
                    time.sleep(1)
                except ValueError:
                    print("  [!] Invalid selection.")
                    time.sleep(1)
