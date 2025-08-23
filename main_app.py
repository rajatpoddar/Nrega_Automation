# main_app.py
import tkinter
from tkinter import messagebox, filedialog
import customtkinter as ctk
import threading, time, subprocess, os, webbrowser, sys, requests, json, uuid, logging, socket, shutil
from urllib.parse import urlencode
from PIL import Image
from packaging.version import parse as parse_version
from getmac import get_mac_address
from datetime import datetime
from dotenv import load_dotenv

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager

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
from tabs.del_work_alloc_tab import DelWorkAllocTab
from tabs.update_outcome_tab import UpdateOutcomeTab
from tabs.duplicate_mr_tab import DuplicateMrTab
from tabs.feedback_tab import FeedbackTab
from tabs.file_management_tab import FileManagementTab
from tabs.scheme_closing_tab import SchemeClosingTab
from tabs.emb_verify_tab import EmbVerifyTab
from tabs.resend_rejected_wg_tab import ResendRejectedWgTab

# --- PERFORMANCE IMPROVEMENT: Moved utility functions to utils.py ---
from utils import resource_path, get_data_path, get_user_downloads_path


if config.OS_SYSTEM == "Windows":
    import ctypes

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

# --- FIX: Load the custom theme BEFORE setting the appearance mode ---
ctk.set_default_color_theme(resource_path("theme.json"))
ctk.set_appearance_mode("System")


class CollapsibleFrame(ctk.CTkFrame):
    def __init__(self, parent, title="", initially_expanded=False):
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.is_expanded = initially_expanded
        self.title = title

        self.header_button = ctk.CTkButton(
            self, text=f"{self.get_arrow()} {self.title}", command=self.toggle,
            anchor="w", font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="transparent", text_color=("gray10", "gray80"), hover=False
        )
        self.header_button.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.update_visibility()

    def get_arrow(self): return "▼" if self.is_expanded else "▶"
    def toggle(self, event=None): self.is_expanded = not self.is_expanded; self.update_visibility()
    def expand(self):
        if not self.is_expanded: self.is_expanded = True; self.update_visibility()
    def collapse(self):
        if self.is_expanded: self.is_expanded = False; self.update_visibility()

    def update_visibility(self):
        self.header_button.configure(text=f"{self.get_arrow()} {self.title.upper()}")
        if self.is_expanded: self.content_frame.grid(row=1, column=0, sticky="ew", padx=(5,0))
        else: self.content_frame.grid_forget()

    def add_widget(self, widget, **pack_options):
        widget.pack(in_=self.content_frame, **pack_options); return widget


