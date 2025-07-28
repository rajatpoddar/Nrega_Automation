# tabs/about_tab.py
import tkinter
from tkinter import messagebox
import customtkinter as ctk
import webbrowser
import config
import os
import sys
import json
from PIL import Image
from datetime import datetime
from urllib.parse import urlencode

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class AboutTab(ctk.CTkFrame):
    def __init__(self, parent, app_instance):
        super().__init__(parent, fg_color="transparent")
        self.app = app_instance
        self.license_info = {}

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self._create_left_frame()
        self._create_right_frame()

        self.app.after(100, self.app._update_about_tab_info)

    def _create_left_frame(self):
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(0, weight=1)

        self.tab_view = ctk.CTkTabview(left_frame)
        self.tab_view.grid(row=0, column=0, sticky="nsew")
        self.tab_view.add("Subscription")
        self.tab_view.add("Changelog")
        self.tab_view.add("Updates")

        # --- Subscription Tab ---
        sub_tab = self.tab_view.tab("Subscription")
        sub_tab.grid_columnconfigure(0, weight=1)
        
        sub_frame = ctk.CTkFrame(sub_tab, fg_color="transparent")
        sub_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        sub_frame.grid_columnconfigure(1, weight=1)

        self.welcome_label = ctk.CTkLabel(sub_frame, text="Welcome!", font=ctk.CTkFont(size=18, weight="bold"))
        self.welcome_label.grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 10), sticky="w")

        status_bar = ctk.CTkFrame(sub_frame, fg_color="transparent")
        status_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 15))
        self.status_label = ctk.CTkLabel(status_bar, text="INACTIVE", font=ctk.CTkFont(size=12, weight="bold"), fg_color="gray", corner_radius=6, text_color="white")
        self.status_label.pack(side="left", padx=(0, 10), ipady=3, ipadx=8)
        self.days_remaining_label = ctk.CTkLabel(status_bar, text="-- days remaining", text_color="gray50")
        self.days_remaining_label.pack(side="left")

        details_frame = ctk.CTkFrame(sub_frame, fg_color="transparent")
        details_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 20))
        details_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(details_frame, text="Plan Type:", text_color="gray50").grid(row=0, column=0, sticky="w")
        self.plan_type_label = ctk.CTkLabel(details_frame, text="N/A", font=ctk.CTkFont(weight="bold"))
        self.plan_type_label.grid(row=0, column=1, sticky="w", padx=10)

        ctk.CTkLabel(details_frame, text="License Key:", text_color="gray50").grid(row=1, column=0, sticky="w", pady=(5,0))
        key_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        key_frame.grid(row=1, column=1, sticky="ew", padx=10, pady=(5,0))
        self.key_label = ctk.CTkLabel(key_frame, text="N/A", font=ctk.CTkFont(family="monospace"))
        self.key_label.pack(side="left")
        ctk.CTkButton(key_frame, text="Copy", width=50, command=self._copy_key).pack(side="left", padx=(10, 0))

        ctk.CTkLabel(details_frame, text="Expires On:", text_color="gray50").grid(row=2, column=0, sticky="w", pady=(5,0))
        self.expires_on_value_label = ctk.CTkLabel(details_frame, text="N/A", font=ctk.CTkFont(weight="bold"))
        self.expires_on_value_label.grid(row=2, column=1, sticky="w", padx=10, pady=(5,0))
        
        # --- NEW: Device Count ---
        ctk.CTkLabel(details_frame, text="Devices Used:", text_color="gray50").grid(row=3, column=0, sticky="w", pady=(5,0))
        self.devices_used_label = ctk.CTkLabel(details_frame, text="N/A", font=ctk.CTkFont(weight="bold"))
        self.devices_used_label.grid(row=3, column=1, sticky="w", padx=10, pady=(5,0))

        ctk.CTkLabel(details_frame, text="Machine ID:", text_color="gray50").grid(row=4, column=0, sticky="w", pady=(5,0))
        machine_id_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        machine_id_frame.grid(row=4, column=1, sticky="ew", padx=10, pady=(5,0))
        self.machine_id_label = ctk.CTkLabel(machine_id_frame, text="N/A", font=ctk.CTkFont(family="monospace"))
        self.machine_id_label.pack(side="left")
        ctk.CTkButton(machine_id_frame, text="Copy", width=50, command=self._copy_machine_id).pack(side="left", padx=(10,0))

        # --- Changelog Tab ---
        changelog_tab = self.tab_view.tab("Changelog")
        changelog_tab.grid_rowconfigure(0, weight=1); changelog_tab.grid_columnconfigure(0, weight=1)
        self.changelog_text = ctk.CTkTextbox(changelog_tab, wrap=tkinter.WORD, state="disabled")
        self.changelog_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self._load_changelog_from_file()

        # --- Updates Tab ---
        update_tab = self.tab_view.tab("Updates")
        update_tab.grid_columnconfigure(0, weight=1)
        update_frame = ctk.CTkFrame(update_tab, fg_color="transparent")
        update_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        update_frame.grid_columnconfigure(1, weight=1)
        
        self.current_version_label = ctk.CTkLabel(update_frame, text=f"Current Version: {config.APP_VERSION}")
        self.latest_version_label = ctk.CTkLabel(update_frame, text="Latest Version: Checking...")
        self.update_button = ctk.CTkButton(update_frame, text="Check for Updates", command=self.check_for_updates)
        self.update_progress = ctk.CTkProgressBar(update_frame)
        self.update_progress.set(0)
        
        self.current_version_label.grid(row=0, column=0, sticky="w", pady=5)
        self.latest_version_label.grid(row=0, column=1, sticky="w", pady=5)
        self.update_button.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10,0))
    
    def _load_changelog_from_file(self):
        changelog_content = {}
        try:
            changelog_path = resource_path("changelog.json")
            with open(changelog_path, 'r', encoding='utf-8') as f:
                changelog_content = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            changelog_content = {"Error": [f"Could not load changelog.json: {e}"]}
        
        self.changelog_text.configure(state="normal")
        self.changelog_text.delete("1.0", tkinter.END)
        self.changelog_text.tag_config("bold", underline=True)
        
        for version, changes in changelog_content.items():
            self.changelog_text.insert(tkinter.END, f"Version {version}\n", "bold")
            for change in changes:
                self.changelog_text.insert(tkinter.END, f"  • {change}\n")
            self.changelog_text.insert(tkinter.END, "\n")
        
        self.changelog_text.configure(state="disabled")

    def _create_right_frame(self):
        self.action_panel_container = ctk.CTkFrame(self)
        self.action_panel_container.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.action_panel_container.grid_columnconfigure(0, weight=1)
        self.action_panel_container.grid_rowconfigure(0, weight=1)
        # Initially populate with a placeholder
        self._update_action_panel("Loading", "N/A")

    def _update_action_panel(self, status, key_type):
        for widget in self.action_panel_container.winfo_children():
            widget.destroy()

        if key_type == 'trial':
            # ACTION PANEL FOR TRIAL USERS
            panel = ctk.CTkFrame(self.action_panel_container, border_color="#3B82F6", border_width=2)
            panel.grid(row=0, column=0, sticky="nsew")
            panel.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(panel, text="Trial Version Active", font=ctk.CTkFont(size=16, weight="bold"), text_color="#3B82F6").pack(pady=(20,10), padx=20)
            ctk.CTkLabel(panel, text="Upgrade to a full license to unlock all features permanently and remove limitations.", wraplength=300, justify="center").pack(pady=5, padx=20)
            ctk.CTkButton(panel, text="Upgrade to Full License", command=lambda: self.app.show_purchase_window(context='upgrade')).pack(pady=20, ipady=5)
        
        elif status in ["Expired", "Expires Soon"]:
            # ACTION PANEL FOR EXPIRING/EXPIRED USERS
            panel = ctk.CTkFrame(self.action_panel_container, border_color="#DD6B20", border_width=2)
            panel.grid(row=0, column=0, sticky="nsew")
            panel.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(panel, text="Your License Needs Attention!", font=ctk.CTkFont(size=16, weight="bold"), text_color="#DD6B20").pack(pady=(20,10), padx=20)
            ctk.CTkLabel(panel, text="Renew your subscription to continue using all features without interruption.", wraplength=300, justify="center").pack(pady=5, padx=20)
            ctk.CTkButton(panel, text="Renew Subscription Now", command=lambda: self.app.show_purchase_window(context='renew')).pack(pady=20, ipady=5)
        
        else:
            # --- NEW: USER MANAGEMENT PANEL FOR PAID USERS ---
            panel = ctk.CTkFrame(self.action_panel_container)
            panel.grid(row=0, column=0, sticky="nsew")
            panel.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(panel, text="User Management", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20,10), padx=20)
            
            # Display list of activated devices (view only)
            scrollable_frame = ctk.CTkScrollableFrame(panel, label_text="Activated Devices")
            scrollable_frame.pack(expand=True, fill="both", padx=15, pady=5)
            
            activated_machines_str = self.license_info.get('activated_machines', '')
            activated_machines = activated_machines_str.split(',') if activated_machines_str else []

            if not activated_machines:
                scrollable_frame.configure(label_text="No devices activated yet.")
            else:
                for machine_id in activated_machines:
                    is_current_device = (machine_id == self.app.machine_id)
                    label_text = f"  {machine_id}" + (" (This Device)" if is_current_device else "")
                    
                    device_label = ctk.CTkLabel(scrollable_frame, text=label_text, anchor="w", font=ctk.CTkFont(family="monospace"))
                    device_label.pack(side="left", expand=True, fill="x", padx=10, pady=5)

            # Button to request deactivation via email
            ctk.CTkButton(panel, text="Request Device Deactivation", command=self.request_deactivation_email).pack(pady=(10,5), padx=15, fill='x')

            # Link to website for general management
            ctk.CTkLabel(panel, text="Visit our website to manage your subscription or view payment history.", wraplength=300, justify="center").pack(pady=(15, 5), padx=20)
            ctk.CTkButton(panel, text="Go to Website", command=lambda: webbrowser.open(config.MAIN_WEBSITE_URL)).pack(pady=(0, 20))

    def request_deactivation_email(self):
        user_name = self.license_info.get('user_name', 'N/A')
        license_key = self.license_info.get('key', 'N/A')
        
        subject = "Request for Device Deactivation"
        body = (
            f"Hello Support Team,\n\n"
            f"I would like to request the deactivation of a device from my license.\n\n"
            f"Please specify which Machine ID you would like to remove from the list below:\n\n"
            f"My Activated Devices:\n"
            f"{self.license_info.get('activated_machines', 'N/A').replace(',', '\n')}\n\n"
            f"--- My License Details ---\n"
            f"Name: {user_name}\n"
            f"License Key: {license_key}\n\n"
            f"Thank you."
        )
        
        # URL Encode the subject and body
        encoded_subject = urlencode({'subject': subject})[8:]
        encoded_body = urlencode({'body': body})[5:]
        
        mailto_url = f"mailto:{config.SUPPORT_EMAIL}?subject={encoded_subject}&body={encoded_body}"
        
        try:
            webbrowser.open(mailto_url)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open email client. Please manually email {config.SUPPORT_EMAIL}.\n\nError: {e}")

    def update_subscription_details(self, license_info):
        self.license_info = license_info # Store for internal use
        self.welcome_label.configure(text=f"Welcome, {license_info.get('user_name', 'Valued User')}!")
        self.machine_id_label.configure(text=self.app.machine_id)

        expires_at_str = license_info.get('expires_at')
        status, days_remaining, status_color = "Inactive", None, "gray"

        if expires_at_str:
            try:
                expiry_date = datetime.fromisoformat(expires_at_str.split('T')[0]).date()
                delta = expiry_date - datetime.now().date()
                days_remaining = delta.days
                if days_remaining < 0:
                    status, status_color = "Expired", "#E53E3E" # Red
                elif days_remaining <= 15:
                    status, status_color = "Expires Soon", "#DD6B20" # Orange
                else:
                    status, status_color = "Active", "#38A169" # Green
            except (ValueError, TypeError): pass

        self.status_label.configure(text=status.upper(), fg_color=status_color)
        if days_remaining is not None:
            if days_remaining < 0: self.days_remaining_label.configure(text=f"Expired {-days_remaining} day{'s' if days_remaining != -1 else ''} ago")
            else: self.days_remaining_label.configure(text=f"{days_remaining} day{'s' if days_remaining != 1 else ''} remaining")
        else: self.days_remaining_label.configure(text="--")
        
        key_type = license_info.get('key_type', 'N/A')
        self.plan_type_label.configure(text=f"{str(key_type).capitalize()} Plan")

        self.key_label.configure(text=license_info.get('key', 'N/A'))
        self.expires_on_value_label.configure(text=expires_at_str.split('T')[0] if expires_at_str else 'N/A')
        
        # --- Update Device Count ---
        max_devices = license_info.get('max_devices', 1)
        activated_machines_str = license_info.get('activated_machines', '')
        activated_count = len(activated_machines_str.split(',')) if activated_machines_str else 0
        self.devices_used_label.configure(text=f"{activated_count} of {max_devices} used")

        # --- Update the action panel based on new info ---
        self._update_action_panel(status, key_type)

    def _copy_key(self):
        key_to_copy = self.key_label.cget("text")
        if key_to_copy and key_to_copy != "N/A":
            self.app.clipboard_clear()
            self.app.clipboard_append(key_to_copy)
            messagebox.showinfo("Copied", "License key copied to clipboard.")
            
    def _copy_machine_id(self):
        self.app.clipboard_clear()
        self.app.clipboard_append(self.app.machine_id)
        messagebox.showinfo("Copied", "Machine ID copied to clipboard.")

    def check_for_updates(self):
        self.update_button.configure(state="disabled", text="Checking...")
        self.app.check_for_updates_background()

    def download_and_install_update(self, url, version):
        self.app.download_and_install_update(url, version)