# main_app.py v2.3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading, time, subprocess, os, webbrowser, sys, requests, json, uuid
from PIL import Image, ImageTk
from packaging.version import parse as parse_version
from getmac import get_mac_address
from appdirs import user_data_dir
from pathlib import Path
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options

import config
from tabs import msr_tab, wagelist_gen_tab, wagelist_send_tab, wc_gen_tab, mb_entry_tab, if_edit_tab, musterroll_gen_tab, about_tab, jobcard_verify_tab, fto_generation_tab

def get_data_path(filename):
    app_name = "NREGA-Dashboard"
    app_author = "PoddarSolutions"
    data_dir = user_data_dir(app_name, app_author)
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, filename)

def get_user_downloads_path():
    downloads_dir = os.path.join(Path.home(), "Downloads", "NREGA-Dashboard")
    os.makedirs(downloads_dir, exist_ok=True)
    return downloads_dir

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class NregaDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NREGA Automation Dashboard")
        self.geometry("1x1+0+0")
        self.is_licensed = False
        self.license_info = {}
        self.machine_id = self._get_machine_id()
        self.open_on_about_tab = False
        self.after(100, self.start_app)

    def get_data_path(self, filename):
        return get_data_path(filename)
        
    def get_user_downloads_path(self):
        return get_user_downloads_path()

    def open_chrome_remote_debug(self, target_os):
        if config.OS_SYSTEM != target_os:
            messagebox.showinfo("Wrong Button", f"This button is for {target_os}. You are on {config.OS_SYSTEM}.")
            return
        port = "9222"
        profile_dir = os.path.expanduser("~/ChromeProfileForNREGA") if target_os == "Darwin" else "C:\\ChromeProfileForNREGA"
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" if target_os == "Darwin" else "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        if not os.path.exists(chrome_path):
            messagebox.showerror("Error", f"Google Chrome not found at:\n{chrome_path}")
            return
        try:
            os.makedirs(profile_dir, exist_ok=True)
            startup_url = "https://nrega.palojori.in"
            subprocess.Popen([chrome_path, f"--remote-debugging-port={port}", f"--user-data-dir={profile_dir}", startup_url])
            messagebox.showinfo("Chrome Launched", "Chrome is starting with remote debugging.\nPlease log in to the NREGA website before starting automation.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch Chrome:\n{e}")

    def _get_machine_id(self):
        try:
            mac = get_mac_address()
            if mac: return mac
            return "unknown-device-" + str(uuid.getnode())
        except Exception:
            return "error-getting-mac"

    def start_app(self):
        if not self.machine_id or "error" in self.machine_id:
             messagebox.showerror("Fatal Error", "Could not get a unique machine identifier. The application cannot continue.")
             self.destroy()
             return
        self.is_licensed = self.check_license()
        if self.is_licensed:
            self.check_expiry_and_notify()
            self.build_main_ui()
        else:
            self.destroy()

    def check_expiry_and_notify(self):
        """Checks for license expiry and shows a warning if it's within 3 days."""
        expires_at_str = self.license_info.get('expires_at')
        if not expires_at_str:
            return

        try:
            if 'T' in expires_at_str:
                expiry_date = datetime.fromisoformat(expires_at_str.split('T')[0])
            else:
                expiry_date = datetime.fromisoformat(expires_at_str)

            today = datetime.now()
            time_left = expiry_date - today

            if timedelta(days=0) < time_left <= timedelta(days=3):
                days_left = time_left.days + 1
                day_str = "day" if days_left == 1 else "days"
                messagebox.showwarning(
                    "License Expiring Soon",
                    f"Your license will expire in {days_left} {day_str}.\n\n"
                    "Please renew your subscription to continue using the application without interruption."
                )
                self.open_on_about_tab = True
        except (ValueError, TypeError) as e:
            print(f"Could not parse expiry date: {expires_at_str}. Error: {e}")

    def build_main_ui(self):
        self.geometry("1000x800")
        self.minsize(900, 700)
        self.center_window()
        self.style = ttk.Style(self)
        self.theme_current = "light"
        self._apply_theme()
        self.automation_threads = {}
        self.stop_events = {}
        self.csv_paths = {}
        self.configure(bg=config.STYLE_CONFIG["colors"]["light"]["background"])

        main_frame = ttk.Frame(self, padding="20", style="Background.TFrame")
        main_frame.pack(expand=True, fill="both")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=0)
        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=0)

        self._create_header(main_frame)
        self._create_notebook(main_frame)
        self._create_footer(main_frame)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        update_thread = threading.Thread(target=self.check_for_updates_background, daemon=True)
        update_thread.start()

    def _create_notebook(self, parent):
        notebook = ttk.Notebook(parent, style="Modern.TNotebook")
        notebook.grid(row=1, column=0, sticky="nsew")

        tabs_to_create = {
            "MR Gen": musterroll_gen_tab.create_tab,
            # "⚙️ Fill E-MR (Beta)": mr_fill_tab.create_tab,
            "MR Payment": msr_tab.create_tab,
            "FTO Generation": fto_generation_tab.create_tab, # <-- ADDED NEW TAB
            "Gen Wagelist": wagelist_gen_tab.create_tab,
            "Send Wagelist": wagelist_send_tab.create_tab,
            "Verify Jobcard": jobcard_verify_tab.create_tab,
            "⚠️ eMB Entry": mb_entry_tab.create_tab,
            "WC Gen (Abua)": wc_gen_tab.create_tab,
            "⚠️ IF Editor (Abua)": if_edit_tab.create_tab,
            "About": about_tab.create_tab,
        }

        about_tab_frame = None

        for tab_text, creation_func in tabs_to_create.items():
            tab_frame = ttk.Frame(notebook, padding="20", style="Tab.TFrame")
            notebook.add(tab_frame, text=tab_text)
            creation_func(tab_frame, self)
            if tab_text == "About":
                about_tab_frame = tab_frame

        if self.open_on_about_tab and about_tab_frame:
            self.after(100, lambda: notebook.select(about_tab_frame))


    def _create_header(self, parent):
        header_frame = ttk.Frame(parent, style="Background.TFrame")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        try:
            logo_path = resource_path("logo.png")
            logo_image = Image.open(logo_path).resize((50, 50), Image.Resampling.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(logo_image)
            ttk.Label(header_frame, image=self.logo_photo, style="Background.TLabel").pack(side="left", padx=(0, 15))
        except Exception as e:
            print(f"Warning: logo.png not found or failed to load. Skipping icon. Error: {e}")
        title_container = ttk.Frame(header_frame, style="Background.TFrame")
        title_container.pack(side="left", fill="x", expand=True)
        ttk.Label(title_container, text="NREGA Automation Dashboard", font=config.STYLE_CONFIG["font_title"], style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_container, text="Log in, navigate to the correct page, then start the required task.", font=config.STYLE_CONFIG["font_normal"], style="Secondary.TLabel").pack(anchor="w")
        button_frame = ttk.Frame(header_frame, style="Background.TFrame")
        button_frame.pack(side="right")

        ttk.Button(button_frame, text="Chrome (macOS)", command=lambda: self.open_chrome_remote_debug('Darwin'), style="macOS.TButton").pack(side="left", padx=5)
        ttk.Button(button_frame, text="Chrome (Windows)", command=lambda: self.open_chrome_remote_debug('Windows'), style="Windows.TButton").pack(side="left", padx=5)

        self.theme_button = ttk.Button(button_frame, text="🌙", command=self.toggle_theme, width=3)
        self.theme_button.pack(side="left", padx=(10, 0))

    def _create_footer(self, parent):
        footer_frame = ttk.Frame(parent, style="Background.TFrame")
        footer_frame.grid(row=2, column=0, sticky="ew", pady=(15, 0))

        copyright_label = ttk.Label(footer_frame, text="© 2025 Made with ❤️ by Rajat Poddar. ⚠️ Tabs : some prefilled use with caution", cursor="hand2", style="Secondary.TLabel", font=config.STYLE_CONFIG["font_small"])
        copyright_label.pack(side="left")
        copyright_label.bind("<Button-1>", lambda e: webbrowser.open_new_tab("https://github.com/rajatpoddar"))

        button_container = ttk.Frame(footer_frame, style="Background.TFrame")
        button_container.pack(side="right")
        ttk.Button(button_container, text="Workcode Extractor ↗", command=lambda: webbrowser.open_new_tab("https://workcode.palojori.in"), style="Link.TButton").pack(side="right", padx=(10, 0))
        ttk.Button(button_container, text="Nrega Palojori ↗", command=lambda: webbrowser.open_new_tab("https://nrega.palojori.in"), style="Link.TButton").pack(side="right")

    def check_license(self):
        license_file = get_data_path('license.dat')
        try:
            if os.path.exists(license_file):
                with open(license_file, 'r') as f:
                    self.license_info = json.load(f)
                    key = self.license_info.get('key')
                if self.validate_on_server(key, is_startup_check=True):
                    return True
                else:
                    if 'reason' in self.license_info and "Connection" in self.license_info['reason']:
                        return False
                    os.remove(license_file)
                    messagebox.showerror("License Invalid", "Your license is no longer valid. Please start a new trial or purchase a key.")
                    return self.show_activation_window()
            else:
                return self.show_activation_window()
        except Exception:
            if os.path.exists(license_file): os.remove(license_file)
            return self.show_activation_window()

    def validate_on_server(self, key, is_startup_check=False):
        server_url = "https://nrega-server.palojori.in/validate"
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            payload = {"key": key, "machine_id": self.machine_id}
            response = requests.post(server_url, json=payload, timeout=10, headers=headers)

            data = response.json()
            if response.status_code == 200 and data.get("status") == "valid":
                self.license_info = {'key': key, 'expires_at': data.get('expires_at')}
                if not is_startup_check:
                    messagebox.showinfo("License Valid", f"Activation successful!\nExpires on: {self.license_info['expires_at'].split('T')[0]}")
                return True
            else:
                reason = data.get("reason", "Unknown error.")
                if not is_startup_check:
                    messagebox.showerror("Validation Failed", f"License validation failed: {reason}")
                self.license_info['reason'] = reason
                return False
        except requests.exceptions.RequestException as e:
            print(f"A network error occurred during license validation: {e}")
            if is_startup_check:
                messagebox.showinfo(
                    "Server Offline",
                    "The license server is currently offline for an update. Please try again later."
                )
            else:
                messagebox.showerror(
                    "Connection Error",
                    "Could not connect to the license server. Please check your internet connection and try again."
                )
            self.license_info['reason'] = "Connection Error"
            return False

    def show_activation_window(self):
        activation_window = tk.Toplevel(self)
        activation_window.title("Activate Product")
        win_width, win_height = 450, 350
        x = (self.winfo_screenwidth() // 2) - (win_width // 2)
        y = (self.winfo_screenheight() // 2) - (win_height // 2)
        activation_window.geometry(f'{win_width}x{win_height}+{x}+{y}')
        activation_window.resizable(False, False)
        activation_window.transient(self)
        activation_window.grab_set()
        main_frame = ttk.Frame(activation_window, padding=20)
        main_frame.pack(expand=True, fill="both")
        ttk.Label(main_frame, text="Product Activation", font=config.STYLE_CONFIG["font_bold"]).pack(pady=(0, 10))
        is_activated = tk.BooleanVar(value=False)

        def on_start_trial():
            server_url = "https://nrega-server.palojori.in/request-trial"
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.post(server_url, json={"machine_id": self.machine_id}, timeout=15, headers=headers)
                data = response.json()
                if response.status_code == 200 and data.get("status") == "success":
                    self.license_info = {'key': data.get("key"), 'expires_at': data.get('expires_at')}
                    license_file = get_data_path('license.dat')
                    with open(license_file, 'w') as f: json.dump(self.license_info, f)
                    messagebox.showinfo("Trial Started", f"Your 30-day free trial has started!\nExpires on: {self.license_info['expires_at'].split('T')[0]}")
                    is_activated.set(True)
                    activation_window.destroy()
                else:
                    messagebox.showerror("Trial Error", data.get("reason", "Could not start trial."))
            except requests.exceptions.RequestException:
                messagebox.showerror("Connection Error", "Could not connect to the server to start a trial.")

        ttk.Button(main_frame, text="Start 30-Day Free Trial", style="Accent.TButton", command=on_start_trial).pack(pady=5, ipady=4, fill='x')
        ttk.Label(main_frame, text="— OR —").pack(pady=10)
        ttk.Label(main_frame, text="Enter a purchased license key:").pack(pady=(5, 5))
        key_entry = ttk.Entry(main_frame, width=40, font=config.STYLE_CONFIG["font_normal"])
        key_entry.pack(pady=5)
        key_entry.focus_set()

        def on_activate_paid():
            key = key_entry.get().strip()
            if not key:
                messagebox.showwarning("Input Required", "Please enter a license key.")
                return
            if self.validate_on_server(key):
                license_file = get_data_path('license.dat')
                with open(license_file, 'w') as f: json.dump(self.license_info, f)
                is_activated.set(True)
                activation_window.destroy()

        ttk.Button(main_frame, text="Activate with Key", command=on_activate_paid).pack(pady=10, ipady=4, fill='x')
        self.wait_window(activation_window)
        return is_activated.get()

    def check_for_updates_background(self):
        time.sleep(2)
        update_url = "https://nrega-dashboard.palojori.in/version.json"
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(update_url, timeout=5, headers=headers)
            if response.status_code == 200:
                data = response.json()
                latest_version_str = data.get("latest_version")
                download_url = data.get("download_url")
                if parse_version(latest_version_str) > parse_version(config.APP_VERSION):
                    self.after(0, self.show_update_prompt, latest_version_str, download_url)
        except Exception as e:
            print(f"Could not check for updates: {e}")

    def show_update_prompt(self, version, url):
        if messagebox.askyesno("Update Available", f"A new version ({version}) is available. Would you like to go to the download page now?"):
            webbrowser.open_new_tab(url)

    def center_window(self):
        self.update_idletasks()
        width, height = 1000, 800
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def _apply_theme(self):
        theme = config.STYLE_CONFIG["colors"][self.theme_current]
        font_normal = config.STYLE_CONFIG["font_normal"]
        self.style.theme_use('clam')
        self.style.configure('.', background=theme["background"], foreground=theme["text"], font=font_normal, borderwidth=0, focusthickness=0)
        self.style.configure("TFrame", background=theme["frame"])
        self.style.configure("Background.TFrame", background=theme["background"])
        self.style.configure("TLabel", background=theme["frame"], foreground=theme["text"], padding=5, font=font_normal)
        self.style.configure("Background.TLabel", background=theme["background"])
        self.style.configure("Title.TLabel", background=theme["background"], foreground=theme["text"])
        self.style.configure("Secondary.TLabel", background=theme["background"], foreground=theme["text_secondary"])
        self.style.configure("Instruction.TLabel", background=theme["frame"], foreground=theme["text_secondary"], font=config.STYLE_CONFIG["font_small"])
        self.style.configure("Status.TLabel", background=theme["frame"], foreground=theme["text_secondary"], padding=(5, 10))
        self.style.configure("TButton", background=theme["background"], foreground=theme["text"], font=font_normal, padding=(10, 8))
        self.style.map("TButton", background=[('active', theme["border"])])
        self.style.configure("Accent.TButton", background=theme["accent"], foreground=theme["accent_text"], font=config.STYLE_CONFIG["font_bold"])
        self.style.map("Accent.TButton", background=[('active', theme["accent"]), ('disabled', theme["border"])])
        self.style.configure("Outline.TButton", background=theme["background"], foreground=theme["text"], highlightbackground=theme["border"], highlightthickness=1)
        self.style.map("Outline.TButton", bordercolor=[('active', theme["accent"])], background=[('active', theme["background"])])
        self.style.configure("Link.TButton", foreground=theme["accent"], background=theme["background"], font=config.STYLE_CONFIG["font_small"])
        self.style.map("Link.TButton", foreground=[('active', theme["text"])])

        # Custom styles for the Chrome launch buttons
        self.style.configure("macOS.TButton", background='#ffcc80', foreground='#1d1d1f', font=font_normal, padding=(10, 8), borderwidth=0)
        self.style.map("macOS.TButton", background=[('active', '#ffb74d')])
        # Light blue for Windows button
        self.style.configure("Windows.TButton", background='#81d4fa', foreground='#1d1d1f', font=font_normal, padding=(10, 8), borderwidth=0)
        self.style.map("Windows.TButton", background=[('active', '#4fc3f7')])

        self.style.configure("TEntry", fieldbackground=theme["background"], foreground=theme["text"], bordercolor=theme["border"], insertcolor=theme["text"])
        self.style.map("TEntry", bordercolor=[('focus', theme["accent"])])
        self.style.configure("TCombobox", fieldbackground=theme["background"], foreground=theme["text"], bordercolor=theme["border"], arrowcolor=theme["text_secondary"], insertcolor=theme["text"])
        self.style.configure("TProgressbar", background=theme["accent"], troughcolor=theme["background"], bordercolor=theme["background"], lightcolor=theme["accent"], darkcolor=theme["accent"])
        self.style.configure("TLabelframe", background=theme["frame"], bordercolor=theme["border"], padding=15)
        self.style.configure("TLabelframe.Label", background=theme["frame"], foreground=theme["text_secondary"], font=font_normal)
        self.style.configure("Modern.TNotebook", background=theme["background"], borderwidth=0)
        self.style.configure("Modern.TNotebook.Tab", background=theme["background"], foreground=theme["text_secondary"], padding=(10, 8), font=font_normal, borderwidth=0)
        self.style.map("Modern.TNotebook.Tab", background=[("selected", theme["frame"]), ('active', theme["border"])], foreground=[("selected", theme["text"])])
        self.style.configure("Tab.TFrame", background=theme["frame"])
        self._update_non_ttk_widgets(self)

    def _update_non_ttk_widgets(self, parent):
        theme = config.STYLE_CONFIG["colors"][self.theme_current]
        self.configure(bg=theme["background"])
        if isinstance(parent, (scrolledtext.ScrolledText, tk.Text)):
            parent.config(bg=theme["background"], fg=theme["text"], insertbackground=theme["text"], relief="solid", bd=1, highlightthickness=1, highlightbackground=theme["border"])
        for child in parent.winfo_children():
            self._update_non_ttk_widgets(child)

    def toggle_theme(self):
        self.theme_current = "dark" if self.theme_current == "light" else "light"
        self.theme_button.config(text="☀️" if self.theme_current == "dark" else "🌙")
        self._apply_theme()

    def start_automation_thread(self, key, target_func, args=()):
        if self.automation_threads.get(key) and self.automation_threads[key].is_alive():
            messagebox.showwarning("In Progress", f"The '{key}' task is already running.")
            return

        self.stop_events[key] = threading.Event()
        thread_args = (self,) + args
        thread = threading.Thread(target=target_func, args=thread_args, daemon=True)
        self.automation_threads[key] = thread
        thread.start()

    def log_message(self, log_widget, message, level="info"):
        log_widget.config(state="normal")
        log_widget.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        log_widget.config(state="disabled")
        log_widget.see(tk.END)

    def clear_log(self, log_widget):
        log_widget.config(state="normal")
        log_widget.delete("1.0", tk.END)
        log_widget.config(state="disabled")

    def connect_to_chrome(self):
        try:
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except WebDriverException as e:
            messagebox.showerror(
                "Connection Failed",
                "Could not connect to Chrome. Please ensure:\n\n"
                "1. You have launched Chrome using one of the 'Chrome' buttons in the app.\n"
                "2. Chrome is still running.\n\n"
                f"Error: {e}"
            )
            raise ConnectionAbortedError("Failed to connect to Chrome debugger.") from e

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit? This will stop any running automations."):
            for event in self.stop_events.values():
                if event: event.set()
            time.sleep(0.5)
            self.destroy()

if __name__ == '__main__':
    app = NregaDashboard()
    app.mainloop()