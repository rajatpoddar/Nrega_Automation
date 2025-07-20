# tabs/about_tab.py (Final Centralized Version)
import tkinter
from tkinter import messagebox
import customtkinter as ctk
import webbrowser
import config
import os
import sys
from PIL import Image
import requests
import threading
from packaging.version import parse as parse_version
import subprocess

# This dictionary will be accessible by the main app
widgets = {}

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def create_tab(parent_frame, app_instance):
    parent_frame.grid_columnconfigure(0, weight=3)
    parent_frame.grid_columnconfigure(1, weight=2)
    parent_frame.grid_rowconfigure(0, weight=1)

    # --- LEFT FRAME ---
    left_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
    left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    left_frame.grid_columnconfigure(0, weight=1)
    left_frame.grid_rowconfigure(2, weight=1)

    # 1. Update Information Frame
    update_frame = ctk.CTkFrame(left_frame)
    update_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
    update_frame.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(update_frame, text="Application Updates", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=15, pady=(15,5), sticky="w")
    
    # Store widgets for external access from main_app
    widgets['current_version_label'] = ctk.CTkLabel(update_frame, text=f"Current Version: {config.APP_VERSION}")
    widgets['latest_version_label'] = ctk.CTkLabel(update_frame, text="Latest Version: Checking...")
    widgets['update_button'] = ctk.CTkButton(update_frame, text="Check for Updates", command=lambda: check_for_updates(app_instance))
    widgets['update_progress'] = ctk.CTkProgressBar(update_frame)
    widgets['update_progress'].set(0)
    
    widgets['current_version_label'].grid(row=1, column=0, sticky="w", padx=15, pady=5)
    widgets['latest_version_label'].grid(row=1, column=1, sticky="w", padx=15, pady=5)
    widgets['update_button'].grid(row=2, column=0, columnspan=2, sticky="ew", padx=15, pady=(5,15))
    
    # Immediately update the UI with the status from the main app
    app_instance.after(100, app_instance._update_about_tab_info)

    # 2. License Information
    license_frame = ctk.CTkFrame(left_frame)
    license_frame.grid(row=1, column=0, sticky="ew")
    license_frame.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(license_frame, text="License Information", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=15, pady=(15,5), sticky="w")
    
    ctk.CTkLabel(license_frame, text="Status:").grid(row=1, column=0, sticky="w", padx=15, pady=5)
    widgets['status_label'] = ctk.CTkLabel(license_frame, text="Active", text_color="#2E8B57") # Default to Active
    widgets['status_label'].grid(row=1, column=1, sticky="w", padx=15, pady=5)
    
    ctk.CTkLabel(license_frame, text="License Key:").grid(row=2, column=0, sticky="w", padx=15, pady=5)
    widgets['license_key_label'] = ctk.CTkLabel(license_frame, text="N/A", font=ctk.CTkFont(weight="bold"))
    widgets['license_key_label'].grid(row=2, column=1, sticky="w", padx=15, pady=5)
    
    ctk.CTkLabel(license_frame, text="Expires On:").grid(row=3, column=0, sticky="w", padx=15, pady=5)
    widgets['expires_on_label'] = ctk.CTkLabel(license_frame, text="N/A")
    widgets['expires_on_label'].grid(row=3, column=1, sticky="w", padx=15, pady=5)
    
    ctk.CTkLabel(license_frame, text="Machine ID:").grid(row=4, column=0, sticky="w", padx=15, pady=(5,15))
    machine_id_frame = ctk.CTkFrame(license_frame, fg_color="transparent")
    machine_id_frame.grid(row=4, column=1, sticky="ew", padx=15, pady=(5,15))
    machine_id_frame.grid_columnconfigure(0, weight=1)
    
    id_label = ctk.CTkLabel(machine_id_frame, text=app_instance.machine_id, anchor="w")
    id_label.grid(row=0, column=0, sticky="ew")
    
    def copy_id():
        app_instance.clipboard_clear()
        app_instance.clipboard_append(app_instance.machine_id)
        copy_button.configure(text="Copied!")
        app_instance.after(2000, lambda: copy_button.configure(text="Copy"))

    copy_button = ctk.CTkButton(machine_id_frame, text="Copy", width=60, command=copy_id)
    copy_button.grid(row=0, column=1, padx=(10,0))
    
    # 3. Changelog
    changelog_frame = ctk.CTkFrame(left_frame)
    changelog_frame.grid(row=2, column=0, sticky="nsew", pady=(15, 0))
    changelog_frame.grid_columnconfigure(0, weight=1)
    changelog_frame.grid_rowconfigure(1, weight=1)
    
    ctk.CTkLabel(changelog_frame, text="Changelog", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=15, pady=(15,5), sticky="w")
    changelog_text = ctk.CTkTextbox(changelog_frame, wrap=tkinter.WORD, state="disabled")
    changelog_text.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0,15))
    
    changelog_content = {
         "2.4.1": [
            "Implemented a new, professional two-tone color theme for light mode.",
            "Introduced a centralized `theme.json` file for easy UI color customization.",
            "Fixed numerous theme inconsistencies, including button visibility and content backgrounds.",
            "Corrected asymmetrical layout in the header for a balanced and polished look.",
            "Added the user's Machine ID to the 'About' page with a 'Copy' button for easier support.",
            "Fixed the automatic update checker to display the correct status on the 'About' page at startup.",
            "Updated the pricing display on the 'About' page to show a promotional offer style."
        ],
        "2.4.0": ["Complete UI Overhaul to CustomTkinter.", "Modern, vertical IDE-style navigation.", "In-App Updates: Check, download, and install directly."],
        "2.3.1": ["Muster Roll Gen: Fixed crash with user-provided work keys.", "FTO Generation: Improved error handling.", "eMB Entry: Added optional 'Panchayat' field.", "MSR Processor: Added 'Export to PDF' feature."],
    }
    changelog_text.configure(state="normal")
    changelog_text.delete("1.0", tkinter.END)
    changelog_text.tag_config("bold", underline=True)
    for version, changes in changelog_content.items():
        changelog_text.insert(tkinter.END, f"Version {version}\n", "bold")
        for change in changes:
            changelog_text.insert(tkinter.END, f"  • {change}\n")
        changelog_text.insert(tkinter.END, "\n")
    changelog_text.configure(state="disabled")

    # --- RIGHT FRAME ---
    qr_frame = ctk.CTkFrame(parent_frame)
    qr_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
    qr_frame.grid_columnconfigure(0, weight=1)
    
    ctk.CTkLabel(qr_frame, text="Subscription Payment", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5))
    donation_note = "To support maintenance and future updates, please consider a small donation. You'll receive a license key in return."
    note_label = ctk.CTkLabel(qr_frame, text=donation_note, wraplength=350, justify="center", text_color="gray50")
    note_label.pack(pady=(5, 15), padx=20)

    try:
        qr_image = ctk.CTkImage(Image.open(resource_path("payment_qr.png")), size=(250, 350))
        qr_label = ctk.CTkLabel(qr_frame, image=qr_image, text="", anchor="center")
        qr_label.pack(pady=5, padx=5)
    except Exception as e:
        error_label = ctk.CTkLabel(qr_frame, text="Could not load payment QR code.", justify="center")
        error_label.pack(expand=True, padx=10, pady=10)
        print(f"Error loading QR code image: {e}")

    pricing_frame = ctk.CTkFrame(qr_frame, fg_color="transparent")
    pricing_frame.pack(pady=(15, 10))
    strike_font = ctk.CTkFont(size=12, overstrike=True)
    bold_font = ctk.CTkFont(size=14, weight="bold")
    ctk.CTkLabel(pricing_frame, text="₹199", font=strike_font, text_color="gray50").pack(side="left", padx=(0, 2))
    ctk.CTkLabel(pricing_frame, text="₹99/Month", font=bold_font).pack(side="left", padx=(0, 10))
    ctk.CTkLabel(pricing_frame, text="₹1999", font=strike_font, text_color="gray50").pack(side="left", padx=(0, 2))
    ctk.CTkLabel(pricing_frame, text="₹999/Year", font=bold_font).pack(side="left")

