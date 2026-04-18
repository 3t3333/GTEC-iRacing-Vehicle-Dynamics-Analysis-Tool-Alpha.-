with open('opendav.py', 'r') as f:
    lines = f.readlines()

start_idx = 0
for i, line in enumerate(lines):
    if "session_choice = input(\"\\nSelect session type (number) or 'q' to quit: \").strip().lower()" in line:
        start_idx = i
        break

end_idx = 0
for i in range(start_idx, len(lines)):
    if "if go_back:" in lines[i]:
        end_idx = i
        break

new_lines = [
    "        session_choice = input(\"\\nSelect option (number) or 'q' to quit: \").strip().lower()\n",
    "        if session_choice == 'q':\n",
    "            splash.show_exit_screen()\n",
    "            return\n",
    "        \n",
    "        if session_choice == '2':\n",
    "            splash.show_help_screen()\n",
    "            continue\n",
    "        \n",
    "        if session_choice == '3':\n",
    "            from ui.settings import show_settings\n",
    "            show_settings()\n",
    "            continue\n",
    "            \n",
    "        if session_choice != '1':\n",
    "            print(\"[!] Invalid selection.\")\n",
    "            import time\n",
    "            time.sleep(1)\n",
    "            continue\n",
    "            \n",
    "        selected_files = []\n",
    "        go_back = False\n",
    "        \n",
    "        splash.print_header(\"Telemetry Archive\")\n",
    "        for i, info in enumerate(file_infos):\n",
    "            print(f\"  {i + 1}. {info}\")\n",
    "        print(\"─\" * 64)\n",
    "        while True:\n",
    "            choice = input(\"\\nSelect a file to analyze (number), 'p' for previous menu, or 'q' to quit: \").strip().lower()\n",
    "            if choice == 'q':\n",
    "                splash.show_exit_screen()\n",
    "                sys.exit(0)\n",
    "            if choice == 'p':\n",
    "                go_back = True\n",
    "                break\n",
    "            try:\n",
    "                choice_idx = int(choice) - 1\n",
    "                if 0 <= choice_idx < len(ld_files):\n",
    "                    selected_files.append(os.path.join(telemetry_dir, ld_files[choice_idx]))\n",
    "                    break\n",
    "                else:\n",
    "                    print(\"[!] Invalid selection.\")\n",
    "            except ValueError:\n",
    "                print(\"[!] Please enter a valid number.\")\n",
    "\n"
]

lines = lines[:start_idx] + new_lines + lines[end_idx:]

with open('opendav.py', 'w') as f:
    f.writelines(lines)
