import sys
import os
import re
from prompt_toolkit.application import Application
from prompt_toolkit.layout.containers import Window, HSplit, WindowAlign
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

import ui.splash as splash

STYLE = Style.from_dict({
    'border': '#2D8AE2',
    'title': '#2D8AE2 bold',
    'selection': '#D2751D bold',
    'selected_item': '#32CD32 bold', # Lime Green for checked boxes
    'action': '#00FFFF bold',
    'description': '#00FFFF',
    'bg': '#1a1a1a',
})

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

class MultiSelectTUI:
    def __init__(self):
        self.kb = KeyBindings()
        self.cursor_index = 0
        self.items = []
        self.selected_indices = set()
        self.result = None
        self.title = ""
        self.subtitle = ""

        @self.kb.add('up')
        def _(event):
            self.cursor_index = (self.cursor_index - 1) % len(self.items)

        @self.kb.add('down')
        def _(event):
            self.cursor_index = (self.cursor_index + 1) % len(self.items)

        @self.kb.add(' ')
        def _(event):
            # Toggle checkbox
            if self.items[self.cursor_index].get('selectable', True):
                if self.cursor_index in self.selected_indices:
                    self.selected_indices.remove(self.cursor_index)
                else:
                    self.selected_indices.add(self.cursor_index)

        @self.kb.add('enter')
        def _(event):
            # Return all selected item objects
            self.result = [self.items[i] for i in self.selected_indices]
            # If nothing selected but hit enter on an item, maybe select that one?
            if not self.result and self.items[self.cursor_index].get('selectable', True):
                self.result = [self.items[self.cursor_index]]
            event.app.exit()

        @self.kb.add('a')
        def _(event):
            # Select all valid
            for i, item in enumerate(self.items):
                if item.get('is_valid', False):
                    self.selected_indices.add(i)

        @self.kb.add('f')
        def _(event):
            # Select only fastest
            self.selected_indices.clear()
            for i, item in enumerate(self.items):
                if "FASTEST" in item.get('status', ""):
                    self.selected_indices.add(i)
                    break

        @self.kb.add('q')
        def _(event):
            self.result = []
            event.app.exit()

    def _get_render_text(self):
        result = []
        
        # Header Box
        top_border = "┌" + "─" * (splash.BOX_WIDTH - 2) + "┐\n"
        bot_border = "└" + "─" * (splash.BOX_WIDTH - 2) + "┘\n"
        
        result.append(("class:border", " " * splash.PADDING + top_border))
        
        # Title Line
        t_len = len(self.title)
        pad_t = splash.BOX_WIDTH - 2 - t_len
        result.append(("class:border", " " * splash.PADDING + "│"))
        result.append(("class:title", " " + self.title + " " * (pad_t - 1)))
        result.append(("class:border", "│\n"))
        
        if self.subtitle:
            s_len = len(self.subtitle)
            pad_s = splash.BOX_WIDTH - 2 - s_len
            result.append(("class:border", " " * splash.PADDING + "│"))
            result.append(("", " " + self.subtitle + " " * (pad_s - 1)))
            result.append(("class:border", "│\n"))
            
        result.append(("class:border", " " * splash.PADDING + bot_border))
        
        # Table Header
        inner_w = splash.BOX_WIDTH - 2
        result.append(("class:border", " " * splash.PADDING + "┌" + "─" * inner_w + "┐\n"))
        
        header_str = f"   [ ] | {'ID':4} | {'LAP TIME':12} | {'STATUS':30}"
        pad_h = inner_w - len(header_str)
        result.append(("class:border", " " * splash.PADDING + "│"))
        result.append(("class:description", header_str + " " * pad_h))
        result.append(("class:border", "│\n"))
        
        result.append(("class:border", " " * splash.PADDING + "├" + "─" * inner_w + "┤\n"))
        
        # Rows
        for i, item in enumerate(self.items):
            is_cursor = (i == self.cursor_index)
            is_checked = (i in self.selected_indices)
            
            chk = "[X]" if is_checked else "[ ]"
            lap_id = str(item.get('lap_num', '-')).ljust(4)
            time_val = f"{item.get('time', 0.0):.3f}s".ljust(12)
            status = str(item.get('status', '')).ljust(30)
            
            prefix = " > " if is_cursor else "   "
            row_str = f"{prefix}{chk} | {lap_id} | {time_val} | {status}"
            pad_r = inner_w - len(row_str)
            
            result.append(("class:border", " " * splash.PADDING + "│"))
            
            if is_cursor:
                result.append(("class:selection", row_str + " " * pad_r))
            elif is_checked:
                result.append(("class:selected_item", row_str + " " * pad_r))
            else:
                if item.get('is_valid', False):
                    result.append(("class:action", row_str + " " * pad_r))
                else:
                    # Grey out invalid
                    result.append(("", row_str + " " * pad_r))
                    
            result.append(("class:border", "│\n"))

        result.append(("class:border", " " * splash.PADDING + "└" + "─" * inner_w + "┘\n"))
        
        footer = " [SPACE] Checkbox | [A] Select All Valid | [F] Select Fastest | [ENTER] Analyze | [Q] Quit "
        pad_f = (splash.BOX_WIDTH - len(footer)) // 2
        result.append(("class:title", " " * (splash.PADDING + pad_f) + footer + "\n"))

        return result

    def run(self, items, title, subtitle=""):
        self.items = items
        self.title = title
        self.subtitle = subtitle
        self.cursor_index = 0
        self.selected_indices = set()
        
        # Auto-select the fastest lap by default so the user can just hit enter
        for i, item in enumerate(self.items):
            if "FASTEST" in item.get('status', ""):
                self.selected_indices.add(i)
                self.cursor_index = i
                break
                
        text_control = FormattedTextControl(
            self._get_render_text,
            key_bindings=self.kb,
            focusable=True,
            show_cursor=False
        )
        
        def mouse_handler(mouse_event):
            if mouse_event.event_type == 'MOUSE_UP':
                y = mouse_event.position.y
                # Header + Title + Subtitle + TableHeader = ~7 lines.
                # Let's dynamically calculate
                offset = 7 if self.subtitle else 6
                
                if offset <= y < offset + len(self.items):
                    idx = y - offset
                    self.cursor_index = idx
                    # Toggle selection
                    if idx in self.selected_indices:
                        self.selected_indices.remove(idx)
                    else:
                        self.selected_indices.add(idx)
        
        text_control.mouse_handler = mouse_handler
        
        layout = Layout(HSplit([Window(content=text_control, align=WindowAlign.LEFT)]))
        
        app = Application(layout=layout, key_bindings=self.kb, mouse_support=True, full_screen=True, style=STYLE)
        app.run()
        
        os.system('cls' if os.name == 'nt' else 'clear')
        return self.result

multi_tui = MultiSelectTUI()
def get_multi_lap_choice(items, title, subtitle=""):
    return multi_tui.run(items, title, subtitle)
