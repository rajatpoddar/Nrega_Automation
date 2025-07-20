# main_app.py (Final Production Version)
import tkinter
from tkinter import messagebox, filedialog
import customtkinter as ctk
import threading, time, subprocess, os, webbrowser, sys, requests, json, uuid
from PIL import Image
from packaging.version import parse as parse_version
from getmac import get_mac_address
from appdirs import user_data_dir
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions

import config
from tabs import msr_tab, wagelist_gen_tab, wagelist_send_tab, wc_gen_tab, mb_entry_tab, if_edit_tab, musterroll_gen_tab, about_tab, jobcard_verify_tab, fto_generation_tab

# Import ctypes for Windows sleep prevention
if config.OS_SYSTEM == "Windows":
    import ctypes

# --- Load Environment Variables ---
load_dotenv()

# --- SENTRY INTEGRATION ---
import sentry_sdk
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        release=f"{config.APP_NAME}@{config.APP_VERSION}",
        traces_sample_rate=1.0,
    )

# --- THEME AND APPEARANCE ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("theme.json")


def get_data_path(filename):
    app_name = "NREGA-Dashboard"
    app_author = "PoddarSolutions"
    data_dir = user_data_dir(app_name, app_author)
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, filename)

def get_user_downloads_path():
    return os.path.join(Path.home(), "Downloads")

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class NregaDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NREGA Automation Dashboard")
        self.geometry("1100x800")
        self.minsize(1000, 700)

        self.is_licensed = False
        self.license_info = {}
        self.machine_id = self._get_machine_id()
        self.update_info = {"status": "Checking...", "version": None, "url": None}
        
        if SENTRY_DSN:
            sentry_sdk.set_user({"id": self.machine_id})
            sentry_sdk.set_tag("os.name", config.OS_SYSTEM)

        self.open_on_about_tab = False
        self.sleep_prevention_process = None
        self.active_automations = set()

        self.icon_images = {}
        
        self.automation_threads = {}
        self.stop_events = {}
        self.nav_buttons = {}
        self.content_frames = {}

        self.after(100, self.start_app)
        
    def start_app(self):
        """Builds the UI first, then initiates the license check flow."""
        self.build_main_ui()
        self.after(200, self.perform_license_check_flow)
        self.check_for_updates_background() # Start background update check

    def perform_license_check_flow(self):
        """The core logic for checking a license and locking/unlocking the app."""
        self.is_licensed = self.check_license()

        if self.is_licensed:
            self.check_expiry_and_notify()
            self._unlock_app()
            self.after(100, self._update_about_tab_info) # Update UI after check
        else:
            self._lock_app_to_about_tab()
            if self.show_activation_window():
                self.is_licensed = True
                self.check_expiry_and_notify()
                self._unlock_app()
                self.after(100, self._update_about_tab_info) # Update UI after activation
            else:
                self.destroy()

    def _lock_app_to_about_tab(self):
        """Disables all controls and forces the 'About' tab to be visible."""
        self.show_frame("About")
        for name, button in self.nav_buttons.items():
            if name != "About":
                button.configure(state="disabled")
        
        self.launch_chrome_btn.configure(state="disabled")
        self.theme_combo.configure(state="disabled")

    def _unlock_app(self):
        """Enables all controls for a licensed user."""
        for button in self.nav_buttons.values():
            button.configure(state="normal")
            
        self.launch_chrome_btn.configure(state="normal")
        self.theme_combo.configure(state="normal")

    def get_data_path(self, filename):
        return get_data_path(filename)
        
    def get_user_downloads_path(self):
        return get_user_downloads_path()

    def _load_icon(self, name, path, size=(20, 20)):
        try:
            full_path = resource_path(path)
            if os.path.exists(full_path):
                image = Image.open(full_path)
                photo_image = ctk.CTkImage(light_image=image, dark_image=image, size=size)
                self.icon_images[name] = photo_image
                return photo_image
        except Exception as e:
            print(f"Warning: Could not load icon '{name}' from {path}. Error: {e}")
        return None

    def open_browser_remote_debug(self, browser_name):
        if browser_name == 'chrome':
            port = "9222"
            profile_dir_name = "ChromeProfileForNREGA"
            paths_to_check = {
                "Darwin": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
                "Windows": ["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"]
            }
            args = [f"--remote-debugging-port={port}"]
        else:
            messagebox.showerror("Error", f"Unsupported browser: {browser_name}")
            return

        profile_dir = os.path.join(os.path.expanduser("~"), profile_dir_name)
        browser_path = next((path for path in paths_to_check.get(config.OS_SYSTEM, []) if os.path.exists(path)), None)

        if not browser_path:
            messagebox.showerror("Error", f"{browser_name.title()} not found in standard locations.")
            return
        
        try:
            os.makedirs(profile_dir, exist_ok=True)
            startup_url = "https://nrega.palojori.in"
            command = [browser_path] + args + [f"--user-data-dir={profile_dir}", startup_url]
            subprocess.Popen(command)
            messagebox.showinfo(f"{browser_name.title()} Launched", f"{browser_name.title()} is starting with remote debugging.\nPlease log in to the NREGA website before starting automation.")
        except Exception as e:
            if SENTRY_DSN: sentry_sdk.capture_exception(e)
            messagebox.showerror("Error", f"Failed to launch {browser_name.title()}:\n{e}")

    def _get_machine_id(self):
        try:
            mac = get_mac_address()
            if mac: return mac
            return "unknown-device-" + str(uuid.getnode())
        except Exception:
            return "error-getting-mac"

    def build_main_ui(self):
        self._load_icon("chrome", "assets/icons/chrome.png")
        self._load_icon("whatsapp", "assets/icons/whatsapp.png", size=(16, 16))
        self._load_icon("nrega", "assets/icons/nrega.png", size=(16, 16))

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._create_header()
        self._create_main_layout()
        self._create_footer()
        
        initial_tab = "About" if self.open_on_about_tab else "MR Gen"
        self.after(100, lambda: self.show_frame(initial_tab))
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _create_header(self):
        header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20,0))
        
        try:
            logo_image = ctk.CTkImage(Image.open(resource_path("logo.png")), size=(50, 50))
            logo_label = ctk.CTkLabel(header_frame, image=logo_image, text="")
            logo_label.pack(side="left", padx=(0, 15))
        except Exception as e:
            print(f"Warning: logo.png not found: {e}")
        
        title_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_container.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(title_container, text="NREGA Automation Dashboard", font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(title_container, text=f"v{config.APP_VERSION} | Log in, then select a task from the left panel.", anchor="w").pack(anchor="w")
        
        controls_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        controls_frame.pack(side="right")

        self.launch_chrome_btn = ctk.CTkButton(controls_frame, text="Launch Chrome", image=self.icon_images.get("chrome"), command=lambda: self.open_browser_remote_debug('chrome'), width=140)
        self.launch_chrome_btn.pack(side="left", padx=(0,10))
        
        theme_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        theme_frame.pack(side="left", padx=10, fill="y")
        
        ctk.CTkLabel(theme_frame, text="Theme:").pack(side="left", padx=(0, 5))
        self.theme_combo = ctk.CTkOptionMenu(theme_frame, values=["System", "Light", "Dark"], command=self.on_theme_change)
        self.theme_combo.pack(side="left")

    def _create_main_layout(self):
        main_frame = ctk.CTkFrame(self, corner_radius=0)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10,0))
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        self._create_nav_buttons(main_frame)
        
        self.content_area = ctk.CTkFrame(main_frame)
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)
        
        self._create_content_frames()

    def _create_nav_buttons(self, parent):
        nav_frame = ctk.CTkFrame(parent, width=220, corner_radius=10)
        nav_frame.grid(row=0, column=0, sticky="nsw")
        
        tabs_to_create = self.get_tabs_definition()
        for name, data in tabs_to_create.items():
            icon = data["icon"]
            btn = ctk.CTkButton(nav_frame, text=f"{icon}  {name}", command=lambda n=name: self.show_frame(n), 
                                anchor="w", font=ctk.CTkFont(size=14), height=40,
                                corner_radius=8, fg_color="transparent", text_color=("gray10", "gray90"),
                                hover_color=("gray75", "gray25"))
            btn.pack(fill="x", padx=10, pady=(5,0))
            self.nav_buttons[name] = btn

    def _create_content_frames(self):
        tabs_to_create = self.get_tabs_definition()
        for name, data in tabs_to_create.items():
            frame = ctk.CTkFrame(self.content_area)
            frame.grid(row=0, column=0, sticky="nsew")
            data["creation_func"](frame, self)
            self.content_frames[name] = frame
    
    def get_tabs_definition(self):
        return {
            "MR Gen": {"creation_func": musterroll_gen_tab.create_tab, "icon": config.ICONS["MR Gen"]},
            "MR Payment": {"creation_func": msr_tab.create_tab, "icon": config.ICONS["MR Payment"]},
            "Gen Wagelist": {"creation_func": wagelist_gen_tab.create_tab, "icon": config.ICONS["Gen Wagelist"]},
            "Send Wagelist": {"creation_func": wagelist_send_tab.create_tab, "icon": config.ICONS["Send Wagelist"]},
            "FTO Generation": {"creation_func": fto_generation_tab.create_tab, "icon": config.ICONS["FTO Generation"]},
            "Verify Jobcard": {"creation_func": jobcard_verify_tab.create_tab, "icon": config.ICONS["Verify Jobcard"]},
            "eMB Entry⚠️": {"creation_func": mb_entry_tab.create_tab, "icon": config.ICONS["eMB Entry"]},
            "WC Gen (Abua)": {"creation_func": wc_gen_tab.create_tab, "icon": config.ICONS["WC Gen (Abua)"]},
            "IF Editor (Abua)⚠️": {"creation_func": if_edit_tab.create_tab, "icon": config.ICONS["IF Editor (Abua)"]},
            "About": {"creation_func": about_tab.create_tab, "icon": config.ICONS["About"]},
        }

    def show_frame(self, page_name):
        frame_to_show = self.content_frames[page_name]
        frame_to_show.tkraise()
        for name, button in self.nav_buttons.items():
            if name == page_name:
                button.configure(fg_color=("white", "gray28"))
            else:
                button.configure(fg_color="transparent")
    
    def _create_footer(self):
        footer_frame = ctk.CTkFrame(self, height=40, corner_radius=0)
        footer_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(10,15))
        
        copyright_label = ctk.CTkLabel(footer_frame, text="© 2025 Made with ❤️ by Rajat Poddar.", text_color="gray50")
        copyright_label.pack(side="left", padx=15)
        copyright_label.bind("<Button-1>", lambda e: webbrowser.open_new_tab("https://github.com/rajatpoddar"))
        
        button_container = ctk.CTkFrame(footer_frame, fg_color="transparent")
        button_container.pack(side="right", padx=15)

        whatsapp_link = "https://chat.whatsapp.com/Bup3hDCH3wn2shbUryv8wn?mode=r_c"
        whatsapp_btn = ctk.CTkButton(button_container, text="Join WhatsApp Group", image=self.icon_images.get("whatsapp"),
                                  command=lambda: webbrowser.open_new_tab(whatsapp_link), fg_color="transparent", hover=False,
                                  text_color=("gray10", "gray80"))
        whatsapp_btn.pack(side="right", padx=(10, 0))

        nrega_btn = ctk.CTkButton(button_container, text="Nrega Palojori ↗", image=self.icon_images.get("nrega"),
                                  command=lambda: webbrowser.open_new_tab("https://nrega.palojori.in"), fg_color="transparent", hover=False,
                                  text_color=("gray10", "gray80"))
        nrega_btn.pack(side="right")

    def on_theme_change(self, new_theme: str):
        ctk.set_appearance_mode(new_theme)
        self.after(100, self.restyle_all_treeviews)

    def restyle_all_treeviews(self):
        """Helper function to find and restyle all Treeview widgets."""
        if hasattr(musterroll_gen_tab, 'style_treeview'): musterroll_gen_tab.style_treeview(self)
        if hasattr(msr_tab, 'style_treeview'): msr_tab.style_treeview(self)
        if hasattr(wagelist_gen_tab, 'style_treeview'): wagelist_gen_tab.style_treeview(self)
        if hasattr(fto_generation_tab, 'style_treeview'): fto_generation_tab.style_treeview(self)
        if hasattr(mb_entry_tab, 'style_treeview'): mb_entry_tab.style_treeview(self)
        if hasattr(wagelist_send_tab, 'style_treeview'): wagelist_send_tab.style_treeview(self)

    def check_license(self):
        license_file = get_data_path('license.dat')
        try:
            if os.path.exists(license_file):
                with open(license_file, 'r') as f: self.license_info = json.load(f)
                if self.validate_on_server(self.license_info.get('key'), is_startup_check=True): return True
                else: return False
            else: return False
        except Exception as e:
            if SENTRY_DSN: sentry_sdk.capture_exception(e)
            if os.path.exists(license_file): os.remove(license_file)
            return False

    def validate_on_server(self, key, is_startup_check=False):
        server_url = "https://nrega-server.palojori.in/validate"
        try:
            response = requests.post(server_url, json={"key": key, "machine_id": self.machine_id}, timeout=10)
            data = response.json()
            if response.status_code == 200 and data.get("status") == "valid":
                self.license_info = {'key': key, 'expires_at': data.get('expires_at')}
                if not is_startup_check: messagebox.showinfo("License Valid", f"Activation successful!\nExpires on: {self.license_info['expires_at'].split('T')[0]}")
                return True
            else:
                reason = data.get("reason", "Unknown error.")
                if not is_startup_check: messagebox.showerror("Validation Failed", f"License validation failed: {reason}")
                self.license_info['reason'] = reason
                return False
        except requests.exceptions.RequestException as e:
            if not is_startup_check: messagebox.showerror("Connection Error", f"Could not connect to the license server: {e}")
            self.license_info['reason'] = "Connection Error"
            return False

    def show_activation_window(self):
        activation_window = ctk.CTkToplevel(self)
        activation_window.title("Activate Product")
        win_width, win_height = 450, 480
        x = (self.winfo_screenwidth() // 2) - (win_width // 2)
        y = (self.winfo_screenheight() // 2) - (win_height // 2)
        activation_window.geometry(f'{win_width}x{win_height}+{x}+{y}')
        activation_window.resizable(False, False)
        activation_window.transient(self)
        activation_window.grab_set()
        
        main_frame = ctk.CTkFrame(activation_window, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        ctk.CTkLabel(main_frame, text="Product Activation", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0, 10))
        is_activated = tkinter.BooleanVar(value=False)

        def on_start_trial():
            server_url = "https://nrega-server.palojori.in/request-trial"
            try:
                headers = {'User-Agent': f'{config.APP_NAME}/{config.APP_VERSION}'}
                response = requests.post(server_url, json={"machine_id": self.machine_id}, timeout=15, headers=headers)
                data = response.json()
                if response.status_code == 200 and data.get("status") == "success":
                    self.license_info = {'key': data.get("key"), 'expires_at': data.get('expires_at')}
                    with open(get_data_path('license.dat'), 'w') as f: json.dump(self.license_info, f)
                    messagebox.showinfo("Trial Started", f"Your 30-day free trial has started!\nExpires on: {self.license_info['expires_at'].split('T')[0]}")
                    is_activated.set(True)
                    activation_window.destroy()
                else:
                    messagebox.showerror("Trial Error", data.get("reason", "Could not start trial."))
            except requests.exceptions.RequestException:
                messagebox.showerror("Connection Error", "Could not connect to the server to start a trial.")

        ctk.CTkButton(main_frame, text="Start 30-Day Free Trial", command=on_start_trial).pack(pady=5, ipady=4, fill='x')
        ctk.CTkLabel(main_frame, text="— OR —").pack(pady=10)

        machine_id_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        machine_id_frame.pack(pady=(10, 5), fill='x')
        ctk.CTkLabel(machine_id_frame, text="Your Machine ID (for support):").pack(anchor='w')
        id_display_frame = ctk.CTkFrame(machine_id_frame, fg_color="transparent")
        id_display_frame.pack(fill='x', expand=True, pady=(2, 10))
        id_entry = ctk.CTkEntry(id_display_frame, textvariable=ctk.StringVar(value=self.machine_id))
        id_entry.configure(state="readonly")
        id_entry.pack(side='left', fill='x', expand=True)
        def copy_id():
            self.clipboard_clear(); self.clipboard_append(self.machine_id)
            copy_button.configure(text="Copied!")
            self.after(2000, lambda: copy_button.configure(text="Copy"))
        copy_button = ctk.CTkButton(id_display_frame, text="Copy", command=copy_id, width=60)
        copy_button.pack(side='left', padx=(5, 0))

        ctk.CTkLabel(main_frame, text="Enter a purchased license key:").pack(pady=(5, 5))
        key_entry = ctk.CTkEntry(main_frame, width=300)
        key_entry.pack(pady=5)
        key_entry.focus_set()

        def on_activate_paid():
            key = key_entry.get().strip()
            if not key: messagebox.showwarning("Input Required", "Please enter a license key."); return
            if self.validate_on_server(key):
                with open(get_data_path('license.dat'), 'w') as f: json.dump(self.license_info, f)
                is_activated.set(True)
                activation_window.destroy()

        ctk.CTkButton(main_frame, text="Activate with Key", command=on_activate_paid).pack(pady=10, ipady=4, fill='x')
        ctk.CTkLabel(main_frame, text="Need help? Contact support at rajatpoddar@outlook.com", text_color="gray50").pack(pady=(15,0))
        
        self.wait_window(activation_window)
        return is_activated.get()

    def check_expiry_and_notify(self):
        expires_at_str = self.license_info.get('expires_at')
        if not expires_at_str: return
        try:
            expiry_date = datetime.fromisoformat(expires_at_str.split('T')[0]).date()
            days_left = (expiry_date - datetime.now().date()).days
            if 0 <= days_left < 3:
                message = f"Your license expires today." if days_left == 0 else f"Your license will expire in {days_left} day{'s' if days_left > 1 else ''}."
                messagebox.showwarning("License Expiring Soon", f"{message}\nPlease renew your subscription.")
                self.open_on_about_tab = True
        except (ValueError, TypeError) as e:
            print(f"Could not parse expiry date: {expires_at_str}. Error: {e}")
            if SENTRY_DSN: sentry_sdk.capture_exception(e)

    def start_automation_thread(self, key, target_func, args=()):
        if self.automation_threads.get(key) and self.automation_threads[key].is_alive():
            messagebox.showwarning("In Progress", f"The '{key}' task is already running.")
            return

        self.prevent_sleep()
        self.active_automations.add(key)
        self.stop_events[key] = threading.Event()
        
        def thread_wrapper():
            try:
                target_func(self, *args)
            finally:
                self.after(0, self.on_automation_finished, key)

        thread = threading.Thread(target=thread_wrapper, daemon=True)
        self.automation_threads[key] = thread
        thread.start()

    def log_message(self, log_widget, message, level="info"):
        log_widget.configure(state="normal")
        log_widget.insert(tkinter.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        log_widget.configure(state="disabled")
        log_widget.see(tkinter.END)

    def clear_log(self, log_widget):
        log_widget.configure(state="normal")
        log_widget.delete("1.0", tkinter.END)
        log_widget.configure(state="disabled")

    def connect_to_chrome(self):
        driver = None
        try:
            options = ChromeOptions()
            options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            driver = webdriver.Chrome(options=options)
            return driver
        except WebDriverException as e:
            if SENTRY_DSN: sentry_sdk.capture_exception(e)
            messagebox.showerror("Connection Failed", f"Could not connect to Chrome. Please ensure:\n\n1. You launched Chrome from the app.\n2. It is still running.\n\n" f"Error: {e}")
            for event in self.stop_events.values(): event.set()
            return None

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit? This will stop any running automations."):
            self.active_automations.clear()
            self.allow_sleep()
            for event in self.stop_events.values(): event.set()
            time.sleep(0.5)
            self.destroy()

    def prevent_sleep(self):
        if not self.active_automations:
            print("Preventing system sleep.")
            if config.OS_SYSTEM == "Windows": ctypes.windll.kernel32.SetThreadExecutionState(0x80000003)
            elif config.OS_SYSTEM == "Darwin":
                if self.sleep_prevention_process is None: self.sleep_prevention_process = subprocess.Popen(["caffeinate", "-d"])
    
    def allow_sleep(self):
        if not self.active_automations:
            print("Allowing system sleep.")
            if config.OS_SYSTEM == "Windows": ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            elif config.OS_SYSTEM == "Darwin":
                if self.sleep_prevention_process:
                    self.sleep_prevention_process.terminate()
                    self.sleep_prevention_process = None

    def on_automation_finished(self, key):
        if key in self.active_automations: self.active_automations.remove(key)
        if not self.active_automations: self.allow_sleep()

    def _update_about_tab_info(self):
        """Refreshes all dynamic info on the About page after validation."""
        try:
            if 'update_button' in about_tab.widgets:
                # Update License Info
                key_text = self.license_info.get('key', 'N/A')
                expires_text = self.license_info.get('expires_at', 'N/A').split('T')[0]
                about_tab.widgets['license_key_label'].configure(text=key_text)
                about_tab.widgets['expires_on_label'].configure(text=expires_text)

                # Update Update Info
                info = self.update_info
                about_widgets = about_tab.widgets
                if info['status'] == 'available':
                    about_widgets['latest_version_label'].configure(text=f"Latest Version: {info['version']}")
                    about_widgets['update_button'].configure(
                        text=f"Download & Install v{info['version']}",
                        state="normal",
                        fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
                        command=lambda: about_tab.download_and_install_update(self, about_widgets, info['url'], info['version'])
                    )
                    self.show_update_prompt(info['version'])
                elif info['status'] == 'updated':
                    about_widgets['latest_version_label'].configure(text=f"Latest Version: {config.APP_VERSION}")
                    about_widgets['update_button'].configure(text="You are up to date", state="disabled")
                else:
                    about_widgets['latest_version_label'].configure(text="Latest Version: Error")
                    about_widgets['update_button'].configure(text="Check for Updates", state="normal")
            else:
                self.after(100, self._update_about_tab_info)
        except Exception as e:
            print(f"Could not update About tab UI: {e}")

    def check_for_updates_background(self):
        def _check():
            time.sleep(2)
            update_url = "https://nrega-dashboard.palojori.in/version.json"
            try:
                response = requests.get(update_url, timeout=10)
                response.raise_for_status()
                data = response.json()
                latest_version = data.get("latest_version")
                url_key = f"download_url_{sys.platform}" if sys.platform in ["win32", "darwin"] else f"download_url_windows"
                download_url = data.get(url_key)
                if latest_version and parse_version(latest_version) > parse_version(config.APP_VERSION):
                    self.update_info = {"status": "available", "version": latest_version, "url": download_url}
                else:
                    self.update_info = {"status": "updated", "version": latest_version, "url": download_url}
            except Exception as e:
                self.update_info['status'] = 'error'
                print(f"Update check failed: {e}")
            finally:
                self.after(0, self._update_about_tab_info)
        threading.Thread(target=_check, daemon=True).start()

    def show_update_prompt(self, version):
        if messagebox.askyesno("Update Available", f"A new version ({version}) is available. Go to the 'About' page to download?"):
            self.show_frame("About")

if __name__ == '__main__':
    try:
        app = NregaDashboard()
        app.mainloop()
    except Exception as e:
        if SENTRY_DSN: sentry_sdk.capture_exception(e)
        messagebox.showerror("Fatal Startup Error", f"A critical error occurred on startup:\n\n{e}\n\nThe application will now close.")