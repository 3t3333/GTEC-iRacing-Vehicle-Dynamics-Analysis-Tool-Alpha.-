from core import ibt_adapter
file_path = 'webanalysisfeature/lap.ibt'
data = ibt_adapter.fromfile(file_path, meta_only=False)
print("Channels in IBT:")
for ch in sorted(data.channels.keys()):
    print(ch)
