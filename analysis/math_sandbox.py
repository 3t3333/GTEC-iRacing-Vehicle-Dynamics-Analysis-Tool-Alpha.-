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
from core.config import get_gui_mode
from ui.graphing import show_ctk_graph
                show_ctk_graph(fig, "OpenDAV - Math Sandbox")
            else:
                plt.show()
