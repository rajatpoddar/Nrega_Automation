# tabs/fto_generation_tab.py (Upgraded to CustomTkinter)
import tkinter
from tkinter import ttk, messagebox
import customtkinter as ctk
import threading, time, json, os, re
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoAlertPresentException, NoSuchElementException
import config

widgets = {}
CONFIG_FILE = None

def style_treeview(app):
    """Applies customtkinter-like styling to the ttk.Treeview widget."""
    style = ttk.Style()
    bg_color = app._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
    text_color = app._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
    header_bg = app._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"])
    selected_color = app._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["hover_color"])
    style.theme_use("default")
    style.configure("Treeview", background=bg_color, foreground=text_color, fieldbackground=bg_color, borderwidth=0)
    style.map('Treeview', background=[('selected', selected_color)])
    style.configure("Treeview.Heading", background=header_bg, foreground=text_color, relief="flat")
    style.map("Treeview.Heading", background=[('active', selected_color)])

def _capitalize_entry(var):
    """Helper function to automatically capitalize text in an entry widget."""
    var.set(var.get().upper())

def create_tab(parent_frame, app_instance):
    """Creates the FTO Generation tab UI with CustomTkinter."""
    global CONFIG_FILE
    CONFIG_FILE = app_instance.get_data_path('fto_gen_config.json')

    parent_frame.grid_columnconfigure(0, weight=1)
    parent_frame.grid_rowconfigure(1, weight=1)

    controls_frame = ctk.CTkFrame(parent_frame)
    controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    controls_frame.grid_columnconfigure((1, 3), weight=1)

    widgets['district_var'] = ctk.StringVar()
    widgets['district_var'].trace_add('write', lambda *args: _capitalize_entry(widgets['district_var']))
    ctk.CTkLabel(controls_frame, text="District:").grid(row=0, column=0, sticky='w', padx=15, pady=5)
    widgets['district_entry'] = ctk.CTkEntry(controls_frame, textvariable=widgets['district_var'])
    widgets['district_entry'].grid(row=0, column=1, sticky='ew', padx=15, pady=5)

    ctk.CTkLabel(controls_frame, text="Block:").grid(row=0, column=2, sticky='w', padx=10, pady=5)
    widgets['block_entry'] = ctk.CTkEntry(controls_frame)
    widgets['block_entry'].grid(row=0, column=3, sticky='ew', padx=15, pady=5)

    ctk.CTkLabel(controls_frame, text="Panchayat:").grid(row=1, column=0, sticky='w', padx=15, pady=5)
    widgets['panchayat_entry'] = ctk.CTkEntry(controls_frame)
    widgets['panchayat_entry'].grid(row=1, column=1, columnspan=3, sticky='ew', padx=15, pady=5)
    
    ctk.CTkLabel(controls_frame, text="User ID:").grid(row=2, column=0, sticky='w', padx=15, pady=5)
    widgets['user_id_entry'] = ctk.CTkEntry(controls_frame)
    widgets['user_id_entry'].grid(row=2, column=1, columnspan=3, sticky='ew', padx=15, pady=5)

    note_text = "Note: You can manually log in, then run this automation to create both FTOs (Aadhaar-based & Top-up)."
    ctk.CTkLabel(controls_frame, text=note_text, text_color="gray50", wraplength=500).grid(row=3, column=0, columnspan=4, sticky='w', padx=15, pady=10)

    action_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
    action_frame.grid(row=4, column=0, columnspan=4, sticky='ew', pady=10)
    action_frame.grid_columnconfigure((0, 1, 2), weight=1)

    widgets['start_button'] = ctk.CTkButton(action_frame, text="▶ Start FTO Process", command=lambda: start_automation(app_instance))
    widgets['start_button'].grid(row=0, column=0, sticky="ew", padx=(0,5))
    widgets['stop_button'] = ctk.CTkButton(action_frame, text="Stop", command=lambda: app_instance.stop_events["fto_gen"].set(), state="disabled", fg_color="gray50")
    widgets['stop_button'].grid(row=0, column=1, sticky="ew", padx=5)
    widgets['reset_button'] = ctk.CTkButton(action_frame, text="Reset", fg_color="transparent", border_width=2, border_color=("gray70", "gray40"), text_color=("gray10", "#DCE4EE"), command=lambda: reset_ui(app_instance))
    widgets['reset_button'].grid(row=0, column=2, sticky="ew", padx=(5,0))
    
    notebook = ctk.CTkTabview(parent_frame)
    notebook.grid(row=1, column=0, sticky="nsew")
    logs_frame = notebook.add("Logs & Status")
    results_frame = notebook.add("Results (FTO Numbers)")

    logs_frame.grid_columnconfigure(0, weight=1); logs_frame.grid_rowconfigure(2, weight=1)
    widgets['status_label'] = ctk.CTkLabel(logs_frame, text="Status: Ready")
    widgets['status_label'].grid(row=0, column=0, sticky='w')
    widgets['progress_bar'] = ctk.CTkProgressBar(logs_frame)
    widgets['progress_bar'].set(0)
    widgets['progress_bar'].grid(row=1, column=0, sticky='ew', pady=5)
    widgets['log_display'] = ctk.CTkTextbox(logs_frame, wrap=tkinter.WORD, state="disabled")
    widgets['log_display'].grid(row=2, column=0, sticky='nsew')

    results_frame.grid_columnconfigure(0, weight=1); results_frame.grid_rowconfigure(0, weight=1)
    cols = ("Page", "FTO Number", "Timestamp")
    widgets['results_tree'] = ttk.Treeview(results_frame, columns=cols, show='headings')
    widgets['results_tree'].heading("Page", text="Page Processed"); widgets['results_tree'].heading("FTO Number", text="FTO Number Generated"); widgets['results_tree'].heading("Timestamp", text="Time")
    widgets['results_tree'].column("Page", width=150); widgets['results_tree'].column("FTO Number", width=400); widgets['results_tree'].column("Timestamp", width=100, anchor='center')
    widgets['results_tree'].grid(row=0, column=0, sticky='nsew')
    scrollbar = ctk.CTkScrollbar(results_frame, command=widgets['results_tree'].yview)
    widgets['results_tree'].configure(yscroll=scrollbar.set); scrollbar.grid(row=0, column=1, sticky='ns')
    style_treeview(app_instance)

    load_inputs()