# --- FIX: Inherit from ctk.CTk to ensure themes work correctly ---
class NregaBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.attributes("-alpha", 0.0)
        self.title(f"{config.APP_NAME}"); self.geometry("1100x800"); self.minsize(1000, 700)
        self.history_manager = HistoryManager(self.get_data_path)
        self.is_licensed = False; self.license_info = {}; self.machine_id = self._get_machine_id()
        self.update_info = {"status": "Checking...", "version": None, "url": None}
        if SENTRY_DSN: sentry_sdk.set_user({"id": self.machine_id}); sentry_sdk.set_tag("os.name", config.OS_SYSTEM)
        self.driver = None; self.active_browser = None; self.open_on_about_tab = False
        self.sleep_prevention_process = None; self.is_validating_license = False
        self.active_automations = set(); self.icon_images = {}; self.automation_threads = {}
        self.stop_events = {}; self.nav_buttons = {}; self.content_frames = {}; self.tab_instances = {}
        self.button_to_category_frame = {}

        self.status_label = None
        self.server_status_indicator = None
        self.loading_animation_label = None
        self.is_animating = False

        self.header_welcome_prefix_label = None
        self.header_welcome_name_label = None
        self.header_welcome_suffix_label = None

        self._load_icon("chrome", "assets/icons/chrome.png")
        self._load_icon("firefox", "assets/icons/firefox.png")
        self._load_icon("nrega", "assets/icons/nrega.png")
        self. _load_icon("whatsapp", "assets/icons/whatsapp.png")
        self._load_icon("feedback", "assets/icons/feedback.png")
        self._load_icon("wc_extractor", "assets/icons/extractor.png")

        self.bind("<FocusIn>", self._on_window_focus)
        self.after(0, self.start_app)

    def bring_to_front(self):
        """Brings the application window to the front."""
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def set_status(self, message, color=None):
        if self.status_label:
            if color is None:
                message_lower = message.lower()
                if "running" in message_lower:
                    color = "#E53E3E"  # Red
                elif "finished" in message_lower:
                    color = "#3B82F6"  # Blue
                elif "ready" in message_lower:
                    color = "#38A169"  # Green
                else:
                    color = "gray50"
            
            self.status_label.configure(text=f"Status: {message}", text_color=color)

            if "running" in message.lower():
                if not self.is_animating:
                    self.is_animating = True
                    self._animate_loading_icon()
            else:
                self.is_animating = False

    def _animate_loading_icon(self, frame_index=0):
        if not self.is_animating:
            if self.loading_animation_label:
                self.loading_animation_label.configure(text="")
            return

        frames = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
        if self.loading_animation_label:
            self.loading_animation_label.configure(text=frames[frame_index])

        next_frame_index = (frame_index + 1) % len(frames)
        self.after(80, self._animate_loading_icon, next_frame_index)

    def set_server_status(self, is_connected: bool):
        if self.server_status_indicator:
            color = "green" if is_connected else "red"
            self.server_status_indicator.configure(fg_color=color)
        
    def start_app(self):
        self.splash = self._create_splash_screen()
        # --- PERFORMANCE IMPROVEMENT: Initialize app in a background thread ---
        threading.Thread(target=self._initialize_app, daemon=True).start()


    def _initialize_app(self):
        # --- This now runs in a background thread, so we use `self.after` to schedule UI updates ---
        self.after(0, self._setup_main_window)
        self.after(200, self._destroy_splash)

        self.perform_license_check_flow()
        
        self.after(500, self.run_onboarding_if_needed)

    def _setup_main_window(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._create_header()
        self._create_footer()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.deiconify()
        self.attributes("-alpha", 1.0)
        self.set_status("Initializing...")
    
    def _destroy_splash(self):
        if self.splash:
            self.splash.destroy()
            self.splash = None

    def run_onboarding_if_needed(self):
        first_run_flag_path = get_data_path('.first_run_complete')
        if not os.path.exists(first_run_flag_path):
            self.show_onboarding_guide()
            try:
                with open(first_run_flag_path, 'w') as f:
                    f.write(datetime.now().isoformat())
            except Exception as e:
                print(f"Could not write first run flag file: {e}")

    def show_onboarding_guide(self):
        messagebox.showinfo(
            "Welcome to NREGA Bot!",
            "Welcome! This quick guide will show you how to get started."
        )
        messagebox.showinfo(
            "Step 1: Launch a Browser",
            "First, click one of the 'Launch' buttons at the top right to open a special browser window.\n\n"
            "We recommend using Chrome for the best experience."
        )
        messagebox.showinfo(
            "Step 2: Log In to the Portal",
            "In the new browser window that opens, log in to the NREGA portal with your credentials, just like you normally would."
        )
        messagebox.showinfo(
            "Step 3: Choose Your Task",
            "Once you are logged in, come back to this app and select the task you want to automate from the list on the left."
        )
        messagebox.showinfo(
            "You're All Set!",
            "Now you can fill in the required details for your chosen task and click 'Start Automation'. Enjoy the magic!\n\n"
            "For more detailed instructions, please visit our website from the link in the footer."
        )

    def _create_splash_screen(self):
        splash = ctk.CTkToplevel(self)
        splash.overrideredirect(True)
        splash_width, splash_height = 300, 200
        screen_width, screen_height = splash.winfo_screenwidth(), splash.winfo_screenheight()
        x, y = (screen_width / 2) - (splash_width / 2), (screen_height / 2) - (splash_height / 2)
        splash.geometry(f'{splash_width}x{splash_height}+{int(x)}+{int(y)}')
        try:
            logo_image = ctk.CTkImage(Image.open(resource_path("logo.png")), size=(80, 80))
            ctk.CTkLabel(splash, image=logo_image, text="").pack(pady=(20, 10))
        except Exception: pass
        ctk.CTkLabel(splash, text=f"{config.APP_NAME}\nLoading...", font=("SF Pro Display", 14)).pack()
        splash.lift(); splash.attributes("-topmost", True)
        return splash

    def perform_license_check_flow(self):
        self.is_licensed = self.check_license()
        if self.is_licensed:
            self.after(0, self._setup_licensed_ui)
        else:
            self.after(0, self._setup_unlicensed_ui)

    def _setup_licensed_ui(self):
        self._create_main_layout()
        is_expiring = self.check_expiry_and_notify()
        self._ping_server_in_background()
        self._unlock_app()
        self.after(100, self._update_about_tab_info)
        first_tab_name = list(list(self.get_tabs_definition().values())[0].keys())[0]
        self.show_frame("About" if is_expiring else first_tab_name)
        self.check_for_updates_background()
        self.set_status("Ready")

    def _setup_unlicensed_ui(self):
        self._create_main_layout(for_activation=True)
        self._lock_app_to_about_tab()
        if self.show_activation_window():
            self.is_licensed = True
            for widget in self.main_layout_frame.winfo_children(): widget.destroy()
            self._setup_licensed_ui()
        else:
            self.destroy()

    def _ping_server_in_background(self):
        if not self.license_info.get('key'):
            self.after(0, self.set_server_status, False)
            return
        def ping():
            try:
                requests.post(f"{config.LICENSE_SERVER_URL}/validate", json={"key": self.license_info['key'], "machine_id": self.machine_id}, timeout=10)
                self.after(0, self.set_server_status, True)
            except requests.exceptions.RequestException:
                self.after(0, self.set_server_status, False)
        threading.Thread(target=ping, daemon=True).start()

    def _on_window_focus(self, event=None):
        if self.is_licensed and not self.is_validating_license:
            threading.Thread(target=self._validate_in_background, daemon=True).start()

    def _validate_in_background(self):
        try:
            self.is_validating_license = True
            is_valid = self.validate_on_server(self.license_info['key'], is_startup_check=True)
            if is_valid:
                self.after(0, self._update_about_tab_info)
                
                file_manager_tab = self.tab_instances.get("File Manager")
                if file_manager_tab:
                    self.after(0, lambda: file_manager_tab.update_storage_info(self.license_info.get('total_usage'), self.license_info.get('max_storage')))
                    self.after(0, lambda: file_manager_tab.refresh_files(file_manager_tab.current_folder_id, add_to_history=False))
        finally:
            self.is_validating_license = False

    def check_license(self):
        license_file = get_data_path('license.dat')
        if not os.path.exists(license_file): return False
        try:
            with open(license_file, 'r', encoding='utf-8') as f: self.license_info = json.load(f)
            if 'key' not in self.license_info or 'expires_at' not in self.license_info: raise ValueError("Invalid license file")
            expiry_date = datetime.fromisoformat(self.license_info['expires_at'].split('T')[0]).date()
            if expiry_date >= datetime.now().date(): return True
            else: return self.validate_on_server(self.license_info.get('key'), is_startup_check=True)
        except Exception:
            if os.path.exists(license_file): os.remove(license_file)
            return False

    def _lock_app_to_about_tab(self):
        self.show_frame("About")
        for name, button in self.nav_buttons.items():
            if name != "About": button.configure(state="disabled")
        self.launch_chrome_btn.configure(state="disabled")
        self.launch_firefox_btn.configure(state="disabled")
        self.theme_combo.configure(state="disabled")

    def _unlock_app(self):
        for button in self.nav_buttons.values(): button.configure(state="normal")
        self.launch_chrome_btn.configure(state="normal")
        self.launch_firefox_btn.configure(state="normal")
        self.theme_combo.configure(state="normal")

    def get_data_path(self, filename): return get_data_path(filename)
    def get_user_downloads_path(self): return get_user_downloads_path()
    def open_folder(self, path):
        try:
            if os.path.exists(path):
                if sys.platform == "win32": os.startfile(path)
                elif sys.platform == "darwin": subprocess.call(["open", path])
                else: subprocess.call(["xdg-open", path])
        except Exception as e: messagebox.showerror("Error", f"Could not open folder: {e}")

    def _load_icon(self, name, path, size=(20, 20)):
        try:
            self.icon_images[name] = ctk.CTkImage(Image.open(resource_path(path)), size=size)
        except Exception as e: print(f"Warning: Could not load icon '{name}': {e}")

    def launch_chrome_detached(self):
        port, profile_dir = "9222", os.path.join(os.path.expanduser("~"), "ChromeProfileForNREGABot")
        os.makedirs(profile_dir, exist_ok=True)
        paths = {"Darwin": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"], "Windows": ["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"]}
        browser_path = next((p for p in paths.get(config.OS_SYSTEM, []) if os.path.exists(p)), None)
        if not browser_path: messagebox.showerror("Error", "Google Chrome not found."); return
        try:
            cmd = [browser_path, f"--remote-debugging-port={port}", f"--user-data-dir={profile_dir}", config.MAIN_WEBSITE_URL, "https://bookmark.nregabot.com/"]
            creation_flags = 0x00000008 if config.OS_SYSTEM == "Windows" else 0
            subprocess.Popen(cmd, creationflags=creation_flags, start_new_session=(config.OS_SYSTEM != "Windows"))
            messagebox.showinfo("Chrome Launched", "Chrome is starting. Please log in to the NREGA website.")
        except Exception as e: messagebox.showerror("Error", f"Failed to launch Chrome:\n{e}")

    def launch_firefox_managed(self):
        if self.driver and messagebox.askyesno("Browser Running", "Close existing Firefox session and start a new one?"):
            self.driver.quit(); self.driver = None
        elif self.driver: return
        try:
            profile_dir = os.path.join(os.path.expanduser("~"), "FirefoxProfileForNREGABot")
            os.makedirs(profile_dir, exist_ok=True)
            options = FirefoxOptions(); options.add_argument("-profile"); options.add_argument(profile_dir)
            self.driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
            self.active_browser = "firefox"
            messagebox.showinfo("Browser Launched", "Firefox is starting. Please log in to the NREGA website.")
            self.driver.get(config.MAIN_WEBSITE_URL)
            self.driver.execute_script("window.open(arguments[0], '_blank');", "https://bookmark.nregabot.com/")
            self.driver.switch_to.window(self.driver.window_handles[0])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch Firefox:\n{e}"); self.driver = None; self.active_browser = None

    def get_driver(self):
        firefox_active = False
        if self.driver:
            try: _ = self.driver.window_handles; firefox_active = True
            except WebDriverException: self.driver = None
        chrome_active = False
        try:
            with socket.create_connection(("127.0.0.1", 9222), timeout=0.1): chrome_active = True
        except (socket.timeout, ConnectionRefusedError): pass
        
        if firefox_active and chrome_active:
            self.active_browser = "firefox"; return self.driver
        elif firefox_active: self.active_browser = "firefox"; return self.driver
        elif chrome_active: return self._connect_to_chrome()
        else: messagebox.showerror("Connection Failed", "No browser is running. Please launch one first."); return None
    
    def _connect_to_chrome(self):
        try:
            options = ChromeOptions(); options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            driver = webdriver.Chrome(options=options); self.active_browser = 'chrome'; return driver
        except WebDriverException as e: messagebox.showerror("Connection Failed", f"Could not connect to Chrome.\nError: {e}"); return None

    def _get_machine_id(self):
        try: return get_mac_address() or "unknown-" + str(uuid.getnode())
        except Exception: return "error-mac"

    def _create_header(self):
        header = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20,0))
        try:
            logo = ctk.CTkImage(Image.open(resource_path("logo.png")), size=(50, 50))
            ctk.CTkLabel(header, image=logo, text="").pack(side="left", padx=(0, 15))
        except Exception: pass
        
        title_frame = ctk.CTkFrame(header, fg_color="transparent"); title_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(title_frame, text=config.APP_NAME, font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w")
        
        welcome_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
        welcome_frame.pack(anchor="w")

        self.header_welcome_prefix_label = ctk.CTkLabel(welcome_frame, text=f"v{config.APP_VERSION} | Log in, then select a task.", anchor="w")
        self.header_welcome_prefix_label.pack(side="left")

        self.header_welcome_name_label = ctk.CTkLabel(welcome_frame, text="", anchor="w")
        self.header_welcome_name_label.pack(side="left")

        self.header_welcome_suffix_label = ctk.CTkLabel(welcome_frame, text="", anchor="w")
        self.header_welcome_suffix_label.pack(side="left")
        
        controls = ctk.CTkFrame(header, fg_color="transparent"); controls.pack(side="right")
        
        self.extractor_btn = ctk.CTkButton(controls, text="Workcode Extractor", image=self.icon_images.get("wc_extractor"), command=lambda: self.show_frame("Workcode Extractor"), width=160)
        self.extractor_btn.pack(side="left", padx=(0,10))

        self.launch_chrome_btn = ctk.CTkButton(controls, text="Launch Chrome", image=self.icon_images.get("chrome"), command=self.launch_chrome_detached, width=140)
        self.launch_chrome_btn.pack(side="left", padx=(0,5))
        self.launch_firefox_btn = ctk.CTkButton(controls, text="Launch Firefox", image=self.icon_images.get("firefox"), command=self.launch_firefox_managed, width=140)
        self.launch_firefox_btn.pack(side="left", padx=(0,10))
        
        theme_frame = ctk.CTkFrame(controls, fg_color="transparent"); theme_frame.pack(side="left", padx=10, fill="y")
        ctk.CTkLabel(theme_frame, text="Theme:").pack(side="left", padx=(0, 5))
        self.theme_combo = ctk.CTkOptionMenu(theme_frame, values=["System", "Light", "Dark"], command=self.on_theme_change); self.theme_combo.pack(side="left")

    def _update_header_welcome_message(self):
        if not self.header_welcome_prefix_label: return

        user_name = self.license_info.get('user_name')
        key_type = self.license_info.get('key_type')

        if user_name:
            self.header_welcome_prefix_label.configure(text=f"v{config.APP_VERSION} | Welcome, ")
            self.header_welcome_name_label.configure(text=user_name)
            self.header_welcome_suffix_label.configure(text="!")

            if key_type != 'trial':
                self.header_welcome_name_label.configure(
                    text_color=("gold4", "#FFD700"), 
                    font=ctk.CTkFont(size=13, weight="bold")
                )
            else:
                default_color = ctk.ThemeManager.theme["CTkLabel"]["text_color"]
                self.header_welcome_name_label.configure(
                    text_color=default_color, 
                    font=ctk.CTkFont(size=13, weight="normal")
                )
        else:
            self.header_welcome_prefix_label.configure(text=f"v{config.APP_VERSION} | Log in, then select a task.")
            self.header_welcome_name_label.configure(text="")
            self.header_welcome_suffix_label.configure(text="")


    def _create_main_layout(self, for_activation=False):
        self.main_layout_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_layout_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10,0))
        self.main_layout_frame.grid_rowconfigure(0, weight=1); self.main_layout_frame.grid_columnconfigure(1, weight=1)
        
        nav_scroll_frame = ctk.CTkScrollableFrame(self.main_layout_frame, width=200, label_text="", fg_color="transparent")
        nav_scroll_frame.grid(row=0, column=0, sticky="nsw", padx=(0,5))
        self._create_nav_buttons(nav_scroll_frame)
        
        self.content_area = ctk.CTkFrame(self.main_layout_frame, fg_color="transparent"); self.content_area.grid(row=0, column=1, sticky="nsew")
        self.content_area.grid_rowconfigure(0, weight=1); self.content_area.grid_columnconfigure(0, weight=1)
        self._create_content_frames(for_activation)

    def _create_nav_buttons(self, parent):
        self.nav_buttons = {}
        self.button_to_category_frame = {}
        
        all_tabs_by_key = {
            data["key"]: {"name": name, **data}
            for category, tabs in self.get_tabs_definition().items()
            for name, data in tabs.items() if "key" in data
        }

        most_used_keys = self.history_manager.get_most_used_keys()
        if most_used_keys:
            most_used_frame = CollapsibleFrame(parent, title="Most Used", initially_expanded=True)
            most_used_frame.pack(fill="x", pady=0, padx=0)
            for key in most_used_keys:
                if key in all_tabs_by_key:
                    tab_data = all_tabs_by_key[key]
                    name = tab_data["name"]
                    btn = ctk.CTkButton(
                        most_used_frame.content_frame, text=f" {tab_data['icon']}  {name}",
                        command=lambda n=name: self.show_frame(n), anchor="w",
                        font=ctk.CTkFont(size=13), height=32, corner_radius=6,
                        fg_color="transparent", text_color=("gray10", "gray90"),
                        hover_color=("gray75", "gray25")
                    )
                    btn.pack(fill="x", padx=5, pady=2)
                    self.nav_buttons[name] = btn
                    self.button_to_category_frame[name] = most_used_frame

        is_first_category = True
        for category, tabs in self.get_tabs_definition().items():
            should_expand = is_first_category and not most_used_keys
            
            category_frame = CollapsibleFrame(parent, title=category, initially_expanded=should_expand)
            category_frame.pack(fill="x", pady=0, padx=0)
            
            for name, data in tabs.items():
                if name not in self.nav_buttons:
                    btn = ctk.CTkButton(
                        category_frame.content_frame, text=f" {data['icon']}  {name}",
                        command=lambda n=name: self.show_frame(n), anchor="w",
                        font=ctk.CTkFont(size=13), height=32, corner_radius=6,
                        fg_color="transparent", text_color=("gray10", "gray90"),
                        hover_color=("gray75", "gray25")
                    )
                    btn.pack(fill="x", padx=5, pady=2)
                    self.nav_buttons[name] = btn
                
                self.button_to_category_frame[name] = category_frame
            is_first_category = False

    def _create_content_frames(self, for_activation=False):
        self.content_frames = {}
        self.tab_instances = {}
        tabs_to_create = {"Application": self.get_tabs_definition()["Application"]} if for_activation else self.get_tabs_definition()

        for category, tabs in tabs_to_create.items():
            for name, data in tabs.items():
                # --- LAZY LOADING: Only create the frame container ---
                frame_container = ctk.CTkFrame(self.content_area, fg_color="transparent")
                frame_container.grid(row=0, column=0, sticky="nsew")
                self.content_frames[name] = frame_container
                # --- The tab instance will be created in `show_frame` ---

    def get_tabs_definition(self):
        return {
            "Core NREGA Tasks": {
                "MR Gen": {"creation_func": MusterrollGenTab, "icon": config.ICONS["MR Gen"], "key": "muster"},
                "MR Payment": {"creation_func": MsrTab, "icon": config.ICONS["MR Payment"], "key": "msr"},
                "Gen Wagelist": {"creation_func": WagelistGenTab, "icon": config.ICONS["Gen Wagelist"], "key": "gen"},
                "Send Wagelist": {"creation_func": WagelistSendTab, "icon": config.ICONS["Send Wagelist"], "key": "send"},
                "FTO Generation": {"creation_func": FtoGenerationTab, "icon": config.ICONS["FTO Generation"], "key": "fto_gen"},
                "eMB Entry⚠️": {"creation_func": MbEntryTab, "icon": config.ICONS["eMB Entry"], "key": "mb_entry"},
                "eMB Verify": {"creation_func": EmbVerifyTab, "icon": config.ICONS["eMB Verify"], "key": "emb_verify"},
                "Scheme Closing": {"creation_func": SchemeClosingTab, "icon": "🏁", "key": "scheme_close"},
                "Del Work Alloc": {"creation_func": DelWorkAllocTab, "icon": "🗑️", "key": "del_work_alloc"},
                "Duplicate MR Print": {"creation_func": DuplicateMrTab, "icon": config.ICONS["Duplicate MR Print"], "key": "dup_mr"},
            },
            "Records & Workcode": {
                "WC Gen": {"creation_func": WcGenTab, "icon": config.ICONS["WC Gen (Abua)"], "key": "wc_gen"},
                "IF Editor": {"creation_func": IfEditTab, "icon": config.ICONS["IF Editor (Abua)"], "key": "if_edit"},
                "Add Activity": {"creation_func": AddActivityTab, "icon": config.ICONS["Add Activity"], "key": "add_activity"},
            },
            "Utilities & Verification": {
                "Verify Jobcard": {"creation_func": JobcardVerifyTab, "icon": config.ICONS["Verify Jobcard"], "key": "jc_verify"},
                "Verify ABPS": {"creation_func": AbpsVerifyTab, "icon": config.ICONS["Verify ABPS"], "key": "abps_verify"},
                "Workcode Extractor": {"creation_func": WorkcodeExtractorTab, "icon": config.ICONS["Workcode Extractor"], "key": "wc_extract"},
                "Resend Rejected WG": {"creation_func": ResendRejectedWgTab, "icon": config.ICONS["Resend Rejected WG"], "key": "resend_wg"},
                "Update Outcome": {"creation_func": UpdateOutcomeTab, "icon": config.ICONS["Update Outcome"], "key": "update_outcome"},
                "File Manager": {"creation_func": FileManagementTab, "icon": config.ICONS["File Manager"], "key": "file_manager"},
            },
            "Application": {
                 "Feedback": {"creation_func": FeedbackTab, "icon": config.ICONS["Feedback"]},
                 "About": {"creation_func": AboutTab, "icon": config.ICONS["About"]},
            }
        }

    def show_frame(self, page_name):
        # --- LAZY LOADING: Create tab instance on demand ---
        if page_name not in self.tab_instances:
            tabs_definition = self.get_tabs_definition()
            for category, tabs in tabs_definition.items():
                if page_name in tabs:
                    data = tabs[page_name]
                    tab_instance = data["creation_func"](self.content_frames[page_name], self)
                    tab_instance.pack(expand=True, fill="both")
                    self.tab_instances[page_name] = tab_instance
                    break
        
        if page_name in self.button_to_category_frame:
            self.button_to_category_frame[page_name].expand()
            
        self.content_frames[page_name].tkraise()
        for name, button in self.nav_buttons.items():
            button.configure(fg_color=("gray90", "gray28") if name == page_name else "transparent")
    
    def _create_footer(self):
        footer = ctk.CTkFrame(self, height=40, corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 15))
        footer.grid_columnconfigure(0, weight=0)
        footer.grid_columnconfigure(1, weight=0)
        footer.grid_columnconfigure(2, weight=1)
        footer.grid_columnconfigure(3, weight=0)

        left_frame = ctk.CTkFrame(footer, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="w", padx=15)
        ctk.CTkLabel(left_frame, text="© 2025 NREGA Bot", text_color="gray50").pack(side="left")
        
        status_frame = ctk.CTkFrame(footer, fg_color="transparent")
        status_frame.grid(row=0, column=1, columnspan=2, sticky="ew", padx=20)
        
        self.loading_animation_label = ctk.CTkLabel(status_frame, text="", width=20, font=ctk.CTkFont(size=14))
        self.loading_animation_label.pack(side="left")
        
        self.status_label = ctk.CTkLabel(status_frame, text="Status: Ready", text_color="gray50", anchor="w")
        self.status_label.pack(side="left")

        button_container = ctk.CTkFrame(footer, fg_color="transparent")
        button_container.grid(row=0, column=3, sticky="e", padx=15)

        nrega_btn = ctk.CTkButton(button_container, text="NREGA Bot Website ↗", image=self.icon_images.get("nrega"), command=lambda: webbrowser.open_new_tab(config.MAIN_WEBSITE_URL), fg_color="transparent", hover=False, text_color=("gray10", "gray80"))
        nrega_btn.pack(side="left")

        community_btn = ctk.CTkButton(button_container, text="Community", image=self.icon_images.get("whatsapp"), command=lambda: webbrowser.open_new_tab("https://chat.whatsapp.com/Bup3hDCH3wn2shbUryv8wn"), fg_color="transparent", hover=False, text_color=("gray10", "gray80"))
        community_btn.pack(side="left", padx=(10, 0))

        support_btn = ctk.CTkButton(button_container, text="Contact Support", image=self.icon_images.get("feedback"), command=lambda: self.show_frame("Feedback"), fg_color="transparent", hover=False, text_color=("gray10", "gray80"))
        support_btn.pack(side="left", padx=(10, 0))

        self.server_status_indicator = ctk.CTkFrame(button_container, width=12, height=12, corner_radius=6, fg_color="gray")
        self.server_status_indicator.pack(side="left", padx=(10, 5))
        ctk.CTkLabel(button_container, text="Server").pack(side="left")

        self.set_status("Ready")

    def save_demo_csv(self, file_type: str):
        try:
            source_path = resource_path(f"assets/demo_{file_type}.csv")
            if not os.path.exists(source_path):
                messagebox.showerror("Error", f"Demo file not found: demo_{file_type}.csv")
                return
            save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], initialfile=f"{file_type}_data.csv", title=f"Save Demo {file_type.upper()} CSV")
            if save_path:
                shutil.copyfile(source_path, save_path)
                messagebox.showinfo("Success", f"Demo file saved to:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save demo file: {e}")

    def on_theme_change(self, new_theme: str): ctk.set_appearance_mode(new_theme); self.after(100, self.restyle_all_treeviews)
    def restyle_all_treeviews(self):
        for tab in self.tab_instances.values():
            if hasattr(tab, 'style_treeview') and hasattr(tab, 'results_tree'): tab.style_treeview(tab.results_tree)
            if hasattr(tab, 'style_treeview') and hasattr(tab, 'files_tree'): tab.style_treeview(tab.files_tree)
    
    def _update_about_tab_info(self):
        self._update_header_welcome_message()
        try:
            about_tab = self.tab_instances.get("About")
            if about_tab:
                about_tab.update_subscription_details(self.license_info)
                info = self.update_info
                if info['status'] == 'available':
                    about_tab.latest_version_label.configure(text=f"Latest Version: {info['version']}")
                    about_tab.update_button.configure(text=f"Download & Install v{info['version']}", state="normal", command=lambda: about_tab.download_and_install_update(info['url'], info['version']))
                    about_tab.show_new_version_changelog(info.get('changelog', []))
                elif info['status'] == 'updated':
                    about_tab.latest_version_label.configure(text=f"Latest Version: {config.APP_VERSION}")
                    about_tab.update_button.configure(text="You are up to date", state="disabled")
                    about_tab.hide_new_version_changelog()
                else:
                    about_tab.latest_version_label.configure(text=f"Latest Version: {info['status'].capitalize()}"); about_tab.update_button.configure(text="Check for Updates", state="normal")
                    about_tab.hide_new_version_changelog()
        except Exception: pass

    def validate_on_server(self, key, is_startup_check=False):
        try:
            response = requests.post(f"{config.LICENSE_SERVER_URL}/api/validate", json={"key": key, "machine_id": self.machine_id}, timeout=10)
            self.after(0, self.set_server_status, True)
            data = response.json()
            if response.status_code == 200 and data.get("status") == "valid":
                self.license_info = data
                self.license_info['key'] = key
                with open(get_data_path('license.dat'), 'w') as f: json.dump(self.license_info, f)
                if not is_startup_check: messagebox.showinfo("License Valid", f"Activation successful!\nExpires on: {self.license_info['expires_at'].split('T')[0]}")
                return True
            else:
                if not is_startup_check: messagebox.showerror("Validation Failed", data.get('reason', 'Unknown error.'))
                return False
        except requests.exceptions.RequestException as e:
            self.after(0, self.set_server_status, False)
            if not is_startup_check: messagebox.showerror("Connection Error", f"Could not connect to license server: {e}")
            return False
        except json.JSONDecodeError:
            self.after(0, self.set_server_status, False)
            if not is_startup_check: messagebox.showerror("Connection Error", f"Could not connect to the license server: Expecting value: line 1 column 1 (char 0)")
            return False


    def show_activation_window(self):
        activation_window = ctk.CTkToplevel(self); activation_window.title("Activate Product")
        win_width, win_height = 450, 500; x, y = (self.winfo_screenwidth() // 2) - (win_width // 2), (self.winfo_screenheight() // 2) - (win_height // 2)
        activation_window.geometry(f'{win_width}x{win_height}+{x}+{y}'); activation_window.resizable(False, False); activation_window.transient(self); activation_window.grab_set()
        main_frame = ctk.CTkFrame(activation_window, fg_color="transparent"); main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        ctk.CTkLabel(main_frame, text="Product Activation", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0, 10))
        is_activated = tkinter.BooleanVar(value=False)
        tab_view = ctk.CTkTabview(main_frame); tab_view.pack(expand=True, fill="both"); tab_view.add("New User"); tab_view.add("Existing User")
        new_user_tab = tab_view.tab("New User")
        def open_trial_form():
            activation_window.withdraw()
            if self.show_trial_registration_window(): is_activated.set(True); activation_window.destroy()
            else: activation_window.deiconify()
        ctk.CTkButton(new_user_tab, text="Start 30-Day Free Trial", command=open_trial_form).pack(pady=(20, 5), ipady=4, fill='x', padx=10)
        ctk.CTkLabel(new_user_tab, text="— OR —").pack(pady=10); ctk.CTkLabel(new_user_tab, text="Enter a purchased license key:").pack(pady=(5, 5))
        key_entry = ctk.CTkEntry(new_user_tab, width=300); key_entry.pack(pady=5, padx=10, fill='x')
        def on_activate_paid():
            key = key_entry.get().strip()
            if not key: messagebox.showwarning("Input Required", "Please enter a license key.", parent=activation_window); return
            if self.validate_on_server(key): is_activated.set(True); activation_window.destroy()
        ctk.CTkButton(new_user_tab, text="Activate with Key", command=on_activate_paid).pack(pady=10, ipady=4, fill='x', padx=10)
        existing_user_tab = tab_view.tab("Existing User")
        ctk.CTkLabel(existing_user_tab, text="Already have a license? Activate this device by logging in with your registered email.", wraplength=380, justify="center").pack(pady=(20, 15))
        email_entry_login = ctk.CTkEntry(existing_user_tab, placeholder_text="Enter your registered email"); email_entry_login.pack(pady=5, fill='x', padx=10); email_entry_login.focus_set()
        def on_login_activate():
            email = email_entry_login.get().strip()
            if not email: messagebox.showwarning("Input Required", "Please enter your email address.", parent=activation_window); return
            login_btn.configure(state="disabled", text="Activating...")
            try:
                response = requests.post(f"{config.LICENSE_SERVER_URL}/api/login-for-activation", json={"email": email, "machine_id": self.machine_id}, timeout=15)
                data = response.json()
                if response.status_code == 200 and data.get("status") == "success":
                    self.license_info = data
                    with open(get_data_path('license.dat'), 'w') as f: json.dump(self.license_info, f)
                    messagebox.showinfo("Activation Successful", f"Device activated successfully!\nWelcome back, {data.get('user_name', 'User')}.")
                    is_activated.set(True); activation_window.destroy()
                else: messagebox.showerror("Activation Failed", data.get("reason", "An unknown error occurred."), parent=activation_window)
            except requests.exceptions.RequestException as e: messagebox.showerror("Connection Error", f"Could not connect to the license server: {e}", parent=activation_window)
            finally:
                if login_btn.winfo_exists(): login_btn.configure(state="normal", text="Login & Activate Device")
        login_btn = ctk.CTkButton(existing_user_tab, text="Login & Activate Device", command=on_login_activate); login_btn.pack(pady=15, ipady=4, fill='x', padx=10)
        links_frame = ctk.CTkFrame(main_frame, fg_color="transparent"); links_frame.pack(pady=(15,0), fill="x")
        buy_link_label = ctk.CTkLabel(links_frame, text="Purchase a License Key", text_color=("blue", "cyan"), cursor="hand2"); buy_link_label.pack()
        buy_link_label.bind("<Button-1>", lambda e: webbrowser.open_new_tab(f"{config.LICENSE_SERVER_URL}/buy"))
        self.wait_window(activation_window)
        return is_activated.get()

    def show_trial_registration_window(self):
        trial_window = ctk.CTkToplevel(self); trial_window.title("Trial Registration")
        win_width, win_height = 480, 600; x, y = (self.winfo_screenwidth() // 2) - (win_width // 2), (self.winfo_screenheight() // 2) - (win_height // 2)
        trial_window.geometry(f'{win_width}x{win_height}+{x}+{y}'); trial_window.resizable(False, False); trial_window.transient(self); trial_window.grab_set()
        scroll_frame = ctk.CTkScrollableFrame(trial_window, fg_color="transparent", label_fg_color="transparent"); scroll_frame.pack(expand=True, fill="both", padx=10, pady=10)
        ctk.CTkLabel(scroll_frame, text="Start Your Free Trial", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0, 5))
        ctk.CTkLabel(scroll_frame, text="Please provide your details to begin.", text_color="gray50").pack(pady=(0, 15))
        entries = {}; fields = ["Full Name", "Email", "Mobile", "Block", "District", "State", "Pincode"]
        for field in fields:
            key = field.lower().replace(" ", "_"); ctk.CTkLabel(scroll_frame, text=field, anchor="w").pack(fill="x", padx=10)
            entry = ctk.CTkEntry(scroll_frame); entry.pack(fill="x", padx=10, pady=(0, 10)); entries[key] = entry
        is_successful = tkinter.BooleanVar(value=False)
        def submit_trial_request():
            import re
            user_data = {key: entry.get().strip() for key, entry in entries.items()}
            
            email = user_data.get('email', '')
            mobile = user_data.get('mobile', '')

            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                messagebox.showwarning("Invalid Input", "Please enter a valid email address.", parent=trial_window)
                return
            
            if not (mobile.isdigit() and len(mobile) == 10):
                messagebox.showwarning("Invalid Input", "Please enter a valid 10-digit mobile number.", parent=trial_window)
                return

            user_data["name"] = user_data.pop("full_name"); user_data["machine_id"] = self.machine_id
            if not all(user_data.values()): messagebox.showwarning("Input Required", "All fields are required to start a trial.", parent=trial_window); return
            submit_btn.configure(state="disabled", text="Requesting...")
            try:
                response = requests.post(f"{config.LICENSE_SERVER_URL}/api/request-trial", json=user_data, timeout=15, headers={'User-Agent': f'{config.APP_NAME}/{config.APP_VERSION}'})
                data = response.json()
                if response.status_code == 200 and data.get("status") == "success":
                    self.license_info = {'key': data.get("key"), 'expires_at': data.get('expires_at'), 'user_name': user_data['name'], 'key_type': 'trial'}
                    with open(get_data_path('license.dat'), 'w') as f: json.dump(self.license_info, f)
                    success_reason = data.get("reason", "Your 30-day free trial has started!")
                    messagebox.showinfo("Success!", f"{success_reason}\nExpires on: {self.license_info['expires_at'].split('T')[0]}")
                    is_successful.set(True); trial_window.destroy()
                else: messagebox.showerror("Trial Error", data.get("reason", "Could not start trial."), parent=trial_window)
            except requests.exceptions.RequestException: messagebox.showerror("Connection Error", "Could not connect to the server to start a trial.", parent=trial_window)
            finally: 
                if submit_btn.winfo_exists():
                    submit_btn.configure(state="normal", text="Start Trial")
        submit_btn = ctk.CTkButton(scroll_frame, text="Start Trial", command=submit_trial_request); submit_btn.pack(pady=20, ipady=4, fill='x', padx=10)
        self.wait_window(trial_window)
        return is_successful.get()

    def show_purchase_window(self, context='upgrade'):
        purchase_window = ctk.CTkToplevel(self)
        title = "Renew Subscription" if context == 'renew' else "Upgrade to Full License"
        purchase_window.title(title)
        win_width, win_height = 480, 420
        x, y = (self.winfo_screenwidth()//2) - (win_width//2), (self.winfo_screenheight()//2) - (win_height//2)
        purchase_window.geometry(f'{win_width}x{win_height}+{x}+{y}')
        purchase_window.resizable(False, False)
        purchase_window.transient(self)
        purchase_window.grab_set()

        main_frame = ctk.CTkFrame(purchase_window, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        ctk.CTkLabel(main_frame, text=title, font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0, 15))
        ctk.CTkLabel(main_frame, text="1. Choose Your Plan", font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(fill="x", padx=10, pady=(10,5))
        
        plan_options = [
            "Monthly Plan (₹99 / device)",
            "Quarterly Plan (₹289 / device)",
            "Half Yearly Plan (₹569 / device)",
            "Yearly Plan (₹999 / device)"
        ]
        plan_menu = ctk.CTkOptionMenu(main_frame, values=plan_options)
        plan_menu.pack(fill="x", padx=10, pady=(0,5))

        ctk.CTkLabel(main_frame, text="Number of Devices:", anchor="w").pack(fill="x", padx=10, pady=(15, 5))
        devices_input = ctk.CTkOptionMenu(main_frame, values=["1", "2", "3"])
        devices_input.set(str(self.license_info.get('max_devices', 1)))
        devices_input.pack(fill="x", padx=10)

        prices = {"monthly": 99, "quarterly": 289, "half_yearly": 569, "yearly": 999}
        total_price_label = ctk.CTkLabel(main_frame, text="Total: ₹99", font=ctk.CTkFont(size=18, weight="bold"))
        total_price_label.pack(pady=25)
        
        def update_price(*args):
            plan_selection = plan_menu.get().lower()
            plan_key = "monthly" 
            if "yearly" in plan_selection: plan_key = "yearly"
            if "half yearly" in plan_selection: plan_key = "half_yearly"
            if "quarterly" in plan_selection: plan_key = "quarterly"

            device_count = int(devices_input.get())
            total_price = prices[plan_key] * device_count
            total_price_label.configure(text=f"Total: ₹{total_price}")

        plan_menu.configure(command=lambda v: update_price())
        devices_input.configure(command=lambda v: update_price())
        update_price()

        def proceed_to_payment():
            submit_btn.configure(state="disabled", text="Initializing...")
            form_data = {
                "name": self.license_info.get('user_name', ''), "email": self.license_info.get('user_email', ''),
                "mobile": self.license_info.get('user_mobile', ''), "block": self.license_info.get('user_block', ''),
                "district": self.license_info.get('user_district', ''), "state": self.license_info.get('user_state', ''),
                "pincode": self.license_info.get('user_pincode', ''),
                "existing_key": self.license_info.get('key')
            }
            
            if not all([form_data['name'], form_data['email'], form_data['mobile']]):
                messagebox.showwarning("User Details Missing", "Your user details could not be found. Please contact support.", parent=purchase_window)
                submit_btn.configure(state="normal", text="Proceed to Payment"); return
            
            plan_selection = plan_menu.get().lower()
            plan_key = "monthly" 
            if "yearly" in plan_selection: plan_key = "yearly"
            if "half yearly" in plan_selection: plan_key = "half_yearly"
            if "quarterly" in plan_selection: plan_key = "quarterly"
            
            device_count = int(devices_input.get())
            form_data.update({'plan_type': plan_key, 'max_devices': device_count})

            try:
                base_url = f"{config.LICENSE_SERVER_URL}/buy"
                query_params = urlencode({k: v for k, v in form_data.items() if v is not None})
                full_url = f"{base_url}?{query_params}"
                webbrowser.open_new_tab(full_url)
                purchase_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Could not open payment page: {e}", parent=purchase_window)
            finally:
                if submit_btn.winfo_exists():
                    submit_btn.configure(state="normal", text="Proceed to Payment")

        submit_btn = ctk.CTkButton(main_frame, text="Proceed to Payment", command=proceed_to_payment)
        submit_btn.pack(pady=20, ipady=5, fill='x', padx=10)

    def check_expiry_and_notify(self):
        expires_at_str = self.license_info.get('expires_at')
        if not expires_at_str: return False
        try:
            days_left = (datetime.fromisoformat(expires_at_str.split('T')[0]).date() - datetime.now().date()).days
            if 0 <= days_left < 7:
                message = f"Your license expires today." if days_left == 0 else f"Your license will expire in {days_left} day{'s' if days_left != 1 else ''}."
                messagebox.showwarning("License Expiring Soon", f"{message}\nPlease renew your subscription from the website.")
                self.open_on_about_tab = True; return True
        except (ValueError, TypeError) as e:
            print(f"Could not parse expiry date: {expires_at_str}. Error: {e}")
            if SENTRY_DSN: sentry_sdk.capture_exception(e)
        return False
        
    def start_automation_thread(self, key, target_func, args=()):
        if self.automation_threads.get(key) and self.automation_threads[key].is_alive():
            messagebox.showwarning("In Progress", f"The task is already running."); return
        
        self.history_manager.increment_usage(key)

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
        log_widget.configure(state="normal"); log_widget.insert(tkinter.END, f"[{time.strftime('%H:%M:%S')}] {message}\n"); log_widget.configure(state="disabled"); log_widget.see(tkinter.END)
    def clear_log(self, log_widget): log_widget.configure(state="normal"); log_widget.delete("1.0", tkinter.END); log_widget.configure(state="disabled")

    def on_closing(self, force_close=False):
        do_close = force_close or messagebox.askokcancel("Quit", "Do you want to quit? This will stop any running automations.")
        if do_close:
            self.attributes("-alpha", 0.0)
            self.active_automations.clear()
            self.allow_sleep()
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as e:
                    print(f"Error quitting driver: {e}")
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
                if self.sleep_prevention_process: self.sleep_prevention_process.terminate(); self.sleep_prevention_process = None

    def on_automation_finished(self, key):
        if key in self.active_automations:
            self.active_automations.remove(key)
        
        self.set_status("Automation Finished")
        self.after(5000, lambda: self.set_status("Ready"))

        if not self.active_automations:
            self.allow_sleep()

    def check_for_updates_background(self):
        def _check():
            time.sleep(2)
            try:
                response = requests.get(f"{config.MAIN_WEBSITE_URL}/version.json", timeout=10); response.raise_for_status(); data = response.json()
                latest_version = data.get("latest_version")
                url_key = "download_url_macos" if sys.platform == "darwin" else "download_url_windows"
                download_url = data.get(url_key)
                changelog_notes = data.get("changelog", {}).get(latest_version, [])

                if latest_version and parse_version(latest_version) > parse_version(config.APP_VERSION):
                    self.update_info = {"status": "available", "version": latest_version, "url": download_url, "changelog": changelog_notes}
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
        if messagebox.askyesno("Update Available", f"A new version ({version}) is available. Go to the 'Updates' tab to download?"):
            self.show_frame("About")
            about_tab_instance = self.tab_instances.get("About")
            if about_tab_instance: about_tab_instance.tab_view.set("Updates")

    def update_history(self, field_key: str, value: str): self.history_manager.save_entry(field_key, value)

    def download_and_install_update(self, url, version):
        about_tab = self.tab_instances.get("About")
        if not about_tab:
            messagebox.showerror("Error", "Could not find the About Tab to show progress.")
            return

        about_tab.update_button.configure(state="disabled")
        about_tab.update_progress.grid(row=4, column=0, pady=(10, 10), padx=20, sticky='ew')

        def _download_worker():
            try:
                filename = url.split('/')[-1]
                download_path = os.path.join(self.get_user_downloads_path(), filename)
                
                self.after(0, lambda: about_tab.update_button.configure(text="Downloading..."))
                
                with requests.get(url, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    total_size = int(r.headers.get('content-length', 0))
                    bytes_downloaded = 0
                    with open(download_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                            bytes_downloaded += len(chunk)
                            if total_size > 0:
                                progress = bytes_downloaded / total_size
                                self.after(0, about_tab.update_progress.set, progress)
                
                self.after(0, lambda: about_tab.update_button.configure(text="Download Complete. Installing..."))
                
                if sys.platform == "win32": 
                    messagebox.showinfo(
                        "Ready to Update",
                        "The update has been downloaded. The application will now close to run the installer.",
                        parent=self
                    )
                    os.startfile(download_path)
                    self.after(200, os._exit, 0)

                elif sys.platform == "darwin": 
                    subprocess.call(["open", download_path])
                    self.after(0, messagebox.showinfo, "Installation Instructions", f"The installer '{filename}' has been downloaded and opened.\nPlease drag the NREGA Bot icon into your Applications folder.\n\nThe application will now close.")
                    self.after(3000, self.on_closing, True)

            except Exception as e:
                self.after(0, messagebox.showerror, "Update Failed", f"Could not download or run the update.\\n\\nError: {e}")
                if about_tab.winfo_exists():
                    self.after(0, lambda: about_tab.update_button.configure(state="normal", text=f"Download & Install v{version}"))
                    self.after(0, about_tab.update_progress.grid_forget)
                    self.after(0, about_tab.update_progress.set, 0)
        
        threading.Thread(target=_download_worker, daemon=True).start()

def initialize_webdriver_manager():
    """Initializes GeckoDriverManager in a background thread to avoid blocking the UI."""
    def run():
        try:
            logging.info("Checking for GeckoDriver...")
            GeckoDriverManager().install()
            logging.info("GeckoDriver is up to date.")
        except Exception as e:
            logging.error(f"Could not download/update GeckoDriver: {e}")
            # Consider showing a non-blocking error message if needed
            # For example, using a pub/sub mechanism to send a message to the main app
    threading.Thread(target=run, daemon=True).start()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # --- SINGLE INSTANCE LOCK ---
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 60123))  # Use a specific port
    except OSError:
        # Another instance is running, tell it to focus and exit.
        try:
            s.connect(("127.0.0.1", 60123))
            s.sendall(b'focus')
        except Exception as e:
            logging.error(f"Failed to send focus request: {e}")
        finally:
            s.close()
            sys.exit(0)


    initialize_webdriver_manager()
    
    try: 
        app = NregaBotApp()

        def listen_for_focus_requests():
            s.listen(1)
            while True:
                conn, addr = s.accept()
                data = conn.recv(1024)
                if data == b'focus':
                    app.after(0, app.bring_to_front)
                conn.close()

        threading.Thread(target=listen_for_focus_requests, daemon=True).start()
        
        app.mainloop()
    except Exception as e:
        if SENTRY_DSN: sentry_sdk.capture_exception(e)
        logging.critical(f"A fatal error occurred on startup: {e}", exc_info=True)
        messagebox.showerror("Fatal Startup Error", f"A critical error occurred on startup:\n\n{e}\n\nThe application will now close.")
    finally:
        s.close()