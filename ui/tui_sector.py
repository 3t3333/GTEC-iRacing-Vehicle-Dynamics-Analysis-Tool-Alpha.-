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
    'handle': '#FF1493 bold',
    'selected_bar': '#32CD32',
    'unselected_bar': '#555555',
    'sector_mark': '#FFD700',
    'action': '#00FFFF bold',
    'bg': '#1a1a1a',
    'spd_1': '#ff0000', # Red <100
    'spd_2': '#ff8c00', # Orange 100-150
    'spd_3': '#ffd700', # Yellow 150-200
    'spd_4': '#00ffff', # Cyan 200-250
    'spd_5': '#0000ff', # Blue >250
})

class SectorSliderTUI:
    def __init__(self):
        self.kb = KeyBindings()
        self.bar_width = 80
        self.max_dist = 0
        self.sectors_pct = []
        self.speed_trace = None
        
        self.start_pct = 0.0
        self.end_pct = 1.0
        
        self.active_handle = 'start'
        self.result = None

        @self.kb.add('left')
        def _(event): self._move_handle(-0.01)

        @self.kb.add('right')
        def _(event): self._move_handle(0.01)
            
        @self.kb.add('up')
        def _(event): self._move_handle(0.05)

        @self.kb.add('down')
        def _(event): self._move_handle(-0.05)

        @self.kb.add('tab')
        def _(event): self.active_handle = 'end' if self.active_handle == 'start' else 'start'
            
        @self.kb.add('a')
        def _(event): self.start_pct, self.end_pct = 0.0, 1.0

        # Auto-Snap Hotkeys 1-9
        for i in range(1, 10):
            @self.kb.add(str(i))
            def _(event, i=i):
                if i <= len(self.sectors_pct) + 1:
                    # Sector i starts at sectors_pct[i-2] and ends at sectors_pct[i-1]
                    s_idx = i - 1
                    starts = [0.0] + self.sectors_pct
                    ends = self.sectors_pct + [1.0]
                    self.start_pct = starts[s_idx]
                    self.end_pct = ends[s_idx]

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

    def _get_speed_class(self, spd):
        if spd < 100: return "class:spd_1"
        if spd < 150: return "class:spd_2"
        if spd < 200: return "class:spd_3"
        if spd < 250: return "class:spd_4"
        return "class:spd_5"

    def _get_render_text(self):
        result = []
        inner_w = splash.BOX_WIDTH - 2
        bar_start_idx = (inner_w - self.bar_width) // 2
        
        # Header Box
        result.append(("class:border", " " * splash.PADDING + "┌" + "─" * inner_w + "┐\n"))
        title = "[ GRAPHICAL SECTOR ISOLATION ]"
        pad_t = inner_w - len(title)
        result.append(("class:border", " " * splash.PADDING + "│"))
        result.append(("class:title", " " + title + " " * (pad_t - 1)))
        result.append(("class:border", "│\n"))
        result.append(("class:border", " " * splash.PADDING + "└" + "─" * inner_w + "┘\n"))

        result.append(("class:border", " " * splash.PADDING + "┌" + "─" * inner_w + "┐\n"))
        
        # 1. Sector Top Ticks & Labels
        top_ticks = [" "] * self.bar_width
        label_ticks = [" "] * self.bar_width
        for i, pct in enumerate(self.sectors_pct):
            idx = int(pct * (self.bar_width - 1))
            if 0 <= idx < self.bar_width: top_ticks[idx] = "▼"
            lbl = f"S{i+1}"
            if 0 <= idx < self.bar_width - len(lbl):
                for j, char in enumerate(lbl): label_ticks[idx+j] = char
        
        result.append(("class:border", " " * splash.PADDING + "│"))
        result.append(("", " " * bar_start_idx))
        result.append(("class:sector_mark", "".join(top_ticks)))
        result.append(("class:border", " " * (inner_w - bar_start_idx - self.bar_width) + "│\n"))
        
        result.append(("class:border", " " * splash.PADDING + "│"))
        result.append(("", " " * bar_start_idx))
        result.append(("class:sector_mark", "".join(label_ticks)))
        result.append(("class:border", " " * (inner_w - bar_start_idx - self.bar_width) + "│\n"))

        # 2. The Main Bar
        start_idx = int(self.start_pct * (self.bar_width - 1))
        end_idx = int(self.end_pct * (self.bar_width - 1))
        
        bar_chars = []
        for i in range(self.bar_width):
            if i == start_idx and self.active_handle == 'start': bar_chars.append(("class:handle", "█"))
            elif i == end_idx and self.active_handle == 'end': bar_chars.append(("class:handle", "█"))
            elif i == start_idx or i == end_idx: bar_chars.append(("class:handle", "│"))
            elif start_idx < i < end_idx: bar_chars.append(("class:selected_bar", "█"))
            else: bar_chars.append(("class:unselected_bar", "▒"))
                
        result.append(("class:border", " " * splash.PADDING + "│"))
        result.append(("", " " * bar_start_idx))
        for c in bar_chars: result.append(c)
        result.append(("class:border", " " * (inner_w - bar_start_idx - self.bar_width) + "│\n"))
        
        # 3. Speed Trace Overlay
        if self.speed_trace is not None and len(self.speed_trace) == self.bar_width:
            spd_chars = []
            for i in range(self.bar_width):
                spd = self.speed_trace[i]
                c_class = self._get_speed_class(spd)
                spd_chars.append((c_class, "▄"))
            
            result.append(("class:border", " " * splash.PADDING + "│"))
            result.append(("", " " * bar_start_idx))
            for c in spd_chars: result.append(c)
            result.append(("class:border", " " * (inner_w - bar_start_idx - self.bar_width) + "│\n"))

        # Status Text
        start_val = self.start_pct * self.max_dist
        end_val = self.end_pct * self.max_dist
        
        status_str = f" Start: {start_val:6.0f}m {'(ACTIVE)' if self.active_handle == 'start' else '        '} | End: {end_val:6.0f}m {'(ACTIVE)' if self.active_handle == 'end' else '        '}"
        pad_stat = inner_w - len(status_str)
        result.append(("class:border", " " * splash.PADDING + "│" + " " * inner_w + "│\n"))
        result.append(("class:border", " " * splash.PADDING + "│"))
        result.append(("class:action", status_str + " " * pad_stat))
        result.append(("class:border", "│\n"))
        
        # Speed Legend
        legend_str = " Speed Legend:  "
        result.append(("class:border", " " * splash.PADDING + "│"))
        result.append(("", " " * 4 + legend_str))
        result.append(("class:spd_1", "▄ <100   "))
        result.append(("class:spd_2", "▄ 100-150   "))
        result.append(("class:spd_3", "▄ 150-200   "))
        result.append(("class:spd_4", "▄ 200-250   "))
        result.append(("class:spd_5", "▄ >250   "))
        pad_leg = inner_w - 4 - len(legend_str) - (7+10+10+10+7)
        result.append(("", " " * pad_leg))
        result.append(("class:border", "│\n"))

        result.append(("class:border", " " * splash.PADDING + "└" + "─" * inner_w + "┘\n"))
        
        footer = " [1-9] Snap to Sector | [TAB] Switch Handle | [ARROWS] Move | [ENTER] Confirm "
        pad_f = (splash.BOX_WIDTH - len(footer)) // 2
        result.append(("class:title", " " * (splash.PADDING + pad_f) + footer + "\n"))

        return result

    def run(self, max_dist, sectors_pct, speed_trace=None):
        self.max_dist = max_dist
        self.sectors_pct = sectors_pct
        self.speed_trace = speed_trace
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
def get_sector_choice(max_dist, sectors_pct, speed_trace=None):
    return sector_tui.run(max_dist, sectors_pct, speed_trace)
