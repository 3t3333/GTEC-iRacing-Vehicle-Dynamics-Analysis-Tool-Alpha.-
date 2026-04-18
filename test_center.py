import os
import shutil

def center_print(text, width=66):
    try:
        term_width = shutil.get_terminal_size().columns
    except Exception:
        term_width = 80
    
    # Calculate padding based on the fixed width of our ASCII boxes (66 chars)
    padding = max(0, (term_width - width) // 2)
    print(" " * padding + text)

center_print("┌────────────────────────────────────────────────────────────────┐")
center_print("│                ██┐   ██┐██████┐  █████┐                        │")
center_print("│                ██│   ██│██┌──██┐██┌──██┐                       │")
center_print("│                ██│   ██│██│  ██│███████│                       │")
center_print("│                └██┐ ██┌┘██│  ██│██┌──██│                       │")
center_print("│                  ████┌┘ ██████┌┘██│  ██│                       │")
center_print("│                  └───┘  └─────┘ └─┘  └─┘                       │")
center_print("└────────────────────────────────────────────────────────────────┘")
