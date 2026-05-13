import os
import sys
import re
import numpy as np
from prompt_toolkit.application import Application
from prompt_toolkit.layout.containers import Window, HSplit, WindowAlign, VSplit
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
import ui.splash as splash
from ui.metadata_printer import print_session_metadata

STYLE = Style.from_dict({
    'border': '#2D8AE2',
    'active_border': '#D2751D bold', # OpenDAV Orange
    'title': '#2D8AE2 bold',
    'active_title': '#D2751D bold',
    'action': '#00FFFF bold',
    'sidebar_title': '#ffffff bold',
    'sidebar_active': '#32CD32 bold', # Green selection in sidebar
    'sidebar_inactive': '#888888',
    'bg': '#1a1a1a',
})

# --- SYNTAX PARSING LOGIC (Pre-processor) ---
def parse_formula(math_str):
    """
    Parses the user's custom syntax.
    Example: 'LSRL [RH Center] + [Ride Height RL] / 4'
    Returns: plot_type ('L', 'SP', 'LSRL'), pure_math_expression, list_of_channels
    """
    if not math_str:
        return None, None, []
        
    # Find prefix (L, SP, or LSRL)
    match = re.match(r'^\s*(LSRL|SP|L)\s+(.*)$', math_str, re.IGNORECASE)
    if match:
        plot_type = match.group(1).upper()
        expression = match.group(2).strip()
    else:
        plot_type = 'L' # Default to Line if no prefix
        expression = math_str.strip()
        
    # Extract all channels in brackets
    channels = re.findall(r'\[(.*?)\]', expression)
    return plot_type, expression, channels