def set_ui_state(running):
    state = "disabled" if running else "normal"
    widgets['start_button'].configure(state=state)
    widgets['stop_button'].configure(state="normal" if running else "disabled")
    widgets['reset_button'].configure(state=state)
    for key in ['district_entry', 'block_entry', 'panchayat_entry', 'user_id_entry']: widgets[key].configure(state=state)

def update_status(text, progress=None):
    widgets['status_label'].configure(text=f"Status: {text}")
    if progress is not None: widgets['progress_bar'].set(progress / 100)

# Logic functions are included for completeness but are unchanged.
def save_inputs():
    data = {'district': widgets['district_entry'].get(), 'block': widgets['block_entry'].get(), 'panchayat': widgets['panchayat_entry'].get(), 'user_id': widgets['user_id_entry'].get()}
    try:
        with open(CONFIG_FILE, 'w') as f: json.dump(data, f, indent=4)
    except Exception as e: print(f"Error saving FTO config: {e}")

def load_inputs():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f: data = json.load(f)
            widgets['district_entry'].insert(0, data.get('district', '')); widgets['block_entry'].insert(0, data.get('block', ''))
            widgets['panchayat_entry'].insert(0, data.get('panchayat', '')); widgets['user_id_entry'].insert(0, data.get('user_id', ''))
    except (json.JSONDecodeError, IOError) as e: print(f"Error loading FTO config: {e}")

def reset_ui(app):
    if messagebox.askokcancel("Reset Form?", "This will clear all inputs, results, and logs."):
        for key in ['district_entry', 'block_entry', 'panchayat_entry', 'user_id_entry']: widgets[key].delete(0, tkinter.END)
        app.clear_log(widgets['log_display'])
        for item in widgets['results_tree'].get_children(): widgets['results_tree'].delete(item)
        update_status("Ready", 0)
        app.log_message(widgets['log_display'], "Form has been reset.")
        if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)

def start_automation(app): save_inputs(); app.start_automation_thread("fto_gen", run_automation_logic)
def _log_result(app, page_name, fto_number): app.after(0, lambda: widgets['results_tree'].insert("", "end", values=(page_name, fto_number, datetime.now().strftime("%H:%M:%S"))))

