# tabs/about_tab.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import webbrowser
import config
import os
import sys
from PIL import Image, ImageTk
import requests
import threading
from packaging.version import parse as parse_version
import subprocess

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def create_tab(parent_frame, app_instance):
    # --- Main Layout Configuration ---
    parent_frame.columnconfigure(0, weight=3) # Assign more weight to the left frame
    parent_frame.columnconfigure(1, weight=2) # Assign less weight to the right frame
    parent_frame.rowconfigure(0, weight=1)

    # --- LEFT FRAME ---
    left_frame = ttk.Frame(parent_frame)
    left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    left_frame.columnconfigure(0, weight=1)
    left_frame.rowconfigure(3, weight=1) # Allow changelog to expand

    # 1. Update Information Frame
    update_frame = ttk.LabelFrame(left_frame, text="Application Updates")
    update_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
    update_frame.columnconfigure(1, weight=1)

    widgets = {
        'current_version_label': ttk.Label(update_frame, text=f"Current Version: {config.APP_VERSION}"),
        'latest_version_label': ttk.Label(update_frame, text="Latest Version: Checking..."),
        'update_button': ttk.Button(update_frame, text="Check for Updates", command=lambda: check_for_updates(app_instance, widgets)),
        'update_progress': ttk.Progressbar(update_frame, orient='horizontal', mode='determinate')
    }
    
    widgets['current_version_label'].grid(row=0, column=0, sticky="w", padx=10, pady=5)
    widgets['latest_version_label'].grid(row=0, column=1, sticky="w", padx=10, pady=5)
    widgets['update_button'].grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
    
    # 2. License Information
    license_frame = ttk.LabelFrame(left_frame, text="License Information")
    license_frame.grid(row=1, column=0, sticky="ew")
    license_frame.columnconfigure(1, weight=1)
    ttk.Label(license_frame, text="Status:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    ttk.Label(license_frame, text="Active", foreground=config.STYLE_CONFIG["colors"]["light"]["success"]).grid(row=0, column=1, sticky="w", padx=5, pady=5)
    ttk.Label(license_frame, text="License Key:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    key_text = app_instance.license_info.get('key', 'N/A')
    ttk.Label(license_frame, text=key_text, font=config.STYLE_CONFIG["font_bold"]).grid(row=1, column=1, sticky="w", padx=5, pady=5)
    ttk.Label(license_frame, text="Expires On:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    expires_text = app_instance.license_info.get('expires_at', 'N/A').split('T')[0]
    ttk.Label(license_frame, text=expires_text).grid(row=2, column=1, sticky="w", padx=5, pady=5)

    # 3. App Information
    app_info_frame = ttk.LabelFrame(left_frame, text="Application Information")
    app_info_frame.grid(row=2, column=0, sticky="ew", pady=(15, 0))
    app_info_frame.columnconfigure(1, weight=1)
    ttk.Label(app_info_frame, text="Version:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    ttk.Label(app_info_frame, text=config.APP_VERSION).grid(row=0, column=1, sticky="w", padx=5, pady=5)
    ttk.Label(app_info_frame, text="Homepage:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    homepage_link = ttk.Label(app_info_frame, text="https://nrega-dashboard.palojori.in/", style="Link.TLabel", cursor="hand2")
    homepage_link.grid(row=1, column=1, sticky="w", padx=5, pady=5)
    homepage_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://nrega-dashboard.palojori.in/"))
    ttk.Label(app_info_frame, text="Support Email:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    ttk.Label(app_info_frame, text="rajatpoddar@outlook.com").grid(row=2, column=1, sticky="w", padx=5, pady=5)

    # 4. Changelog
    changelog_frame = ttk.LabelFrame(left_frame, text="Changelog")
    changelog_frame.grid(row=3, column=0, sticky="nsew", pady=(15, 0))
    changelog_frame.columnconfigure(0, weight=1)
    changelog_frame.rowconfigure(0, weight=1)
    
    changelog_text = scrolledtext.ScrolledText(changelog_frame, wrap=tk.WORD, state="disabled", relief="flat")
    changelog_text.grid(row=0, column=0, sticky="nsew")
    
    changelog_content = {
        "2.4.0": [
            "Complete UI Overhaul: Modern, vertical IDE-style navigation.",
            "In-App Updates: Check for, download, and install updates directly from the 'About' page.",
            "Startup Crash Fixed: Resolved critical bug preventing UI load."
        ],
        "2.3.1": [
            "Muster Roll Gen: Fixed crash with user-provided work keys.",
            "FTO Generation: Improved error handling for clearer messages.",
            "eMB Entry: Added optional 'Panchayat' field and session memory.",
            "MSR Processor: Added 'Export to PDF' feature.",
        ],
    }
    changelog_text.config(state="normal")
    changelog_text.delete("1.0", tk.END)
    for version, changes in changelog_content.items():
        changelog_text.insert(tk.END, f"Version {version}\n", "bold")
        for change in changes:
            changelog_text.insert(tk.END, f"  • {change}\n")
        changelog_text.insert(tk.END, "\n")
    changelog_text.config(state="disabled")
    changelog_text.tag_config("bold", font=config.STYLE_CONFIG["font_bold"])

    # --- RIGHT FRAME (Reverted to original, simpler layout) ---
    qr_frame = ttk.LabelFrame(parent_frame, text="Subscription Payment")
    qr_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
    qr_frame.columnconfigure(0, weight=1)
    
    donation_note = (
        "To support maintenance and future updates, please consider a small donation. "
        "You'll receive a license key in return."
    )
    # Using wraplength. The container's width will determine the final wrapping.
    note_label = ttk.Label(qr_frame, text=donation_note, wraplength=350, justify="center", style="Secondary.TLabel")
    note_label.pack(pady=(10, 15))

    try:
        qr_image_path = resource_path("payment_qr.png")
        img = Image.open(qr_image_path)
        img_resized = img.resize((250, 250), Image.Resampling.LANCZOS)
        app_instance.qr_photo_image = ImageTk.PhotoImage(img_resized)
        qr_label = ttk.Label(qr_frame, image=app_instance.qr_photo_image, anchor="center")
        qr_label.pack(pady=5, padx=5)
    except Exception as e:
        error_label = ttk.Label(qr_frame, text="Could not load payment QR code.", justify="center")
        error_label.pack(expand=True, padx=10, pady=10)
        print(f"Error loading QR code image: {e}")

    pricing_label = ttk.Label(qr_frame, text="₹99/Month or ₹999/Year License Key", font=config.STYLE_CONFIG["font_bold"], justify="center")
    pricing_label.pack(pady=(15, 10))

    # --- Automatically check for updates on tab creation ---
    check_for_updates(app_instance, widgets)


def check_for_updates(app_instance, widgets):
    """Checks for application updates in a separate thread."""
    widgets['update_button'].config(state="disabled", text="Checking...")
    
    def _check():
        update_url = "https://nrega-dashboard.palojori.in/version.json"
        try:
            response = requests.get(update_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            latest_version = data.get("latest_version")
            
            download_url = None
            if sys.platform == "win32":
                url_key = "download_url_windows"
                download_url = data.get(url_key)
            elif sys.platform == "darwin":
                url_key = "download_url_macos"
                download_url = data.get(url_key)

            # --- ADDED: Detailed Debugging Print ---
            print(f"DEBUG: Update check complete.")
            print(f"DEBUG: Latest version from server: {latest_version}")
            print(f"DEBUG: Current app version: {config.APP_VERSION}")
            print(f"DEBUG: OS Detected: {sys.platform}")
            print(f"DEBUG: URL Key used: {url_key}")
            print(f"DEBUG: Fetched Download URL: {download_url}")
            # --- End of Debugging Print ---

            app_instance.after(0, lambda: widgets['latest_version_label'].config(text=f"Latest Version: {latest_version or 'N/A'}"))

            if latest_version and download_url and parse_version(latest_version) > parse_version(config.APP_VERSION):
                app_instance.after(0, lambda: widgets['update_button'].config(
                    text=f"Download & Install v{latest_version}",
                    state="normal",
                    style="Accent.TButton",
                    command=lambda: download_and_install_update(app_instance, widgets, download_url, latest_version)
                ))
            elif latest_version and parse_version(latest_version) <= parse_version(config.APP_VERSION):
                 app_instance.after(0, lambda: widgets['update_button'].config(text="You are up to date", state="disabled"))
            else:
                reason = "URL key missing in version.json" if not download_url else "Version error"
                app_instance.after(0, lambda: widgets['update_button'].config(text=f"Update unavailable for your OS", state="disabled"))
                print(f"INFO: Update button disabled. Reason: {reason}")


        except requests.RequestException as e:
            app_instance.after(0, lambda: widgets['latest_version_label'].config(text="Latest Version: Error"))
            app_instance.after(0, lambda: widgets['update_button'].config(text="Check for Updates", state="normal"))
            print(f"Update check failed: {e}")
        except json.JSONDecodeError as e:
            app_instance.after(0, lambda: widgets['latest_version_label'].config(text="Latest Version: Invalid JSON"))
            app_instance.after(0, lambda: widgets['update_button'].config(text="Check for Updates", state="normal"))
            print(f"Failed to parse version.json: {e}")


    threading.Thread(target=_check, daemon=True).start()


def download_and_install_update(app_instance, widgets, url, version):
    """Downloads the update and runs the installer."""
    if not messagebox.askyesno("Confirm Update", f"You are about to download and install version {version}. The application will close to complete the installation. Do you want to continue?"):
        return

    widgets['update_button'].grid_remove()
    widgets['update_progress'].grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
    widgets['update_progress']['value'] = 0

    def _download():
        try:
            downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
            
            if sys.platform == "win32":
                installer_name = f"NREGA-Dashboard-v{version}-Setup.exe"
            elif sys.platform == "darwin":
                installer_name = f"NREGA-Dashboard-v{version}.dmg"
            else:
                 installer_name = f"NREGA-Dashboard-v{version}-update"

            installer_path = os.path.join(downloads_path, installer_name)
            
            app_instance.after(0, lambda: widgets['latest_version_label'].config(text=f"Downloading to: {downloads_path}"))

            with requests.get(url, stream=True, timeout=300) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                bytes_downloaded = 0
                with open(installer_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        if total_size > 0:
                            progress = (bytes_downloaded / total_size) * 100
                            app_instance.after(0, lambda p=progress: widgets['update_progress'].config(value=p))
            
            app_instance.after(0, lambda: widgets['latest_version_label'].config(text="Download complete. Starting installer..."))
            
            if sys.platform == "win32":
                subprocess.Popen([installer_path])
            elif sys.platform == "darwin":
                subprocess.Popen(['open', installer_path])
            
            app_instance.after(2000, app_instance.destroy)

        except Exception as e:
            messagebox.showerror("Update Failed", f"Could not download or run the update.\n\nError: {e}\n\nPlease try downloading manually from the website.")
            app_instance.after(0, lambda: widgets['update_button'].grid())
            app_instance.after(0, lambda: widgets['update_progress'].grid_remove())

    threading.Thread(target=_download, daemon=True).start()
