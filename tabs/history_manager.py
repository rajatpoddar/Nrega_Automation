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
            if field_key not in self.history_data:
                self.history_data[field_key] = []
            
            if value not in self.history_data[field_key]:
                self.history_data[field_key].append(value)
                self.history_data[field_key].sort()
                
                try:
                    with open(self.history_file, 'w') as f:
                        json.dump(self.history_data, f, indent=4)
                except IOError as e:
                    print(f"Error saving history: {e}")

    # --- NEW: Methods for tracking usage ---
    def increment_usage(self, automation_key: str):
        """Increments the usage count for a given automation key."""
        with self.lock:
            if "_usage_stats" not in self.history_data:
                self.history_data["_usage_stats"] = {}
            
            stats = self.history_data["_usage_stats"]
            stats[automation_key] = stats.get(automation_key, 0) + 1
            
            try:
                with open(self.history_file, 'w') as f:
                    json.dump(self.history_data, f, indent=4)
            except IOError as e:
                print(f"Error saving usage stats: {e}")

    def get_most_used_keys(self, count: int = 5) -> list:
        """Gets a sorted list of the most used automation keys."""
        stats = self.history_data.get("_usage_stats", {})
        if not stats:
            return []
        
        # Sort items by count (value) in descending order
        sorted_stats = sorted(stats.items(), key=lambda item: item[1], reverse=True)
        
        # Return only the keys of the top items
        return [item[0] for item in sorted_stats[:count]]