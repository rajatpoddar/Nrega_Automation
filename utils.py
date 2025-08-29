# utils.py
import os
import sys
import json  # <-- Add this import
from pathlib import Path
from appdirs import user_data_dir

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_data_path(filename):
    """Get the path to the application's data directory."""
    app_name = "NREGABot"
    app_author = "PoddarSolutions"
    data_dir = user_data_dir(app_name, app_author)
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, filename)

# --- ADD THESE TWO NEW FUNCTIONS ---
def get_config():
    """Reads the config file from the user's app data directory."""
    config_path = get_data_path('config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Return an empty dictionary if the file doesn't exist or is corrupted
        return {}

def save_config(config_data):
    """Saves the config data to the user's app data directory."""
    config_path = get_data_path('config.json')
    with open(config_path, 'w') as f:
        json.dump(config_data, f, indent=4)
# ------------------------------------

def get_user_downloads_path():
    """Get the path to the user's downloads folder."""
    return os.path.join(Path.home(), "Downloads")