def process_verification_page(app, driver, wait, verification_url, page_identifier):
    try:
        app.log_message(widgets['log_display'], f"Navigating to {page_identifier}..."); driver.get(verification_url)
        wait.until(EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_wage_list_verify"))); app.log_message(widgets['log_display'], "Verification page loaded.")
        if not driver.find_elements(By.XPATH, "//input[contains(@id, '_auth')]"): app.log_message(widgets['log_display'], "No records found on this page.", "warning"); return "No records to process."
        app.log_message(widgets['log_display'], "Accepting all rows..."); driver.execute_script("document.querySelectorAll('input[id*=\"_auth\"]').forEach(radio => radio.click());")
        app.log_message(widgets['log_display'], "Clicking 'Submit'..."); wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ch_verified"))).click()
        app.log_message(widgets['log_display'], "Clicking 'Authorise'..."); wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_btn"))).click()
        app.log_message(widgets['log_display'], "Waiting for confirmation..."); alert = wait.until(EC.alert_is_present())
        fto_match = re.search(r'FTO No : \((.*?)\)', alert.text); fto_number = fto_match.group(1) if fto_match else "Not Found"
        app.log_message(widgets['log_display'], f"Captured FTO: {fto_number}", "success"); _log_result(app, page_identifier, fto_number); alert.accept()
    except TimeoutException: app.log_message(widgets['log_display'], "Page timed out or no records found.", "warning")
    except Exception as e: app.log_message(widgets['log_display'], f"Error during verification: {e}", "error")

def run_automation_logic(app):
    app.after(0, set_ui_state, True); app.clear_log(widgets['log_display'])
    app.after(0, lambda: [widgets['results_tree'].delete(item) for item in widgets['results_tree'].get_children()]); update_status("Starting...", 0)
    try:
        d, b, p, u = widgets['district_entry'].get().strip(), widgets['block_entry'].get().strip(), widgets['panchayat_entry'].get().strip(), widgets['user_id_entry'].get().strip()
        if not all([d, b, p, u]): messagebox.showerror("Input Required", "All fields are required."); app.after(0, set_ui_state, False); return
        driver = app.connect_to_chrome(); wait = WebDriverWait(driver, 20)
        login_url, v_url1, v_url2 = "https://mnregaweb3.nic.in/Netnrega/FTO/Login.aspx?&level=HomeACGP&state_code=34", "https://mnregaweb3.nic.in/netnrega/FTO/ftoverify_aadhar.aspx?cate=Z&Digest=KfhSIdpgz01z37eG0dybsw", "https://mnregaweb3.nic.in/netnrega/FTO/ftoverify_aadhar.aspx?wg_topup=S"
        app.log_message(widgets['log_display'], "Checking login status...")
        if "ftoindexframe.aspx" in driver.current_url.lower(): app.log_message(widgets['log_display'], "Already logged in.", "success"); update_status("Login detected...", 50)
        else:
            app.log_message(widgets['log_display'], "Navigating to Login Page..."); driver.get(login_url); update_status("Filling login details...", 10)
            try:
                Select(wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddl_District")))).select_by_visible_text(d)
                wait.until(lambda d: len(Select(d.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_Block")).options) > 1); Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_Block")).select_by_visible_text(b)
                wait.until(lambda d: len(Select(d.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_Panch")).options) > 1); Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_Panch")).select_by_visible_text(p)
            except NoSuchElementException: raise ValueError(f"A selection (District, Block, or Panchayat) was not found.")
            wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_txt_UserID"))).send_keys(u); app.log_message(widgets['log_display'], "Login details filled.")
            update_status("Waiting for manual login...", 25); app.after(0, lambda: messagebox.showinfo("Action Required", "Please enter your Password and CAPTCHA in the browser, then click 'Login'."))
            WebDriverWait(driver, 300).until(EC.url_contains("ftoindexframe.aspx")); app.log_message(widgets['log_display'], "Login successful!", "success"); update_status("Login successful...", 50)
        
        process_verification_page(app, driver, wait, v_url1, "Aadhaar FTO"); update_status("First page processed.", 75)
        process_verification_page(app, driver, wait, v_url2, "Top-Up FTO"); update_status("All tasks complete!", 100)
        app.log_message(widgets['log_display'], "Workflow complete."); app.after(0, lambda: messagebox.showinfo("Workflow Complete", "Check the Results tab for FTO numbers."))
    except Exception as e: error_msg = f"A critical error occurred: {e}"; app.log_message(widgets['log_display'], error_msg, "error"); messagebox.showerror("Automation Error", error_msg)
    finally: app.after(0, set_ui_state, False); app.after(0, update_status, "Finished.")