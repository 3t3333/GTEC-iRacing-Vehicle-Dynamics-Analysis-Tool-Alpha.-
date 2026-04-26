import sys
import os
import re
import numpy as np
from prompt_toolkit.application import Application
from prompt_toolkit.layout.containers import Window, HSplit, WindowAlign, VSplit
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
import ui.splash as splash

STYLE = Style.from_dict({
    'border': '#2D8AE2',
    'title': '#2D8AE2 bold',
    'handle': '#FF1493 bold', # Pink for handles
    'selected_bar': '#32CD32', # Lime Green for the selected zone
    'unselected_bar': '#555555', # Grey
    'sector_mark': '#FFD700', # Gold
    'action': '#00FFFF bold',
    'bg': '#1a1a1a',
})

class SectorSliderTUI:
    def __init__(self):
        self.kb = KeyBindings()
        self.bar_width = 80
        self.max_dist = 0
        self.sectors_pct = []
        
        self.start_pct = 0.0
        self.end_pct = 1.0
        
        self.active_handle = 'start' # 'start' or 'end'
        self.result = None

        @self.kb.add('left')
        def _(event):
            self._move_handle(-0.01)

        @self.kb.add('right')
        def _(event):
            self._move_handle(0.01)
            
        @self.kb.add('up')
        def _(event):
            self._move_handle(0.05)

        @self.kb.add('down')
        def _(event):
            self._move_handle(-0.05)

        @self.kb.add('tab')
        def _(event):
            self.active_handle = 'end' if self.active_handle == 'start' else 'start'
            
        @self.kb.add('a')
        def _(event):
            self.start_pct = 0.0
            self.end_pct = 1.0

        @self.kb.add('enter')
        def _(event):
            self.result = (self.start_pct * self.max_dist, self.end_pct * self.max_dist)
            event.app.exit()

        @self.kb.add('q')
        @self.kb.add('escape')
        def _(event):
            self.result = None
            event.app.exit()

    def _move_handle(self, delta):
        if self.active_handle == 'start':
            self.start_pct = max(0.0, min(self.start_pct + delta, self.end_pct - 0.01))
        else:
            self.end_pct = max(self.start_pct + 0.01, min(self.end_pct + delta, 1.0))

    def _get_render_text(self):
        result = []
        
        # Header Box
        top_border = "┌" + "─" * (splash.BOX_WIDTH - 2) + "┐\n"
        bot_border = "└" + "─" * (splash.BOX_WIDTH - 2) + "┘\n"
        
        result.append(("class:border", " " * splash.PADDING + top_border))
        
        title = "[ GRAPHICAL SECTOR ISOLATION ]"
        t_len = len(title)
        pad_t = splash.BOX_WIDTH - 2 - t_len
        result.append(("class:border", " " * splash.PADDING + "│"))
        result.append(("class:title", " " + title + " " * (pad_t - 1)))
        result.append(("class:border", "│\n"))
        result.append(("class:border", " " * splash.PADDING + bot_border))

        # We will build the slider manually
        inner_w = splash.BOX_WIDTH - 2
        result.append(("class:border", " " * splash.PADDING + "┌" + "─" * inner_w + "┐\n"))
        
        # Calculate positions
        bar_start_idx = (inner_w - self.bar_width) // 2
        
        # 1. Sector Top Ticks
        top_ticks = [" "] * self.bar_width
        for i, pct in enumerate(self.sectors_pct):
            idx = int(pct * (self.bar_width - 1))
            if 0 <= idx < self.bar_width:
                top_ticks[idx] = "▼"
        
        top_str = "".join(top_ticks)
        result.append(("class:border", " " * splash.PADDING + "│"))
        result.append(("", " " * bar_start_idx))
        result.append(("class:sector_mark", top_str))
        result.append(("", " " * (inner_w - bar_start_idx - self.bar_width)))
        result.append(("class:border", "│\n"))
        
        # 1b. Sector Labels
        label_ticks = [" "] * self.bar_width
        for i, pct in enumerate(self.sectors_pct):
            idx = int(pct * (self.bar_width - 1))
            label = f"S{i+1}"
            if 0 <= idx < self.bar_width - len(label):
                for j, char in enumerate(label):
                    label_ticks[idx+j] = char
        
        lbl_str = "".join(label_ticks)
        result.append(("class:border", " " * splash.PADDING + "│"))
        result.append(("", " " * bar_start_idx))
        result.append(("class:sector_mark", lbl_str))
        result.append(("", " " * (inner_w - bar_start_idx - self.bar_width)))
        result.append(("class:border", "│\n"))

        # 2. The Main Bar
        start_idx = int(self.start_pct * (self.bar_width - 1))
        end_idx = int(self.end_pct * (self.bar_width - 1))
        
        bar_chars = []
        for i in range(self.bar_width):
            if i == start_idx and self.active_handle == 'start':
                bar_chars.append(("class:handle", "█"))
            elif i == end_idx and self.active_handle == 'end':
                bar_chars.append(("class:handle", "█"))
            elif i == start_idx or i == end_idx:
                bar_chars.append(("class:handle", "│"))
            elif start_idx < i < end_idx:
                bar_chars.append(("class:selected_bar", "█"))
            else:
                bar_chars.append(("class:unselected_bar", "▒"))
                
        result.append(("class:border", " " * splash.PADDING + "│"))
        result.append(("", " " * bar_start_idx))
        for c in bar_chars: result.append(c)
        result.append(("", " " * (inner_w - bar_start_idx - self.bar_width)))
        result.append(("class:border", "│\n"))
        
        # 3. Bottom 25% Ticks
        bot_ticks = [" "] * self.bar_width
        for pct in [0.25, 0.50, 0.75]:
            idx = int(pct * (self.bar_width - 1))
            if 0 <= idx < self.bar_width:
                bot_ticks[idx] = "▲"
                
        bot_str = "".join(bot_ticks)
        result.append(("class:border", " " * splash.PADDING + "│"))
        result.append(("", " " * bar_start_idx))
        result.append(("", bot_str))
        result.append(("", " " * (inner_w - bar_start_idx - self.bar_width)))
        result.append(("class:border", "│\n"))
        
        # Status Text
        start_val = self.start_pct * self.max_dist
        end_val = self.end_pct * self.max_dist
        
        status_str = f" Start: {start_val:6.0f}m {'(ACTIVE)' if self.active_handle == 'start' else '        '} | End: {end_val:6.0f}m {'(ACTIVE)' if self.active_handle == 'end' else '        '}"
        pad_stat = inner_w - len(status_str)
        result.append(("class:border", " " * splash.PADDING + "│" + " " * inner_w + "│\n"))
        result.append(("class:border", " " * splash.PADDING + "│"))
        result.append(("class:action", status_str + " " * pad_stat))
        result.append(("class:border", "│\n"))
        
        result.append(("class:border", " " * splash.PADDING + "└" + "─" * inner_w + "┘\n"))
        
        footer = " [TAB] Switch Handle | [ARROWS] Move | [A] Full Lap | [ENTER] Confirm | [Q] Cancel "
        pad_f = (splash.BOX_WIDTH - len(footer)) // 2
        result.append(("class:title", " " * (splash.PADDING + pad_f) + footer + "\n"))

        return result

    def run(self, max_dist, sectors_pct):
        self.max_dist = max_dist
        self.sectors_pct = sectors_pct
        self.start_pct = 0.0
        self.end_pct = 1.0
        self.result = None
        
        text_control = FormattedTextControl(
            self._get_render_text,
            key_bindings=self.kb,
            focusable=True,
            show_cursor=False
        )
        
        layout = Layout(HSplit([Window(content=text_control, align=WindowAlign.LEFT)]))
        app = Application(layout=layout, key_bindings=self.kb, full_screen=True, style=STYLE)
        app.run()
        
        os.system('cls' if os.name == 'nt' else 'clear')
        return self.result

sector_tui = SectorSliderTUI()
def get_sector_choice(max_dist, sectors_pct):
    return sector_tui.run(max_dist, sectors_pct)
