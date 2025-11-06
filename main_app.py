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

# --- ADD THIS IMPORT ---
import pygame

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
from tabs.mr_tracking_tab import MrTrackingTab
from tabs.dashboard_report_tab import DashboardReportTab
from tabs.mr_fill_tab import MrFillTab
from tabs.pdf_merger_tab import PdfMergerTab
from tabs.issued_mr_report_tab import IssuedMrReportTab
from tabs.zero_mr_tab import ZeroMrTab

from utils import resource_path, get_data_path, get_user_downloads_path, get_config, save_config

if config.OS_SYSTEM == "Windows":
    import ctypes

load_dotenv()

# --- ADD THIS LINE AFTER load_dotenv() ---
config.create_default_config_if_not_exists()

# --- ADD THIS SECTION ---
# Store original messagebox functions before we patch them
_original_showinfo = messagebox.showinfo
_original_showwarning = messagebox.showwarning
_original_showerror = messagebox.showerror
# --- END SECTION ---

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
    
class OnboardingStep(ctk.CTkFrame):
    """A single step frame for the onboarding guide."""
    def __init__(self, parent, title, description, icon):
        super().__init__(parent, fg_color="transparent")
        self.pack(expand=True, fill="both", padx=20, pady=(10, 0))

        if icon:
            icon_label = ctk.CTkLabel(self, image=icon, text="")
            icon_label.pack(pady=(10, 15))

        title_label = ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=18, weight="bold"))
        title_label.pack(pady=(0, 10))

        desc_label = ctk.CTkLabel(self, text=description, wraplength=380, justify="center")
        desc_label.pack(pady=(0, 20))


