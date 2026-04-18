with open('core/cloud.py', 'r') as f:
    content = f.read()

# Replace load_cloud_settings to use opendav_config.json or use core.config
new_load_logic = """    def load_cloud_settings(self):
        from core.config import load_config
        config = load_config()
        self.base_url = config.get("supabase_url", "")
        self.anon_key = config.get("supabase_key", "")"""

import re
content = re.sub(r'    def load_cloud_settings\(self\):[\s\S]*?self\.anon_key = data\.get\("supabase_key", ""\)', new_load_logic, content)

with open('core/cloud.py', 'w') as f:
    f.write(content)
