# gw2x_config.py
import json
import os

CONFIG_FILE = "gw2x_settings.json"

DEFAULT_CONFIG = {
    # Window
    "allow_resize": False,
    "opacity": 1.0,

    # Hotkeys
    "hk_next": "F9",
    "hk_back": "F10",

    # AutoTP
    "auto_tp_retry": False,
    "auto_tp_retry_count": 1,

    # Future-proof
    # "theme": "dark",
}

class GW2XConfig:
    def __init__(self):
        self.data = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.data.update(json.load(f))
        except Exception as e:
            print(f"[Config] Failed to load: {e}")

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"[Config] Failed to save: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value