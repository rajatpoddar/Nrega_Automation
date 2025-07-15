# tabs/about_tab.py
import tkinter as tk
from tkinter import ttk, scrolledtext
import webbrowser
import config
import os
import sys
from PIL import Image, ImageTk

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def create_tab(parent_frame, app_instance):
    # --- Main Layout Configuration (60/40 split) ---
    parent_frame.columnconfigure(0, weight=3) # Assign 60% of width
    parent_frame.columnconfigure(1, weight=2) # Assign 40% of width
    parent_frame.rowconfigure(0, weight=1)    # Allow the main row to expand vertically

    # --- LEFT FRAME (Column 0) ---
    left_frame = ttk.Frame(parent_frame)
    left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    left_frame.columnconfigure(0, weight=1)
    # Configure row 2 (changelog) to take up all remaining vertical space
    left_frame.rowconfigure(2, weight=1)

    # 1. License Information (in left_frame)
    license_frame = ttk.LabelFrame(left_frame, text="License Information")
    license_frame.grid(row=0, column=0, sticky="ew")
    license_frame.columnconfigure(1, weight=1)
    ttk.Label(license_frame, text="Status:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    ttk.Label(license_frame, text="Active", foreground=config.STYLE_CONFIG["colors"]["light"]["success"]).grid(row=0, column=1, sticky="w", padx=5, pady=5)
    ttk.Label(license_frame, text="License Key:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    key_text = app_instance.license_info.get('key', 'N/A')
    ttk.Label(license_frame, text=key_text, font=config.STYLE_CONFIG["font_bold"]).grid(row=1, column=1, sticky="w", padx=5, pady=5)
    ttk.Label(license_frame, text="Expires On:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    expires_text = app_instance.license_info.get('expires_at', 'N/A').split('T')[0]
    ttk.Label(license_frame, text=expires_text).grid(row=2, column=1, sticky="w", padx=5, pady=5)

    # 2. App Information (in left_frame)
    app_info_frame = ttk.LabelFrame(left_frame, text="Application Information")
    app_info_frame.grid(row=1, column=0, sticky="ew", pady=(15, 0)) # Add padding only to the top
    app_info_frame.columnconfigure(1, weight=1)
    ttk.Label(app_info_frame, text="Version:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    ttk.Label(app_info_frame, text=config.APP_VERSION).grid(row=0, column=1, sticky="w", padx=5, pady=5)
    ttk.Label(app_info_frame, text="Homepage:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    homepage_link = ttk.Label(app_info_frame, text="https://nrega-dashboard.palojori.in/", style="Link.TLabel", cursor="hand2")
    homepage_link.grid(row=1, column=1, sticky="w", padx=5, pady=5)
    homepage_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://nrega-dashboard.palojori.in/"))
    ttk.Label(app_info_frame, text="Support Email:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    ttk.Label(app_info_frame, text="rajatpoddar@outlook.com").grid(row=2, column=1, sticky="w", padx=5, pady=5)

    # 3. Changelog (in left_frame)
    changelog_frame = ttk.LabelFrame(left_frame, text="Changelog")
    changelog_frame.grid(row=2, column=0, sticky="nsew", pady=(15, 0))
    changelog_frame.columnconfigure(0, weight=1)
    changelog_frame.rowconfigure(0, weight=1)
    
    changelog_text = scrolledtext.ScrolledText(changelog_frame, wrap=tk.WORD, state="disabled", relief="flat")
    changelog_text.grid(row=0, column=0, sticky="nsew")
    
    # UPDATED: Added new version 2.2.0 with all recent changes
    changelog_content = {
        "2.2.0": [
            "Added new 'MR Fill & Absent' automation tab with manual edit pause.",
            "Added new 'Jobcard Verify & Photo' automation tab.",
            "Enhanced 'Jobcard Verify' to loop through all job cards and use folder-based or default photo matching.",
            "Enhanced 'MSR Processor' and 'Wagelist Gen' with improved, more resilient error handling and clearer results.",
            "Fixed various bugs including StaleElementReferenceException and UnexpectedAlertPresentException.",
            "Added 'Copy Log' button and 'Results' tabs to several modules for better user feedback."
        ],
        "2.1.0": [
            "Added license expiry notifications (within 3 days of expiry).",
            "Improved 'About' tab layout with a 60/40 split for better readability.",
            "Added donation and pricing information to the payment section.",
            "Updated support email address."
        ],
        "2.0.0": [
            "UI Overhaul: Shortened and reordered tab names for better visibility.",
            "Enhanced header buttons for launching Chrome with a clearer design.",
            "Added a direct link to the 'Nrega Palojori' website in the footer.",
            "Added 'Copy Log' button to more tabs for easier debugging."
        ],
        "1.8.0": [
            "Added 'Muster Roll Generator' feature with automatic mode and smart skipping.",
            "Fixed 'Read-only file system' error for built applications."
        ],
        "1.5.0": [
            "Enhanced security by locking paid keys to a single device.",
            "Added 'Reset' button to all tabs to clear inputs and logs.",
            "Added admin feature to reset machine binding for a key."
        ],
    }
    changelog_text.config(state="normal")
    for version, changes in changelog_content.items():
        changelog_text.insert(tk.END, f"Version {version}\n", "bold")
        for change in changes:
            changelog_text.insert(tk.END, f"  • {change}\n")
        changelog_text.insert(tk.END, "\n")
    changelog_text.config(state="disabled")
    changelog_text.tag_config("bold", font=config.STYLE_CONFIG["font_bold"])

    # --- RIGHT FRAME (Column 1) ---
    qr_frame = ttk.LabelFrame(parent_frame, text="Subscription Payment")
    qr_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
    qr_frame.columnconfigure(0, weight=1)
    
    donation_note = (
        "Please consider making a small donation to support the time and effort "
        "required for app maintenance, bug fixes, and future updates. "
        "In return for your support, you'll receive a license key."
    )
    note_label = ttk.Label(qr_frame, text=donation_note, wraplength=350, justify="center", style="Secondary.TLabel")
    note_label.pack(pady=(10, 15))

    try:
        qr_image_path = resource_path("payment_qr.png")
        img = Image.open(qr_image_path)
        
        original_width, original_height = img.size
        new_height = 300 
        new_width = int(new_height * (original_width / original_height))
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        app_instance.qr_photo_image = ImageTk.PhotoImage(img_resized)
        qr_label = ttk.Label(qr_frame, image=app_instance.qr_photo_image, anchor="center")
        qr_label.pack(pady=5, padx=5)

    except Exception as e:
        error_text = "Could not load payment QR code.\n\nEnsure 'payment_qr.png' is in the application folder."
        error_label = ttk.Label(qr_frame, text=error_text, justify="center", wraplength=200)
        error_label.pack(expand=True, padx=10, pady=10)
        print(f"Error loading QR code image: {e}")

    pricing_label = ttk.Label(qr_frame, text="₹99 for 1-Month License Key or ₹999 for 1-Year License Key", font=config.STYLE_CONFIG["font_bold"], justify="center")
    pricing_label.pack(pady=(15, 10))