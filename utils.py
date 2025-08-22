# utils.py
import os
import sys
from pathlib import Path
from appdirs import user_data_dir

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
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

def get_user_downloads_path():
    """Get the path to the user's downloads folder."""
    return os.path.join(Path.home(), "Downloads")