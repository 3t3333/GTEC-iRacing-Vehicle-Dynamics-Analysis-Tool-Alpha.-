import sys
import os
import time
import re

# OpenDAV Theme Colors
OpenDAV_FG = "\033[38;2;45;138;226m"      # Blue #2D8AE2
OpenDAV_RESET = "\033[0m"

# Semantic Colors
C_INFO = "\033[36m"      # Cyan
C_SUCCESS = "\033[32m"   # Green
C_WARNING = "\033[33m"   # Yellow
C_DANGER = "\033[38;2;255;20;147m" # Pinkish Red
C_ACTION = "\033[1;36m"  # Bold Cyan
C_GOLD = "\033[38;2;210;117;29m"   # Orange/Gold

BOX_WIDTH = 100
PADDING = 10

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')
    sys.stdout.flush()

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

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

def print_centered(text, color="", fill=False):
    """Prints text centered within the PADDING area."""
    if fill:
        plain_text = strip_ansi(text)
        inner_width = BOX_WIDTH - 2
        padding_len = (inner_width - len(plain_text)) // 2
        
        # We need the left border to be OpenDAV_FG, then the text (which might have its own color), then right border OpenDAV_FG
        line = OpenDAV_FG + "│" + " " * padding_len + color + text + OpenDAV_RESET + " " * (inner_width - padding_len - len(plain_text)) + OpenDAV_FG + "│" + OpenDAV_RESET
        sys.stdout.write(" " * PADDING + line + "\n")
    else:
        # If it's a full border line like ┌──┐, just color the whole line
        sys.stdout.write(" " * PADDING + color + text + OpenDAV_RESET + "\n")

def print_box_line(content, color=OpenDAV_FG):
    """Prints a single line wrapped in vertical box borders."""
    inner_width = BOX_WIDTH - 2
    visual_len = len(strip_ansi(content))
    padding = inner_width - visual_len
    
    # The content itself may contain RESET codes. So we MUST inject the color code for the right border
    # immediately before drawing it.
    line = color + "│" + OpenDAV_RESET + content + (" " * padding) + color + "│" + OpenDAV_RESET
    sys.stdout.write(" " * PADDING + line + "\n")

def print_header(title="", path=""):
    clear_screen()
    sys.stdout.write("\n")
    
    top_border = "┌" + "─" * (BOX_WIDTH - 2) + "┐"
    bot_border = "└" + "─" * (BOX_WIDTH - 2) + "┘"
    
    # 1. Print Logo Box
    sys.stdout.write(" " * PADDING + get_gradient_color(0) + top_border + "\n")
    for i, line in enumerate(ascii_art):
        ratio = (i + 1) / (len(ascii_art) + 1)
        color = get_gradient_color(ratio)
        centered_content = line.center(BOX_WIDTH - 2)
        sys.stdout.write(" " * PADDING + color + "│" + centered_content + "│" + "\n")
    sys.stdout.write(" " * PADDING + get_gradient_color(1) + bot_border + "\n")

    # 2. Print Subtitle Box
    print_centered(top_border, color=OpenDAV_FG)
    sub = "Open Source Data Analysis and Visualization Systems"
    if path:
        sub = f"{path} > {title}" if title else path
    print_centered(sub, fill=True, color=OpenDAV_FG)
    print_centered(bot_border, color=OpenDAV_FG)
    
    # 3. Local Context Chip
    if title and not path:
        chip_inner = f"  {title}  "
        print_centered("┌" + "─" * len(chip_inner) + "┐", color=C_INFO)
        print_centered("│" + chip_inner + "│", color=C_INFO)
        print_centered("└" + "─" * len(chip_inner) + "┘", color=C_INFO)
    
    sys.stdout.write(OpenDAV_RESET)
    sys.stdout.flush()

