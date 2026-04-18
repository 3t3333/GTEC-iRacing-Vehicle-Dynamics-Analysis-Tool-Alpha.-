import os
from core import ibt_adapter
import yaml

file_path = 'webanalysisfeature/lap.ibt'
data = ibt_adapter.fromfile(file_path, meta_only=True)
yaml_str = getattr(data.head, 'session_info_yaml', b'').decode('utf-8', errors='ignore')

try:
    y_data = yaml.safe_load(yaml_str)
    if 'CarSetup' in y_data:
        print(yaml.dump(y_data['CarSetup']))
    else:
        print("No CarSetup found")
except Exception as e:
    print(e)
