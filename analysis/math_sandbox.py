import os
import sys
import re
import json
import datetime
import numpy as np
from prompt_toolkit.application import Application
from prompt_toolkit.layout.containers import Window, HSplit, WindowAlign, VSplit
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
import ui.splash as splash
from ui.metadata_printer import print_session_metadata
from core.config import get_gui_mode
from ui.graphing import show_ctk_graph

VMS_DIR = "vms"

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
    if not math_str: return []
    # Split by prefixes L, SP, LSRL, CT. 
    tokens = re.split(r'(?i)(?:^|\s+)(LSRL|SP|L|CT)\s+', math_str)
    
    commands = []
    
    # Parse tokens
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if not tok.strip():
            i += 1
            continue
            
        if tok.upper() in ('LSRL', 'SP', 'L', 'CT'):
            plot_type = tok.upper()
            if i + 1 < len(tokens):
                raw_expression = tokens[i+1].strip()
                i += 2
            else:
                break
        else:
            plot_type = 'L'
            raw_expression = tok.strip()
            i += 1
            
        if not raw_expression: continue
            
        # Parse out SHADE or GATE conditions
        expression = raw_expression
        cond_expr = None
        if 'SHADE' in expression.upper():
            parts = re.split(r'(?i)\s+SHADE\s+', expression, 1)
            expression = parts[0].strip()
            cond_expr = parts[1].strip()
        elif 'GATE' in expression.upper():
            parts = re.split(r'(?i)\s+GATE\s+', expression, 1)
            expression = parts[0].strip()
            cond_expr = parts[1].strip()
            
        x_expr, y_expr, z_expr = None, expression, None
        
        if plot_type in ('SP', 'LSRL') and ',' in expression:
            parts = expression.split(',', 1)
            x_expr = parts[0].strip()
            y_expr = parts[1].strip()
        elif plot_type == 'CT':
            # Check for commas
            commas_count = expression.count(',')
            if commas_count >= 2:
                parts = expression.split(',', 2)
                x_expr = parts[0].strip()
                y_expr = parts[1].strip()
                z_expr = parts[2].strip()
            elif commas_count == 1:
                parts = expression.split(',', 1)
                x_expr = parts[0].strip()
                y_expr = parts[1].strip()
                z_expr = "[Speed]" # Default Z axis is Speed
            else:
                # No commas. Shortcut!
                # If expression is [Aero Balance] or [Downforce] or any single variable,
                # we map X = Average Front Ride Height, Y = Average Rear Ride Height, Z = Expression
                x_expr = "( [Ride Height FL] + [Ride Height FR] ) / 2.0"
                y_expr = "( [Ride Height RL] + [Ride Height RR] ) / 2.0"
                z_expr = expression
            
        channels = re.findall(r'\[(.*?)\]', raw_expression)
        commands.append((plot_type, expression, channels, x_expr, y_expr, z_expr, cond_expr))
        
    return commands

