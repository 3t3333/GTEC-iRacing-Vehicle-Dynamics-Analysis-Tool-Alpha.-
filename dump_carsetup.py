from core import ibt_adapter
import yaml
import pprint

file_path = 'webanalysisfeature/lap.ibt'
data = ibt_adapter.fromfile(file_path, meta_only=False)
yaml_str = getattr(data.head, 'session_info_yaml', b'').decode('utf-8', errors='ignore')

try:
    y_data = yaml.safe_load(yaml_str)
    if 'CarSetup' in y_data:
        setup = y_data['CarSetup']
        for k, v in setup.items():
            if k != 'UpdateCount':
                print(f"--- {k} ---")
                print(yaml.dump(v))
except Exception as e:
    print(e)
