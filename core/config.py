import os
import json

CONFIG_FILE = 'gtec_config.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(conf):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(conf, f)
    except:
        pass

GUI_MODE = load_config().get('gui_mode', 1) # 1=Legacy, 2=Plotly, 3=CustomTkinter

def get_gui_mode():
    global GUI_MODE
    return GUI_MODE

def set_gui_mode(mode):
    global GUI_MODE
    GUI_MODE = mode
