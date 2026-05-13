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
    'sidebar_active': '#D2751D bold', # Orange selection in sidebar
    'sidebar_inactive': '#888888',
    'bg': '#1a1a1a',
})

def parse_formula(math_str):
    if not math_str: return None, None, []
    match = re.match(r'^\s*(LSRL|SP|L)\s+(.*)$', math_str, re.IGNORECASE)
    if match:
        plot_type = match.group(1).upper()
        expression = match.group(2).strip()
    else:
        plot_type = 'L'
        expression = math_str.strip()
    channels = re.findall(r'\[(.*?)\]', expression)
    return plot_type, expression, channels

class SandboxTUI:
    def __init__(self, formulas, all_channels):
        self.kb = KeyBindings()
        self.mode = 'pane' # 'pane', 'sidebar_main', 'sidebar_calc', 'sidebar_cat', 'sidebar_chan_list', 'sidebar_syntax'
        self.active_pane = 0
        self.sb_idx = 0      
        self.sb_scroll = 0
        self.formulas = formulas
        self.all_channels = sorted(all_channels)
        self.result = None
        self.current_list = []
        
        # Categorization
        self.categories = {
            "Dynamics": (["Speed", "LatAccel", "LongAccel", "VertAccel", "Yaw", "Pitch", "Roll", "Velocity", "body_v"], 
                         "Core vehicle motion and G-forces."),
            "Suspension": (["shockDefl", "shockVel", "rideHeight", "Suspension Load", "SpringRate", "PerchOffset"],
                           "Suspension movement and travel."),
            "Tires": (["temp", "press", "wear", "Tread", "pressure"],
                      "Thermodynamics and pressure."),
            "Controls": (["Throttle", "Brake", "Steering", "Clutch", "Gear", "RPM", "Handbrake"],
                        "Driver inputs."),
            "Engine": (["Fuel", "WaterTemp", "OilTemp", "OilPress", "Voltage", "ManifoldPress"],
                      "Power unit and health."),
            "All Channels": ([""], "Complete list of telemetry sensors.")
        }
        self.active_cat = None
        self.cat_keys = list(self.categories.keys())

        @self.kb.add('escape')
        def _(event):
            if self.mode == 'pane': 
                self.mode = 'sidebar_main'
                self.sb_idx = 0

        @self.kb.add('tab')
        def _(event):
            if self.mode != 'pane': 
                self.mode = 'pane'

        @self.kb.add('up')
        def _(event):
            if self.mode == 'pane':
                if self.active_pane in (1, 2): self.active_pane = 0
                elif self.active_pane == 3: self.active_pane = 1
            else:
                self.sb_idx = max(0, self.sb_idx - 1)
                if self.sb_idx < self.sb_scroll: 
                    self.sb_scroll = self.sb_idx

        @self.kb.add('down')
        def _(event):
            if self.mode == 'pane':
                if self.active_pane == 0: self.active_pane = 1
                elif self.active_pane in (1, 2): self.active_pane = 3
            else:
                limit = len(self.current_list) - 1 if self.mode in ('sidebar_calc', 'sidebar_cat', 'sidebar_chan_list') else 2
                if limit < 0: limit = 0
                self.sb_idx = min(limit, self.sb_idx + 1)
                if self.sb_idx >= self.sb_scroll + 15:
                    self.sb_scroll = self.sb_idx - 14

        @self.kb.add('left')
        def _(event):
            if self.mode == 'pane':
                if self.active_pane == 2: self.active_pane = 1
            elif self.mode == 'sidebar_chan_list': 
                self.mode = 'sidebar_cat'
                self.current_list = self.cat_keys
                self.sb_idx = self.cat_keys.index(self.active_cat) if self.active_cat in self.cat_keys else 0
                self.sb_scroll = 0
            elif self.mode != 'sidebar_main': 
                self.mode = 'sidebar_main'
                self.sb_idx = 0
                self.sb_scroll = 0

        @self.kb.add('right')
        @self.kb.add('enter')
        def _(event):
            if self.mode == 'sidebar_main':
                if self.sb_idx == 0: 
                    self.mode = 'sidebar_calc'
                    self.current_list = ["RH Center", "Downforce", "Aero Balance"]
                    self.sb_idx = 0; self.sb_scroll = 0
                elif self.sb_idx == 1: 
                    self.mode = 'sidebar_cat'
                    self.current_list = self.cat_keys
                    self.sb_idx = 0; self.sb_scroll = 0
                elif self.sb_idx == 2: 
                    self.mode = 'sidebar_syntax'
                    self.current_list = []
            elif self.mode == 'sidebar_cat':
                self.active_cat = self.cat_keys[self.sb_idx]
                self.mode = 'sidebar_chan_list'
                keywords, _ = self.categories[self.active_cat]
                if keywords == [""]:
                    self.current_list = self.all_channels
                else:
                    self.current_list = [ch for ch in self.all_channels if any(k.lower() in ch.lower() for k in keywords)]
                self.sb_idx = 0; self.sb_scroll = 0
            elif self.mode == 'pane' and event.key_sequence[0].name == 'enter':
                self.result = ('render', None)
                event.app.exit()

        @self.kb.add('i')
        def _(event):
            if self.mode in ('sidebar_calc', 'sidebar_chan_list') and self.current_list:
                ch = self.current_list[self.sb_idx]
                f = self.formulas[self.active_pane]
                if f and not f.endswith(' '): f += ' '
                self.formulas[self.active_pane] = f + f"[{ch}] "

        @self.kb.add('backspace')
        @self.kb.add('delete')
        @self.kb.add('c-h')
        def _(event):
            if self.mode == 'pane':
                # Quick clear
                self.formulas[self.active_pane] = ""

        @self.kb.add('e')
        def _(event):
            if self.mode == 'pane':
                self.result = ('edit', self.active_pane)
                event.app.exit()

        @self.kb.add('q')
        def _(event):
            self.result = ('quit', None)
            event.app.exit()

    def _get_sidebar_text(self):
        res = []
        res.append(("", "\n\n"))
        
        if self.mode == 'sidebar_main':
            res.append(("class:sidebar_title", "  [ DIRECTORY ]\n\n"))
            items = ["Calculated Channels >>", "Raw Channels >>", "Syntaxing Guide >>"]
            for i, txt in enumerate(items):
                prefix = "  > " if self.sb_idx == i else "    "
                cls = "class:sidebar_active" if self.sb_idx == i else "class:sidebar_inactive"
                res.append((cls, f"{prefix}{txt}\n\n"))
                    
        elif self.mode == 'sidebar_calc':
            res.append(("class:sidebar_title", "  [ CALCULATED CHANNELS ]\n"))
            res.append(("class:sidebar_inactive", f"  (Press 'i' to Insert -> Pane {self.active_pane})\n\n"))
            calcs_desc = {
                "RH Center": "Avg of 4 corners (mm)",
                "Downforce": "Total aero load (N)",
                "Aero Balance": "Front aero dist (%)"
            }
            for i, ch in enumerate(self.current_list):
                cls = "class:sidebar_active" if self.sb_idx == i else "class:sidebar_inactive"
                prefix = "  > " if self.sb_idx == i else "    "
                res.append((cls, f"{prefix}[{ch}]\n"))
                res.append((cls, f"      {calcs_desc[ch]}\n\n"))
            
        elif self.mode == 'sidebar_cat':
            res.append(("class:sidebar_title", "  [ RAW CATEGORIES ]\n"))
            res.append(("class:sidebar_inactive", "  (Press LEFT to return)\n\n"))
            for i, cat in enumerate(self.current_list):
                prefix = "  > " if self.sb_idx == i else "    "
                cls = "class:sidebar_active" if self.sb_idx == i else "class:sidebar_inactive"
                res.append((cls, f"{prefix}{cat}\n"))
                if self.sb_idx == i:
                    res.append(("class:sidebar_inactive", f"    {self.categories[cat][1][:28]}...\n"))
                res.append(("", "\n"))

        elif self.mode == 'sidebar_chan_list':
            res.append(("class:sidebar_title", f"  [ {self.active_cat.upper()} ]\n"))
            res.append(("class:sidebar_inactive", f"  (Press 'i' to Insert -> Pane {self.active_pane})\n\n"))
            
            visible_items = self.current_list[self.sb_scroll:self.sb_scroll+15]
            for idx, ch in enumerate(visible_items):
                actual_idx = self.sb_scroll + idx
                if actual_idx == self.sb_idx:
                    res.append(("class:sidebar_active", f"  > [{ch}]\n"))
                else:
                    res.append(("class:sidebar_inactive", f"    [{ch}]\n"))
            
            if self.sb_scroll + 15 < len(self.current_list):
                rem = len(self.current_list) - (self.sb_scroll+15)
                res.append(("class:sidebar_inactive", f"\n  ... ({rem} more) \n"))
            
        elif self.mode == 'sidebar_syntax':
            res.append(("class:sidebar_title", "  [ SYNTAX GUIDE ]\n"))
            res.append(("class:sidebar_inactive", "  (Press LEFT to return)\n\n"))
            
            res.append(("class:action", "  L \n"))
            res.append(("class:sidebar_inactive", "    Line Graph vs Dist\n\n"))
            res.append(("class:action", "  SP \n"))
            res.append(("class:sidebar_inactive", "    Scatter Plot\n\n"))
            res.append(("class:action", "  LSRL \n"))
            res.append(("class:sidebar_inactive", "    Scatter + Regression\n\n"))
            res.append(("class:sidebar_title", "  Example:\n"))
            res.append(("class:action", "  LSRL [RH Center] * 2\n"))
            
        return res

    def _get_panes_text(self):
        res = []
        def format_f(pane_id, width):
            f_str = self.formulas[pane_id]
            if not f_str: return "  (Empty)  ".center(width)
            if len(f_str) > width - 4: f_str = f_str[:width-7] + "..."
            return f"  {f_str}  ".center(width)

        def b_class(pane): return "class:active_border" if (self.active_pane == pane and self.mode == 'pane') else "class:border"
        def t_class(pane): return "class:active_title" if (self.active_pane == pane and self.mode == 'pane') else "class:title"
        
        iw = 80; hw = (iw - 2) // 2
        res.append(("", "\n\n"))
        res.append((b_class(0), "┌" + "─" * iw + "┐\n"))
        res.append((b_class(0), "│" + " [ TOP PANE ] Distance Line Graph ".center(iw) + "│\n"))
        res.append((b_class(0), "│" + " " * iw + "│\n"))
        res.append((b_class(0), "│" + format_f(0, iw) + "│\n"))
        res.append((b_class(0), "│" + " " * iw + "│\n"))
        res.append((b_class(0), "└" + "─" * iw + "┘\n"))

        res.append((b_class(1), "┌" + "─" * hw + "┐"))
        res.append(("", "  "))
        res.append((b_class(2), "┌" + "─" * hw + "┐\n"))
        res.append((b_class(1), "│" + " [ MID-LEFT ] Plot Area ".center(hw) + "│"))
        res.append(("", "  "))
        res.append((b_class(2), "│" + " [ MID-RIGHT ] Plot Area ".center(hw) + "│\n"))

        for idx in range(6):
            if idx == 2:
                res.append((b_class(1), "│" + format_f(1, hw) + "│"))
                res.append(("", "  "))
                res.append((b_class(2), "│" + format_f(2, hw) + "│\n"))
            else:
                res.append((b_class(1), "│" + " " * hw + "│"))
                res.append(("", "  "))
                res.append((b_class(2), "│" + " " * hw + "│\n"))

        res.append((b_class(1), "└" + "─" * hw + "┘"))
        res.append(("", "  "))
        res.append((b_class(2), "└" + "─" * hw + "┘\n"))

        res.append((b_class(3), "┌" + "─" * iw + "┐\n"))
        res.append((b_class(3), "│" + " [ BOTTOM PANE ] Distance Line Graph ".center(iw) + "│\n"))
        res.append((b_class(3), "│" + " " * iw + "│\n"))
        res.append((b_class(3), "│" + format_f(3, iw) + "│\n"))
        res.append((b_class(3), "│" + " " * iw + "│\n"))
        res.append((b_class(3), "└" + "─" * iw + "┘\n"))
        return res

    def _get_footer(self):
        footer = " [ESC] Sidebar | [TAB] Panes | [i] Insert Channel | [E] Edit Formula | [Bksp] Clear | [ENTER] Render | [Q] Quit "
        return [("class:title", "\n" + footer.center(120) + "\n")]

    def run(self):
        self.active_pane = 0
        self.result = None
        
        sidebar_window = Window(content=FormattedTextControl(self._get_sidebar_text), width=40)
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
    if headless: return
    
    all_channels = list(sessions[0]['data'].channels.keys())
    formulas = {0: "", 1: "", 2: "", 3: ""}
    tui = SandboxTUI(formulas, all_channels)
    
    while True:
        splash.clear_screen()
        splash.print_header("Math Sandbox - Dashboard Layout")
        print("\n  Design your custom 4-pane telemetry dashboard.")
        
        res = tui.run()
        if not res: break
        
        action, payload = res
        if action == 'quit': 
            break
            
        elif action == 'edit':
            pane_id = payload
            splash.clear_screen()
            splash.print_header(f"Edit Formula: Pane {pane_id}")
            print("  Syntax: L [channel] (Line), SP [channel] (Scatter), LSRL [channel] (Regression)")
            print(f"  Current: {formulas[pane_id]}")
            new_f = input("\n  Enter new formula (or press Enter to keep): ").strip()
            if new_f: formulas[pane_id] = new_f
            
        elif action == 'render':
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
