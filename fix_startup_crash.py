with open('opendav.py', 'r') as f:
    content = f.read()

# 1. Remove the early import of tui_engine
content = content.replace("from ui.tui_engine import get_tui_choice\n", "")

# 2. Add prompt_toolkit to the dependency checker
deps_block = """    # Check customtkinter
    for _ in range(5): update_screen("Checking dependency: customtkinter...")
    try:
        import customtkinter
    except ImportError:
        if is_frozen:
            update_screen("Warning: customtkinter missing. GUI Mode 3 disabled.")
            time.sleep(2)
        else:
            update_screen("Patching: installing customtkinter...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import customtkinter"""

new_deps_block = deps_block + """

    # Check prompt_toolkit (for TUI)
    for _ in range(5): update_screen("Checking dependency: prompt_toolkit...")
    try:
        import prompt_toolkit
    except ImportError:
        if is_frozen:
            update_screen("Error: prompt_toolkit missing from bundle!")
            fatal_error = True
            time.sleep(2)
        else:
            update_screen("Patching: installing prompt_toolkit...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "prompt_toolkit"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import prompt_toolkit"""

if deps_block in content:
    content = content.replace(deps_block, new_deps_block)
else:
    print("Failed to find deps block")

# 3. Add the import inside main()
main_def = "def main():\n    telemetry_dir = \"telemetry\""
new_main_def = "def main():\n    from ui.tui_engine import get_tui_choice\n    telemetry_dir = \"telemetry\""

if main_def in content:
    content = content.replace(main_def, new_main_def)
else:
    print("Failed to find main def")

with open('opendav.py', 'w') as f:
    f.write(content)
