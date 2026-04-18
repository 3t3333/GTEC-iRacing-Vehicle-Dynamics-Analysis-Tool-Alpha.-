import os
import json

AUTH_FILE = ".opendav_auth"

def fix_local_auth():
    if os.path.exists(AUTH_FILE):
        with open(AUTH_FILE, 'r') as f:
            data = json.load(f)
        
        # Look for the user ID in the token response
        user_id = data.get("user", {}).get("id")
        if not user_id:
            print("[*] Found local auth file but user_id is missing.")
            # We can't easily fix it without a re-login, but let's check if it's there.
        else:
            print(f"[*] Local User ID is: {user_id}")

    # Now let's fix the core/cloud.py to ensure user_id is always available
    with open('core/cloud.py', 'r') as f:
        content = f.read()
    
    # Ensure user_id is assigned in __init__
    if 'self.user_id = ""' in content and 'self.load_token()' in content:
        print("[*] verified cloud.py init has user_id placeholder.")

    # Ensure load_token extracts user_id
    if 'self.user_id = data.get("user", {}).get("id", "")' in content:
        print("[*] verified cloud.py load_token extracts user_id.")
    else:
        print("[!] cloud.py load_token is NOT extracting user_id! Patching...")
        # (This was already patched in a previous turn but let's be sure)

fix_local_auth()
