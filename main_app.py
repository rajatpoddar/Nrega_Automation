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
from tabs.update_estimate_tab import UpdateEstimateTab
from tabs.duplicate_mr_tab import DuplicateMrTab
from tabs.feedback_tab import FeedbackTab
from tabs.file_management_tab import FileManagementTab
from tabs.scheme_closing_tab import SchemeClosingTab
from tabs.emb_verify_tab import EmbVerifyTab
from tabs.resend_rejected_wg_tab import ResendRejectedWgTab
from tabs.SA_report_tab import SAReportTab
from tabs.mis_reports_tab import MisReportsTab
from tabs.demand_tab import DemandTab

from utils import resource_path, get_data_path, get_user_downloads_path, get_config, save_config

if config.OS_SYSTEM == "Windows":
    import ctypes

load_dotenv()

# --- ADD THIS LINE AFTER load_dotenv() ---
config.create_default_config_if_not_exists()

import sentry_sdk
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        release=f"{config.APP_NAME}@{config.APP_VERSION}",
        traces_sample_rate=1.0,
    )

ctk.set_default_color_theme(resource_path("theme.json"))
ctk.set_appearance_mode("System")


class CollapsibleFrame(ctk.CTkFrame):
    def __init__(self, parent, title=""):
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.title = title

        # Replaced the button with a simple, non-clickable label
        self.header_label = ctk.CTkLabel(
            self, text=self.title.upper(),
            anchor="w", font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray10", "gray80")
        )
        self.header_label.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 2))

        # Content frame is now always visible
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="ew", padx=(5, 0))

    def add_widget(self, widget, **pack_options):
        widget.pack(in_=self.content_frame, **pack_options)
        return widget


class NregaBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        # self.withdraw()
        self.attributes("-alpha", 0.0)

        self.initial_width = 1100
        self.initial_height = 800
        self.geometry(f"{self.initial_width}x{self.initial_height}")

        self.title(f"{config.APP_NAME}"); self.minsize(1000, 700)
        self.history_manager = HistoryManager(self.get_data_path)
        self.is_licensed = False; self.license_info = {}; self.machine_id = self._get_machine_id()
        self.update_info = {"status": "Checking...", "version": None, "url": None}
        if SENTRY_DSN: sentry_sdk.set_user({"id": self.machine_id}); sentry_sdk.set_tag("os.name", config.OS_SYSTEM)
        self.driver = None; self.active_browser = None; self.open_on_about_tab = False
        self.sleep_prevention_process = None; self.is_validating_license = False
        self.active_automations = set(); self.icon_images = {}; self.automation_threads = {}
        self.stop_events = {}; self.nav_buttons = {}; self.content_frames = {}; self.tab_instances = {}
        self.button_to_category_frame = {}
        self.category_frames = {}
        self.last_selected_category = get_config('last_selected_category', 'All Automations')

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
        self._load_icon("whatsapp", "assets/icons/whatsapp.png")
        self._load_icon("feedback", "assets/icons/feedback.png")
        self._load_icon("wc_extractor", "assets/icons/extractor.png")

        # --- ADD THIS SECTION FOR DISCLAIMER ICONS ---
        self._load_icon("disclaimer_warning", "assets/icons/emojis/warning.png", size=(16,16))
        self._load_icon("disclaimer_thunder", "assets/icons/emojis/thunder.png", size=(16,16))
        self._load_icon("disclaimer_tools", "assets/icons/emojis/tools.png", size=(16,16))

        self._load_icon("emoji_mr_gen", "assets/icons/emojis/mr_gen.png", size=(16,16))
        self._load_icon("emoji_mr_payment", "assets/icons/emojis/mr_payment.png", size=(16,16))
        self._load_icon("emoji_gen_wagelist", "assets/icons/emojis/gen_wagelist.png", size=(16,16))
        self._load_icon("emoji_send_wagelist", "assets/icons/emojis/send_wagelist.png", size=(16,16))
        self._load_icon("emoji_fto_gen", "assets/icons/emojis/fto_gen.png", size=(16,16))
        self._load_icon("emoji_emb_entry", "assets/icons/emojis/warning.png", size=(16,16))
        self._load_icon("emoji_emb_verify", "assets/icons/emojis/emb_verify.png", size=(16,16))
        self._load_icon("emoji_scheme_closing", "assets/icons/emojis/scheme_closing.png", size=(16,16))
        self._load_icon("emoji_del_work_alloc", "assets/icons/emojis/del_work_alloc.png", size=(16,16))
        self._load_icon("emoji_duplicate_mr", "assets/icons/emojis/duplicate_mr.png", size=(16,16))
        self._load_icon("emoji_wc_gen", "assets/icons/emojis/wc_gen.png", size=(16,16))
        self._load_icon("emoji_if_editor", "assets/icons/emojis/if_editor.png", size=(16,16))
        self._load_icon("emoji_add_activity", "assets/icons/emojis/add_activity.png", size=(16,16))
        self._load_icon("emoji_verify_jobcard", "assets/icons/emojis/verify_jobcard.png", size=(16,16))
        self._load_icon("emoji_verify_abps", "assets/icons/emojis/verify_abps.png", size=(16,16))
        self._load_icon("emoji_wc_extractor", "assets/icons/emojis/wc_extractor.png", size=(16,16))
        self._load_icon("emoji_resend_wg", "assets/icons/emojis/resend_wg.png", size=(16,16))
        self._load_icon("emoji_update_outcome", "assets/icons/emojis/update_outcome.png", size=(16,16))
        self._load_icon("emoji_file_manager", "assets/icons/emojis/file_manager.png", size=(16,16))
        self._load_icon("emoji_feedback", "assets/icons/emojis/feedback.png", size=(16,16))
        self._load_icon("emoji_about", "assets/icons/emojis/about.png", size=(16,16))
        self._load_icon("emoji_social_audit", "assets/icons/emojis/social_audit.png", size=(16,16))
        self._load_icon("emoji_mis_reports", "assets/icons/emojis/mis_reports.png", size=(16,16))
        self._load_icon("emoji_demand", "assets/icons/emojis/demand.png", size=(16,16))


        self.bind("<FocusIn>", self._on_window_focus)
        self.after(0, self.start_app)

    def bring_to_front(self):
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def set_status(self, message, color=None):
        if self.status_label:
            if color is None:
                message_lower = message.lower()
                if "running" in message_lower: color = "#E53E3E"
                elif "finished" in message_lower: color = "#3B82F6"
                elif "ready" in message_lower: color = "#38A169"
                else: color = "gray50"
            self.status_label.configure(text=f"Status: {message}", text_color=color)
            if "running" in message.lower():
                if not self.is_animating: self.is_animating = True; self._animate_loading_icon()
            else: self.is_animating = False

    def _animate_loading_icon(self, frame_index=0):
        if not self.is_animating:
            if self.loading_animation_label: self.loading_animation_label.configure(text="")
            return
        frames = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
        if self.loading_animation_label: self.loading_animation_label.configure(text=frames[frame_index])
        self.after(80, self._animate_loading_icon, (frame_index + 1) % len(frames))

    def set_server_status(self, is_connected: bool):
        if self.server_status_indicator: self.server_status_indicator.configure(fg_color="green" if is_connected else "red")

    def start_app(self):
        self.splash = self._create_splash_screen()
        # This thread will handle all the slow initialization tasks
        threading.Thread(target=self._initialize_app, daemon=True).start()

    def _initialize_app(self):
        """
        Handles slow initialization tasks in a background thread to keep the UI responsive.
        """
        # 1. Setup the main window structure immediately.
        self.after(0, self._setup_main_window)

        # 2. Perform the license check.
        self.perform_license_check_flow()

        # 3. Transition from the splash screen.
        self.after(800, self._transition_from_splash)

        # 4. Run onboarding if it's the first time.
        self.after(1000, self.run_onboarding_if_needed)


    def _transition_from_splash(self):
        if self.splash: self._fade_out_splash(self.splash, step=0)

    def _fade_out_splash(self, splash, step):
        if step <= 10:
            splash.attributes("-alpha", 1.0 - (step / 10))
            self.after(40, lambda: self._fade_out_splash(splash, step + 1))
        else:
            splash.destroy(); self.splash = None
            # --- FIX: Schedule the fade-in to run in the next event loop cycle ---
            self.after(0, self._fade_in_main_window)

    def _fade_in_main_window(self):
        # This new sequence correctly centers the window BEFORE showing it
        self.update_idletasks()

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (self.initial_width // 2)
        y = (screen_height // 2) - (self.initial_height // 2)

        self.geometry(f'{self.initial_width}x{self.initial_height}+{x}+{y}')

        # We no longer need self.deiconify() because the window was never hidden

        # Start the fade-in animation
        for i in range(11):
            self.after(i * 50, lambda a=i/10.0: self.attributes("-alpha", a))

    def _setup_main_window(self):
        self.grid_rowconfigure(1, weight=1); self.grid_columnconfigure(0, weight=1)
        self._create_header(); self._create_footer()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        # Create the main layout immediately but in a loading state
        self._create_main_layout(for_activation=True)
        self.set_status("Initializing...")

    def _destroy_splash(self):
        if self.splash: self.splash.destroy(); self.splash = None

    def run_onboarding_if_needed(self):
        flag_path = get_data_path('.first_run_complete')
        if not os.path.exists(flag_path):
            self.show_onboarding_guide()
            try:
                with open(flag_path, 'w') as f: f.write(datetime.now().isoformat())
            except Exception as e: print(f"Could not write first run flag: {e}")

    def show_onboarding_guide(self):
        messagebox.showinfo("Welcome to NREGA Bot!", "This quick guide will show you how to get started.")
        messagebox.showinfo("Step 1: Launch a Browser", "First, click one of the 'Launch' buttons to open a special browser.\nWe recommend Chrome.")
        messagebox.showinfo("Step 2: Log In to the Portal", "In the new browser, log in to the NREGA portal with your credentials.")
        messagebox.showinfo("Step 3: Choose Your Task", "Once logged in, return to this app and select your desired automation task.")
        messagebox.showinfo("You're All Set!", "Fill in the required details and click 'Start Automation'.\nFor more, visit our website from the link in the footer.")

    def _create_splash_screen(self):
        splash = ctk.CTkToplevel(self); splash.overrideredirect(True)
        w, h = 300, 200; sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
        x, y = (sw/2) - (w/2), (sh/2) - (h/2)
        splash.geometry(f'{w}x{h}+{int(x)}+{int(y)}')
        try:
            logo = ctk.CTkImage(Image.open(resource_path("logo.png")), size=(80, 80))
            ctk.CTkLabel(splash, image=logo, text="").pack(pady=(20, 10))
        except Exception: pass
        ctk.CTkLabel(splash, text=f"{config.APP_NAME}\nLoading...", font=("SF Pro Display", 14)).pack()
        splash.lift(); splash.attributes("-topmost", True)
        return splash
    
    def perform_license_check_flow(self):
        self.is_licensed = self.check_license()
        self.after(0, self._setup_licensed_ui if self.is_licensed else self._setup_unlicensed_ui)

    def _preload_and_update_about_tab(self):
        if "About" not in self.tab_instances: self.show_frame("About", raise_frame=False)
        self._update_about_tab_info(); self.update_idletasks()

    def _setup_licensed_ui(self):
        # The main layout already exists, so we just re-create the nav buttons and unlock
        for widget in self.main_layout_frame.winfo_children(): widget.destroy()
        self._create_main_layout(for_activation=False) # Re-create with all buttons

        is_expiring = self.check_expiry_and_notify()
        self._preload_and_update_about_tab()
        self._ping_server_in_background(); self._unlock_app()
        first_tab = list(list(self.get_tabs_definition().values())[0].keys())[0]
        self.show_frame("About" if is_expiring else first_tab)
        self.check_for_updates_background(); self.set_status("Ready")


    def _setup_unlicensed_ui(self):
        # App is already in the locked "about tab" state from _setup_main_window
        self._preload_and_update_about_tab()
        self.set_status("Activation Required")
        # Now, show the activation window. If successful, re-init the UI.
        if self.show_activation_window():
            self.is_licensed = True # Mark as licensed
            self._setup_licensed_ui() # Re-setup the UI in licensed mode
        else:
            self.on_closing(force=True) # Close the app if activation is cancelled

    def _ping_server_in_background(self):
        # This function now re-schedules itself to run periodically.
        def ping():
            is_connected = False
            try:
                # Use a lightweight GET request just to check for connectivity.
                requests.get(config.LICENSE_SERVER_URL, timeout=10)
                is_connected = True
            except requests.exceptions.RequestException:
                is_connected = False
            finally:
                # Always update the UI and reschedule the next check.
                self.after(0, self.set_server_status, is_connected)
                # Reschedule this check to run again in 5 minutes (300,000 ms).
                self.after(300000, ping) # Changed from re-threading

        # Start the first check in a separate thread to not block the UI.
        # Subsequent checks are scheduled on the main thread's event loop via self.after().
        threading.Thread(target=ping, daemon=True).start()

    def _on_window_focus(self, event=None):
        if self.is_licensed and not self.is_validating_license:
            self.after(500, lambda: threading.Thread(target=self._validate_in_background, daemon=True).start())

    def _validate_in_background(self):
        try:
            self.is_validating_license = True
            if self.validate_on_server(self.license_info.get('key'), is_startup_check=True):
                self.after(0, self._update_about_tab_info)
                fm_tab = self.tab_instances.get("File Manager")
                if fm_tab:
                    self.after(0, lambda: fm_tab.update_storage_info(self.license_info.get('total_usage'), self.license_info.get('max_storage')))
                    self.after(0, lambda: fm_tab.refresh_files(fm_tab.current_folder_id, add_to_history=False))
        finally: self.is_validating_license = False

    def check_license(self):
        lic_file = get_data_path('license.dat')
        if not os.path.exists(lic_file):
            return False
        
        try:
            with open(lic_file, 'r', encoding='utf-8') as f:
                self.license_info = json.load(f)

            # 1. Quick local validation
            if 'key' not in self.license_info or 'expires_at' not in self.license_info:
                raise ValueError("Invalid license file format.")

            expires_dt = datetime.fromisoformat(self.license_info['expires_at'].split('T')[0])
            if datetime.now() > expires_dt:
                # The local license is expired. Don't even try to start.
                return False

            # 2. Start a background thread to validate with the server.
            #    This won't block the app from starting.
            threading.Thread(target=self.validate_on_server, args=(self.license_info['key'], True), daemon=True).start()

            # 3. Assume the local license is valid for this session.
            return True

        except Exception as e:
            print(f"License check error, treating as unlicensed: {e}")
            if os.path.exists(lic_file):
                os.remove(lic_file)
            return False

    def _lock_app_to_about_tab(self):
        # This function is now called as part of the initial UI setup
        self.show_frame("About")
        for name, btn in self.nav_buttons.items():
            if name != "About": btn.configure(state="disabled")
        if hasattr(self, 'launch_chrome_btn'):
            self.launch_chrome_btn.configure(state="disabled")
            self.launch_firefox_btn.configure(state="disabled")
            self.theme_combo.configure(state="disabled")


    def _unlock_app(self):
        for btn in self.nav_buttons.values(): btn.configure(state="normal")
        self.launch_chrome_btn.configure(state="normal"); self.launch_firefox_btn.configure(state="normal")
        self.theme_combo.configure(state="normal")

    def get_data_path(self, filename): return get_data_path(filename)
    def get_user_downloads_path(self): return get_user_downloads_path()
    def open_folder(self, path):
        try:
            if os.path.exists(path):
                if sys.platform == "win32": os.startfile(path)
                else: subprocess.call(["open" if sys.platform == "darwin" else "xdg-open", path])
        except Exception as e: messagebox.showerror("Error", f"Could not open folder: {e}")

    def _load_icon(self, name, path, size=(20, 20)):
        try: self.icon_images[name] = ctk.CTkImage(Image.open(resource_path(path)), size=size)
        except Exception as e: print(f"Warning: Could not load icon '{name}': {e}")

    def launch_chrome_detached(self):
        port, p_dir = "9222", os.path.join(os.path.expanduser("~"), "ChromeProfileForNREGABot")
        os.makedirs(p_dir, exist_ok=True)
        paths = {"Darwin": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"], "Windows": [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]}
        b_path = next((p for p in paths.get(config.OS_SYSTEM, []) if os.path.exists(p)), None)
        if not b_path: messagebox.showerror("Error", "Google Chrome not found."); return
        try:
            cmd = [b_path, f"--remote-debugging-port={port}", f"--user-data-dir={p_dir}", config.MAIN_WEBSITE_URL, "https://bookmark.nregabot.com/"]
            flags = 0x00000008 if config.OS_SYSTEM == "Windows" else 0
            subprocess.Popen(cmd, creationflags=flags, start_new_session=(config.OS_SYSTEM != "Windows"))
            messagebox.showinfo("Chrome Launched", "Chrome is starting. Please log in to the NREGA website.")
        except Exception as e: messagebox.showerror("Error", f"Failed to launch Chrome:\n{e}")

    def launch_firefox_managed(self):
        if self.driver and messagebox.askyesno("Browser Running", "Close existing Firefox and start new?"): self.driver.quit(); self.driver = None
        elif self.driver: return
        try:
            p_dir = os.path.join(os.path.expanduser("~"), "FirefoxProfileForNREGABot"); os.makedirs(p_dir, exist_ok=True)
            opts = FirefoxOptions(); opts.add_argument("-profile"); opts.add_argument(p_dir)
            self.driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=opts)
            self.active_browser = "firefox"; messagebox.showinfo("Browser Launched", "Firefox is starting. Please log in.")
            self.driver.get(config.MAIN_WEBSITE_URL); self.driver.execute_script("window.open(arguments[0], '_blank');", "https://bookmark.nregabot.com/")
            self.driver.switch_to.window(self.driver.window_handles[0])
        except Exception as e: messagebox.showerror("Error", f"Failed to launch Firefox:\n{e}"); self.driver = None; self.active_browser = None

    def get_driver(self):
        ff_active = False
        if self.driver:
            try: _ = self.driver.window_handles; ff_active = True
            except WebDriverException: self.driver = None
        cr_active = False
        try:
            with socket.create_connection(("127.0.0.1", 9222), timeout=0.1): cr_active = True
        except (socket.timeout, ConnectionRefusedError): pass
        if ff_active: self.active_browser = "firefox"; return self.driver
        if cr_active: return self._connect_to_chrome()
        messagebox.showerror("Connection Failed", "No browser is running. Please launch one first."); return None

    def _connect_to_chrome(self):
        try:
            opts = ChromeOptions(); opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            driver = webdriver.Chrome(options=opts); self.active_browser = 'chrome'; return driver
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

        welcome_frame = ctk.CTkFrame(title_frame, fg_color="transparent"); welcome_frame.pack(anchor="w")
        self.header_welcome_prefix_label = ctk.CTkLabel(welcome_frame, text=f"v{config.APP_VERSION} | Log in, then select a task.", anchor="w"); self.header_welcome_prefix_label.pack(side="left")
        self.header_welcome_name_label = ctk.CTkLabel(welcome_frame, text="", anchor="w"); self.header_welcome_name_label.pack(side="left")
        self.header_welcome_suffix_label = ctk.CTkLabel(welcome_frame, text="", anchor="w"); self.header_welcome_suffix_label.pack(side="left")

        controls = ctk.CTkFrame(header, fg_color="transparent"); controls.pack(side="right")
        
        # --- BUTTONS HAVE BEEN UPDATED HERE ---
        self.extractor_btn = ctk.CTkButton(controls, text="Extractor", image=self.icon_images.get("wc_extractor"), command=lambda: self.show_frame("Workcode Extractor"), width=110)
        self.extractor_btn.pack(side="left", padx=(0,10))
        
        self.launch_chrome_btn = ctk.CTkButton(controls, text="Chrome", image=self.icon_images.get("chrome"), command=self.launch_chrome_detached, width=100)
        self.launch_chrome_btn.pack(side="left", padx=(0,5))

        self.launch_firefox_btn = ctk.CTkButton(controls, text="Firefox", image=self.icon_images.get("firefox"), command=self.launch_firefox_managed, width=100)
        self.launch_firefox_btn.pack(side="left", padx=(0,10))

        theme_frame = ctk.CTkFrame(controls, fg_color="transparent"); theme_frame.pack(side="left", padx=10, fill="y")
        ctk.CTkLabel(theme_frame, text="Theme:").pack(side="left", padx=(0, 5))
        self.theme_combo = ctk.CTkOptionMenu(theme_frame, values=["System", "Light", "Dark"], command=self.on_theme_change)
        self.theme_combo.pack(side="left")

    def _update_header_welcome_message(self):
        if not self.header_welcome_prefix_label: return
        user_name, key_type = self.license_info.get('user_name'), self.license_info.get('key_type')
        if user_name:
            self.header_welcome_prefix_label.configure(text=f"v{config.APP_VERSION} | Welcome, ")
            self.header_welcome_name_label.configure(text=user_name)
            self.header_welcome_suffix_label.configure(text="!")
            if key_type != 'trial':
                self.header_welcome_name_label.configure(text_color=("gold4", "#FFD700"), font=ctk.CTkFont(size=13, weight="bold"))
            else:
                self.header_welcome_name_label.configure(text_color=ctk.ThemeManager.theme["CTkLabel"]["text_color"], font=ctk.CTkFont(size=13, weight="normal"))
        else:
            self.header_welcome_prefix_label.configure(text=f"v{config.APP_VERSION} | Log in, then select a task.")
            self.header_welcome_name_label.configure(text=""); self.header_welcome_suffix_label.configure(text="")

    def _create_main_layout(self, for_activation=False):
        self.main_layout_frame = ctk.CTkFrame(self, corner_radius=0); self.main_layout_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10,0))
        self.main_layout_frame.grid_rowconfigure(0, weight=1); self.main_layout_frame.grid_columnconfigure(1, weight=1)

        nav_scroll_frame = ctk.CTkScrollableFrame(self.main_layout_frame, width=200, label_text="", fg_color="transparent")
        nav_scroll_frame.grid(row=0, column=0, sticky="nsw", padx=(0,5))
        self._create_nav_buttons(nav_scroll_frame)

        self.content_area = ctk.CTkFrame(self.main_layout_frame); self.content_area.grid(row=0, column=1, sticky="nsew")
        self.content_area.grid_rowconfigure(0, weight=1); self.content_area.grid_columnconfigure(0, weight=1)
        self._create_content_frames()

        if for_activation:
            self._lock_app_to_about_tab()


    def _create_nav_buttons(self, parent):
        self.nav_buttons.clear()
        self.button_to_category_frame.clear()
        self.category_frames.clear()

        # --- Add Category Filter Dropdown ---
        ctk.CTkLabel(parent, text="Category Filter:", font=ctk.CTkFont(size=12)).pack(fill="x", padx=10, pady=(5, 2))
        categories = ["All Automations"] + list(self.get_tabs_definition().keys())
        self.category_filter_menu = ctk.CTkOptionMenu(parent, values=categories, command=self._on_category_filter_change)
        self.category_filter_menu.set(self.last_selected_category)
        self.category_filter_menu.pack(fill="x", padx=10, pady=(0, 15))

        # --- Create all category frames ---
        for cat, tabs in self.get_tabs_definition().items():
            # --- THIS LINE IS CHANGED ---
            cat_frame = CollapsibleFrame(parent, title=cat)
            # Store the frame but don't pack it yet
            self.category_frames[cat] = cat_frame
            
            for name, data in tabs.items():
                btn = ctk.CTkButton(
                    cat_frame.content_frame, text=f" {name}", image=data.get("icon"), 
                    compound="left", command=lambda n=name: self.show_frame(n), 
                    anchor="w", font=ctk.CTkFont(size=13), height=32, corner_radius=6, 
                    fg_color="transparent", text_color=("gray10", "gray90"), 
                    hover_color=("gray75", "gray25")
                )
                btn.pack(fill="x", padx=5, pady=2)
                self.nav_buttons[name] = btn
                self.button_to_category_frame[name] = cat_frame
        
        # --- Initially filter the view based on the saved category ---
        self._filter_nav_menu(self.last_selected_category)

    def _on_category_filter_change(self, selected_category: str):
        """Called when the user selects a new category from the dropdown."""
        save_config('last_selected_category', selected_category)
        self._filter_nav_menu(selected_category)

    def _filter_nav_menu(self, selected_category: str):
        """Shows or hides category frames based on the filter."""
        for category, frame in self.category_frames.items():
            # Hide the frame first to prevent layout jumping
            frame.pack_forget()
            if selected_category == "All Automations" or category == selected_category:
                # Show the frame if it matches the selection or if 'All' is selected
                frame.pack(fill="x", pady=0, padx=0)

    def _create_content_frames(self):
        self.content_frames.clear()
        self.tab_instances.clear()
        # We only create the 'About' tab initially, others are created on demand.
        self.show_frame("About", raise_frame=False)

    def get_tabs_definition(self):
        return {
            "Core NREGA Tasks": {
                "MR Gen": {"creation_func": MusterrollGenTab, "icon": self.icon_images.get("emoji_mr_gen"), "key": "muster"},
                "MR Payment": {"creation_func": MsrTab, "icon": self.icon_images.get("emoji_mr_payment"), "key": "msr"},
                "Gen Wagelist": {"creation_func": WagelistGenTab, "icon": self.icon_images.get("emoji_gen_wagelist"), "key": "gen"},
                "Send Wagelist": {"creation_func": WagelistSendTab, "icon": self.icon_images.get("emoji_send_wagelist"), "key": "send"},
                "FTO Generation": {"creation_func": FtoGenerationTab, "icon": self.icon_images.get("emoji_fto_gen"), "key": "fto_gen"},
                "Scheme Closing": {"creation_func": SchemeClosingTab, "icon": self.icon_images.get("emoji_scheme_closing"), "key": "scheme_close"},
                "Del Work Alloc": {"creation_func": DelWorkAllocTab, "icon": self.icon_images.get("emoji_del_work_alloc"), "key": "del_work_alloc"},
                "Duplicate MR Print": {"creation_func": DuplicateMrTab, "icon": self.icon_images.get("emoji_duplicate_mr"), "key": "dup_mr"},
                "Demand": {"creation_func": DemandTab, "icon": self.icon_images.get("emoji_demand"), "key": "demand"},
            },
            # --- ADD THIS NEW CATEGORY ---
            "JE & AE Automation": {
                "eMB Entry": {"creation_func": MbEntryTab, "icon": self.icon_images.get("emoji_emb_entry"), "key": "mb_entry"},
                "eMB Verify": {"creation_func": EmbVerifyTab, "icon": self.icon_images.get("emoji_emb_verify"), "key": "emb_verify"},
            },
            "Records & Workcode": {
                "WC Gen": {"creation_func": WcGenTab, "icon": self.icon_images.get("emoji_wc_gen"), "key": "wc_gen"},
                "IF Editor": {"creation_func": IfEditTab, "icon": self.icon_images.get("emoji_if_editor"), "key": "if_edit"},
                "Add Activity": {"creation_func": AddActivityTab, "icon": self.icon_images.get("emoji_add_activity"), "key": "add_activity"},
                "Update Estimate": {"creation_func": UpdateEstimateTab, "icon": self.icon_images.get("emoji_update_outcome"), "key": "update_outcome"},
            },
            "Utilities & Verification": {
                "Verify Jobcard": {"creation_func": JobcardVerifyTab, "icon": self.icon_images.get("emoji_verify_jobcard"), "key": "jc_verify"},
                "Verify ABPS": {"creation_func": AbpsVerifyTab, "icon": self.icon_images.get("emoji_verify_abps"), "key": "abps_verify"},
                "Workcode Extractor": {"creation_func": WorkcodeExtractorTab, "icon": self.icon_images.get("emoji_wc_extractor"), "key": "wc_extract"},
                "Resend Rejected WG": {"creation_func": ResendRejectedWgTab, "icon": self.icon_images.get("emoji_resend_wg"), "key": "resend_wg"},
                "File Manager": {"creation_func": FileManagementTab, "icon": self.icon_images.get("emoji_file_manager"), "key": "file_manager"},
            },
            "Reporting": {
                "Social Audit Report": {"creation_func": SAReportTab, "icon": self.icon_images.get("emoji_social_audit"), "key": "social_audit_respond"},
                "MIS Reports": {"creation_func": MisReportsTab, "icon": self.icon_images.get("emoji_mis_reports"), "key": "mis_reports"},
            },
            "Application": {
                 "Feedback": {"creation_func": FeedbackTab, "icon": self.icon_images.get("emoji_feedback")},
                 "About": {"creation_func": AboutTab, "icon": self.icon_images.get("emoji_about")},
            }
        }

    def show_frame(self, page_name, raise_frame=True):
        # Check if the frame has already been created
        if page_name not in self.tab_instances:
            # If not, find its creation function from the tabs definition
            tabs = self.get_tabs_definition()
            for cat, tab_items in tabs.items():
                if page_name in tab_items:
                    # Create the frame and the tab instance inside it
                    frame = ctk.CTkFrame(self.content_area)
                    frame.grid(row=0, column=0, sticky="nsew")
                    self.content_frames[page_name] = frame

                    # Create the actual tab content
                    instance = tab_items[page_name]["creation_func"](frame, self)
                    instance.pack(expand=True, fill="both")
                    self.tab_instances[page_name] = instance
                    break # Stop searching once found

        # Now, raise the frame to the front
        if raise_frame:
            # --- REMOVE THIS LINE ---
            # if page_name in self.button_to_category_frame:
            #     self.button_to_category_frame[page_name].expand()
            
            if page_name in self.content_frames:
                self.content_frames[page_name].tkraise()
            for name, btn in self.nav_buttons.items():
                btn.configure(fg_color=("gray90", "gray28") if name == page_name else "transparent")

    def open_web_file_manager(self):
        if self.license_info.get('key'):
            auth_url = f"{config.LICENSE_SERVER_URL}/authenticate-from-app/{self.license_info['key']}?next=files"
            webbrowser.open_new_tab(auth_url)
        else:
            messagebox.showerror("Error", "License key not found. Please log in to use the web file manager.")

    def _create_footer(self):
        footer = ctk.CTkFrame(self, height=40, corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 15))
        footer.grid_columnconfigure((0, 1, 3), weight=0); footer.grid_columnconfigure(2, weight=1)

        left_frame = ctk.CTkFrame(footer, fg_color="transparent"); left_frame.grid(row=0, column=0, sticky="w", padx=15)
        ctk.CTkLabel(left_frame, text="© 2025 NREGA Bot", text_color="gray50").pack(side="left")

        status_frame = ctk.CTkFrame(footer, fg_color="transparent"); status_frame.grid(row=0, column=1, columnspan=2, sticky="ew", padx=20)
        self.loading_animation_label = ctk.CTkLabel(status_frame, text="", width=20, font=ctk.CTkFont(size=14)); self.loading_animation_label.pack(side="left")
        self.status_label = ctk.CTkLabel(status_frame, text="Status: Ready", text_color="gray50", anchor="w"); self.status_label.pack(side="left")

        btn_container = ctk.CTkFrame(footer, fg_color="transparent"); btn_container.grid(row=0, column=3, sticky="e", padx=15)
        def create_link(parent, text, image_key, url):
            btn = ctk.CTkButton(parent, text=text, image=self.icon_images.get(image_key), command=lambda: webbrowser.open_new_tab(url), fg_color="transparent", hover=False, text_color=("gray10", "gray80"))
            return btn
        ctk.CTkButton(btn_container, text="File Manager", image=self.icon_images.get("emoji_file_manager"), command=self.open_web_file_manager, fg_color="transparent", hover=False, text_color=("gray10", "gray80")).pack(side="left")
        ctk.CTkButton(btn_container, text="Community", image=self.icon_images.get("whatsapp"), command=lambda: webbrowser.open_new_tab("https://chat.whatsapp.com/Bup3hDCH3wn2shbUryv8wn"), fg_color="transparent", hover=False, text_color=("gray10", "gray80")).pack(side="left", padx=(10, 0))
        ctk.CTkButton(btn_container, text="Contact Support", image=self.icon_images.get("feedback"), command=lambda: self.show_frame("Feedback"), fg_color="transparent", hover=False, text_color=("gray10", "gray80")).pack(side="left", padx=(10, 0))
        self.server_status_indicator = ctk.CTkFrame(btn_container, width=12, height=12, corner_radius=6, fg_color="gray"); self.server_status_indicator.pack(side="left", padx=(10, 5))
        ctk.CTkLabel(btn_container, text="Server").pack(side="left")
        self.set_status("Ready")

    def save_demo_csv(self, file_type: str):
        try:
            src = resource_path(f"assets/demo_{file_type}.csv")
            if not os.path.exists(src): messagebox.showerror("Error", f"Demo file not found: demo_{file_type}.csv"); return
            save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], initialfile=f"{file_type}_data.csv", title=f"Save Demo {file_type.upper()} CSV")
            if save_path: shutil.copyfile(src, save_path); messagebox.showinfo("Success", f"Demo file saved to:\n{save_path}")
        except Exception as e: messagebox.showerror("Error", f"Could not save demo file: {e}")

    def on_theme_change(self, new_theme: str): ctk.set_appearance_mode(new_theme); self.after(100, self.restyle_all_treeviews)
    def restyle_all_treeviews(self):
        for tab in self.tab_instances.values():
            if hasattr(tab, 'style_treeview'):
                if hasattr(tab, 'results_tree'): tab.style_treeview(tab.results_tree)
                if hasattr(tab, 'files_tree'): tab.style_treeview(tab.files_tree)

    def _update_about_tab_info(self):
        self._update_header_welcome_message()
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

    def validate_on_server(self, key, is_startup_check=False):
        try:
            resp = requests.post(f"{config.LICENSE_SERVER_URL}/api/validate", json={"key": key, "machine_id": self.machine_id}, timeout=10)
            self.after(0, self.set_server_status, True)
            data = resp.json()

            if resp.status_code == 200 and data.get("status") == "valid":
                # Server confirms the license is valid, update the local file with the latest info.
                self.license_info = {**data, 'key': key}
                with open(get_data_path('license.dat'), 'w') as f:
                    json.dump(self.license_info, f)
                if not is_startup_check:
                    messagebox.showinfo("License Valid", f"Activation successful!\nExpires on: {self.license_info['expires_at'].split('T')[0]}")
                return True
            else:
                # Server says the license is invalid (expired, blocked, etc.).
                # Delete the local license file so the app won't open next time.
                lic_file = get_data_path('license.dat')
                if os.path.exists(lic_file):
                    os.remove(lic_file)
                if not is_startup_check:
                    messagebox.showerror("Validation Failed", data.get('reason', 'Unknown error.'))
                return False

        except requests.exceptions.RequestException:
            self.after(0, self.set_server_status, False)
            # If the server is offline, we don't treat it as a failure.
            # We just can't sync. Only show an error if it's an interactive check.
            if not is_startup_check:
                messagebox.showerror("Connection Error", "Could not connect to the license server. Please check your internet connection.")
            # IMPORTANT: Return True here to allow offline use if the server is unreachable.
            return True

    def send_wagelist_data_and_switch_tab(self, start, end):
        self.show_frame("Send Wagelist")
        send_tab = self.tab_instances.get("Send Wagelist")
        if send_tab and hasattr(send_tab, 'populate_wagelist_data'):
            self.after(100, lambda: send_tab.populate_wagelist_data(start, end))
        else: print("Error: Send Wagelist tab not found or is missing method.")

    def show_activation_window(self):
        win = ctk.CTkToplevel(self); win.title("Activate Product")
        w, h = 450, 500; x, y = (self.winfo_screenwidth()//2) - (w//2), (self.winfo_screenheight()//2) - (h//2)
        win.geometry(f'{w}x{h}+{x}+{y}'); win.resizable(False, False); win.transient(self); win.grab_set()

        main = ctk.CTkFrame(win, fg_color="transparent"); main.pack(expand=True, fill="both", padx=20, pady=20)
        ctk.CTkLabel(main, text="Product Activation", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0, 10))
        activated = tkinter.BooleanVar(value=False)
        tabs = ctk.CTkTabview(main); tabs.pack(expand=True, fill="both"); tabs.add("New User"); tabs.add("Existing User")

        def on_trial():
            win.withdraw()
            if self.show_trial_registration_window(): activated.set(True); win.destroy()
            else: win.deiconify()

        def on_activate():
            key = key_entry.get().strip()
            if not key: messagebox.showwarning("Input Required", "Please enter a license key.", parent=win); return
            if self.validate_on_server(key): activated.set(True); win.destroy()

        def on_login():
            email = email_entry.get().strip()
            if not email: messagebox.showwarning("Input Required", "Please enter your email.", parent=win); return
            login_btn.configure(state="disabled", text="Activating...")
            try:
                resp = requests.post(f"{config.LICENSE_SERVER_URL}/api/login-for-activation", json={"email": email, "machine_id": self.machine_id}, timeout=15)
                data = resp.json()
                if resp.status_code == 200 and data.get("status") == "success":
                    self.license_info = data
                    with open(get_data_path('license.dat'), 'w') as f: json.dump(self.license_info, f)
                    messagebox.showinfo("Success", f"Device activated!\nWelcome back, {data.get('user_name', 'User')}.")
                    activated.set(True); win.destroy()
                else: messagebox.showerror("Activation Failed", data.get("reason", "Unknown error."), parent=win)
            except requests.exceptions.RequestException as e: messagebox.showerror("Connection Error", f"Could not connect: {e}", parent=win)
            finally:
                if login_btn.winfo_exists(): login_btn.configure(state="normal", text="Login & Activate Device")

        new_user = tabs.tab("New User")
        ctk.CTkButton(new_user, text="Start 30-Day Free Trial", command=on_trial).pack(pady=(20, 5), ipady=4, fill='x', padx=10)
        ctk.CTkLabel(new_user, text="— OR —").pack(pady=10); ctk.CTkLabel(new_user, text="Enter a purchased license key:").pack(pady=(5, 5))
        key_entry = ctk.CTkEntry(new_user, width=300); key_entry.pack(pady=5, padx=10, fill='x')
        ctk.CTkButton(new_user, text="Activate with Key", command=on_activate).pack(pady=10, ipady=4, fill='x', padx=10)

        existing_user = tabs.tab("Existing User")
        ctk.CTkLabel(existing_user, text="Activate this device by logging in with your registered email.", wraplength=380, justify="center").pack(pady=(20, 15))
        email_entry = ctk.CTkEntry(existing_user, placeholder_text="Enter your registered email"); email_entry.pack(pady=5, fill='x', padx=10); email_entry.focus_set()
        login_btn = ctk.CTkButton(existing_user, text="Login & Activate Device", command=on_login); login_btn.pack(pady=15, ipady=4, fill='x', padx=10)

        links = ctk.CTkFrame(main, fg_color="transparent"); links.pack(pady=(15,0), fill="x")
        buy_link = ctk.CTkLabel(links, text="Purchase a License Key", text_color=("blue", "cyan"), cursor="hand2"); buy_link.pack()
        buy_link.bind("<Button-1>", lambda e: webbrowser.open_new_tab(f"{config.LICENSE_SERVER_URL}/buy"))

        self.wait_window(win); return activated.get()

    def show_trial_registration_window(self):
        win = ctk.CTkToplevel(self); win.title("Trial Registration")
        w, h = 480, 600; x, y = (self.winfo_screenwidth()//2) - (w//2), (self.winfo_screenheight()//2) - (h//2)
        win.geometry(f'{w}x{h}+{x}+{y}'); win.resizable(False, False); win.transient(self); win.grab_set()

        scroll = ctk.CTkScrollableFrame(win, fg_color="transparent", label_fg_color="transparent"); scroll.pack(expand=True, fill="both", padx=10, pady=10)
        ctk.CTkLabel(scroll, text="Start Your Free Trial", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0, 5))
        ctk.CTkLabel(scroll, text="Please provide your details to begin.", text_color="gray50").pack(pady=(0, 15))

        entries = {}
        for field in ["Full Name", "Email", "Mobile", "Block", "District", "State", "Pincode"]:
            key = field.lower().replace(" ", "_"); ctk.CTkLabel(scroll, text=field, anchor="w").pack(fill="x", padx=10)
            entry = ctk.CTkEntry(scroll); entry.pack(fill="x", padx=10, pady=(0, 10)); entries[key] = entry

        successful = tkinter.BooleanVar(value=False)
        def submit_request():
            import re
            user_data = {k: e.get().strip() for k, e in entries.items()}
            email, mobile = user_data.get('email', ''), user_data.get('mobile', '')
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email): messagebox.showwarning("Invalid Input", "Valid email is required.", parent=win); return
            if not (mobile.isdigit() and len(mobile) == 10): messagebox.showwarning("Invalid Input", "Valid 10-digit mobile is required.", parent=win); return
            user_data["name"] = user_data.pop("full_name"); user_data["machine_id"] = self.machine_id
            if not all(user_data.values()): messagebox.showwarning("Input Required", "All fields are required.", parent=win); return

            submit_btn.configure(state="disabled", text="Requesting...")
            try:
                resp = requests.post(f"{config.LICENSE_SERVER_URL}/api/request-trial", json=user_data, timeout=15, headers={'User-Agent': f'{config.APP_NAME}/{config.APP_VERSION}'})
                data = resp.json()
                if resp.status_code == 200 and data.get("status") == "success":
                    self.license_info = {'key': data.get("key"), 'expires_at': data.get('expires_at'), 'user_name': user_data['name'], 'key_type': 'trial'}
                    with open(get_data_path('license.dat'), 'w') as f: json.dump(self.license_info, f)
                    messagebox.showinfo("Success!", f"{data.get('reason', 'Trial has started!')}\nExpires on: {self.license_info['expires_at'].split('T')[0]}")
                    successful.set(True); win.destroy()
                else: messagebox.showerror("Trial Error", data.get("reason", "Could not start trial."), parent=win)
            except requests.exceptions.RequestException: messagebox.showerror("Connection Error", "Could not connect to server.", parent=win)
            finally:
                if submit_btn.winfo_exists(): submit_btn.configure(state="normal", text="Start Trial")

        submit_btn = ctk.CTkButton(scroll, text="Start Trial", command=submit_request); submit_btn.pack(pady=20, ipady=4, fill='x', padx=10)
        self.wait_window(win); return successful.get()

    def show_purchase_window(self, context='upgrade'):
        win = ctk.CTkToplevel(self)
        title = "Renew Subscription" if context == 'renew' else "Upgrade to Full License"
        win.title(title); w, h = 480, 420; x, y = (self.winfo_screenwidth()//2) - (w//2), (self.winfo_screenheight()//2) - (h//2)
        win.geometry(f'{w}x{h}+{x}+{y}'); win.resizable(False, False); win.transient(self); win.grab_set()

        main = ctk.CTkFrame(win, fg_color="transparent"); main.pack(expand=True, fill="both", padx=20, pady=20)
        ctk.CTkLabel(main, text=title, font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0, 15))
        ctk.CTkLabel(main, text="1. Choose Your Plan", font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(fill="x", padx=10, pady=(10,5))

        plans = ["Monthly (₹99)", "Quarterly (₹289)", "Half Yearly (₹569)", "Yearly (₹999)"]
        plan_menu = ctk.CTkOptionMenu(main, values=plans); plan_menu.pack(fill="x", padx=10, pady=(0,5))
        ctk.CTkLabel(main, text="Number of Devices:").pack(fill="x", padx=10, pady=(15, 5))
        dev_input = ctk.CTkOptionMenu(main, values=[str(i) for i in range(1, 4)]); dev_input.set(str(self.license_info.get('max_devices', 1))); dev_input.pack(fill="x", padx=10)

        prices = {"monthly": 99, "quarterly": 289, "half": 569, "yearly": 999}
        total_label = ctk.CTkLabel(main, text="Total: ₹99", font=ctk.CTkFont(size=18, weight="bold")); total_label.pack(pady=25)

        def update_price(*args):
            plan_key = plan_menu.get().lower().split(' ')[0]
            dev_count = int(dev_input.get())
            total = prices[plan_key] * dev_count
            total_label.configure(text=f"Total: ₹{total}")

        plan_menu.configure(command=update_price); dev_input.configure(command=update_price); update_price()

        def proceed():
            submit_btn.configure(state="disabled", text="Initializing...")
            form = {k.replace('user_', ''): v for k, v in self.license_info.items() if k.startswith('user_')}
            form['existing_key'] = self.license_info.get('key')
            if not all(form.get(k) for k in ['name', 'email', 'mobile']):
                messagebox.showwarning("User Details Missing", "Please contact support.", parent=win); submit_btn.configure(state="normal", text="Proceed"); return
            form.update({'plan_type': plan_menu.get().lower().split(' ')[0], 'max_devices': int(dev_input.get())})
            try:
                webbrowser.open_new_tab(f"{config.LICENSE_SERVER_URL}/buy?{urlencode({k: v for k, v in form.items() if v})}")
                win.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Could not open payment page: {e}", parent=win)
            finally:
                if submit_btn.winfo_exists(): submit_btn.configure(state="normal", text="Proceed")

        submit_btn = ctk.CTkButton(main, text="Proceed to Payment", command=proceed); submit_btn.pack(pady=20, ipady=5, fill='x', padx=10)

    def check_expiry_and_notify(self):
        expires_str = self.license_info.get('expires_at')
        if not expires_str: return False
        try:
            days = (datetime.fromisoformat(expires_str.split('T')[0]).date() - datetime.now().date()).days
            if 0 <= days < 7:
                msg = f"License expires {'today' if days == 0 else f'in {days} day' + ('s' if days != 1 else '')}."
                messagebox.showwarning("License Expiring", f"{msg}\nPlease renew from the website."); self.open_on_about_tab = True; return True
        except (ValueError, TypeError) as e:
            if SENTRY_DSN: sentry_sdk.capture_exception(e)
        return False

    def start_automation_thread(self, key, target, args=()):
        if self.automation_threads.get(key) and self.automation_threads[key].is_alive():
            messagebox.showwarning("In Progress", "Task is already running."); return
        self.history_manager.increment_usage(key); self.prevent_sleep()
        self.active_automations.add(key); self.stop_events[key] = threading.Event()
        def wrapper():
            try: target(*args)
            finally: self.after(0, self.on_automation_finished, key)
        thread = threading.Thread(target=wrapper, daemon=True); self.automation_threads[key] = thread; thread.start()

    def log_message(self, log, msg, level="info"): log.configure(state="normal"); log.insert(tkinter.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n"); log.configure(state="disabled"); log.see(tkinter.END)
    def clear_log(self, log): log.configure(state="normal"); log.delete("1.0", tkinter.END); log.configure(state="disabled")

    def on_closing(self, force=False):
        if force or messagebox.askokcancel("Quit", "Quit? This will stop running automations."):
            self.attributes("-alpha", 0.0); self.active_automations.clear(); self.allow_sleep()
            if self.driver:
                try: self.driver.quit()
                except Exception as e: print(f"Error quitting driver: {e}")
            for event in self.stop_events.values(): event.set()
            self.after(100, self.destroy)

    def prevent_sleep(self):
        if not self.active_automations:
            print("Preventing sleep.");
            if config.OS_SYSTEM == "Windows": ctypes.windll.kernel32.SetThreadExecutionState(0x80000003)
            elif config.OS_SYSTEM == "Darwin":
                if not self.sleep_prevention_process: self.sleep_prevention_process = subprocess.Popen(["caffeinate", "-d"])

    def allow_sleep(self):
        if not self.active_automations:
            print("Allowing sleep.")
            if config.OS_SYSTEM == "Windows": ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            elif config.OS_SYSTEM == "Darwin":
                if self.sleep_prevention_process: self.sleep_prevention_process.terminate(); self.sleep_prevention_process = None

    def on_automation_finished(self, key):
        if key in self.active_automations: self.active_automations.remove(key)
        self.set_status("Automation Finished"); self.after(5000, lambda: self.set_status("Ready"))
        if not self.active_automations: self.allow_sleep()

    def check_for_updates_background(self):
        def _check():
            time.sleep(2)
            try:
                resp = requests.get(f"{config.MAIN_WEBSITE_URL}/version.json", timeout=10); resp.raise_for_status(); data = resp.json()
                latest = data.get("latest_version")
                url_key = "download_url_macos" if sys.platform == "darwin" else "download_url_windows"
                url = data.get(url_key); notes = data.get("changelog", {}).get(latest, [])
                if latest and parse_version(latest) > parse_version(config.APP_VERSION):
                    self.update_info = {"status": "available", "version": latest, "url": url, "changelog": notes}
                    self.after(0, self.show_update_prompt, latest)
                else: self.update_info = {"status": "updated", "version": latest, "url": url}
            except Exception as e: self.update_info['status'] = 'error'
            finally: self.after(0, self._update_about_tab_info)
        threading.Thread(target=_check, daemon=True).start()

    def show_update_prompt(self, version):
        if messagebox.askyesno("Update Available", f"Version {version} is available. Go to the 'Updates' tab?"):
            self.show_frame("About")
            about = self.tab_instances.get("About")
            if about: about.tab_view.set("Updates")

    def update_history(self, key, val): self.history_manager.save_entry(key, val)

    def download_and_install_update(self, url, version):
        about = self.tab_instances.get("About")
        if not about: messagebox.showerror("Error", "Could not find About Tab."); return
        about.update_button.configure(state="disabled"); about.update_progress.grid(row=4, column=0, pady=10, padx=20, sticky='ew')

        def _worker():
            try:
                filename = url.split('/')[-1]; dl_path = os.path.join(self.get_user_downloads_path(), filename)
                self.after(0, lambda: about.update_button.configure(text="Downloading..."))
                with requests.get(url, stream=True, timeout=60) as r:
                    r.raise_for_status(); total = int(r.headers.get('content-length', 0)); downloaded = 0
                    with open(dl_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk); downloaded += len(chunk)
                            if total > 0: self.after(0, about.update_progress.set, downloaded / total)

                self.after(0, lambda: about.update_button.configure(text="Download Complete. Installing..."))
                if sys.platform == "win32":
                    messagebox.showinfo("Ready to Update", "The app will now close to run the installer.", parent=self)
                    os.startfile(dl_path); self.after(200, os._exit, 0)
                elif sys.platform == "darwin":
                    subprocess.call(["open", dl_path])
                    self.after(0, messagebox.showinfo, "Instructions", f"'{filename}' has been opened.\nDrag the icon to Applications.\nApp will now close.")
                    self.after(3000, self.on_closing, True)
            except Exception as e:
                self.after(0, messagebox.showerror, "Update Failed", f"Could not run update.\n\nError: {e}")
                if about.winfo_exists():
                    self.after(0, lambda: about.update_button.configure(state="normal", text=f"Download v{version}"))
                    self.after(0, about.update_progress.grid_forget); self.after(0, about.update_progress.set, 0)
        threading.Thread(target=_worker, daemon=True).start()

def initialize_webdriver_manager():
    """Downloads/updates drivers for Chrome and Firefox before the app starts."""
    print("Initializing WebDriver Manager...")
    try:
        print("Checking for Chrome driver...")
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service as ChromeService
        ChromeService(ChromeDriverManager().install())
        print("Chrome driver is up to date.")
    except Exception as e:
        print(f"Could not initialize ChromeDriver: {e}")

    try:
        print("Checking for Firefox driver (GeckoDriver)...")
        from webdriver_manager.firefox import GeckoDriverManager
        from selenium.webdriver.firefox.service import Service as FirefoxService
        FirefoxService(GeckoDriverManager().install())
        print("GeckoDriver is up to date.")
    except Exception as e:
        print(f"Could not initialize GeckoDriver: {e}")
    print("WebDriver Manager initialization complete.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try: s.bind(("127.0.0.1", 60123))
    except OSError:
        try: s.connect(("127.0.0.1", 60123)); s.sendall(b'focus')
        except Exception as e: logging.error(f"Failed to send focus: {e}")
        finally: s.close(); sys.exit(0)

    # Run webdriver manager in a thread so the UI can appear even faster
    threading.Thread(target=initialize_webdriver_manager, daemon=True).start()

    try:
        app = NregaBotApp()
        def listen():
            s.listen(1)
            while True:
                conn, addr = s.accept()
                if conn.recv(1024) == b'focus': app.after(0, app.bring_to_front)
                conn.close()
        threading.Thread(target=listen, daemon=True).start()
        app.mainloop()
    except Exception as e:
        if SENTRY_DSN: sentry_sdk.capture_exception(e)
        logging.critical(f"Fatal startup error: {e}", exc_info=True)
        messagebox.showerror("Fatal Startup Error", f"A critical error occurred:\n\n{e}\n\nThe app will now close.")
    finally: s.close()