def check_for_updates(app_instance):
    """Triggers the central update check in the main app."""
    widgets['update_button'].configure(state="disabled", text="Checking...")
    app_instance.check_for_updates_background()

def download_and_install_update(app_instance, widgets, url, version):
    if not messagebox.askyesno("Confirm Update", f"You are about to download and install version {version}. The application will close to complete the installation. Do you want to continue?"):
        return

    widgets['update_button'].grid_remove()
    widgets['update_progress'].grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(5,10))
    widgets['update_progress'].set(0)

    def _download():
        try:
            downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
            installer_name = f"NREGA-Dashboard-v{version}-{'Setup.exe' if sys.platform == 'win32' else '.dmg'}"
            installer_path = os.path.join(downloads_path, installer_name)
            
            app_instance.after(0, lambda: widgets['latest_version_label'].configure(text=f"Downloading..."))

            with requests.get(url, stream=True, timeout=300) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                bytes_downloaded = 0
                with open(installer_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        if total_size > 0:
                            progress = (bytes_downloaded / total_size)
                            app_instance.after(0, lambda p=progress: widgets['update_progress'].set(p))
            
            app_instance.after(0, lambda: widgets['latest_version_label'].configure(text="Download complete. Starting installer..."))
            
            if sys.platform == "win32":
                subprocess.Popen([installer_path])
            elif sys.platform == "darwin":
                subprocess.Popen(['open', installer_path])
            
            app_instance.after(2000, app_instance.destroy)

        except Exception as e:
            messagebox.showerror("Update Failed", f"Could not download or run the update.\n\nError: {e}\n\nPlease try downloading manually.")
            app_instance.after(0, lambda: widgets['update_button'].grid())
            app_instance.after(0, lambda: widgets['update_progress'].grid_remove())

    threading.Thread(target=_download, daemon=True).start()
