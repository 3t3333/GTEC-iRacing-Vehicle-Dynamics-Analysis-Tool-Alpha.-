import re

with open('core/cloud.py', 'r') as f:
    content = f.read()

# Force the load_token to extract the user_id from the JSON structure
old_load = """    def load_token(self):
        if os.path.exists(AUTH_FILE):
            with open(AUTH_FILE, 'r') as f:
                data = json.load(f)
                return data.get("access_token", "")
        return \"\"\" """

new_load = """    def load_token(self):
        if os.path.exists(AUTH_FILE):
            with open(AUTH_FILE, 'r') as f:
                data = json.load(f)
                # Extract the nested User ID from the Supabase token response
                self.user_id = data.get("user", {}).get("id", "")
                return data.get("access_token", "")
        return \"\"\" """

# Using a simpler string replacement to avoid regex issues
if 'return data.get("access_token", "")' in content and 'self.user_id =' not in content.split('def load_token')[1].split('return')[0]:
    content = content.replace('return data.get("access_token", "")', 'self.user_id = data.get("user", {}).get("id", "")\n                return data.get("access_token", "")')

# Also fix the settings menu logic to be more descriptive if it fails
with open('ui/settings.py', 'r') as f:
    s_content = f.read()

s_content = s_content.replace(
    'print("[!] Database Error: Are you sure you ran the \'simgit_setup.sql\' script in Supabase?")',
    'print(f"[!] Database Error (Admin ID: {cloud.user_id}): Either the table is empty or the SQL script failed.")'
)

with open('core/cloud.py', 'w') as f:
    f.write(content)
with open('ui/settings.py', 'w') as f:
    f.write(s_content)
