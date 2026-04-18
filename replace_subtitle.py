import re

with open("website_preview.html", "r") as f:
    html = f.read()

old_subtitle = r"Professional-grade iRacing vehicle dynamics analysis suite.\s*Built by engineers, for engineers. Stop guessing, start measuring."
new_subtitle = "OpenDAV is a CLI-based analysis system that parses MoTeC i2 files and computes various measurements related to vehicle dynamics."

html = re.sub(old_subtitle, new_subtitle, html)

with open("website_preview.html", "w") as f:
    f.write(html)
print("Updated subtitle")