class SandboxTUI:
    def __init__(self, formulas, all_channels):
        self.kb = KeyBindings()
        self.mode = 'pane' # 'pane', 'sidebar_main', 'sidebar_calc', 'sidebar_cat', 'sidebar_chan_list', 'sidebar_custom_expr', 'sidebar_syntax', 'sidebar_vms'
        self.active_pane = 0
        self.sb_idx = 0      
        self.sb_scroll = 0
        self.formulas = formulas
        self.all_channels = sorted(all_channels)
        self.custom_expressions = {}
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
                limit = len(self.current_list) - 1 if self.mode in ('sidebar_calc', 'sidebar_cat', 'sidebar_chan_list', 'sidebar_custom_expr', 'sidebar_vms') else 3
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
        def _(event):
            if self.mode == 'pane':
                if self.active_pane == 1: self.active_pane = 2
            elif self.mode == 'sidebar_main':
                self._enter_sidebar_menu()
            elif self.mode == 'sidebar_cat':
                self.active_cat = self.cat_keys[self.sb_idx]
                self.mode = 'sidebar_chan_list'
                keywords, _ = self.categories[self.active_cat]
                if keywords == [""]:
                    self.current_list = self.all_channels
                else:
                    self.current_list = [ch for ch in self.all_channels if any(k.lower() in ch.lower() for k in keywords)]
                self.sb_idx = 0; self.sb_scroll = 0

        @self.kb.add('enter')
        def _(event):
            if self.mode == 'pane':
                self.result = ('render', None)
                event.app.exit()
            elif self.mode == 'sidebar_main':
                self._enter_sidebar_menu()
            elif self.mode == 'sidebar_cat':
                self.active_cat = self.cat_keys[self.sb_idx]
                self.mode = 'sidebar_chan_list'
                keywords, _ = self.categories[self.active_cat]
                if keywords == [""]:
                    self.current_list = self.all_channels
                else:
                    self.current_list = [ch for ch in self.all_channels if any(k.lower() in ch.lower() for k in keywords)]
                self.sb_idx = 0; self.sb_scroll = 0
            elif self.mode == 'sidebar_vms':
                if self.current_list:
                    vm_file = self.current_list[self.sb_idx]
                    self.result = ('load_vm', vm_file)
                    event.app.exit()

        @self.kb.add('i')
        def _(event):
            if self.mode in ('sidebar_calc', 'sidebar_chan_list', 'sidebar_custom_expr') and self.current_list:
                ch = self.current_list[self.sb_idx]
                f = self.formulas[self.active_pane]
                if f and not f.endswith(' '): f += ' '
                self.formulas[self.active_pane] = f + f"[{ch}] "

        @self.kb.add('backspace')
        @self.kb.add('delete')
        @self.kb.add('c-h')
        def _(event):
            if self.mode == 'pane':
                self.formulas[self.active_pane] = ""

        @self.kb.add('a')
        def _(event):
            if self.mode == 'sidebar_custom_expr':
                self.result = ('add_expr', None)
                event.app.exit()

        @self.kb.add('d')
        def _(event):
            if self.mode == 'sidebar_custom_expr' and self.current_list:
                self.result = ('delete_expr', self.current_list[self.sb_idx])
                event.app.exit()

        @self.kb.add('e')
        def _(event):
            if self.mode == 'pane':
                self.result = ('edit', self.active_pane)
                event.app.exit()
            elif self.mode == 'sidebar_custom_expr' and self.current_list:
                self.result = ('edit_expr', self.current_list[self.sb_idx])
                event.app.exit()

        @self.kb.add('c-p')
        def _(event):
            if self.mode == 'pane':
                self.result = ('print', None)
                event.app.exit()
                
        @self.kb.add('c-s')
        def _(event):
            if self.mode == 'pane':
                self.result = ('save_vm', None)
                event.app.exit()

        @self.kb.add('q')
        def _(event):
            self.result = ('quit', None)
            event.app.exit()

    def _enter_sidebar_menu(self):
        if self.sb_idx == 0: 
            self.mode = 'sidebar_calc'
            self.current_list = ["RH Center", "Downforce", "Aero Balance"]
            self.sb_idx = 0; self.sb_scroll = 0
        elif self.sb_idx == 1: 
            self.mode = 'sidebar_cat'
            self.current_list = self.cat_keys
            self.sb_idx = 0; self.sb_scroll = 0
        elif self.sb_idx == 2:
            self.mode = 'sidebar_custom_expr'
            self.current_list = sorted(list(self.custom_expressions.keys()))
            self.sb_idx = 0; self.sb_scroll = 0
        elif self.sb_idx == 3: 
            self.mode = 'sidebar_vms'
            if not os.path.exists(VMS_DIR): os.makedirs(VMS_DIR)
            self.current_list = [f for f in os.listdir(VMS_DIR) if f.endswith('.json')]
            self.sb_idx = 0; self.sb_scroll = 0
        elif self.sb_idx == 4: 
            self.mode = 'sidebar_syntax'
            self.current_list = []

    def _get_sidebar_text(self):
        res = []
        res.append(("", "\n\n"))
        if self.mode == 'sidebar_main':
            res.append(("class:sidebar_title", "  [ DIRECTORY ]\n\n"))
            items = ["Calculated Channels >>", "Raw Channels >>", "Custom Expressions >>", "Visualization Models >>", "Syntaxing Guide >>"]
            for i, txt in enumerate(items):
                prefix = "  > " if self.sb_idx == i else "    "
                cls = "class:sidebar_active" if self.sb_idx == i else "class:sidebar_inactive"
                res.append((cls, f"{prefix}{txt}\n\n"))
        elif self.mode == 'sidebar_calc':
            res.append(("class:sidebar_title", "  [ CALCULATED CHANNELS ]\n"))
            res.append(("class:sidebar_inactive", f"  (Press 'i' to Insert -> Pane {self.active_pane})\n\n"))
            calcs_desc = { "RH Center": "Avg of 4 corners (mm)", "Downforce": "Total aero load (N)", "Aero Balance": "Front aero dist (%)" }
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
                if actual_idx == self.sb_idx: res.append(("class:sidebar_active", f"  > [{ch}]\n"))
                else: res.append(("class:sidebar_inactive", f"    [{ch}]\n"))
            if self.sb_scroll + 15 < len(self.current_list):
                rem = len(self.current_list) - (self.sb_scroll+15)
                res.append(("class:sidebar_inactive", f"\n  ... ({rem} more) \n"))
        elif self.mode == 'sidebar_custom_expr':
            res.append(("class:sidebar_title", "  [ CUSTOM EXPRESSIONS ]\n"))
            res.append(("class:sidebar_inactive", "  (Press 'a' to Add | 'd' to Delete)\n"))
            res.append(("class:sidebar_inactive", f"  (Press 'e' to Edit | 'i' to Insert -> Pane {self.active_pane})\n\n"))
            if not self.current_list:
                res.append(("class:sidebar_inactive", "    No custom expressions defined.\n"))
            else:
                for i, name in enumerate(self.current_list):
                    cls = "class:sidebar_active" if self.sb_idx == i else "class:sidebar_inactive"
                    prefix = "  > " if self.sb_idx == i else "    "
                    expr_val = self.custom_expressions[name]
                    # Handle both dictionary and legacy raw strings
                    if isinstance(expr_val, dict):
                        formula_str = expr_val.get('formula', '')
                    else:
                        formula_str = str(expr_val)
                    res.append((cls, f"{prefix}{name}\n"))
                    if self.sb_idx == i:
                        res.append(("class:sidebar_inactive", f"      = {formula_str[:28]}\n"))
                    res.append(("", "\n"))
        elif self.mode == 'sidebar_vms':
            res.append(("class:sidebar_title", "  [ VISUALIZATION MODELS ]\n"))
            res.append(("class:sidebar_inactive", "  (Press ENTER to Load)\n\n"))
            if not self.current_list:
                res.append(("class:sidebar_inactive", "    No VM presets found.\n    (Press Ctrl+S to save one)"))
            else:
                visible_items = self.current_list[self.sb_scroll:self.sb_scroll+15]
                for idx, vm in enumerate(visible_items):
                    actual_idx = self.sb_scroll + idx
                    cls = "class:sidebar_active" if actual_idx == self.sb_idx else "class:sidebar_inactive"
                    prefix = "  > " if actual_idx == self.sb_idx else "    "
                    res.append((cls, f"{prefix}{vm}\n"))
        elif self.mode == 'sidebar_syntax':
            res.append(("class:sidebar_title", "  [ SYNTAX GUIDE ]\n"))
            res.append(("class:sidebar_inactive", "  (Press LEFT to return)\n\n"))
            res.append(("class:action", "  L [channel] \n"))
            res.append(("class:sidebar_inactive", "    Line Graph (Y) vs Distance\n\n"))
            res.append(("class:action", "  SP [X-channel], [Y-channel] \n"))
            res.append(("class:sidebar_inactive", "    Scatter Plot (X vs Y)\n\n"))
            res.append(("class:action", "  L [Y] SHADE [Cond] \n"))
            res.append(("class:sidebar_inactive", "    Shaded Line overlay\n\n"))
            res.append(("class:action", "  SP [X],[Y] GATE [Cond] \n"))
            res.append(("class:sidebar_inactive", "    Ghost Cloud Scatter overlay\n\n"))
            res.append(("class:action", "  CT [X], [Y], [Z] \n"))
            res.append(("class:sidebar_inactive", "    3D Triangulated Contour Map\n\n"))
            res.append(("class:action", "  CT [Aero Balance] (Shortcut) \n"))
            res.append(("class:sidebar_inactive", "    Maps X=FrontRH, Y=RearRH, Z=Aero\n\n"))
            res.append(("class:sidebar_inactive", "  *If no comma is used for SP/LSRL,\n    X defaults to Speed (km/h).\n\n"))
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
        footer = " [ESC] Sidebar | [TAB] Panes | [i] Insert | [E] Edit | [Ctrl+S] Save VM | [ENTER] Render | [Ctrl+P] Print | [Q] Quit "
        return [("class:title", "\\n" + footer.center(120) + "\\n")]

    def run(self):
        sidebar_window = Window(content=FormattedTextControl(self._get_sidebar_text), width=40)
        separator = Window(width=3, char=' │ ', style='class:border')
        panes_window = Window(content=FormattedTextControl(self._get_panes_text), width=85)
        layout = Layout(HSplit([VSplit([sidebar_window, separator, panes_window]), 
                               Window(content=FormattedTextControl(self._get_footer), height=2)]))
        app = Application(layout=layout, key_bindings=self.kb, full_screen=True, style=STYLE)
        app.run()
        os.system('cls' if os.name == 'nt' else 'clear')
        return self.result