class OnboardingGuide(ctk.CTkToplevel):
    """A professional, step-by-step onboarding guide window."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.current_step = 0

        self.title("Welcome to NREGA Bot!")
        # --- Increased height slightly to better accommodate content ---
        w, h = 450, 350
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f'{w}x{h}+{x}+{y}')
        self.resizable(False, False)
        self.transient(parent)
        self.attributes("-topmost", True)
        self.grab_set()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- NEW: Main container is now a scrollable frame ---
        self.scrollable_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scrollable_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.steps_data = [
            {"title": "Step 1: Launch a Browser", "desc": "First, click one of the 'Chrome' buttons in the main app to open a special browser. We recommend Chrome.", "icon": self.parent.icon_images.get("onboarding_launch")},
            {"title": "Step 2: Log In to the Portal", "desc": "In the new browser window, log in to the NREGA portal with your official credentials.", "icon": self.parent.icon_images.get("onboarding_login")},
            {"title": "Step 3: Choose Your Task", "desc": "Once logged in, return to this app and select your desired automation task from the navigation menu on the left.", "icon": self.parent.icon_images.get("onboarding_select")},
            {"title": "You're All Set!", "desc": "Fill in the required details for your chosen task and click 'Start Automation'. For more help, visit our website from the link in the footer.", "icon": self.parent.icon_images.get("onboarding_start")}
        ]

        self.step_frames = []
        for i, step_info in enumerate(self.steps_data):
            # --- Steps are now placed inside the scrollable_container ---
            frame = OnboardingStep(self.scrollable_container, step_info["title"], step_info["desc"], step_info["icon"])
            # We don't need to append to a list and hide/show, we will just clear and recreate
            # but for this simple case, we will let them stack and tkraise will work fine.
            self.step_frames.append(frame)


        self.footer = ctk.CTkFrame(self)
        self.footer.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 20))
        self.footer.grid_columnconfigure(0, weight=1) # Makes the progress bar expand

        self.progress_bar = ctk.CTkProgressBar(self.footer, height=10)
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 15))

        self.next_button = ctk.CTkButton(self.footer, text="Next", command=self.show_next_step, width=100)
        self.next_button.grid(row=0, column=1)

        self.show_step(0)
        self.focus_force()

    def show_step(self, step_index):
        # This logic remains the same
        for i, frame in enumerate(self.step_frames):
            if i == step_index:
                # Pack the frame if it's not already, and then raise it.
                # This ensures it's visible inside the scrollable area.
                frame.pack(expand=True, fill="both")
                frame.tkraise()
            else:
                # Unpack other frames to ensure proper layout
                frame.pack_forget()

        progress_value = (step_index + 1) / len(self.steps_data)
        self.progress_bar.set(progress_value)

        if step_index == len(self.steps_data) - 1:
            self.next_button.configure(text="Finish", command=self.destroy)
        else:
            self.next_button.configure(text="Next")

    def show_next_step(self):
        self.current_step += 1
        if self.current_step < len(self.steps_data):
            self.show_step(self.current_step)


class NregaBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        # self.withdraw()
        self.attributes("-alpha", 0.0)

        # --- ADD THIS LINE TO INITIALIZE PYGAME MIXER ---
        try:
            pygame.mixer.init()
        except Exception as e:
            print(f"Warning: Could not initialize audio mixer: {e}. Sounds will be disabled.")

        # --- ADD THIS SECTION ---
        # Apply the monkey-patch to intercept messagebox calls
        messagebox.showinfo = self._custom_showinfo
        messagebox.showwarning = self._custom_showwarning
        messagebox.showerror = self._custom_showerror
        # --- END SECTION ---

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

        self.sound_switch_var = tkinter.BooleanVar(value=get_config('sound_enabled', True))

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

        self._load_icon("disclaimer_warning", "assets/icons/emojis/warning.png", size=(16,16))
        self._load_icon("disclaimer_thunder", "assets/icons/emojis/thunder.png", size=(16,16))
        self._load_icon("disclaimer_tools", "assets/icons/emojis/tools.png", size=(16,16))

        self._load_icon("onboarding_launch", "assets/icons/emojis/thunder.png", size=(48, 48))
        self._load_icon("onboarding_login", "assets/icons/emojis/verify_jobcard.png", size=(48, 48))
        self._load_icon("onboarding_select", "assets/icons/emojis/wc_gen.png", size=(48, 48))
        self._load_icon("onboarding_start", "assets/icons/emojis/fto_gen.png", size=(48, 48))

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
        self._load_icon("emoji_mr_tracking", "assets/icons/emojis/mr_tracking.png", size=(16,16))
        self._load_icon("emoji_dashboard_report", "assets/icons/emojis/dashboard_report.png", size=(16,16))
        self._load_icon("emoji_mr_fill", "assets/icons/emojis/mr_fill.png", size=(16,16))
        self._load_icon("emoji_pdf_merger", "assets/icons/emojis/pdf_merger.png", size=(16,16))
        self._load_icon("emoji_issued_mr_report", "assets/icons/emojis/issued_mr_report.png", size=(16,16))
        self._load_icon("emoji_zero_mr", "assets/icons/emojis/zero_mr.png", size=(16,16))


        self.bind("<FocusIn>", self._on_window_focus)
        self.after(0, self.start_app)

    def bring_to_front(self):
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def set_status(self, message, color=None):
        if self.status_label:
            message_lower = message.lower()
            final_color = color # Start with the provided color (if any)
            
            should_animate = False

            if final_color is None: # If no color was forced, determine it
                if "running" in message_lower or "starting" in message_lower or \
                   "navigating" in message_lower or "solving" in message_lower or \
                   "selecting" in message_lower or "opening" in message_lower or \
                   "drilling" in message_lower or "finding" in message_lower or \
                   "clicking" in message_lower or "loading" in message_lower or \
                   "processing" in message_lower or "waiting for" in message_lower or \
                   "retrying" in message_lower:
                    
                    final_color = "#3B82F6" # Blue
                    should_animate = True
                
                elif "finished" in message_lower:
                    final_color = "#E53E3E" # Red
                
                elif "ready" in message_lower:
                    final_color = "#38A169" # Green
                    if message == "Ready": # Only play "ready" sound for the final "Ready" state
                        self.play_sound("success")

                elif "error" in message_lower or "failed" in message_lower:
                    final_color = "#E53E3E" # Red
                    if not "session expired" in message_lower: # Don't play error sound for session expiry retries
                        self.play_sound("error")

                else: # Default for other states (Stopped, No data, etc.)
                    final_color = "gray50" # Default gray

            # Handle animation state
            if should_animate and not self.is_animating:
                self.is_animating = True
                self._animate_loading_icon()
            elif not should_animate:
                self.is_animating = False

            # Configure the status label with the final color
            self.status_label.configure(text=f"Status: {message}", text_color=final_color)

            # Ensure animation label is cleared if animation stops
            if not self.is_animating and self.loading_animation_label:
                 self.loading_animation_label.configure(text="")

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
            OnboardingGuide(self) # Launch the new onboarding window
            try:
                with open(flag_path, 'w') as f: f.write(datetime.now().isoformat())
            except Exception as e: print(f"Could not write first run flag: {e}")



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

        self.after(500, self.run_onboarding_if_needed)


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

    def _on_sound_toggle(self):
        is_enabled = self.sound_switch_var.get()
        save_config('sound_enabled', is_enabled)
        if is_enabled:
            self.play_sound("success") # Play a sound to confirm

    # --- THIS METHOD IS NOW UPDATED FOR PYGAME ---
    def play_sound(self, sound_name: str):
        """Plays a sound using pygame if sounds are enabled."""
        if not self.sound_switch_var.get():
            return
        
        try:
            sound_file = resource_path(f"assets/sounds/{sound_name}.wav")
            if os.path.exists(sound_file):
                # pygame.mixer.Sound() and .play() are non-blocking
                sound = pygame.mixer.Sound(sound_file)
                sound.play()
            else:
                print(f"Sound file not found: {sound_file}")
        except Exception as e:
            # Catch exceptions (e.g., file not found, audio device issue)
            print(f"Error playing sound '{sound_name}' with pygame: {e}")

# --- ADD THIS ENTIRE SECTION OF NEW METHODS ---
    def _custom_showinfo(self, title, message, **options):
        """Custom showinfo to play a sound first."""
        # Check if the message is a "completion" message
        if "finished" in message.lower() or \
           "complete" in message.lower() or \
           "success" in message.lower() or \
           "transferred" in message.lower():
            self.play_sound("complete")
        else:
            self.play_sound("success") # Default for other info popups
        return _original_showinfo(title, message, **options)

    def _custom_showwarning(self, title, message, **options):
        """Custom showwarning to play a sound first."""
        self.play_sound("error") # Use "error" for warnings
        return _original_showwarning(title, message, **options)

    def _custom_showerror(self, title, message, **options):
        """Custom showerror to play a sound first."""
        self.play_sound("error")
        return _original_showerror(title, message, **options)
    # --- END SECTION ---

    def bring_to_front(self):
        self.lift()


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
            if hasattr(self, 'sound_switch'): self.sound_switch.configure(state="disabled") # Disable sound switch


    def _unlock_app(self):
        for btn in self.nav_buttons.values(): btn.configure(state="normal")
        self.launch_chrome_btn.configure(state="normal"); self.launch_firefox_btn.configure(state="normal")
        self.theme_combo.configure(state="normal")
        if hasattr(self, 'sound_switch'): self.sound_switch.configure(state="normal") # Enable sound switch

    def get_data_path(self, filename): return get_data_path(filename)
    def get_user_downloads_path(self): return get_user_downloads_path()
    def open_folder(self, path):
        try:
            if os.path.exists(path):
                if sys.platform == "win32": os.startfile(path)
                else: subprocess.call(["open" if sys.platform == "darwin" else "xdg-open", path])
        except Exception as e: 
            self.play_sound("error")
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def _load_icon(self, name, path, size=(20, 20)):
        try: self.icon_images[name] = ctk.CTkImage(Image.open(resource_path(path)), size=size)
        except Exception as e: print(f"Warning: Could not load icon '{name}': {e}")

    def launch_chrome_detached(self):
        port, p_dir = "9222", os.path.join(os.path.expanduser("~"), "ChromeProfileForNREGABot")
        os.makedirs(p_dir, exist_ok=True)
        paths = {"Darwin": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"], "Windows": [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]}
        b_path = next((p for p in paths.get(config.OS_SYSTEM, []) if os.path.exists(p)), None)
        if not b_path: 
            self.play_sound("error")
            messagebox.showerror("Error", "Google Chrome not found."); 
            return
        try:
            cmd = [b_path, f"--remote-debugging-port={port}", f"--user-data-dir={p_dir}", config.MAIN_WEBSITE_URL, "https://bookmark.nregabot.com/"]
            flags = 0x00000008 if config.OS_SYSTEM == "Windows" else 0
            subprocess.Popen(cmd, creationflags=flags, start_new_session=(config.OS_SYSTEM != "Windows"))
            self.play_sound("success")
            messagebox.showinfo("Chrome Launched", "Chrome is starting. Please log in to the NREGA website.")
        except Exception as e: 
            self.play_sound("error")
            messagebox.showerror("Error", f"Failed to launch Chrome:\n{e}")

    def launch_firefox_managed(self):
        if self.driver and messagebox.askyesno("Browser Running", "Close existing Firefox and start new?"): self.driver.quit(); self.driver = None
        elif self.driver: return
        try:
            p_dir = os.path.join(os.path.expanduser("~"), "FirefoxProfileForNREGABot"); os.makedirs(p_dir, exist_ok=True)
            opts = FirefoxOptions(); opts.add_argument("-profile"); opts.add_argument(p_dir)
            self.driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=opts)
            self.active_browser = "firefox"; 
            self.play_sound("success")
            messagebox.showinfo("Browser Launched", "Firefox is starting. Please log in.")
            self.driver.get(config.MAIN_WEBSITE_URL); self.driver.execute_script("window.open(arguments[0], '_blank');", "https://bookmark.nregabot.com/")
            self.driver.switch_to.window(self.driver.window_handles[0])
        except Exception as e: 
            self.play_sound("error")
            messagebox.showerror("Error", f"Failed to launch Firefox:\n{e}"); 
            self.driver = None; self.active_browser = None

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
        self.play_sound("error")
        messagebox.showerror("Connection Failed", "No browser is running. Please launch one first."); return None

    def _connect_to_chrome(self):
        try:
            opts = ChromeOptions(); opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            driver = webdriver.Chrome(options=opts); self.active_browser = 'chrome'; return driver
        except WebDriverException as e: 
            self.play_sound("error")
            messagebox.showerror("Connection Failed", f"Could not connect to Chrome.\nError: {e}"); return None

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

        sound_frame = ctk.CTkFrame(controls, fg_color="transparent"); sound_frame.pack(side="left", padx=5, fill="y")
        ctk.CTkLabel(sound_frame, text="Sound:").pack(side="left", padx=(0, 5))
        self.sound_switch = ctk.CTkSwitch(sound_frame, text="", variable=self.sound_switch_var, onvalue=True, offvalue=False, command=self._on_sound_toggle, width=0)
        self.sound_switch.pack(side="left")

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

        ctk.CTkLabel(parent, text="Category Filter:", font=ctk.CTkFont(size=12)).pack(fill="x", padx=10, pady=(5, 2))
        categories = ["All Automations"] + list(self.get_tabs_definition().keys())
        self.category_filter_menu = ctk.CTkOptionMenu(parent, values=categories, command=self._on_category_filter_change)
        self.category_filter_menu.set(self.last_selected_category)
        self.category_filter_menu.pack(fill="x", padx=10, pady=(0, 15))

        for cat, tabs in self.get_tabs_definition().items():
            cat_frame = CollapsibleFrame(parent, title=cat)
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
        
        self._filter_nav_menu(self.last_selected_category)

    def _on_category_filter_change(self, selected_category: str):
        """Called when the user selects a new category from the dropdown."""
        save_config('last_selected_category', selected_category)
        self._filter_nav_menu(selected_category)

    def _filter_nav_menu(self, selected_category: str):
        """Shows or hides category frames based on the filter."""
        for category, frame in self.category_frames.items():
            frame.pack_forget()
            if selected_category == "All Automations" or category == selected_category:
                frame.pack(fill="x", pady=0, padx=0)

    def _create_content_frames(self):
        self.content_frames.clear()
        self.tab_instances.clear()
        self.show_frame("About", raise_frame=False)

    def get_tabs_definition(self):
        return {
            "Core NREGA Tasks": {
                "MR Gen": {"creation_func": MusterrollGenTab, "icon": self.icon_images.get("emoji_mr_gen"), "key": "muster"},
                "MR Fill": {"creation_func": MrFillTab, "icon": self.icon_images.get("emoji_mr_fill"), "key": "mr_fill"},
                "MR Payment": {"creation_func": MsrTab, "icon": self.icon_images.get("emoji_mr_payment"), "key": "msr"},
                "Gen Wagelist": {"creation_func": WagelistGenTab, "icon": self.icon_images.get("emoji_gen_wagelist"), "key": "gen"},
                "Send Wagelist": {"creation_func": WagelistSendTab, "icon": self.icon_images.get("emoji_send_wagelist"), "key": "send"},
                "FTO Generation": {"creation_func": FtoGenerationTab, "icon": self.icon_images.get("emoji_fto_gen"), "key": "fto_gen"},
                "Scheme Closing": {"creation_func": SchemeClosingTab, "icon": self.icon_images.get("emoji_scheme_closing"), "key": "scheme_close"},
                "Del Work Alloc": {"creation_func": DelWorkAllocTab, "icon": self.icon_images.get("emoji_del_work_alloc"), "key": "del_work_alloc"},
                "Duplicate MR Print": {"creation_func": DuplicateMrTab, "icon": self.icon_images.get("emoji_duplicate_mr"), "key": "dup_mr"},
                "Demand": {"creation_func": DemandTab, "icon": self.icon_images.get("emoji_demand"), "key": "demand"},
            },
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
                "PDF Merger": {"creation_func": PdfMergerTab, "icon": self.icon_images.get("emoji_pdf_merger"), "key": "pdf_merger"},
                "Zero Mr": {"creation_func": ZeroMrTab, "icon": self.icon_images.get("emoji_zero_mr"), "key": "zero_mr"},
                "File Manager": {"creation_func": FileManagementTab, "icon": self.icon_images.get("emoji_file_manager"), "key": "file_manager"},
            },
            "Reporting": {
                "Social Audit Report": {"creation_func": SAReportTab, "icon": self.icon_images.get("emoji_social_audit"), "key": "social_audit_respond"},
                "MIS Reports": {"creation_func": MisReportsTab, "icon": self.icon_images.get("emoji_mis_reports"), "key": "mis_reports"},
                "MR Tracking": {"creation_func": MrTrackingTab, "icon": self.icon_images.get("emoji_mr_tracking"), "key": "mr_tracking"},
                "Issued MR Details": {"creation_func": IssuedMrReportTab, "icon": self.icon_images.get("emoji_issued_mr_report"), "key": "issued_mr_report"},
                "Dashboard Report": {"creation_func": DashboardReportTab, "icon": self.icon_images.get("emoji_dashboard_report"), "key": "dashboard_report"},
            },
            "Application": {
                 "Feedback": {"creation_func": FeedbackTab, "icon": self.icon_images.get("emoji_feedback")},
                 "About": {"creation_func": AboutTab, "icon": self.icon_images.get("emoji_about")},
            }
        }

    def show_frame(self, page_name, raise_frame=True):
        if page_name not in self.tab_instances:
            tabs = self.get_tabs_definition()
            for cat, tab_items in tabs.items():
                if page_name in tab_items:
                    frame = ctk.CTkFrame(self.content_area)
                    frame.grid(row=0, column=0, sticky="nsew")
                    self.content_frames[page_name] = frame
                    instance = tab_items[page_name]["creation_func"](frame, self)
                    instance.pack(expand=True, fill="both")
                    self.tab_instances[page_name] = instance
                    break 

        if raise_frame:
            if page_name in self.content_frames:
                self.content_frames[page_name].tkraise()
            for name, btn in self.nav_buttons.items():
                btn.configure(fg_color=("gray90", "gray28") if name == page_name else "transparent")

    def open_web_file_manager(self):
        if self.license_info.get('key'):
            auth_url = f"{config.LICENSE_SERVER_URL}/authenticate-from-app/{self.license_info['key']}?next=files"
            webbrowser.open_new_tab(auth_url)
        else:
            self.play_sound("error")
            messagebox.showerror("Error", "License key not found. Please log in to use the web file manager.")

    def switch_to_if_edit_with_data(self, data):
        """Switches to the IF Editor tab and passes data from the WC Gen tab."""
        if not data:
            return
        
        self.show_frame("IF Editor")
        
        if_edit_instance = self.tab_instances.get("IF Editor")
        if if_edit_instance and hasattr(if_edit_instance, 'load_data_from_wc_gen'):
            if_edit_instance.load_data_from_wc_gen(data)
            self.play_sound("success")
            messagebox.showinfo(
                "Data Transferred",
                f"{len(data)} work code(s) have been successfully transferred to the IF Editor tab.\n\n"
                "You can now configure and start the IF Editor automation.",
                parent=self
            )
        else:
            self.play_sound("error")
            messagebox.showerror("Error", "Could not find the IF Editor tab instance or it's missing the required method.")

    def switch_to_msr_tab_with_data(self, workcodes: str, panchayat_name: str):
        """Switches to the MSR Payment tab and passes data from MR Tracking."""
        
        # Ensure the frame and instance exist
        self.show_frame("MR Payment")
        
        msr_instance = self.tab_instances.get("MR Payment")
        
        if msr_instance and hasattr(msr_instance, 'load_data_from_mr_tracking'):
            msr_instance.load_data_from_mr_tracking(workcodes, panchayat_name)
            self.play_sound("success")
            messagebox.showinfo(
                "Data Transferred",
                f"{len(workcodes.splitlines())} workcode(s) and Panchayat '{panchayat_name}' have been transferred to the MR Payment tab.",
                parent=self
            )
        else:
            self.play_sound("error")
            messagebox.showerror("Error", "Could not find the MR Payment tab instance or it's missing the required method.")
    # --- NEW METHOD to send data to eMB Entry ---
    def switch_to_emb_entry_with_data(self, workcodes: str, panchayat_name: str):
        """Switches to the eMB Entry tab and passes data from MR Tracking."""
        
        # Ensure the frame and instance exist
        self.show_frame("eMB Entry")
        
        emb_instance = self.tab_instances.get("eMB Entry")
        
        if emb_instance and hasattr(emb_instance, 'load_data_from_mr_tracking'):
            emb_instance.load_data_from_mr_tracking(workcodes, panchayat_name)
            self.play_sound("success")
            messagebox.showinfo(
                "Data Transferred",
                f"{len(workcodes.splitlines())} workcode(s) and Panchayat '{panchayat_name}' have been transferred to the eMB Entry tab.",
                parent=self
            )
        else:
            self.play_sound("error")
            messagebox.showerror("Error", "Could not find the eMB Entry tab instance or it's missing the required method.")
    # --- END NEW METHOD ---

    def switch_to_mr_fill_with_data(self, workcodes: str, panchayat_name: str):
        """Switches to the MR Fill tab and passes data from Dashboard Report."""
        
        # Ensure the frame and instance exist
        self.show_frame("MR Fill")
        
        mr_fill_instance = self.tab_instances.get("MR Fill")
        
        if mr_fill_instance and hasattr(mr_fill_instance, 'load_data_from_dashboard'):
            mr_fill_instance.load_data_from_dashboard(workcodes, panchayat_name)
            self.play_sound("success")
            messagebox.showinfo(
                "Data Transferred",
                f"{len(workcodes.splitlines())} workcode(s) and Panchayat '{panchayat_name}' have been transferred to the MR Fill tab.",
                parent=self
            )
        else:
            self.play_sound("error")
            messagebox.showerror("Error", "Could not find the MR Fill tab instance or it's missing the required method.")
    # --- END NEW METHOD ---

    # --- NEW METHOD to send user to MR Tracking for ABPS ---
    def switch_to_mr_tracking_for_abps(self):
        """
        Switches to the MR Tracking tab and pre-sets it
        for checking ABPS pendency.
        """
        # Ensure the frame and instance exist
        self.show_frame("MR Tracking")
        
        mr_tracking_instance = self.tab_instances.get("MR Tracking")
        
        if mr_tracking_instance and hasattr(mr_tracking_instance, 'set_for_abps_check'):
            mr_tracking_instance.set_for_abps_check()
            # Play sound *before* the popup
            self.play_sound("success")
            messagebox.showinfo(
                "Action Required",
                "fill the details to check ABPS Labour",
                parent=self
            )
        else:
            self.play_sound("error")
            messagebox.showerror("Error", "Could not find the MR Tracking tab instance or it's missing the required method.")
    # --- END NEW METHOD ---

    def switch_to_duplicate_mr_with_data(self, workcodes: str, panchayat_name: str):
        """Switches to the Duplicate MR Print tab and passes data."""
        
        # Ensure the frame and instance exist
        self.show_frame("Duplicate MR Print")
        
        dup_mr_instance = self.tab_instances.get("Duplicate MR Print")
        
        if dup_mr_instance and hasattr(dup_mr_instance, 'load_data_from_report'):
            dup_mr_instance.load_data_from_report(workcodes, panchayat_name)
            self.play_sound("success")
            messagebox.showinfo(
                "Data Transferred",
                f"{len(workcodes.splitlines())} workcode(s) and Panchayat '{panchayat_name}' have been transferred to the Duplicate MR Print tab.",
                parent=self
            )
        else:
            self.play_sound("error")
            messagebox.showerror("Error", "Could not find the Duplicate MR Print tab instance or it's missing the required method 'load_data_from_report'.")
    # --- END NEW METHOD ---

    # --- NEW METHOD to send data to Zero MR ---
    def switch_to_zero_mr_tab_with_data(self, data_list: list):
        """Switches to the Zero MR tab and passes data from MR Tracking."""
        
        # Ensure the frame and instance exist
        self.show_frame("Zero Mr")
        
        zero_mr_instance = self.tab_instances.get("Zero Mr")
        
        if zero_mr_instance and hasattr(zero_mr_instance, 'load_data_from_mr_tracking'):
            zero_mr_instance.load_data_from_mr_tracking(data_list)
            self.play_sound("success")
            messagebox.showinfo(
                "Data Transferred",
                f"{len(data_list)} MR(s) have been transferred to the Zero MR tab.",
                parent=self
            )
        else:
            self.play_sound("error")
            messagebox.showerror("Error", "Could not find the Zero MR tab instance or it's missing the required method 'load_data_from_mr_tracking'.")
    # --- END NEW METHOD ---
    
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
            if not os.path.exists(src): 
                self.play_sound("error")
                messagebox.showerror("Error", f"Demo file not found: demo_{file_type}.csv"); 
                return
            save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], initialfile=f"{file_type}_data.csv", title=f"Save Demo {file_type.upper()} CSV")
            if save_path: 
                shutil.copyfile(src, save_path); 
                self.play_sound("success")
                messagebox.showinfo("Success", f"Demo file saved to:\n{save_path}")
        except Exception as e: 
            self.play_sound("error")
            messagebox.showerror("Error", f"Could not save demo file: {e}")

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
                self.license_info = {**data, 'key': key}
                with open(get_data_path('license.dat'), 'w') as f:
                    json.dump(self.license_info, f)
                if not is_startup_check:
                    self.play_sound("success")
                    messagebox.showinfo("License Valid", f"Activation successful!\nExpires on: {self.license_info['expires_at'].split('T')[0]}")
                return True
            else:
                lic_file = get_data_path('license.dat')
                if os.path.exists(lic_file):
                    os.remove(lic_file)
                if not is_startup_check:
                    self.play_sound("error")
                    messagebox.showerror("Validation Failed", data.get('reason', 'Unknown error.'))
                return False

        except requests.exceptions.RequestException:
            self.after(0, self.set_server_status, False)
            if not is_startup_check:
                self.play_sound("error")
                messagebox.showerror("Connection Error", "Could not connect to the license server. Please check your internet connection.")
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
            if not key: 
                self.play_sound("error")
                messagebox.showwarning("Input Required", "Please enter a license key.", parent=win); return
            if self.validate_on_server(key): activated.set(True); win.destroy()

        def on_login():
            email = email_entry.get().strip()
            if not email: 
                self.play_sound("error")
                messagebox.showwarning("Input Required", "Please enter your email.", parent=win); return
            login_btn.configure(state="disabled", text="Activating...")
            try:
                resp = requests.post(f"{config.LICENSE_SERVER_URL}/api/login-for-activation", json={"email": email, "machine_id": self.machine_id}, timeout=15)
                data = resp.json()
                if resp.status_code == 200 and data.get("status") == "success":
                    self.license_info = data
                    with open(get_data_path('license.dat'), 'w') as f: json.dump(self.license_info, f)
                    self.play_sound("success")
                    messagebox.showinfo("Success", f"Device activated!\nWelcome back, {data.get('user_name', 'User')}.")
                    activated.set(True); win.destroy()
                else:
                    reason = data.get("reason", "Unknown error.")
                    self.play_sound("error")
                    messagebox.showerror("Activation Failed", reason, parent=win)
                    if data.get("action") == "redirect" and data.get("url"):
                        webbrowser.open_new_tab(data["url"])
            except requests.exceptions.RequestException as e: 
                self.play_sound("error")
                messagebox.showerror("Connection Error", f"Could not connect: {e}", parent=win)
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
        fields = ["Full Name", "Email", "Mobile", "Block"]
        for field in fields:
            key = field.lower().replace(" ", "_")
            ctk.CTkLabel(scroll, text=field, anchor="w").pack(fill="x", padx=10)
            entry = ctk.CTkEntry(scroll)
            entry.pack(fill="x", padx=10, pady=(0, 10))
            entries[key] = entry

        ctk.CTkLabel(scroll, text="State", anchor="w").pack(fill="x", padx=10)
        state_menu = ctk.CTkOptionMenu(scroll, values=["Jharkhand"])
        state_menu.set("Jharkhand")
        state_menu.configure(state="disabled")
        state_menu.pack(fill="x", padx=10, pady=(0, 10))
        entries['state'] = state_menu 

        jharkhand_districts = [
            "Bokaro", "Chatra", "Deoghar", "Dhanbad", "Dumka", "East Singhbhum",
            "Garhwa", "Giridih", "Godda", "Gumla", "Hazaribagh", "Jamtara",
            "Khunti", "Koderma", "Latehar", "Lohardaga", "Pakur", "Palamu",
            "Ramgarh", "Ranchi", "Sahebganj", "Saraikela Kharsawan", "Simdega",
            "West Singhbhum", "Others"
        ]
        ctk.CTkLabel(scroll, text="District", anchor="w").pack(fill="x", padx=10)
        district_menu = ctk.CTkOptionMenu(scroll, values=jharkhand_districts)
        district_menu.set("Select a District") 
        district_menu.pack(fill="x", padx=10, pady=(0, 10))
        entries['district'] = district_menu 

        ctk.CTkLabel(scroll, text="Pincode", anchor="w").pack(fill="x", padx=10)
        pincode_entry = ctk.CTkEntry(scroll)
        pincode_entry.pack(fill="x", padx=10, pady=(0, 10))
        entries['pincode'] = pincode_entry

        successful = tkinter.BooleanVar(value=False)
        def submit_request():
            import re
            user_data = {k: e.get().strip() for k, e in entries.items()}
            email, mobile = user_data.get('email', ''), user_data.get('mobile', '')
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email): 
                self.play_sound("error")
                messagebox.showwarning("Invalid Input", "Valid email is required.", parent=win); return
            if not (mobile.isdigit() and len(mobile) == 10): 
                self.play_sound("error")
                messagebox.showwarning("Invalid Input", "Valid 10-digit mobile is required.", parent=win); return
            if user_data.get('district') == "Select a District": 
                self.play_sound("error")
                messagebox.showwarning("Input Required", "Please select a district.", parent=win); return

            user_data["name"] = user_data.pop("full_name")
            user_data["machine_id"] = self.machine_id
            if not all(user_data.values()): 
                self.play_sound("error")
                messagebox.showwarning("Input Required", "All fields are required.", parent=win); return

            submit_btn.configure(state="disabled", text="Requesting...")
            try:
                resp = requests.post(f"{config.LICENSE_SERVER_URL}/api/request-trial", json=user_data, timeout=15, headers={'User-Agent': f'{config.APP_NAME}/{config.APP_VERSION}'})
                data = resp.json()
                if resp.status_code == 200 and data.get("status") == "success":
                    self.license_info = {'key': data.get("key"), 'expires_at': data.get('expires_at'), 'user_name': user_data['name'], 'key_type': 'trial'}
                    with open(get_data_path('license.dat'), 'w') as f: json.dump(self.license_info, f)
                    self.play_sound("success")
                    messagebox.showinfo("Success!", f"{data.get('reason', 'Trial has started!')}\nExpires on: {self.license_info['expires_at'].split('T')[0]}")
                    successful.set(True); win.destroy()
                else: 
                    self.play_sound("error")
                    messagebox.showerror("Trial Error", data.get("reason", "Could not start trial."), parent=win)
            except requests.exceptions.RequestException: 
                self.play_sound("error")
                messagebox.showerror("Connection Error", "Could not connect to server.", parent=win)
            finally:
                if submit_btn.winfo_exists(): submit_btn.configure(state="normal", text="Start Trial")

        submit_btn = ctk.CTkButton(scroll, text="Start Trial", command=submit_request); submit_btn.pack(pady=20, ipady=4, fill='x', padx=10)
        self.wait_window(win); return successful.get()

    def show_purchase_window(self, context='upgrade'):
        form = {k.replace('user_', ''): v for k, v in self.license_info.items() if k.startswith('user_')}
        form['existing_key'] = self.license_info.get('key')
        
        form['plan_type'] = self.license_info.get('key_type', 'monthly')
        form['max_devices'] = self.license_info.get('max_devices', 1)

        if not form.get('existing_key'):
            self.play_sound("error")
            messagebox.showerror(
                "License Error", 
                "Cannot open purchase page because your license key is not available. Please restart the app or contact support.", 
                parent=self
            )
            return

        try:
            url_params = {k: v for k, v in form.items() if v is not None}
            buy_url = f"{config.LICENSE_SERVER_URL}/buy?{urlencode(url_params)}"
            webbrowser.open_new_tab(buy_url)
        except Exception as e:
            self.play_sound("error")
            messagebox.showerror("Error", f"Could not open the purchase page: {e}", parent=self)

    def check_expiry_and_notify(self):
        expires_str = self.license_info.get('expires_at')
        if not expires_str: return False
        try:
            days = (datetime.fromisoformat(expires_str.split('T')[0]).date() - datetime.now().date()).days
            if 0 <= days < 7:
                msg = f"License expires {'today' if days == 0 else f'in {days} day' + ('s' if days != 1 else '')}."
                self.play_sound("error") 
                messagebox.showwarning("License Expiring", f"{msg}\nPlease renew from the website."); self.open_on_about_tab = True; return True
        except (ValueError, TypeError) as e:
            if SENTRY_DSN: sentry_sdk.capture_exception(e)
        return False

    def start_automation_thread(self, key, target, args=()):
        if self.automation_threads.get(key) and self.automation_threads[key].is_alive():
            self.play_sound("error")
            messagebox.showwarning("In Progress", "Task is already running."); return
        
        self.play_sound("start") 
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
            # --- ADD THIS LINE TO QUIT PYGAME ---
            pygame.mixer.quit()
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
        self.play_sound("update") 
        if messagebox.askyesno("Update Available", f"Version {version} is available. Go to the 'Updates' tab?"):
            self.show_frame("About")
            about = self.tab_instances.get("About")
            if about: about.tab_view.set("Updates")

    def update_history(self, key, val): self.history_manager.save_entry(key, val)

    def remove_history(self, key, val):
        """Asks the HistoryManager to remove a specific entry."""
        if hasattr(self.history_manager, 'remove_entry'):
            self.history_manager.remove_entry(key, val)
        else:
            print(f"Warning: HistoryManager is missing the 'remove_entry' method.")

    def download_and_install_update(self, url, version):
        about = self.tab_instances.get("About")
        if not about: 
            self.play_sound("error")
            messagebox.showerror("Error", "Could not find About Tab."); return
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
                    self.play_sound("success")
                    messagebox.showinfo("Ready to Update", "The app will now close to run the installer.", parent=self)
                    os.startfile(dl_path); self.after(200, os._exit, 0)
                elif sys.platform == "darwin":
                    subprocess.call(["open", dl_path])
                    self.play_sound("success")
                    self.after(0, messagebox.showinfo, "Instructions", f"'{filename}' has been opened.\nDrag the icon to Applications.\nApp will now close.")
                    self.after(3000, self.on_closing, True)
            except Exception as e:
                self.play_sound("error")
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
        try:
            # Try to play a fatal error sound
            pygame.mixer.init()
            pygame.mixer.Sound(resource_path("assets/sounds/error.wav")).play()
            time.sleep(1) # Give sound time to play
        except Exception:
            pass 
        messagebox.showerror("Fatal Startup Error", f"A critical error occurred:\n\n{e}\n\nThe app will now close.")
    finally: s.close()