import re

file_path = "webanalysisfeature/ibt_viewer_feature.html"
with open(file_path, "r") as f:
    content = f.read()

back_button = """<a href="../website_preview.html" style="position: absolute; right: 20px; top: 20px; color: var(--cyan); text-decoration: none; font-weight: bold; font-family: monospace; border: 1px solid var(--border-color); padding: 5px 15px; border-radius: 4px; background: var(--bg-dark);">← Back to OpenDAV</a>
    <div id="header">"""

content = content.replace('<div id="header">', back_button)

with open(file_path, "w") as f:
    f.write(content)
print("Added back button to Tview")
