# config.py
# This file contains centralized configuration settings for the NREGA Dashboard.

# --- Application Version Info ---
APP_NAME = "NREGA-Dashboard"
APP_VERSION = "2.4.1" # Version updated for theme refinement

# --- Platform & UI Configuration ---
import platform
OS_SYSTEM = platform.system()

# --- Centralized Style and Icon Configuration ---
ICONS = {
    "MR Gen": "📄", "MR Payment": "💳", "FTO Generation": "📤",
    "Gen Wagelist": "📋", "Send Wagelist": "➡️", "Verify Jobcard": "✅",
    "eMB Entry": "✏️", "WC Gen (Abua)": "🏗️", "IF Editor (Abua)": "🔧",
    "About": "ℹ️", "Theme": {"light": "🌙", "dark": "☀️"}
}

STYLE_CONFIG = {
    "font_family": "SF Pro Display" if OS_SYSTEM == "Darwin" else "Segoe UI",
    "font_normal": ("SF Pro Display", 13) if OS_SYSTEM == "Darwin" else ("Segoe UI", 10),
    "font_bold": ("SF Pro Display", 13, "bold") if OS_SYSTEM == "Darwin" else ("Segoe UI", 10, "bold"),
    "font_title": ("SF Pro Display", 22, "bold") if OS_SYSTEM == "Darwin" else ("Segoe UI", 18, "bold"),
    "font_small": ("SF Pro Display", 11) if OS_SYSTEM == "Darwin" else ("Segoe UI", 8),
    "font_nav": ("SF Pro Display", 14) if OS_SYSTEM == "Darwin" else ("Segoe UI", 11),

    "colors": {
        "light": {
            "background": "#f5f5f7", "frame": "#ffffff", "text": "#1d1d1f",
            "text_secondary": "#6e6e73", "border": "#d2d2d7", "accent": "#007aff",
            "accent_text": "#ffffff", "danger": "#d93636", "success": "#34c759", "warning": "#ff9500",
            "nav_bg": "#e5e5e7", "nav_fg": "#4f4f52",
            "nav_active_bg": "#ffffff", "nav_active_fg": "#007aff",
            "nav_hover_bg": "#dcdce0",
            # New colors for inner tabs and treeview
            "header_bg": "#e5e5e7",
            "inner_tab_bg": "#f5f5f7",
            "inner_tab_active_bg": "#ffffff",
            "inner_tab_active_fg": "#1d1d1f",
        },
        "dark": {
            "background": "#1c1c1e", "frame": "#2c2c2e", "text": "#f5f5f7",
            "text_secondary": "#8e8e93", "border": "#424245", "accent": "#0a84ff",
            "accent_text": "#ffffff", "danger": "#ff453a", "success": "#32d74b", "warning": "#ff9f0a",
            "nav_bg": "#3a3a3c", "nav_fg": "#d1d1d6",
            "nav_active_bg": "#2c2c2e", "nav_active_fg": "#0a84ff",
            "nav_hover_bg": "#48484a",
            # New colors for inner tabs and treeview
            "header_bg": "#3a3a3c",
            "inner_tab_bg": "#1c1c1e",
            "inner_tab_active_bg": "#2c2c2e",
            "inner_tab_active_fg": "#f5f5f7",
        }
    }
}

# --- Automation Configurations (No changes here) ---

MUSTER_ROLL_CONFIG = {
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
    "url": "https://nregade4.nic.in/Netnrega/mbbook.aspx",
    "measurement_book_no": "", "page_no": "",
    "measurement_date": "", "unit_cost": "282",
    "mate_name": "", "default_pit_count": "112",
    "je_name": "", "je_designation": "JE",
}

IF_EDIT_CONFIG = {
    "url": "https://nregade4.nic.in/netnrega/IFEdit.aspx"
}

WC_GEN_CONFIG = {
    "url": "https://mnregaweb2.nic.in/netnrega/work_entry.aspx"
}