class SandboxTUI:
    def __init__(self, formulas):
        self.kb = KeyBindings()
        self.mode = 'pane' # Modes: 'pane', 'sidebar_main', 'sidebar_calc', 'sidebar_raw', 'sidebar_syntax'
        self.active_pane = 0 # 0: Top, 1: Mid-L, 2: Mid-R, 3: Bottom
        self.sb_idx = 0      # Sidebar menu index
        self.result = None
        self.formulas = formulas

        # --- KEY BINDINGS ---
        @self.kb.add('escape')
        def _(event):
            if self.mode == 'pane':
                self.mode = 'sidebar_main'

        @self.kb.add('tab')
        def _(event):
            if self.mode != 'pane':
                self.mode = 'pane'

        @self.kb.add('up')
        def _(event):
            if self.mode == 'pane':
                if self.active_pane in (1, 2): self.active_pane = 0
                elif self.active_pane == 3: self.active_pane = 1
            elif self.mode == 'sidebar_main':
                self.sb_idx = max(0, self.sb_idx - 1)

        @self.kb.add('down')
        def _(event):
            if self.mode == 'pane':
                if self.active_pane == 0: self.active_pane = 1
                elif self.active_pane in (1, 2): self.active_pane = 3
            elif self.mode == 'sidebar_main':
                self.sb_idx = min(2, self.sb_idx + 1)

        @self.kb.add('left')
        def _(event):
            if self.mode == 'pane':
                if self.active_pane == 2: self.active_pane = 1
            elif self.mode != 'sidebar_main' and self.mode.startswith('sidebar_'):
                self.mode = 'sidebar_main' # Go back to main sidebar

        @self.kb.add('right')
        def _(event):
            if self.mode == 'pane':
                if self.active_pane == 1: self.active_pane = 2
            elif self.mode == 'sidebar_main':
                self._enter_sidebar_menu()
                
        @self.kb.add('enter')
        def _(event):
            if self.mode == 'sidebar_main':
                self._enter_sidebar_menu()
            elif self.mode == 'pane':
                self.result = ('render', None)
                event.app.exit()

        @self.kb.add('e')
        def _(event):
            if self.mode == 'pane':
                self.result = ('edit', self.active_pane)
                event.app.exit()

        @self.kb.add('q')
        def _(event):
            self.result = ('quit', None)
            event.app.exit()

    def _enter_sidebar_menu(self):
        if self.sb_idx == 0: self.mode = 'sidebar_calc'
        elif self.sb_idx == 1: self.mode = 'sidebar_raw'
        elif self.sb_idx == 2: self.mode = 'sidebar_syntax'

    def _get_sidebar_text(self):
        res = []
        res.append(("", "\n\n"))
        
        if self.mode == 'sidebar_main':
            res.append(("class:sidebar_title", "  [ DIRECTORY ]\n\n"))
            items = ["Calculated Channels >>", "Channels >>", "Syntaxing Guide >>"]
            for i, txt in enumerate(items):
                if self.mode == 'sidebar_main' and self.sb_idx == i:
                    res.append(("class:sidebar_active", f"  > {txt}\n\n"))
                else:
                    res.append(("class:sidebar_inactive", f"    {txt}\n\n"))
                    
        elif self.mode == 'sidebar_calc':
            res.append(("class:sidebar_title", "  [ CALCULATED CHANNELS ]\n"))
            res.append(("class:sidebar_inactive", "  (Press LEFT to return)\n\n"))
            
            res.append(("class:action", "  [RH Center]\n"))
            res.append(("class:sidebar_inactive", "    Avg of all 4 corners (mm)\n\n"))
            
            res.append(("class:action", "  [Downforce]\n"))
            res.append(("class:sidebar_inactive", "    Total aero load (N)\n\n"))
            
            res.append(("class:action", "  [Aero Balance]\n"))
            res.append(("class:sidebar_inactive", "    Front aero dist (%)\n\n"))
            
        elif self.mode == 'sidebar_raw':
            res.append(("class:sidebar_title", "  [ RAW CHANNELS ]\n"))
            res.append(("class:sidebar_inactive", "  (Press LEFT to return)\n\n"))
            res.append(("class:action", "  [Speed]\n"))
            res.append(("class:sidebar_inactive", "    Vehicle Speed (km/h)\n\n"))
            res.append(("class:action", "  [Ride Height FL] ...\n"))
            res.append(("class:sidebar_inactive", "    Corner ride heights (mm)\n\n"))
            res.append(("class:action", "  [Suspension Load FL] ...\n"))
            res.append(("class:sidebar_inactive", "    Corner loads (N)\n\n"))
            
        elif self.mode == 'sidebar_syntax':
            res.append(("class:sidebar_title", "  [ SYNTAX GUIDE ]\n"))
            res.append(("class:sidebar_inactive", "  (Press LEFT to return)\n\n"))
            
            res.append(("class:action", "  L  \n"))
            res.append(("class:sidebar_inactive", "    Line Graph vs Distance\n\n"))
            res.append(("class:action", "  SP \n"))
            res.append(("class:sidebar_inactive", "    Scatter Plot\n\n"))
            res.append(("class:action", "  LSRL \n"))
            res.append(("class:sidebar_inactive", "    Scatter + Regression Line\n\n"))
            res.append(("class:sidebar_title", "  Example:\n"))
            res.append(("class:action", "  LSRL [RH Center] * 2\n"))
            
        return res

    def _get_panes_text(self):
        res = []
        
        # Helper to format lines inside boxes
        def format_f(pane_id, width):
            f_str = self.formulas[pane_id]
            if not f_str: return "  (Empty)  ".center(width)
            
            # Truncate if too long
            if len(f_str) > width - 4:
                f_str = f_str[:width-7] + "..."
            return f"  {f_str}  ".center(width)

        def b_class(pane): return "class:active_border" if (self.active_pane == pane and self.mode == 'pane') else "class:border"
        def t_class(pane): return "class:active_title" if (self.active_pane == pane and self.mode == 'pane') else "class:title"
        
        iw = 80 # Inner width
        hw = (iw - 2) // 2 # Half width for mid panes

        res.append(("", "\n\n"))
        
        # Top Pane (0)
        res.append((b_class(0), "┌" + "─" * iw + "┐\n"))
        res.append((b_class(0), "│"))
        res.append((t_class(0), " [ TOP PANE ] Distance Line Graph ".center(iw)))
        res.append((b_class(0), "│\n"))
        res.append((b_class(0), "│" + " " * iw + "│\n"))
        res.append((b_class(0), "│" + format_f(0, iw) + "│\n"))
        res.append((b_class(0), "│" + " " * iw + "│\n"))
        res.append((b_class(0), "└" + "─" * iw + "┘\n"))

        # Mid Panes (1 & 2)
        res.append((b_class(1), "┌" + "─" * hw + "┐"))
        res.append(("", "  "))
        res.append((b_class(2), "┌" + "─" * hw + "┐\n"))
        
        res.append((b_class(1), "│"))
        res.append((t_class(1), " [ MID-LEFT ] Plot Area ".center(hw)))
        res.append((b_class(1), "│"))
        res.append(("", "  "))
        res.append((b_class(2), "│"))
        res.append((t_class(2), " [ MID-RIGHT ] Plot Area ".center(hw)))
        res.append((b_class(2), "│\n"))

        for idx in range(6):
            if idx == 2:
                # Formula line
                l_str = format_f(1, hw)
                r_str = format_f(2, hw)
                res.append((b_class(1), "│" + l_str + "│"))
                res.append(("", "  "))
                res.append((b_class(2), "│" + r_str + "│\n"))
            else:
                res.append((b_class(1), "│" + " " * hw + "│"))
                res.append(("", "  "))
                res.append((b_class(2), "│" + " " * hw + "│\n"))

        res.append((b_class(1), "└" + "─" * hw + "┘"))
        res.append(("", "  "))
        res.append((b_class(2), "└" + "─" * hw + "┘\n"))

        # Bottom Pane (3)
        res.append((b_class(3), "┌" + "─" * iw + "┐\n"))
        res.append((b_class(3), "│"))
        res.append((t_class(3), " [ BOTTOM PANE ] Distance Line Graph ".center(iw)))
        res.append((b_class(3), "│\n"))
        res.append((b_class(3), "│" + " " * iw + "│\n"))
        res.append((b_class(3), "│" + format_f(3, iw) + "│\n"))
        res.append((b_class(3), "│" + " " * iw + "│\n"))
        res.append((b_class(3), "└" + "─" * iw + "┘\n"))
        
        return res

    def _get_footer(self):
        footer = " [ESC] Sidebar | [TAB] Panes | [ARROWS] Navigate | [E] Edit Formula | [ENTER] Render | [Q] Quit "
        return [("class:title", "\n" + footer.center(120) + "\n")]

    def run(self):
        self.active_pane = 0
        self.result = None
        
        sidebar_window = Window(content=FormattedTextControl(self._get_sidebar_text), width=35)
        separator = Window(width=3, char=' │ ', style='class:border')
        panes_window = Window(content=FormattedTextControl(self._get_panes_text), width=85)
        
        main_split = VSplit([sidebar_window, separator, panes_window])
        footer_window = Window(content=FormattedTextControl(self._get_footer), height=2)
        
        layout = Layout(HSplit([main_split, footer_window]))
        app = Application(layout=layout, key_bindings=self.kb, full_screen=True, style=STYLE)
        app.run()
        
        os.system('cls' if os.name == 'nt' else 'clear')
        return self.result


