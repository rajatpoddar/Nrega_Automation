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
        # Add a wrapping frame for padding
        update_wrapper_frame = ctk.CTkFrame(update_tab, fg_color="transparent")
        update_wrapper_frame.pack(expand=True, fill="both", padx=10, pady=10)

        update_frame = ctk.CTkFrame(update_wrapper_frame, fg_color="transparent")
        update_frame.pack(expand=True)
        
        self.current_version_label = ctk.CTkLabel(update_frame, text=f"Current Version: {config.APP_VERSION}")
        self.latest_version_label = ctk.CTkLabel(update_frame, text="Latest Version: Checking...")
        self.update_button = ctk.CTkButton(update_frame, text="Check for Updates", command=self.check_for_updates)
        self.update_progress = ctk.CTkProgressBar(update_frame)
        self.update_progress.set(0)
        
        # FIXED: Added padding between the labels
        self.current_version_label.pack(pady=5, padx=20)
        self.latest_version_label.pack(pady=5, padx=20)
        self.update_button.pack(pady=(20, 10), padx=20, ipady=4, fill='x')
    
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
        self._update_action_panel("Loading", "N/A")

    def _update_action_panel(self, status, key_type):
        for widget in self.action_panel_container.winfo_children():
            widget.destroy()

        # Trial and Renew/Expired panels are unchanged and correct
        if key_type == 'trial':
            panel = ctk.CTkFrame(self.action_panel_container, border_color="#3B82F6", border_width=2)
            panel.grid(row=0, column=0, sticky="nsew")
            panel.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(panel, text="Trial Version Active", font=ctk.CTkFont(size=16, weight="bold"), text_color="#3B82F6").pack(pady=(20,10), padx=20)
            ctk.CTkLabel(panel, text="Upgrade to a full license to unlock all features permanently and remove limitations.", wraplength=300, justify="center").pack(pady=5, padx=20)
            ctk.CTkButton(panel, text="Upgrade to Full License", command=lambda: self.app.show_purchase_window(context='upgrade')).pack(pady=20, ipady=5)
            return

        elif status in ["Expired", "Expires Soon"]:
            panel = ctk.CTkFrame(self.action_panel_container, border_color="#DD6B20", border_width=2)
            panel.grid(row=0, column=0, sticky="nsew")
            panel.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(panel, text="Your License Needs Attention!", font=ctk.CTkFont(size=16, weight="bold"), text_color="#DD6B20").pack(pady=(20,10), padx=20)
            ctk.CTkLabel(panel, text="Renew your subscription to continue using all features without interruption.", wraplength=300, justify="center").pack(pady=5, padx=20)
            ctk.CTkButton(panel, text="Renew Subscription Now", command=lambda: self.app.show_purchase_window(context='renew')).pack(pady=20, ipady=5)
            return
        
        # --- CLEANED UP: Final User Management Panel for Paid Users ---
        panel = ctk.CTkFrame(self.action_panel_container)
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(panel, text="Account Management", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20,10), padx=20)
        
        # --- Activated Devices Section ---
        devices_frame = ctk.CTkFrame(panel, fg_color="transparent")
        devices_frame.pack(expand=True, fill="both", padx=15, pady=(0, 10))
        
        max_devices = self.license_info.get('max_devices', 1)
        activated_machines_str = self.license_info.get('activated_machines', '')
        activated_machines = activated_machines_str.split(',') if activated_machines_str else []
        activated_count = len(activated_machines)

        ctk.CTkLabel(devices_frame, text=f"Activated Devices ({activated_count} of {max_devices} used)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 5))

        # Create a scrollable area for the device list
        scroll_area = ctk.CTkScrollableFrame(devices_frame, fg_color="transparent")
        scroll_area.pack(expand=True, fill="both")

        if not activated_machines:
            ctk.CTkLabel(scroll_area, text="No devices activated yet.", text_color="gray50").pack(pady=10)
        else:
            for machine_id in activated_machines:
                is_current_device = (machine_id == self.app.machine_id)
                device_entry_frame = ctk.CTkFrame(scroll_area, fg_color=("gray85", "gray20"))
                device_entry_frame.pack(fill="x", pady=(0, 5))
                
                label_text = f"  {machine_id}" + (" (This Device)" if is_current_device else "")
                device_label = ctk.CTkLabel(device_entry_frame, text=label_text, anchor="w", font=ctk.CTkFont(family="monospace"))
                device_label.pack(side="left", fill="x", expand=True, padx=10, pady=8)

                deactivate_btn = ctk.CTkButton(
                    device_entry_frame, text="Reset",
                    command=lambda mid=machine_id: self.request_single_device_deactivation(mid),
                    width=140, fg_color="transparent", text_color=("#3B82F6", "#60A5FA"), hover=False,
                )
                deactivate_btn.pack(side="right", padx=(0, 10))

        # --- Bottom Action Buttons ---
        bottom_frame = ctk.CTkFrame(panel, fg_color="transparent")
        bottom_frame.pack(fill='x', padx=15, pady=(5, 15), side='bottom')
        bottom_frame.grid_columnconfigure((0, 1), weight=1)

        manage_url = f"{config.LICENSE_SERVER_URL}/account"
        ctk.CTkButton(bottom_frame, text="Manage on Website", fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE"), command=lambda: webbrowser.open(manage_url)).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkButton(bottom_frame, text="Contact Support", fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE"), command=self.contact_support_email).grid(row=0, column=1, sticky="ew", padx=(5, 0))
        
    def request_single_device_deactivation(self, machine_id_to_deactivate):
        user_name = self.license_info.get('user_name', 'N/A')
        license_key = self.license_info.get('key', 'N/A')
        
        subject = f"Request for Deactivation: Device {machine_id_to_deactivate[:12]}..."
        body = (
            f"Hello Support Team,\n\n"
            f"I would like to request the deactivation of the following device from my license:\n\n"
            f"Machine ID to remove: {machine_id_to_deactivate}\n\n"
            f"--- My License Details ---\n"
            f"Name: {user_name}\n"
            f"License Key: {license_key}\n\n"
            f"Thank you."
        )
        self._open_mailto_url(subject, body)

    def contact_support_email(self):
        user_name = self.license_info.get('user_name', 'N/A')
        license_key = self.license_info.get('key', 'N/A')
        subject = "NREGA Bot Support Request"
        body = (
            f"Hello Support Team,\n\n"
            f"[Please describe your issue here]\n\n"
            f"--- My License Details for Reference ---\n"
            f"Name: {user_name}\n"
            f"License Key: {license_key}\n"
            f"App Version: {config.APP_VERSION}\n"
            f"Machine ID: {self.app.machine_id}\n"
        )
        self._open_mailto_url(subject, body)
        
    def _open_mailto_url(self, subject, body):
        params = {'subject': subject, 'body': body}
        encoded_params = urlencode(params)
        mailto_url = f"mailto:{config.SUPPORT_EMAIL}?{encoded_params}"
        
        try:
            webbrowser.open(mailto_url)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open email client. Please manually email {config.SUPPORT_EMAIL}.\n\nError: {e}")

    def update_subscription_details(self, license_info):
        self.license_info = license_info
        self.welcome_label.configure(text=f"Welcome, {license_info.get('user_name', 'Valued User')}!")
        self.machine_id_label.configure(text=self.app.machine_id)

        expires_at_str = license_info.get('expires_at')
        status, days_remaining, status_color = "Inactive", None, "gray"

        if expires_at_str:
            try:
                expiry_date = datetime.fromisoformat(expires_at_str.split('T')[0]).date()
                delta = expiry_date - datetime.now().date()
                days_remaining = delta.days
                if days_remaining < 0: status, status_color = "Expired", "#E53E3E"
                elif days_remaining <= 15: status, status_color = "Expires Soon", "#DD6B20"
                else: status, status_color = "Active", "#38A169"
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
        
        max_devices = license_info.get('max_devices', 1)
        activated_machines_str = license_info.get('activated_machines', '')
        activated_count = len(activated_machines_str.split(',')) if activated_machines_str else 0
        self.devices_used_label.configure(text=f"{activated_count} of {max_devices} used")

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
