import os
import sys
import numpy as np
from prompt_toolkit.application import Application
from prompt_toolkit.layout.containers import Window, HSplit, WindowAlign
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
import ui.splash as splash

STYLE = Style.from_dict({
    'border': '#2D8AE2',
    'active_border': '#32CD32 bold',
    'title': '#2D8AE2 bold',
    'active_title': '#32CD32 bold',
    'action': '#00FFFF bold',
    'bg': '#1a1a1a',
})

class SandboxTUI:
    def __init__(self):
        self.kb = KeyBindings()
        self.active_pane = 0 # 0: Top, 1: Mid-L, 2: Mid-R, 3: Bottom
        self.result = None

        @self.kb.add('up')
        def _(event):
            if self.active_pane in (1, 2): self.active_pane = 0
            elif self.active_pane == 3: self.active_pane = 1

        @self.kb.add('down')
        def _(event):
            if self.active_pane == 0: self.active_pane = 1
            elif self.active_pane in (1, 2): self.active_pane = 3

        @self.kb.add('left')
        def _(event):
            if self.active_pane == 2: self.active_pane = 1

        @self.kb.add('right')
        def _(event):
            if self.active_pane == 1: self.active_pane = 2

        @self.kb.add('e')
        def _(event):
            self.result = self.active_pane
            event.app.exit()

        @self.kb.add('q')
        @self.kb.add('escape')
        def _(event):
            self.result = 'quit'
            event.app.exit()

    def _get_text(self):
        res = []
        
        # Helper to return classes
        def b_class(pane): return "class:active_border" if self.active_pane == pane else "class:border"
        def t_class(pane): return "class:active_title" if self.active_pane == pane else "class:title"
        
        iw = 76 # Inner width
        hw = (iw - 2) // 2 # Half width for mid panes

        res.append(("", "\n\n"))
        
        # Top Pane (0)
        res.append((b_class(0), "  ┌" + "─" * iw + "┐\n"))
        res.append((b_class(0), "  │"))
        res.append((t_class(0), " [ TOP PANE ] Distance Line Graph ".center(iw)))
        res.append((b_class(0), "│\n"))
        for _ in range(3): res.append((b_class(0), "  │" + " " * iw + "│\n"))
        res.append((b_class(0), "  └" + "─" * iw + "┘\n"))

        # Mid Panes (1 & 2)
        res.append((b_class(1), "  ┌" + "─" * hw + "┐"))
        res.append(("", "  "))
        res.append((b_class(2), "┌" + "─" * hw + "┐\n"))
        
        res.append((b_class(1), "  │"))
        res.append((t_class(1), " [ MID-LEFT ] Square Graph ".center(hw)))
        res.append((b_class(1), "│"))
        res.append(("", "  "))
        res.append((b_class(2), "│"))
        res.append((t_class(2), " [ MID-RIGHT ] Square Graph ".center(hw)))
        res.append((b_class(2), "│\n"))

        for _ in range(8):
            res.append((b_class(1), "  │" + " " * hw + "│"))
            res.append(("", "  "))
            res.append((b_class(2), "│" + " " * hw + "│\n"))

        res.append((b_class(1), "  └" + "─" * hw + "┘"))
        res.append(("", "  "))
        res.append((b_class(2), "└" + "─" * hw + "┘\n"))

        # Bottom Pane (3)
        res.append((b_class(3), "  ┌" + "─" * iw + "┐\n"))
        res.append((b_class(3), "  │"))
        res.append((t_class(3), " [ BOTTOM PANE ] Distance Line Graph ".center(iw)))
        res.append((b_class(3), "│\n"))
        for _ in range(3): res.append((b_class(3), "  │" + " " * iw + "│\n"))
        res.append((b_class(3), "  └" + "─" * iw + "┘\n"))
        
        footer = " [ARROWS] Navigate | [E] Edit Selected Pane | [Q] Quit to Tools "
        res.append(("class:title", "\n" + footer.center(iw + 4) + "\n"))
        return res

    def run(self):
        self.active_pane = 0
        self.result = None
        
        text_control = FormattedTextControl(self._get_text, key_bindings=self.kb, focusable=True, show_cursor=False)
        layout = Layout(HSplit([Window(content=text_control, align=WindowAlign.LEFT)]))
        app = Application(layout=layout, key_bindings=self.kb, full_screen=True, style=STYLE)
        app.run()
        
        os.system('cls' if os.name == 'nt' else 'clear')
        return self.result

def run_custom_math_graph(sessions, headless=False, headless_config=None):
    if headless:
        print("  [!] Headless sandbox not yet implemented.")
        return

    tui = SandboxTUI()
    
    while True:
        splash.clear_screen()
        splash.print_header("Math Sandbox - Dashboard Layout")
        print("\n  Design your custom 4-pane telemetry dashboard.")
        
        choice = tui.run()
        
        if choice == 'quit' or choice is None:
            break
            
        splash.clear_screen()
        print("\n\n")
        print("="*60)
        print("               OPENDAV TEST".center(60))
        pane_names = {0: "TOP PANE", 1: "MID-LEFT PANE", 2: "MID-RIGHT PANE", 3: "BOTTOM PANE"}
        print(f"         (You selected {pane_names[choice]})".center(60))
        print("="*60)
        input("\nPress Enter to return to Dashboard Layout...")
