# tabs/settings_tab.py
import tkinter
from tkinter import messagebox
import customtkinter as ctk
import json

class SettingsTab(ctk.CTkFrame):
    def __init__(self, parent, app_instance):
        super().__init__(parent, fg_color="transparent")
        self.app = app_instance
        self.settings_vars = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # --- Top Frame with Save Button ---
        top_frame = ctk.CTkFrame(self)
        top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top_frame, text="Application Settings", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        ctk.CTkLabel(top_frame, text="Changes made here will override the application defaults. The new settings are used the next time you run an automation.", wraplength=800, justify="left").grid(row=1, column=0, padx=15, pady=(0, 10), sticky="w")
        
        self.save_button = ctk.CTkButton(top_frame, text="Save Settings", command=self.save_settings)
        self.save_button.grid(row=0, column=1, rowspan=2, padx=15, pady=15, sticky="e")
        
        # --- Scrollable Frame for Settings ---
        scrollable_frame = ctk.CTkScrollableFrame(self, label_text="Editable Config Values")
        scrollable_frame.grid(row=1, column=0, sticky="nsew")
        scrollable_frame.grid_columnconfigure(1, weight=1)

        self.populate_settings_ui(scrollable_frame)

    def populate_settings_ui(self, parent):
        """Dynamically creates UI widgets for each setting."""
        row_counter = 0
        # Iterate through a sorted list of keys for consistent order
        for key in sorted(self.app.settings.keys()):
            value = self.app.settings[key]
            if isinstance(value, dict):
                # Create a frame for each dictionary of settings
                group_frame = ctk.CTkFrame(parent)
                group_frame.grid(row=row_counter, column=0, columnspan=2, sticky="ew", padx=5, pady=(10, 5))
                group_frame.grid_columnconfigure(1, weight=1)
                ctk.CTkLabel(group_frame, text=key, font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=5)
                row_counter += 1
                
                sub_row_counter = 1
                # Iterate through sorted sub-keys
                for sub_key, sub_value in sorted(value.items()):
                    if isinstance(sub_value, dict): # Handle nested dicts (like in IF_EDIT)
                        for inner_key, inner_value in sorted(sub_value.items()):
                            self._create_entry(group_frame, f"{sub_key} -> {inner_key}", f"{key}.{sub_key}.{inner_key}", inner_value, sub_row_counter)
                            sub_row_counter += 1
                    else:
                        self._create_entry(group_frame, sub_key, f"{key}.{sub_key}", sub_value, sub_row_counter)
                        sub_row_counter += 1
            else:
                self._create_entry(parent, key, key, value, row_counter)
                row_counter += 1

    def _create_entry(self, parent, label_text, key_path, value, row):
        """Helper to create a label and entry widget for a setting."""
        label = ctk.CTkLabel(parent, text=label_text, wraplength=250)
        label.grid(row=row, column=0, sticky="w", padx=10, pady=5)
        
        var = ctk.StringVar(value=str(value))
        entry = ctk.CTkEntry(parent, textvariable=var)
        entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        
        self.settings_vars[key_path] = var

    def save_settings(self):
        """Saves the current UI values to settings.json."""
        new_settings = {}
        for key_path, var in self.settings_vars.items():
            keys = key_path.split('.')
            current_level = new_settings
            for i, key in enumerate(keys):
                if i == len(keys) - 1:
                    current_level[key] = var.get()
                else:
                    if key not in current_level:
                        current_level[key] = {}
                    current_level = current_level[key]
        
        try:
            settings_path = self.app.get_data_path('settings.json')
            with open(settings_path, 'w') as f:
                json.dump(new_settings, f, indent=4)
            
            # Important: Tell the main app to reload the settings
            self.app.load_settings()
            messagebox.showinfo("Success", "Settings have been saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings.\n\n{e}")