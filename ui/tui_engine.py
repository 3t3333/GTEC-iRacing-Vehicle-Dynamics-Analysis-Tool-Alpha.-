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

# OpenDAV Theme
STYLE = Style.from_dict({
    'border': '#2D8AE2',
    'title': '#2D8AE2 bold',
    'selection': '#D2751D bold', # Gold/Orange
    'description': '#00FFFF', # Cyan
    'action': '#00FFFF bold',
    'bg': '#1a1a1a',
})

class OpenDAV_TUI:
    def __init__(self):
        self.kb = KeyBindings()
        self.selected_index = 0
        self.result = None
        self.menu_items = []
        
        @self.kb.add('up')
        def _(event):
            self.selected_index = (self.selected_index - 1) % len(self.menu_items)

        @self.kb.add('down')
        def _(event):
            self.selected_index = (self.selected_index + 1) % len(self.menu_items)

        @self.kb.add('enter')
        def _(event):
            self.result = str(self.menu_items[self.selected_index][0]).lower()
            event.app.exit()

        @self.kb.add('q')
        def _(event):
            self.result = 'q'
            event.app.exit()

        @self.kb.add('p')
        def _(event):
            self.result = 'p'
            event.app.exit()

        # Keyboard shortcuts 1-9
        for i in range(1, 10):
            @self.kb.add(str(i))
            def _(event, i=i):
                if i <= len(self.menu_items):
                    # Find item with this ID
                    for item in self.menu_items:
                        if str(item[0]) == str(i):
                            self.result = str(i)
                            event.app.exit()
                            break

    def _get_menu_text(self):
        result = []
        
        # Logo & Subtitle
        top_border = "┌" + "─" * (splash.BOX_WIDTH - 2) + "┐\n"
        bot_border = "└" + "─" * (splash.BOX_WIDTH - 2) + "┘\n"
        
        result.append(("class:border", " " * splash.PADDING + top_border))
        for i, line in enumerate(splash.ascii_art):
            result.append(("class:border", " " * splash.PADDING + "│"))
            result.append(("", line.center(splash.BOX_WIDTH - 2)))
            result.append(("class:border", "│\n"))
        result.append(("class:border", " " * splash.PADDING + bot_border))
        
        result.append(("class:border", " " * splash.PADDING + top_border))
        sub = "Open Source Data Analysis and Visualization Systems"
        padding_len = (splash.BOX_WIDTH - 2 - len(sub)) // 2
        result.append(("class:border", " " * splash.PADDING + "│"))
        result.append(("", " " * padding_len + sub + " " * (splash.BOX_WIDTH - 2 - padding_len - len(sub))))
        result.append(("class:border", "│\n"))
        result.append(("class:border", " " * splash.PADDING + bot_border + "\n"))

        # Menu
        inner_w = splash.BOX_WIDTH - 2
        result.append(("class:border", " " * splash.PADDING + "┌" + "─" * inner_w + "┐\n"))
        
        for i, (num, title, desc) in enumerate(self.menu_items):
            is_selected = (i == self.selected_index)
            
            prefix = " > " if is_selected else "   "
            num_str = f"{num}."
            title_str = title.ljust(32)
            desc_str = f">> {desc}"
            
            line_content = f"{prefix}{num_str} {title_str} {desc_str}"
            pad = inner_w - len(line_content)
            
            result.append(("class:border", " " * splash.PADDING + "│"))
            
            if is_selected:
                result.append(("class:selection", line_content + " " * pad))
            else:
                result.append(("class:action", f"{prefix}{num_str} "))
                result.append(("", f"{title_str} "))
                result.append(("class:description", f"{desc_str}" + " " * pad))
                
            result.append(("class:border", "│\n"))
            
        result.append(("class:border", " " * splash.PADDING + "└" + "─" * inner_w + "┘\n"))
        result.append(("", "\n" + " " * (splash.PADDING + 2) + "(Use arrows/mouse to select, ENTER to launch, 'q' to quit)\n"))
        
        return result

    def run_menu(self, menu_items):
        self.menu_items = menu_items
        self.selected_index = 0
        self.result = None
        
        text_control = FormattedTextControl(
            self._get_menu_text,
            key_bindings=self.kb,
            focusable=True,
            show_cursor=False
        )
        
        # Dynamic Mouse Handler
        def mouse_handler(mouse_event):
            if mouse_event.event_type == 'MOUSE_UP':
                y = mouse_event.position.y
                # Header lines = 1 (gap) + 1 (border) + 6 (logo) + 1 (border) + 1 (border) + 1 (sub) + 1 (border) + 1 (gap) + 1 (border) = 13 lines
                # Wait, let's count exactly.
                # gap(0), border(1), logo(2,3,4,5,6,7), border(8), border(9), sub(10), border(11), gap(12), border(13)
                # So menu starts at y=14
                menu_start_y = 14
                if menu_start_y <= y < menu_start_y + len(self.menu_items):
                    idx = y - menu_start_y
                    self.result = str(self.menu_items[idx][0]).lower()
                    app.exit()
        
        text_control.mouse_handler = mouse_handler
        
        layout = Layout(HSplit([Window(content=text_control, align=WindowAlign.LEFT)]))
        
        app = Application(
            layout=layout,
            key_bindings=self.kb,
            mouse_support=True,
            full_screen=True,
            style=STYLE
        )
        
        app.run()
        # Clean cleanup - clear screen for the next tool's print statements
        os.system('cls' if os.name == 'nt' else 'clear')
        return self.result

# Singleton instance
tui = OpenDAV_TUI()

def get_tui_choice(menu_items):
    return tui.run_menu(menu_items)
