import os
import json

CONFIG_FILE = 'opendav_config.json'

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

_config_cache = load_config()
GUI_MODE = _config_cache.get('gui_mode', 1) # 1=Legacy, 2=Plotly, 3=CustomTkinter
DATA_MODE = _config_cache.get('data_mode', 1) # 1=Auto, 2=Strict MoTeC (.ld), 3=Strict iRacing (.ibt)

def get_gui_mode():
    global GUI_MODE
    return GUI_MODE

def set_gui_mode(mode):
    global GUI_MODE
    GUI_MODE = mode
    
def get_data_mode():
    global DATA_MODE
    return DATA_MODE

def set_data_mode(mode):
    global DATA_MODE
    DATA_MODE = mode
