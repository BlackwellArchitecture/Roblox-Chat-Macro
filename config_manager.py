"""
config_manager.py - Persistent Configuration Manager for Roblox Chat Macro
Stores and manages user preferences, message sequences, and intervals.
"""

import json
import os
from typing import Dict, Any

CONFIG_FILE = "macro_config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "hotkey": "F8",
    "chat_key": "/",
    "always_on_top": True,
    "master_interval_enabled": True,
    "master_interval_ms": 1000,
    "send_method": "clipboard",  # "clipboard" or "type"
    "focus_delay_ms": 70,
    "loop_mode": "once",         # "once", "repeat", "continuous"
    "repeat_count": 3,
    "messages": [
      {
        "text": "GG well played!",
        "interval_ms": 1000
      },
      {
        "text": "Nice teamwork everyone!",
        "interval_ms": 1200
      }
    ]
}


def get_config_path() -> str:
    """Returns absolute path to configuration file in working directory."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILE)


def load_config() -> Dict[str, Any]:
    """Loads configuration from JSON file or returns defaults if not found or invalid."""
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = dict(DEFAULT_CONFIG)
                config.update(data)
                # Ensure messages list exists and is populated
                if "messages" not in config or not isinstance(config["messages"], list) or len(config["messages"]) == 0:
                    config["messages"] = list(DEFAULT_CONFIG["messages"])
                return config
        except Exception as e:
            print(f"[ConfigManager] Error reading config: {e}. Using defaults.")
    return dict(DEFAULT_CONFIG)


def save_config(config: Dict[str, Any]) -> bool:
    """Saves current configuration to JSON file."""
    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[ConfigManager] Error saving config: {e}")
        return False
