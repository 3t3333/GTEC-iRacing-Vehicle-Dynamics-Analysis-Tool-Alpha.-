import sys
import os
import time

# OpenDAV Theme Colors
OpenDAV_FG = "\033[38;2;45;138;226m"      # Blue #2D8AE2
OpenDAV_RESET = "\033[0m"
BOX_WIDTH = 100
PADDING = 10

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')
    sys.stdout.flush()

def print_centered(text, width=BOX_WIDTH, color=""):
    sys.stdout.write(" " * PADDING + color + text + OpenDAV_RESET + "\n")

def get_gradient_color(ratio):
    start_rgb = (45, 138, 226)   # Blue #2D8AE2
    end_rgb = (210, 117, 29)     # Orange #D2751D
    
    r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
    g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
    b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
        
    return f"\033[38;2;{r};{g};{b}m"

ascii_art = [
    r"      ██████╗ ██████╗ ███████╗███╗   ██╗      ██████╗  █████╗ ██╗   ██╗   ██████╗██╗     ██╗",
    r"     ██╔═══██╗██╔══██╗██╔════╝████╗  ██║      ██╔══██╗██╔══██╗██║   ██║  ██╔════╝██║     ██║",
    r"     ██║   ██║██████╔╝█████╗  ██╔██╗ ██║█████╗██║  ██║███████║██║   ██║  ██║     ██║     ██║",
    r"     ██║   ██║██╔═══╝ ██╔══╝  ██║╚██╗██║╚════╝██║  ██║██╔══██║╚██╗ ██╔╝  ██║     ██║     ██║",
    r"     ╚██████╔╝██║     ███████╗██║ ╚████║      ██████╔╝██║  ██║ ╚████╔╝██╗╚██████╗███████╗██║",
    r"      ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝      ╚═════╝ ╚═╝  ╚═╝  ╚═══╝ ╚═╝ ╚═════╝╚══════╝╚═╝"
]

def show_splash_screen():
    clear_screen()
    sys.stdout.write("\n\n\n")
    for i, line in enumerate(ascii_art):
        ratio = i / (len(ascii_art) - 1) if len(ascii_art) > 1 else 1
        color_code = get_gradient_color(ratio)
        print_centered(line.center(BOX_WIDTH), BOX_WIDTH, color_code)
    sys.stdout.write("\n\n")
    sys.stdout.flush()

def show_exit_screen():
    clear_screen()
    sys.stdout.write("\n\n\n")
    for i, line in enumerate(ascii_art):
        ratio = i / (len(ascii_art) - 1) if len(ascii_art) > 1 else 1
        color_code = get_gradient_color(ratio)
        print_centered(line.center(BOX_WIDTH), BOX_WIDTH, color_code)
    
    sys.stdout.write("\n")
    spinner = ["|", "/", "-", "\\"]
    end_time = time.time() + 2
    i = 0
    while time.time() < end_time:
        shut_text = f"Shutting Down System {spinner[i % len(spinner)]}"
        padding = PADDING + ((BOX_WIDTH - len(shut_text)) // 2)
        sys.stdout.write(f"\r{' ' * padding}{shut_text}")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write(OpenDAV_RESET + "\n\n")
    sys.stdout.flush()
    time.sleep(0.5)

def print_header(title=""):
    clear_screen()
    sys.stdout.write("\n")
    
    top_border = "┌" + "─" * (BOX_WIDTH - 2) + "┐"
    bot_border = "└" + "─" * (BOX_WIDTH - 2) + "┘"
    
    logo_lines = [top_border]
    for line in ascii_art:
        centered_line = line.center(BOX_WIDTH - 2)
        logo_lines.append(f"│{centered_line}│")
    logo_lines.append(bot_border)
    
    for i, line in enumerate(logo_lines):
        ratio = i / (len(logo_lines) - 1)
        color_code = get_gradient_color(ratio)
        print_centered(line, BOX_WIDTH, color_code)

    print_centered(top_border, BOX_WIDTH, OpenDAV_FG)
    print_centered("│" + "Open Source Data Analysis and Visualization Systems".center(BOX_WIDTH - 2) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered("│" + "Author: Arturo Gomez".center(BOX_WIDTH - 2) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered("│" + "Instagram: @arturoagracing".center(BOX_WIDTH - 2) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered(bot_border, BOX_WIDTH, OpenDAV_FG)
    
    if title:
        print_centered(top_border, BOX_WIDTH, OpenDAV_FG)
        title_line = f"│  {title}"
        print_centered(title_line.ljust(BOX_WIDTH - 1) + "│", BOX_WIDTH, OpenDAV_FG)
        print_centered(bot_border, BOX_WIDTH, OpenDAV_FG)
    
    sys.stdout.write(OpenDAV_RESET)
    sys.stdout.flush()

def show_home_screen():
    print_header("Home")
    top_border = "┌" + "─" * (BOX_WIDTH - 2) + "┐"
    bot_border = "└" + "─" * (BOX_WIDTH - 2) + "┘"
    print_centered(top_border, BOX_WIDTH, OpenDAV_FG)
    print_centered("│  1. Analyze Telemetry File".ljust(BOX_WIDTH - 1) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered("│  2. Automation & Projects".ljust(BOX_WIDTH - 1) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered("│  3. Help / About".ljust(BOX_WIDTH - 1) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered("│  4. Settings".ljust(BOX_WIDTH - 1) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered(bot_border, BOX_WIDTH, OpenDAV_FG)
    sys.stdout.write(OpenDAV_RESET)

def show_help_screen():
    print_header("HELP / ABOUT")
    top_border = "┌" + "─" * (BOX_WIDTH - 2) + "┐"
    bot_border = "└" + "─" * (BOX_WIDTH - 2) + "┘"
    print_centered(top_border, BOX_WIDTH, OpenDAV_FG)
    print_centered("│  OpenDAV: Data Analysis and Visualization".ljust(BOX_WIDTH - 1) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered("│  A professional telemetry analysis suite for MoTeC data.".ljust(BOX_WIDTH - 1) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered("│".ljust(BOX_WIDTH - 1) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered("│  [ CONTACT & SUPPORT ]".ljust(BOX_WIDTH - 1) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered("│  Developer: Arturo Gomez".ljust(BOX_WIDTH - 1) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered("│  Instagram: @arturoagracing".ljust(BOX_WIDTH - 1) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered("│  Email: arturo.gomez.racing@gmail.com".ljust(BOX_WIDTH - 1) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered("│".ljust(BOX_WIDTH - 1) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered("│  [ USAGE HINTS ]".ljust(BOX_WIDTH - 1) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered("│  - Drop .ld/.ibt files in the /telemetry folder.".ljust(BOX_WIDTH - 1) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered("│  - Use 'fl' for Full Lap in distance prompts.".ljust(BOX_WIDTH - 1) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered("│  - Use 'fs' for Full Stint in the Math Sandbox.".ljust(BOX_WIDTH - 1) + "│", BOX_WIDTH, OpenDAV_FG)
    print_centered(bot_border, BOX_WIDTH, OpenDAV_FG)
    sys.stdout.write(OpenDAV_RESET)
    
    prompt_text = "Press Enter to return to Home Screen..."
    padding = PADDING + ((BOX_WIDTH - len(prompt_text)) // 2)
    sys.stdout.write("\n" + " " * padding + prompt_text)
    input()
