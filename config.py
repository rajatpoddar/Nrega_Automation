# config.py
# This file contains centralized configuration settings for the NREGA Dashboard.

# --- Application Version Info ---
APP_NAME = "NREGA-Dashboard"
APP_VERSION = "2.2.0" # Version can be updated as needed

# --- Platform & UI Configuration ---
import platform
OS_SYSTEM = platform.system()

# --- Centralized Style Configuration ---
STYLE_CONFIG = {
    "font_family": "SF Pro Display" if OS_SYSTEM == "Darwin" else "Segoe UI",
    "font_normal": ("SF Pro Display", 13) if OS_SYSTEM == "Darwin" else ("Segoe UI", 10),
    "font_bold": ("SF Pro Display", 13, "bold") if OS_SYSTEM == "Darwin" else ("Segoe UI", 10, "bold"),
    "font_title": ("SF Pro Display", 22, "bold") if OS_SYSTEM == "Darwin" else ("Segoe UI", 18, "bold"),
    "font_small": ("SF Pro Display", 11) if OS_SYSTEM == "Darwin" else ("Segoe UI", 8),
    
    "colors": {
        "light": {
            "background": "#f5f5f7", "frame": "#ffffff", "text": "#1d1d1f",
            "text_secondary": "#6e6e73", "border": "#d2d2d7", "accent": "#007aff",
            "accent_text": "#ffffff", "danger": "#d93636", "success": "#34c759", "warning": "#ff9500"
        },
        "dark": {
            "background": "#1c1c1e", "frame": "#2c2c2e", "text": "#f5f5f7",
            "text_secondary": "#8e8e93", "border": "#424245", "accent": "#0a84ff",
            "accent_text": "#ffffff", "danger": "#ff453a", "success": "#32d74b", "warning": "#ff9f0a"
        }
    }
}


# --- Automation Configurations ---

# New: Configuration for the Muster Roll Generator
MUSTER_ROLL_CONFIG = {
    # Note: Please verify this is the correct URL for muster roll generation.
    "base_url": "https://nregade4.nic.in/Netnrega/preprintmsr.aspx"
}

MSR_CONFIG = {
    "url": "https://nregade4.nic.in/Netnrega/msrpayment.aspx",
    "work_code_index": 1,
    "muster_roll_index": 1,
    "min_delay": 2,
    "max_delay": 6
}

WAGELIST_GEN_CONFIG = {
    "base_url": 'https://nregade4.nic.in/Netnrega/SendMSRtoPO.aspx',
}

MB_ENTRY_CONFIG = {
    "measurement_book_no": "1", "page_no": "2",
    "measurement_date": "10/07/2025", "unit_cost": "282",
    "mate_name": "abc", "default_pit_count": "112",
    "je_name": "Nilesh Hembram", "je_designation": "JE",
}

IF_EDIT_CONFIG = {
    "url": "https://nregade4.nic.in/netnrega/IFEdit.aspx"
}

WC_GEN_CONFIG = {
    "url": "https://mnregaweb2.nic.in/netnrega/work_entry.aspx"
}