def show_splash_screen():
    clear_screen()
    sys.stdout.write("\n\n\n")
    for i, line in enumerate(ascii_art):
        ratio = i / (len(ascii_art) - 1) if len(ascii_art) > 1 else 1
        color_code = get_gradient_color(ratio)
        sys.stdout.write(" " * (PADDING + 5) + color_code + line + OpenDAV_RESET + "\n")
    
    intro_text = f"INITIALIZING OPENDAV ENGINE v1.1"
    sys.stdout.write("\n" + " " * (PADDING + (BOX_WIDTH - len(intro_text))//2) + C_INFO + intro_text + "\n")
    
    bar_width = 40
    for i in range(bar_width + 1):
        percent = int((i / bar_width) * 100)
        bar = "█" * i + "░" * (bar_width - i)
        sys.stdout.write(f"\r{' ' * (PADDING + (BOX_WIDTH - bar_width)//2)}[{bar}] {percent}%")
        sys.stdout.flush()
        time.sleep(0.015)
    
    sys.stdout.write("\n\n")
    time.sleep(0.3)

def show_exit_screen():
    clear_screen()
    sys.stdout.write("\n\n\n")
    for i, line in enumerate(ascii_art):
        ratio = i / (len(ascii_art) - 1) if len(ascii_art) > 1 else 1
        color_code = get_gradient_color(ratio)
        sys.stdout.write(" " * (PADDING + 5) + color_code + line + OpenDAV_RESET + "\n")
    
    sys.stdout.write("\n")
    spinner = ["◐", "◓", "◑", "◒"]
    end_time = time.time() + 1.2
    i = 0
    while time.time() < end_time:
        shut_text = f"Shutting Down OpenDAV Ecosystem {spinner[i % len(spinner)]}"
        padding = PADDING + ((BOX_WIDTH - len(shut_text)) // 2)
        sys.stdout.write(f"\r{' ' * padding}{C_DANGER}{shut_text}{OpenDAV_RESET}")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write("\n\n")
    sys.stdout.flush()

def show_help_screen():
    print_header("HELP / ABOUT")
    inner_w = BOX_WIDTH - 2
    
    print_centered("┌" + "─" * inner_w + "┐", color=OpenDAV_FG)
    print_box_line(f"  {C_ACTION}OpenDAV: Data Analysis and Visualization{OpenDAV_RESET}")
    print_box_line("  Professional telemetry analysis suite optimized for competitive simracing.")
    print_box_line("")
    print_box_line(f"  {C_INFO}[ CORE WORKFLOW ]{OpenDAV_RESET}")
    print_box_line("  1. Drop .ld or .ibt files into the /telemetry/ folder.")
    print_box_line("  2. Use 'Commit' to move them into a tracked SimGit Project.")
    print_box_line("  3. Run automated Workbooks to generate high-res aerodynamic maps.")
    print_box_line("")
    print_box_line(f"  {C_INFO}[ DEVELOPER ]{OpenDAV_RESET} Arturo Gomez | @arturoagracing")
    print_centered("└" + "─" * inner_w + "┘", color=OpenDAV_FG)
    
    prompt = "Press Enter to return to Home Screen..."
    sys.stdout.write("\n" + " " * (PADDING + (BOX_WIDTH - len(prompt))//2) + C_ACTION + prompt + OpenDAV_RESET)
    input()

def show_home_screen():
    print_header("Home")
    menu = [
        (1, "Analyze Telemetry File", "Manual sandbox exploration"),
        (2, "Automation & SimGit Projects", "Enterprise team workflows"),
        (3, "Help / About", "Usage guides and documentation"),
        (4, "Settings", "GUI modes and Cloud configuration")
    ]
    
    inner_w = BOX_WIDTH - 2
    print_centered("┌" + "─" * inner_w + "┐", color=OpenDAV_FG)
    for num, title, desc in menu:
        # Construct content with semantic highlighting
        content = f"  {C_ACTION}{num}.{OpenDAV_RESET} {title.ljust(32)} {C_INFO}>> {desc}{OpenDAV_RESET}"
        print_box_line(content)
    print_centered("└" + "─" * inner_w + "┘", color=OpenDAV_FG)
