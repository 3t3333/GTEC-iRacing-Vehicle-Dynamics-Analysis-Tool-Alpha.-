import sys
import os

def load_splash():
    if os.path.exists("splash.txt"):
        try:
            with open("splash.txt", "r", encoding="utf-8") as f:
                return [line.rstrip("\n") for line in f.readlines()]
        except:
            pass
    return [
        r"      ____ _____ _____ ____  ",
        r"     / ___|_   _| ____/ ___| ",
        r"    | |  _  | | |  _|| |     ",
        r"    | |_| | | | | |__| |___  ",
        r"     \____| |_| |_____\____| ",
        r"                             ",
        r"    GTEC Analysis Software   ",
        r"    (c) Gomez Systems Group  "
    ]

def print_top_to_bottom(lines, start_rgb, end_rgb):
    for i, line in enumerate(lines):
        ratio = i / max(1, (len(lines) - 1))
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
        sys.stdout.write(f"\033[38;2;{r};{g};{b}m{line}\033[0m\n")

def print_left_to_right(lines, start_rgb, end_rgb):
    max_len = max(len(line) for line in lines)
    for line in lines:
        for i, char in enumerate(line):
            ratio = i / max(1, (max_len - 1))
            r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
            g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
            b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
            sys.stdout.write(f"\033[38;2;{r};{g};{b}m{char}")
        sys.stdout.write("\033[0m\n")

if __name__ == "__main__":
    lines = load_splash()
    print("--- Top to Bottom (White to Grey) ---")
    print_top_to_bottom(lines, (255, 255, 255), (100, 100, 100))
    print("\n--- Left to Right (Grey to Red) ---")
    print_left_to_right(lines, (150, 150, 150), (255, 0, 0))
