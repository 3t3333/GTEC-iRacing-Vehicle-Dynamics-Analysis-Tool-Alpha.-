import re

with open('core/telemetry.py', 'r') as f:
    content = f.read()

# We need to make sure the yaml string is correctly injected into metadata during load_telemetry
if "'session_info_yaml':" not in content:
    old_block = """
        if file_path.lower().endswith('.ibt'):
            metadata['driver'] = getattr(data.head, 'driver', 'iRacing User')
            metadata['car'] = getattr(data.head, 'vehicleid', 'iRacing Car')
            metadata['venue'] = getattr(data.head, 'venue', 'iRacing Track')
        else:"""
        
    new_block = """
        if file_path.lower().endswith('.ibt'):
            metadata['driver'] = getattr(data.head, 'driver', 'iRacing User')
            metadata['car'] = getattr(data.head, 'vehicleid', 'iRacing Car')
            metadata['venue'] = getattr(data.head, 'venue', 'iRacing Track')
            # Critical fix: Pass the yaml string directly into the metadata dict
            metadata['session_info_yaml'] = getattr(data.head, 'session_info_yaml', '')
        else:"""
    content = content.replace(old_block, new_block)
    
    with open('core/telemetry.py', 'w') as f:
        f.write(content)
    print("Patched core/telemetry.py")
else:
    print("Already patched")
