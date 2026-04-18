import re
import glob

for filepath in ['analysis/tire_energy.py', 'analysis/aero_rake.py', 'analysis/aero_mapping.py', 'analysis/downforce_mapping.py']:
    with open(filepath, 'r') as f:
        content = f.read()
        
    # 1. Fix the lowercase issue
    content = content.replace(
        "ans_raw = f\"print {headless_config['layout']} < {headless_config['project']}\"",
        "ans_raw = f\"print {headless_config['layout'].lower()} < {headless_config['project']}\""
    )
    content = content.replace(
        "ans = ans_raw.split('<')[0].strip()",
        "ans = ans_raw.split('<')[0].strip().lower()"
    )
    
    # 2. Fix the break issue by putting a universal break at the end of the `open l1`, `print l1` blocks.
    # Instead of finding the print statement, let's just find `save_to_project(fig, project_name, file_out)\n                            plt.close(fig)`
    # and add `if headless: break`
    content = content.replace(
        "save_to_project(fig, project_name, file_out)\n                            plt.close(fig)",
        "save_to_project(fig, project_name, file_out)\n                            plt.close(fig)\n                            if headless: break"
    )
    
    # Let's handle tire_energy which has: save_to_project(fig, project_name, file_out)\n                            plt.close(fig)
    # aero_rake has save_to_project ??? Let's check aero_rake.py!
    
    with open(filepath, 'w') as f:
        f.write(content)
