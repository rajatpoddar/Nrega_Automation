# tabs/history_manager.py
import json
import os
import threading

class HistoryManager:
    def __init__(self, data_path_func):
        self.history_file = data_path_func('autocomplete_history.json')
        self.history_data = self._load_history()
        self.lock = threading.Lock()

    def _load_history(self):
        """Loads history from the JSON file."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {} # Return empty dict on error
        return {}

    def get_suggestions(self, field_key: str) -> list:
        """Gets a list of suggestions for a given field key."""
        return self.history_data.get(field_key, [])

    def save_entry(self, field_key: str, value: str):
        """Saves a new, unique entry for a field key to the history file."""
        if not value: return # Don't save empty values
        
        with self.lock:
            # Ensure the key exists and the value is not already in the list
            if field_key not in self.history_data:
                self.history_data[field_key] = []
            
            if value not in self.history_data[field_key]:
                self.history_data[field_key].append(value)
                # Keep the list sorted for consistency
                self.history_data[field_key].sort()
                
                try:
                    with open(self.history_file, 'w') as f:
                        json.dump(self.history_data, f, indent=4)
                except IOError as e:
                    print(f"Error saving history: {e}")