def run_custom_math_graph(sessions, headless=False, headless_config=None):
    if headless:
        print("  [!] Headless sandbox not yet implemented.")
        return

    formulas = {0: "", 1: "", 2: "", 3: ""}
    tui = SandboxTUI(formulas)
    
    while True:
        splash.clear_screen()
        splash.print_header("Math Sandbox - Dashboard Layout")
        print("\n  Design your custom 4-pane telemetry dashboard.")
        
        action, payload = tui.run()
        
        if action == 'quit':
            break
            
        elif action == 'edit':
            pane_id = payload
            splash.clear_screen()
            splash.print_header(f"Edit Formula: Pane {pane_id}")
            print("  Example: LSRL [RH Center] + [Ride Height RL] / 4\n")
            print(f"  Current: {formulas[pane_id]}")
            new_f = input("\n  Enter new formula (or press Enter to keep): ").strip()
            if new_f:
                formulas[pane_id] = new_f
                
        elif action == 'render':
            # This is where we will hook up matplotlib and NumPy eval!
            splash.clear_screen()
            splash.print_header("Render Mathematical Dashboard")
            print("  [i] Formula Syntax Parser Output:")
            for p_id in range(4):
                f_str = formulas[p_id]
                plot_type, expr, chs = parse_formula(f_str)
                if expr:
                    print(f"      Pane {p_id}: Type='{plot_type}', Expr='{expr}', Channels={chs}")
                else:
                    print(f"      Pane {p_id}: Empty")
                    
            input("\nPress Enter to return to Dashboard Layout...")
