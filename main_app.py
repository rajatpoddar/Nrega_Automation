# main_app.py
import tkinter
from tkinter import messagebox, filedialog
import customtkinter as ctk
import threading, time, subprocess, os, webbrowser, sys, requests, json, uuid, logging # Added logging import
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
from tabs.history_manager import HistoryManager

import config
# --- TAB CLASS IMPORTS ---
from tabs.msr_tab import MsrTab
from tabs.wagelist_gen_tab import WagelistGenTab
from tabs.wagelist_send_tab import WagelistSendTab
from tabs.wc_gen_tab import WcGenTab
from tabs.mb_entry_tab import MbEntryTab
from tabs.if_edit_tab import IfEditTab
from tabs.musterroll_gen_tab import MusterrollGenTab
from tabs.about_tab import AboutTab
from tabs.jobcard_verify_tab import JobcardVerifyTab
from tabs.fto_generation_tab import FtoGenerationTab
from tabs.workcode_extractor_tab import WorkcodeExtractorTab
from tabs.add_activity_tab import AddActivityTab
from tabs.abps_verify_tab import AbpsVerifyTab

if config.OS_SYSTEM == "Windows":
    import ctypes

# --- HELPER FUNCTIONS ---
def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_data_path(filename):
    app_name = "NREGABot"
    app_author = "PoddarSolutions"
    data_dir = user_data_dir(app_name, app_author)
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, filename)

def get_user_downloads_path():
    return os.path.join(Path.home(), "Downloads")

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

ctk.set_appearance_mode("System")
ctk.set_default_color_theme(resource_path("theme.json"))

class NregaBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.attributes("-alpha", 0.0)
        
        self.title(f"{config.APP_NAME}")
        self.geometry("1100x800")
        self.minsize(1000, 700)
        
        self.history_manager = HistoryManager(self.get_data_path)
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
        self.tab_instances = {}

        self.after(0, self.start_app)
        
    def start_app(self):
        self.splash = self._create_splash_screen()
        self.after(200, self._initialize_app)

    def _initialize_app(self):
        self.build_main_ui()
        if self.splash:
            self.splash.destroy()
            self.splash = None
        self.perform_license_check_flow()

    def _create_splash_screen(self):
        splash = ctk.CTkToplevel(self)
        splash.overrideredirect(True)
        splash_width, splash_height = 300, 200
        screen_width, screen_height = splash.winfo_screenwidth(), splash.winfo_screenheight()
        x = (screen_width / 2) - (splash_width / 2)
        y = (screen_height / 2) - (splash_height / 2)
        splash.geometry(f'{splash_width}x{splash_height}+{int(x)}+{int(y)}')
        try:
            logo_image = ctk.CTkImage(Image.open(resource_path("logo.png")), size=(80, 80))
            ctk.CTkLabel(splash, image=logo_image, text="").pack(pady=(20, 10))
        except Exception: pass
        ctk.CTkLabel(splash, text=f"{config.APP_NAME}\nLoading...", font=("SF Pro Display", 14)).pack()
        splash.lift()
        splash.attributes("-topmost", True)
        return splash

    def perform_license_check_flow(self):
        self.is_licensed = self.check_license()
        if self.is_licensed:
            is_expiring = self.check_expiry_and_notify()
            self._ping_server_in_background() # Ensure 'last_seen' is updated
            self._unlock_app()
            self.after(100, self._update_about_tab_info)
            self.show_frame("About" if is_expiring else list(self.get_tabs_definition().keys())[0])
            self.check_for_updates_background()
            self.deiconify()
            self.attributes("-alpha", 1.0)
        else:
            self._lock_app_to_about_tab()
            self.deiconify()
            self.attributes("-alpha", 1.0)
            if self.show_activation_window():
                self.is_licensed = True
                self.check_expiry_and_notify()
                self._unlock_app()
                self.after(100, self._update_about_tab_info)
                self.show_frame(list(self.get_tabs_definition().keys())[0])
                self.check_for_updates_background()
            else:
                self.destroy()

    def _ping_server_in_background(self):
        """Send a fire-and-forget request to update the 'last_seen' timestamp on the server."""
        if not self.license_info.get('key'):
            return
        
        def ping():
            server_url = f"{config.LICENSE_SERVER_URL}/validate"
            try:
                # This call updates 'last_seen' on the server.
                # We don't need to process the response here, just send the ping.
                requests.post(server_url, json={"key": self.license_info['key'], "machine_id": self.machine_id}, timeout=10)
                logging.info("Server ping successful, 'last_seen' updated.")
            except requests.exceptions.RequestException as e:
                logging.warning(f"Could not ping license server in background: {e}")

        threading.Thread(target=ping, daemon=True).start()

    def check_license(self):
        license_file = get_data_path('license.dat')
        if not os.path.exists(license_file):
            return False
        try:
            with open(license_file, 'r', encoding='utf-8') as f:
                self.license_info = json.load(f)
            if 'key' not in self.license_info or 'expires_at' not in self.license_info:
                raise ValueError("License file is missing key or expiry date.")
            
            expiry_date = datetime.fromisoformat(self.license_info['expires_at'].split('T')[0]).date()
            if expiry_date >= datetime.now().date():
                return True
            else:
                # Local license has expired, must re-validate with server
                return self.validate_on_server(self.license_info.get('key'), is_startup_check=True)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            if SENTRY_DSN:
                sentry_sdk.capture_message(f"Corrupted license file found and deleted. Error: {e}")
            os.remove(license_file)
            return False

    def _lock_app_to_about_tab(self):
        self.show_frame("About")
        for name, button in self.nav_buttons.items():
            if name != "About":
                button.configure(state="disabled")
        self.launch_chrome_btn.configure(state="disabled")
        self.theme_combo.configure(state="disabled")

    def _unlock_app(self):
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
                self.icon_images[name] = ctk.CTkImage(light_image=image, dark_image=image, size=size)
        except Exception as e:
            print(f"Warning: Could not load icon '{name}' from {path}. Error: {e}")

    def open_browser_remote_debug(self, browser_name):
        port = "9222"
        profile_dir_name = "ChromeProfileForNREGABot"
        profile_dir = os.path.join(os.path.expanduser("~"), profile_dir_name)
        os.makedirs(profile_dir, exist_ok=True)
        paths_to_check = {
            "Darwin": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
            "Windows": ["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"]
        }
        browser_path = next((path for path in paths_to_check.get(config.OS_SYSTEM, []) if os.path.exists(path)), None)
        if not browser_path:
            messagebox.showerror("Error", "Google Chrome not found in standard locations.")
            return
        try:
            command = [browser_path, f"--remote-debugging-port={port}", f"--user-data-dir={profile_dir}", config.MAIN_WEBSITE_URL]
            if config.OS_SYSTEM == "Windows":
                subprocess.Popen(command, creationflags=0x00000008)
            else:
                subprocess.Popen(command, start_new_session=True)
            messagebox.showinfo("Chrome Launched", "Chrome is starting with remote debugging.\nPlease log in to the NREGA website before starting automation.")
        except Exception as e:
            if SENTRY_DSN: sentry_sdk.capture_exception(e)
            messagebox.showerror("Error", f"Failed to launch Chrome:\n{e}")

    def _get_machine_id(self):
        try:
            return get_mac_address() or "unknown-device-" + str(uuid.getnode())
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
        ctk.CTkLabel(title_container, text=config.APP_NAME, font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w")
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
        main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        main_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10,0))
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        self._create_nav_buttons(main_frame)
        self.content_area = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)
        self._create_content_frames()

    def _create_nav_buttons(self, parent):
        nav_frame = ctk.CTkFrame(parent, width=220)
        nav_frame.grid(row=0, column=0, sticky="nsw")
        tabs_to_create = self.get_tabs_definition()
        for name, data in tabs_to_create.items():
            icon = data["icon"]
            btn = ctk.CTkButton(nav_frame, text=f" {icon}  {name}", command=lambda n=name: self.show_frame(n), 
                                anchor="w", font=ctk.CTkFont(size=14), height=40,
                                corner_radius=8, fg_color="transparent", text_color=("gray10", "gray90"),
                                hover_color=("gray75", "gray25"))
            btn.pack(fill="x", padx=10, pady=(5,0))
            self.nav_buttons[name] = btn

    def _create_content_frames(self):
        tabs_to_create = self.get_tabs_definition()
        for name, data in tabs_to_create.items():
            frame_container = ctk.CTkFrame(self.content_area, fg_color="transparent")
            frame_container.grid(row=0, column=0, sticky="nsew")
            tab_instance = data["creation_func"](frame_container, self)
            tab_instance.pack(expand=True, fill="both")
            self.content_frames[name] = frame_container
            self.tab_instances[name] = tab_instance

    def get_tabs_definition(self):
        return {
            "MR Gen": {"creation_func": MusterrollGenTab, "icon": config.ICONS["MR Gen"]},
            "MR Payment": {"creation_func": MsrTab, "icon": config.ICONS["MR Payment"]},
            "Gen Wagelist": {"creation_func": WagelistGenTab, "icon": config.ICONS["Gen Wagelist"]},
            "Send Wagelist": {"creation_func": WagelistSendTab, "icon": config.ICONS["Send Wagelist"]},
            "FTO Generation": {"creation_func": FtoGenerationTab, "icon": config.ICONS["FTO Generation"]},
            "Verify Jobcard": {"creation_func": JobcardVerifyTab, "icon": config.ICONS["Verify Jobcard"]},
            "eMB Entry⚠️": {"creation_func": MbEntryTab, "icon": config.ICONS["eMB Entry"]},
            "WC Gen (Abua)": {"creation_func": WcGenTab, "icon": config.ICONS["WC Gen (Abua)"]},
            "IF Editor (Abua)⚠️": {"creation_func": IfEditTab, "icon": config.ICONS["IF Editor (Abua)"]},
            "Add Activity": {"creation_func": AddActivityTab, "icon": config.ICONS["Add Activity"]},
            "Verify ABPS": {"creation_func": AbpsVerifyTab, "icon": config.ICONS["Verify ABPS"]},
            "Workcode Extractor": {"creation_func": WorkcodeExtractorTab, "icon": config.ICONS["Workcode Extractor"]},
            "About": {"creation_func": AboutTab, "icon": config.ICONS["About"]},
        }

    def show_frame(self, page_name):
        frame_to_show = self.content_frames[page_name]
        frame_to_show.tkraise()
        for name, button in self.nav_buttons.items():
            button.configure(fg_color=("gray90", "gray28") if name == page_name else "transparent")
    
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
        nrega_btn = ctk.CTkButton(button_container, text="NREGA Bot Website ↗", image=self.icon_images.get("nrega"),
                                  command=lambda: webbrowser.open_new_tab(config.MAIN_WEBSITE_URL), fg_color="transparent", hover=False,
                                  text_color=("gray10", "gray80"))
        nrega_btn.pack(side="right")

    def on_theme_change(self, new_theme: str):
        ctk.set_appearance_mode(new_theme)
        self.after(100, self.restyle_all_treeviews)

    def restyle_all_treeviews(self):
        for tab in self.tab_instances.values():
            if hasattr(tab, 'style_treeview') and hasattr(tab, 'results_tree'):
                tab.style_treeview(tab.results_tree)
    
    def _update_about_tab_info(self):
        try:
            about_tab_instance = self.tab_instances.get("About")
            if about_tab_instance:
                about_tab_instance.update_subscription_details(self.license_info)
                
                info = self.update_info
                if info['status'] == 'available':
                    about_tab_instance.latest_version_label.configure(text=f"Latest Version: {info['version']}")
                    about_tab_instance.update_button.configure(
                        text=f"Download & Install v{info['version']}",
                        state="normal",
                        fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
                        command=lambda: about_tab_instance.download_and_install_update(info['url'], info['version'])
                    )
                elif info['status'] == 'updated':
                    about_tab_instance.latest_version_label.configure(text=f"Latest Version: {config.APP_VERSION}")
                    about_tab_instance.update_button.configure(text="You are up to date", state="disabled")
                else:
                    about_tab_instance.latest_version_label.configure(text=f"Latest Version: {info['status'].capitalize()}")
                    about_tab_instance.update_button.configure(text="Check for Updates", state="normal")
        except Exception as e:
            print(f"Could not update About tab UI: {e}")
            if SENTRY_DSN: sentry_sdk.capture_exception(e)

    def validate_on_server(self, key, is_startup_check=False):
        server_url = f"{config.LICENSE_SERVER_URL}/validate"
        try:
            response = requests.post(server_url, json={"key": key, "machine_id": self.machine_id}, timeout=10)
            data = response.json()
            if response.status_code == 200 and data.get("status") == "valid":
                self.license_info = {
                    'key': key, 
                    'expires_at': data.get('expires_at'),
                    'user_name': data.get('user_name'),
                    'key_type': data.get('key_type', 'paid') # Ensure key_type is saved
                }
                with open(get_data_path('license.dat'), 'w') as f:
                    json.dump(self.license_info, f)
                if not is_startup_check: messagebox.showinfo("License Valid", f"Activation successful!\nExpires on: {self.license_info['expires_at'].split('T')[0]}")
                return True
            else:
                reason = data.get("reason", "Unknown error.")
                if not is_startup_check: messagebox.showerror("Validation Failed", f"License validation failed: {reason}")
                return False
        except requests.exceptions.RequestException as e:
            if not is_startup_check: messagebox.showerror("Connection Error", f"Could not connect to the license server: {e}")
            return False

    def show_activation_window(self):
        activation_window = ctk.CTkToplevel(self)
        activation_window.title("Activate Product")
        # Increased height to fit new links
        win_width, win_height = 450, 440
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

        def open_trial_form():
            activation_window.withdraw()
            if self.show_trial_registration_window():
                is_activated.set(True)
                activation_window.destroy()
            else:
                activation_window.deiconify()

        ctk.CTkButton(main_frame, text="Start 30-Day Free Trial", command=open_trial_form).pack(pady=5, ipady=4, fill='x')
        ctk.CTkLabel(main_frame, text="— OR —").pack(pady=10)

        ctk.CTkLabel(main_frame, text="Enter a purchased license key:").pack(pady=(5, 5))
        key_entry = ctk.CTkEntry(main_frame, width=300)
        key_entry.pack(pady=5)
        key_entry.focus_set()

        def on_activate_paid():
            key = key_entry.get().strip()
            if not key: messagebox.showwarning("Input Required", "Please enter a license key."); return
            if self.validate_on_server(key):
                is_activated.set(True)
                activation_window.destroy()

        ctk.CTkButton(main_frame, text="Activate with Key", command=on_activate_paid).pack(pady=10, ipady=4, fill='x')
        ctk.CTkLabel(main_frame, text=f"Need help? Contact support at {config.SUPPORT_EMAIL}", text_color="gray50").pack(pady=(15,0))
        
        # --- ADDED: Links for purchasing and website ---
        links_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        links_frame.pack(pady=(15,0), fill="x")

        buy_link_label = ctk.CTkLabel(links_frame, text="Purchase a License Key", text_color=("blue", "cyan"), cursor="hand2")
        buy_link_label.pack()
        buy_link_label.bind("<Button-1>", lambda e: webbrowser.open_new_tab(f"{config.LICENSE_SERVER_URL}/buy"))

        website_link_label = ctk.CTkLabel(links_frame, text="Visit our Website", text_color=("blue", "cyan"), cursor="hand2")
        website_link_label.pack(pady=(5,0))
        website_link_label.bind("<Button-1>", lambda e: webbrowser.open_new_tab(config.MAIN_WEBSITE_URL))
        
        self.wait_window(activation_window)
        return is_activated.get()

    def show_trial_registration_window(self):
        trial_window = ctk.CTkToplevel(self)
        trial_window.title("Trial Registration")
        win_width, win_height = 480, 600
        x = (self.winfo_screenwidth() // 2) - (win_width // 2)
        y = (self.winfo_screenheight() // 2) - (win_height // 2)
        trial_window.geometry(f'{win_width}x{win_height}+{x}+{y}')
        trial_window.resizable(False, False)
        trial_window.transient(self)
        trial_window.grab_set()

        scroll_frame = ctk.CTkScrollableFrame(trial_window, fg_color="transparent", label_fg_color="transparent")
        scroll_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        ctk.CTkLabel(scroll_frame, text="Start Your Free Trial", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0, 5))
        ctk.CTkLabel(scroll_frame, text="Please provide your details to begin.", text_color="gray50").pack(pady=(0, 15))

        entries = {}
        fields = ["Full Name", "Email", "Mobile", "Block", "District", "State", "Pincode"]
        for field in fields:
            key = field.lower().replace(" ", "_")
            ctk.CTkLabel(scroll_frame, text=field, anchor="w").pack(fill="x", padx=10)
            entry = ctk.CTkEntry(scroll_frame)
            entry.pack(fill="x", padx=10, pady=(0, 10))
            entries[key] = entry
        
        is_successful = tkinter.BooleanVar(value=False)

        def submit_trial_request():
            user_data = {key: entry.get().strip() for key, entry in entries.items()}
            user_data["name"] = user_data.pop("full_name")
            user_data["machine_id"] = self.machine_id

            if not all(user_data.values()):
                messagebox.showwarning("Input Required", "All fields are required to start a trial.", parent=trial_window)
                return

            submit_btn.configure(state="disabled", text="Requesting...")
            
            server_url = f"{config.LICENSE_SERVER_URL}/api/request-trial"
            try:
                headers = {'User-Agent': f'{config.APP_NAME}/{config.APP_VERSION}'}
                response = requests.post(server_url, json=user_data, timeout=15, headers=headers)
                data = response.json()
                if response.status_code == 200 and data.get("status") == "success":
                    self.license_info = {
                        'key': data.get("key"), 
                        'expires_at': data.get('expires_at'),
                        'user_name': user_data['name'],
                        'key_type': 'trial'
                    }
                    with open(get_data_path('license.dat'), 'w') as f: json.dump(self.license_info, f)
                    messagebox.showinfo("Trial Started", f"Your 30-day free trial has started!\nExpires on: {self.license_info['expires_at'].split('T')[0]}")
                    is_successful.set(True)
                    trial_window.destroy()
                else:
                    messagebox.showerror("Trial Error", data.get("reason", "Could not start trial."), parent=trial_window)
            except requests.exceptions.RequestException:
                messagebox.showerror("Connection Error", "Could not connect to the server to start a trial.", parent=trial_window)
            finally:
                submit_btn.configure(state="normal", text="Start Trial")

        submit_btn = ctk.CTkButton(scroll_frame, text="Start Trial", command=submit_trial_request)
        submit_btn.pack(pady=20, ipady=4, fill='x', padx=10)
        
        self.wait_window(trial_window)
        return is_successful.get()

    def check_expiry_and_notify(self):
        expires_at_str = self.license_info.get('expires_at')
        if not expires_at_str: return False
        try:
            expiry_date = datetime.fromisoformat(expires_at_str.split('T')[0]).date()
            days_left = (expiry_date - datetime.now().date()).days
            if 0 <= days_left < 7:
                message = f"Your license expires today." if days_left == 0 else f"Your license will expire in {days_left} day{'s' if days_left != 1 else ''}."
                messagebox.showwarning("License Expiring Soon", f"{message}\nPlease renew your subscription from the website.")
                self.open_on_about_tab = True
                return True
        except (ValueError, TypeError) as e:
            print(f"Could not parse expiry date: {expires_at_str}. Error: {e}")
            if SENTRY_DSN: sentry_sdk.capture_exception(e)
        return False

    def start_automation_thread(self, key, target_func, args=()):
        if self.automation_threads.get(key) and self.automation_threads[key].is_alive():
            messagebox.showwarning("In Progress", f"The '{key}' task is already running.")
            return

        self.prevent_sleep()
        self.active_automations.add(key)
        self.stop_events[key] = threading.Event()
        
        def thread_wrapper():
            try:
                target_func(*args)
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
            self.attributes("-alpha", 0.0)
            self.active_automations.clear()
            self.allow_sleep()
            for event in self.stop_events.values():
                event.set()
            self.after(100, self.destroy)

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

    def check_for_updates_background(self):
        def _check():
            time.sleep(2)
            update_url = f"{config.MAIN_WEBSITE_URL}/version.json"
            try:
                response = requests.get(update_url, timeout=10)
                response.raise_for_status()
                data = response.json()
                latest_version = data.get("latest_version")
                
                if sys.platform == "win32":
                    url_key = "download_url_windows"
                elif sys.platform == "darwin":
                    url_key = "download_url_macos"
                else:
                    url_key = "download_url_windows"
                download_url = data.get(url_key)

                if latest_version and parse_version(latest_version) > parse_version(config.APP_VERSION):
                    self.update_info = {"status": "available", "version": latest_version, "url": download_url}
                    self.after(0, self.show_update_prompt, latest_version)
                else:
                    self.update_info = {"status": "updated", "version": latest_version, "url": download_url}
            except Exception as e:
                self.update_info['status'] = 'error'
                print(f"Update check failed: {e}")
            finally:
                self.after(0, self._update_about_tab_info)
        threading.Thread(target=_check, daemon=True).start()

    def show_update_prompt(self, version):
        # --- MODIFIED: This now switches to the "Updates" tab ---
        if messagebox.askyesno("Update Available", f"A new version ({version}) is available. Go to the 'Updates' tab to download?"):
            self.show_frame("About")
            about_tab_instance = self.tab_instances.get("About")
            if about_tab_instance:
                about_tab_instance.tab_view.set("Updates")

    def update_history(self, field_key: str, value: str):
        self.history_manager.save_entry(field_key, value)


if __name__ == '__main__':
    # Add basic logging configuration
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    try:
        app = NregaBotApp()
        app.mainloop()
    except Exception as e:
        if SENTRY_DSN:
            sentry_sdk.capture_exception(e)
        logging.critical(f"A fatal error occurred on startup: {e}", exc_info=True)
        messagebox.showerror("Fatal Startup Error", f"A critical error occurred on startup:\n\n{e}\n\nThe application will now close.")