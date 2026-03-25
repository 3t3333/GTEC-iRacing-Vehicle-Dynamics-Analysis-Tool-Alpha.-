import sys
import os
import time

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_splash_screen():
    clear_screen()
    
    # ASCII Art Lines
    lines = [
        r"                ██╗   ██╗██████╗  █████╗ ",
        r"                ██║   ██║██╔══██╗██╔══██╗",
        r"                ██║   ██║██║  ██║███████║",
        r"                ╚██╗ ██╔╝██║  ██║██╔══██║",
        r"                 ╚████╔╝ ██████╔╝██║  ██║",
        r"                  ╚═══╝  ╚═════╝ ╚═╝  ╚═╝",
        r"                                         ",
        r"          GTEC Vehicle Dynamics Analysis System    ",
        r" Copyright © 2026 Gomez Systems Group, all rights reserved"
    ]

    # Grey (150, 150, 150) to White (255, 255, 255) gradient logic
    start_rgb = (150, 150, 150)  # Grey
    end_rgb = (255, 255, 255)    # White
    
    for i, line in enumerate(lines):
        # Calculate interpolation ratio (0.0 to 1.0)
        ratio = i / (len(lines) - 1)
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
        
        # Apply 24-bit foreground color escape sequence: \033[38;2;R;G;Bm
        sys.stdout.write(f"\033[38;2;{r};{g};{b}m{line}\033[0m\n")
    
    sys.stdout.write("\n")

def show_exit_screen():
    clear_screen()
    
    # ASCII Art Lines
    lines = [
        r"                ██╗   ██╗██████╗  █████╗ ",
        r"                ██║   ██║██╔══██╗██╔══██╗",
        r"                ██║   ██║██║  ██║███████║",
        r"                ╚██╗ ██╔╝██║  ██║██╔══██║",
        r"                 ╚████╔╝ ██████╔╝██║  ██║",
        r"                  ╚═══╝  ╚═════╝ ╚═╝  ╚═╝",
        r"                                         ",
        r"          GTEC Vehicle Dynamics Analysis System    ",
        r" Copyright © 2026 Gomez Systems Group, all rights reserved"
    ]

    start_rgb = (150, 150, 150)  # Grey
    end_rgb = (255, 255, 255)   # White
    
    for i, line in enumerate(lines):
        ratio = i / (len(lines) - 1)
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
        sys.stdout.write(f"\033[38;2;{r};{g};{b}m{line}\033[0m\n")
    
    sys.stdout.write("\n")
    spinner = ["|", "/", "-", "\\"]
    end_time = time.time() + 2
    i = 0
    while time.time() < end_time:
        sys.stdout.write(f"\r  Shutting Down System {spinner[i % len(spinner)]} ")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    print("\n\n  ")
    time.sleep(0.5)

def print_header(title=""):
    clear_screen()
    print("╔" + "═"*64 + "╗")
    print("║		 ██╗   ██╗██████╗  █████╗                        ║")
    print("║		 ██║   ██║██╔══██╗██╔══██╗                       ║")
    print("║		 ██║   ██║██║  ██║███████║                       ║")
    print("║		 ╚██╗ ██╔╝██║  ██║██╔══██║                       ║")
    print("║	           ████╔╝ ██████╔╝██║  ██║                       ║")
    print("║		   ╚═══╝  ╚═════╝ ╚═╝  ╚═╝                       ║")
    print("╚" + "═"*64 + "╝")
    print("╔" + "═"*64 + "╗")
    print("║                Vehicle Dynamics Analysis                       ║")
    print("║                 Author: Arturo Gomez                           ║")
    print("║                 Instagram: @arturoagracing                     ║")
    print("╚" + "═"*64 + "╝")
    if title:
        print("╔" + "═"*64 + "╗")
        title_line = f"║  {title}"
        print(title_line.ljust(65) + "║")
        print("╚" + "═"*64 + "╝")

def show_home_screen():
    print_header("Home")
    print("╔" + "═"*64 + "╗")
    print("║  1. Single File Analysis                                       ║")
    print("║  2. Multi-File Comparison                                      ║")
    print("║  3. Settings                                                   ║")
    print("║  4. Help / About                                               ║")
    print("╚" + "═"*64 + "╝")

def show_help_screen():
    print_header("HELP / ABOUT")
    print("╔" + "═"*64 + "╗")
    print("║  GTEC Vehicle Dynamics Analysis System (VDA)                   ║")
    print("║  A professional telemetry analysis suite for MoTeC data.       ║")
    print("║                                                                ║")
    print("║  [ CONTACT & SUPPORT ]                                         ║")
    print("║  Developer: Arturo Gomez                                       ║")
    print("║  Instagram: @arturoagracing                                    ║")
    print("║  Email: arturo.gomez.racing@gmail.com                          ║")
    print("║                                                                ║")
    print("║  [ USAGE HINTS ]                                               ║")
    print("║  - Drop .ld/.id files in the /telemetry folder.                ║")
    print("║  - Use 'fl' for Full Lap in distance prompts.                 ║")
    print("║  - Use 'fs' for Full Stint in the Math Sandbox.                ║")
    print("╚" + "═"*64 + "╝")
    print("\nPress Enter to return to Home Screen...")
    input()