def run_custom_math_graph(sessions, headless=False, headless_config=None):
    if headless: return
    all_channels = list(sessions[0]['data'].channels.keys())
    formulas = {0: "", 1: "", 2: "", 3: ""}
    
    # Load Global Custom Expressions
    custom_expr_file = os.path.join(VMS_DIR, "custom_expressions.json")
    try:
        with open(custom_expr_file, 'r') as f:
            custom_expressions = json.load(f)
    except:
        custom_expressions = {}
        
    tui = SandboxTUI(formulas, all_channels)
    tui.custom_expressions = custom_expressions
    
    while True:
        splash.clear_screen()
        splash.print_header("Math Sandbox - Dashboard Layout")
        res = tui.run()
        if not res: break
        action, payload = res
        if action == 'quit': break
        
        elif action == 'add_expr':
            splash.clear_screen()
            splash.print_header("Add Custom Expression")
            print("  Define a custom mathematical channel using other channels.")
            print("  [!] ALWAYS enclose channel names in brackets, e.g. [LongAccel] > 0.4")
            print("  Syntax: [Brake] > 25 AND abs([WheelSlip]) > 5")
            name = input("\\n  Enter Expression Name (e.g. ABS_Active): ").strip().replace(' ', '_')
            if name:
                from prompt_toolkit import prompt
                expr = prompt("  Formula: ").strip()
                if expr:
                    print("\\n  Select Custom Accent Color:")
                    print("    1. OpenDAV Blue")
                    print("    2. OpenDAV Orange")
                    print("    3. Vibrant Green")
                    print("    4. Hot Pink")
                    print("    5. Deep Purple")
                    print("    6. Aggressive Red")
                    c_choice = input("  Choice [1-6, default=4]: ").strip()
                    color_map = {
                        '1': '#2D8AE2',
                        '2': '#D2751D',
                        '3': '#32CD32',
                        '4': '#FF1493',
                        '5': '#A020F0',
                        '6': '#E53E3E'
                    }
                    sel_color = color_map.get(c_choice, '#FF1493')
                    custom_expressions[name] = {"formula": expr, "color": sel_color}
                    os.makedirs(VMS_DIR, exist_ok=True)
                    with open(custom_expr_file, 'w') as f:
                        json.dump(custom_expressions, f, indent=4)
                    print(f"\\n  [+] Saved expression: {name}")
                import time; time.sleep(0.5)
            tui.custom_expressions = custom_expressions
            tui.mode = 'sidebar_custom_expr'
            tui.current_list = sorted(list(custom_expressions.keys()))
            tui.sb_idx = 0; tui.sb_scroll = 0
            
        elif action == 'delete_expr':
            name = payload
            if name in custom_expressions:
                del custom_expressions[name]
                with open(custom_expr_file, 'w') as f:
                    json.dump(custom_expressions, f, indent=4)
                print(f"\\n  [-] Deleted expression: {name}")
                import time; time.sleep(0.5)
            tui.custom_expressions = custom_expressions
            tui.mode = 'sidebar_custom_expr'
            tui.current_list = sorted(list(custom_expressions.keys()))
            tui.sb_idx = 0; tui.sb_scroll = 0
            
        elif action == 'edit_expr':
            name = payload
            if name in custom_expressions:
                splash.clear_screen()
                splash.print_header(f"Edit Expression: {name}")
                print("  [!] ALWAYS enclose channel names in brackets, e.g. [LongAccel] > 0.4")
                
                # Fetch existing values safely
                old_val = custom_expressions[name]
                if isinstance(old_val, dict):
                    old_formula = old_val.get('formula', '')
                    old_color = old_val.get('color', '#FF1493')
                else:
                    old_formula = str(old_val)
                    old_color = '#FF1493'
                
                from prompt_toolkit import prompt
                new_expr = prompt("  Formula: ", default=old_formula).strip()
                if new_expr:
                    print("\\n  Select Custom Accent Color:")
                    print("    1. OpenDAV Blue")
                    print("    2. OpenDAV Orange")
                    print("    3. Vibrant Green")
                    print("    4. Hot Pink")
                    print("    5. Deep Purple")
                    print("    6. Aggressive Red")
                    c_choice = input(f"  Choice [1-6, current={old_color}]: ").strip()
                    color_map = {
                        '1': '#2D8AE2',
                        '2': '#D2751D',
                        '3': '#32CD32',
                        '4': '#FF1493',
                        '5': '#A020F0',
                        '6': '#E53E3E'
                    }
                    sel_color = color_map.get(c_choice, old_color)
                    custom_expressions[name] = {"formula": new_expr, "color": sel_color}
                    with open(custom_expr_file, 'w') as f:
                        json.dump(custom_expressions, f, indent=4)
                    print(f"\\n  [+] Saved expression: {name}")
                import time; time.sleep(0.5)
            tui.custom_expressions = custom_expressions
            tui.mode = 'sidebar_custom_expr'
            tui.current_list = sorted(list(custom_expressions.keys()))
            tui.sb_idx = sorted(list(custom_expressions.keys())).index(name) if name in custom_expressions else 0
            
        elif action == 'edit':
            pane_id = payload
            splash.clear_screen()
            splash.print_header(f"Edit Formula: Pane {pane_id}")
            print("  Syntax: L [Y-expr], SP [X-expr], [Y-expr], LSRL [X-expr], [Y-expr], CT [X], [Y], [Z]")
            
            from prompt_toolkit import prompt
            new_f = prompt("\\n  Formula: ", default=formulas[pane_id]).strip()
            formulas[pane_id] = new_f
            
        elif action == 'save_vm':
            splash.clear_screen()
            splash.print_header("Save Visualization Model (Preset)")
            print("  Save current 4-pane configuration as a JSON preset.")
            name = input("\\n  Enter VM Name (e.g. Aero_Efficiency): ").strip().replace(' ', '_')
            if name:
                os.makedirs(VMS_DIR, exist_ok=True)
                with open(os.path.join(VMS_DIR, f"{name}.json"), 'w') as f:
                    json.dump({"name": name, "panes": formulas}, f, indent=4)
                print(f"\\n  [+] VM Preset saved to {VMS_DIR}/{name}.json")
                input("  Press Enter to continue...")
                
        elif action == 'load_vm':
            vm_file = payload
            try:
                with open(os.path.join(VMS_DIR, vm_file), 'r') as f:
                    data = json.load(f)
                    # Convert keys to int as JSON saves them as strings
                    formulas.update({int(k): v for k, v in data['panes'].items()})
                print(f"\\n  [+] Loaded VM Preset: {vm_file}")
            except Exception as e:
                print(f"\\n  [!] Error loading VM: {e}")
                input("  Press Enter to continue...")
                
        elif action in ('render', 'print'):
            import matplotlib.pyplot as plt
            from matplotlib.gridspec import GridSpec
            import matplotx
            from matplotlib.colors import LinearSegmentedColormap
            opendav_colors = ["#2D8AE2", "#FF1493", "#D2751D"]
            opendav_cmap = LinearSegmentedColormap.from_list("opendav_aero", opendav_colors, N=256)
            splash.clear_screen()
            splash.print_header("Rendering Math Sandbox Dashboard...")
            session = sessions[0]
            data = session['data']
            channels_map = session['channels']
            try:
                # Build Sector & Lap Mask
                dist_ch = channels_map.get('dist', 'Distance')
                dist_raw = data[dist_ch].data if dist_ch in data else None
                
                lap_ch = channels_map.get('lap', 'Lap')
                lap_raw = data[lap_ch].data if lap_ch in data else None
                
                time_ch = channels_map.get('time', 'SessionTime')
                n_points = len(data[time_ch].data) if time_ch in data else len(data['Speed'].data)
                final_mask = np.ones(n_points, dtype=bool)
                
                bounds = session.get('distance_bounds')
                if bounds and dist_raw is not None:
                    final_mask &= (dist_raw >= bounds[0]) & (dist_raw <= bounds[1])
                    
                md = session.get('metadata', {})
                sel_laps = md.get('selected_laps')
                if sel_laps and lap_raw is not None:
                    final_mask &= np.isin(lap_raw, sel_laps)
                    
                if not np.any(final_mask):
                    print("  [!] Error: The selected sector mask contains no data.")
                    input("\\nPress Enter to return...")
                    continue
                
                spd_ch = next((ch for ch in ['Speed', 'virt_body_v'] if ch in data), 'Speed')
                raw_speed = data[spd_ch].data[final_mask]
                speed_kmh = raw_speed * 3.6 if np.max(raw_speed) < 150 else raw_speed
                
                fl_rh = data['Ride Height FL'].data[final_mask] * 1000 if 'Ride Height FL' in data else np.zeros_like(speed_kmh)
                fr_rh = data['Ride Height FR'].data[final_mask] * 1000 if 'Ride Height FR' in data else np.zeros_like(speed_kmh)
                rl_rh = data['Ride Height RL'].data[final_mask] * 1000 if 'Ride Height RL' in data else np.zeros_like(speed_kmh)
                rr_rh = data['Ride Height RR'].data[final_mask] * 1000 if 'Ride Height RR' in data else np.zeros_like(speed_kmh)
                rh_center = (fl_rh + fr_rh + rl_rh + rr_rh) / 4.0
                
                fl_l = data['Suspension Load FL'].data[final_mask] if 'Suspension Load FL' in data else np.zeros_like(speed_kmh)
                fr_l = data['Suspension Load FR'].data[final_mask] if 'Suspension Load FR' in data else np.zeros_like(speed_kmh)
                rl_l = data['Suspension Load RL'].data[final_mask] if 'Suspension Load RL' in data else np.zeros_like(speed_kmh)
                rr_l = data['Suspension Load RR'].data[final_mask] if 'Suspension Load RR' in data else np.zeros_like(speed_kmh)
                
                overrides = getattr(data, 'overrides', {})
                phys = overrides.get('physics_model', {})
                a_mass = phys.get('actual_mass_kg', 1350.0)
                
                v_g = data['VertAccel'].data[final_mask] / 9.80665 if 'VertAccel' in data else np.ones_like(speed_kmh)
                st_w = (a_mass * 9.80665) 
                
                df_total = (fl_l + fr_l + rl_l + rr_l) - (st_w * v_g)
                aero_bal = (((fl_l + fr_l) - (st_w * 0.45 * v_g)) / (df_total + 1e-6)) * 100.0
                
                dist = dist_raw[final_mask] if dist_raw is not None else np.arange(len(speed_kmh))
                
                math_env = { 'RH Center': rh_center, 'Downforce': df_total, 'Aero Balance': aero_bal, 'Speed': speed_kmh, 'np': np }
                
                # Load standard raw channels
                for ch_name in data.channels: 
                    ch_data = data[ch_name].data
                    if len(ch_data) == len(final_mask): 
                        math_env[ch_name] = ch_data[final_mask]
                    else: 
                        math_env[ch_name] = ch_data
                
                # Evaluate and load custom expressions (pre-compile standard MoTeC logicals on the fly)
                def evaluate_expr(expr, env):
                    eval_str = expr
                    # Compile AND, OR, NOT into bitwise array logic
                    eval_str = re.sub(r'\bAND\b', '&', eval_str, flags=re.IGNORECASE)
                    eval_str = re.sub(r'\bOR\b', '|', eval_str, flags=re.IGNORECASE)
                    eval_str = re.sub(r'\bNOT\b', '~', eval_str, flags=re.IGNORECASE)
                    
                    found_channels = re.findall(r'\[(.*?)\]', eval_str)
                    for c in found_channels:
                        if c in env: 
                            eval_str = eval_str.replace(f'[{c}]', f"env['{c}']")
                        else: 
                            raise ValueError(f"Channel '{c}' not found.")
                    return eval(eval_str, {"__builtins__": {}}, {"env": env, "np": np})
                
                # Evaluate custom expressions in order
                for name, expr_data in custom_expressions.items():
                    if isinstance(expr_data, dict):
                        expr = expr_data.get('formula', '')
                    else:
                        expr = str(expr_data)
                    try:
                        math_env[name] = evaluate_expr(expr, math_env)
                    except Exception as e:
                        math_env[name] = np.zeros_like(speed_kmh) # safe fallback
                        
            except Exception as e:
                print(f"  [!] Error preparing data: {e}"); input("\nPress Enter..."); continue
            try:
                fig = plt.figure(figsize=(16, 10), num='OpenDAV - Math Sandbox Dashboard')
                plt.style.use(matplotx.styles.aura['dark'])
                gs = GridSpec(3, 2, height_ratios=[1, 2, 1], figure=fig)
                pane_axes = { 0: fig.add_subplot(gs[0, :]), 1: fig.add_subplot(gs[1, 0]), 2: fig.add_subplot(gs[1, 1]), 3: fig.add_subplot(gs[2, :]) }
                
                for p_id, ax in pane_axes.items():
                    f_str = formulas[p_id]
                    if not f_str: ax.text(0.5, 0.5, f"Pane {p_id} (Empty)", ha='center', va='center', alpha=0.5); continue
                    try:
                        commands = parse_formula(f_str)
                        colors = ['#0ea5e9', '#D2751D', '#32CD32', '#FF1493', '#A020F0']
                        
                        for i, (p_type, p_expr, _, x_expr, y_expr, z_expr, cond_expr) in enumerate(commands):
                            c_col = colors[i % len(colors)]
                            
                            # Parse condition mask if SHADE or GATE is present
                            cond_mask = None
                            if cond_expr:
                                try:
                                    cond_mask = evaluate_expr(cond_expr, math_env)
                                    # Extract name without brackets to look up color
                                    cond_name = cond_expr.strip('[]')
                                    if cond_name in custom_expressions:
                                        expr_data = custom_expressions[cond_name]
                                        if isinstance(expr_data, dict):
                                            c_col = expr_data.get('color', c_col)
                                except Exception as cond_err:
                                    print(f"  [!] Condition Error on {cond_expr}: {cond_err}")
                            
                            if p_type == 'L':
                                y_data = evaluate_expr(p_expr, math_env)
                                
                                if cond_mask is not None:
                                    # Shaded / Gated line plot
                                    # 1. Base Layer (Faint slate background)
                                    ax.plot(dist, y_data, color='#334155', alpha=0.25, lw=1.2)
                                    # 2. Filter Layer (Mask non-active points)
                                    y_shaded = np.copy(y_data).astype(float)
                                    y_shaded[~cond_mask] = np.nan
                                    # 3. Highlight Layer (Vibrant overlay)
                                    ax.plot(dist, y_shaded, c=c_col, lw=2.5, label=f"{p_expr[:12]} (Gated)")
                                    # 4. Fill Layer
                                    ax.fill_between(dist, y_shaded, 0, color=c_col, alpha=0.12)
                                else:
                                    # Normal continuous line plot
                                    ax.plot(dist, y_data, c=c_col, lw=1.5, label=p_expr[:15])
                                
                                if i == 0: ax.set_ylabel(p_expr[:20])
                                
                            elif p_type in ('SP', 'LSRL'):
                                y_data = evaluate_expr(y_expr, math_env)
                                if x_expr:
                                    x_data = evaluate_expr(x_expr, math_env)
                                    if i == 0: ax.set_xlabel(x_expr[:20])
                                else:
                                    x_data = speed_kmh if p_id in (1, 2) else dist
                                    if i == 0: ax.set_xlabel('Speed (km/h)' if p_id in (1, 2) else 'Distance')
                                    
                                if i == 0: ax.set_ylabel(y_expr[:20])
                                
                                if cond_mask is not None:
                                    # Gated Scatter Overlay (Ghost Cloud technique)
                                    # 1. Ghost Layer (Faint background)
                                    ax.scatter(x_data[~cond_mask], y_data[~cond_mask], color='#222222', s=5, alpha=0.08)
                                    # 2. Focus Layer (Active highlighted data)
                                    ax.scatter(x_data[cond_mask], y_data[cond_mask], c=c_col, s=8, alpha=0.7, label=f"{y_expr[:10]} (Active)")
                                    
                                    if p_type == 'LSRL':
                                        x_gated = x_data[cond_mask]
                                        y_gated = y_data[cond_mask]
                                        idx = np.isfinite(x_gated) & np.isfinite(y_gated)
                                        if np.sum(idx) > 2:
                                            m, b = np.polyfit(x_gated[idx], y_gated[idx], 1)
                                            ax.plot(x_gated, m*x_gated + b, c=c_col, lw=2)
                                            if i == 0: ax.set_title(f"Gated Slope: {m:.4f}", fontsize=10)
                                else:
                                    # Normal standard scatter plot
                                    ax.scatter(x_data, y_data, c=c_col, s=5, alpha=0.3, label=y_expr[:10])
                                    
                                    if p_type == 'LSRL':
                                        idx = np.isfinite(x_data) & np.isfinite(y_data)
                                        if np.sum(idx) > 2:
                                            m, b = np.polyfit(x_data[idx], y_data[idx], 1)
                                            ax.plot(x_data, m*x_data + b, c=c_col, lw=2)
                                            if i == 0: ax.set_title(f"Slope: {m:.4f}", fontsize=10)
                                            
                            elif p_type == 'CT':
                                try:
                                    x_data = evaluate_expr(x_expr, math_env)
                                    y_data = evaluate_expr(y_expr, math_env)
                                    z_data = evaluate_expr(z_expr, math_env)
                                    
                                    idx = np.isfinite(x_data) & np.isfinite(y_data) & np.isfinite(z_data)
                                    if np.sum(idx) > 10:
                                        cntr = ax.tricontourf(x_data[idx], y_data[idx], z_data[idx], levels=15, cmap='plasma', extend='both')
                                        if i == 0:
                                            cbar = fig.colorbar(cntr, ax=ax, shrink=0.8, pad=0.02)
                                            cbar.ax.tick_params(labelsize=8)
                                            ax.set_xlabel(x_expr[:15], fontsize=8)
                                            ax.set_ylabel(y_expr[:15], fontsize=8)
                                            ax.set_title(f"Contour: {z_expr[:20]}", fontsize=10)
                                    else:
                                        ax.text(0.5, 0.5, "Insufficient valid points", color='red', ha='center', va='center')
                                except Exception as e:
                                    ax.text(0.5, 0.5, f"Contour Error: {e}", color='red', ha='center', va='center')
                        
                        if len(commands) > 1:
                            ax.legend(loc='upper right', frameon=False, fontsize=8)
                            
                        import matplotlib.ticker as ticker
                        ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=6, prune='both'))
                        if p_id in (0, 3):
                            ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=12))
                        ax.grid(True, alpha=0.1)
                    except Exception as e: ax.text(0.5, 0.5, f"Error: {e}", color='red', ha='center', va='center')
                plt.tight_layout(); fig.subplots_adjust(top=0.92)
                fig.suptitle(f"OpenDAV Math Sandbox: {os.path.basename(session['file_path'])}", color='white', fontsize=16)
                if action == 'print':
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                    os.makedirs("exports", exist_ok=True)
                    out = os.path.join("exports", f"MathSandbox_{ts}_{os.path.basename(session['file_path'])}.png")
                    plt.savefig(out, dpi=300, bbox_inches='tight'); plt.close(fig)
                    print(f"\\n  [+] Saved Sandbox Dashboard to: {out}")
                    input("  Press Enter to return to editor...")
                else:
                    if get_gui_mode() == 3: show_ctk_graph(fig, "OpenDAV - Math Sandbox")
                    else: 
                        import matplotlib.pyplot as plt
                        plt.ioff(); plt.show(block=True)
                    input("  Press Enter to return to editor...")
            except Exception as outer_e:
                print(f"\\n  [!!!] CRASH during rendering: {outer_e}"); import traceback; traceback.print_exc()
                input("  Press Enter to return to editor...")
