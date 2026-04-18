from core import ibt_adapter
file_path = 'webanalysisfeature/lap.ibt'
data = ibt_adapter.fromfile(file_path, meta_only=True)
yaml_str = getattr(data.head, 'session_info_yaml', b'').decode('utf-8', errors='ignore')
print(yaml_str[:1500])
