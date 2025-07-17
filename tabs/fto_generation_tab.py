# tabs/fto_generation_tab.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import json
import os
import re
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoAlertPresentException, NoSuchElementException

import config

# Use a dictionary to hold widgets for easy access
widgets = {}
CONFIG_FILE = None # Will be set in create_tab

# --- UI and State Management Functions ---

def _capitalize_entry(event):
    """Helper function to automatically capitalize text in an entry widget."""
    widget = event.widget
    current_text = widget.get()
    widget.delete(0, tk.END)
    widget.insert(0, current_text.upper())

def create_tab(parent_frame, app_instance):
    """Creates the FTO Generation tab UI."""
    global CONFIG_FILE
    CONFIG_FILE = app_instance.get_data_path('fto_gen_config.json')

    parent_frame.columnconfigure(0, weight=1)
    parent_frame.rowconfigure(1, weight=1)

    # --- Controls Frame ---
    controls_frame = ttk.LabelFrame(parent_frame, text="FTO Generation Controls")
    controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10), padx=5)
    controls_frame.columnconfigure(1, weight=1)
    controls_frame.columnconfigure(3, weight=1)

    # Input fields
    ttk.Label(controls_frame, text="District:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
    widgets['district_entry'] = ttk.Entry(controls_frame)
    widgets['district_entry'].grid(row=0, column=1, sticky='ew', padx=5, pady=5)
    widgets['district_entry'].bind("<KeyRelease>", _capitalize_entry)

    ttk.Label(controls_frame, text="Block:").grid(row=0, column=2, sticky='w', padx=5, pady=5)
    widgets['block_entry'] = ttk.Entry(controls_frame)
    widgets['block_entry'].grid(row=0, column=3, sticky='ew', padx=5, pady=5)
    # Removed auto-capitalization from Block field as requested

    ttk.Label(controls_frame, text="Panchayat:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
    widgets['panchayat_entry'] = ttk.Entry(controls_frame)
    widgets['panchayat_entry'].grid(row=1, column=1, columnspan=3, sticky='ew', padx=5, pady=5)
    
    ttk.Label(controls_frame, text="User ID:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
    widgets['user_id_entry'] = ttk.Entry(controls_frame)
    widgets['user_id_entry'].grid(row=2, column=1, columnspan=3, sticky='ew', padx=5, pady=5)

    # Instructional Note
    note_text = "Note: You can manually log in to the 1st Signatory homepage, then run this automation to create both FTOs (Aadhaar-based & Top-up)."
    ttk.Label(controls_frame, text=note_text, style="Instruction.TLabel", wraplength=500).grid(row=3, column=0, columnspan=4, sticky='w', padx=5, pady=(10, 5))

    # Action Buttons
    action_frame = ttk.Frame(controls_frame)
    action_frame.grid(row=4, column=0, columnspan=4, sticky='ew', pady=(10, 5))
    action_frame.columnconfigure((0, 1, 2), weight=1)

    widgets['start_button'] = ttk.Button(action_frame, text="▶ Start FTO Process", style="Accent.TButton", command=lambda: start_automation(app_instance))
    widgets['start_button'].grid(row=0, column=0, sticky="ew", padx=(0,5), ipady=5)
    widgets['stop_button'] = ttk.Button(action_frame, text="Stop", command=lambda: app_instance.stop_events["fto_gen"].set(), state="disabled")
    widgets['stop_button'].grid(row=0, column=1, sticky="ew", padx=5, ipady=5)
    widgets['reset_button'] = ttk.Button(action_frame, text="Reset", style="Outline.TButton", command=lambda: reset_ui(app_instance))
    widgets['reset_button'].grid(row=0, column=2, sticky="ew", padx=(5,0), ipady=5)
    
    # --- Notebook for Logs and Results ---
    notebook = ttk.Notebook(parent_frame, style="Modern.TNotebook")
    notebook.grid(row=1, column=0, sticky="nsew", padx=5)
    
    logs_frame = ttk.Frame(notebook, padding=15)
    results_frame = ttk.Frame(notebook, padding=15)
    notebook.add(logs_frame, text="Logs & Status")
    notebook.add(results_frame, text="Results (FTO Numbers)")

    # --- Logs & Status Tab ---
    logs_frame.columnconfigure(0, weight=1)
    logs_frame.rowconfigure(2, weight=1)
    widgets['status_label'] = ttk.Label(logs_frame, text="Status: Ready", style="Status.TLabel")
    widgets['status_label'].grid(row=0, column=0, sticky='w')
    widgets['progress_bar'] = ttk.Progressbar(logs_frame, mode='determinate')
    widgets['progress_bar'].grid(row=1, column=0, sticky='ew', pady=5)
    widgets['log_display'] = scrolledtext.ScrolledText(logs_frame, height=10, wrap=tk.WORD, state="disabled")
    widgets['log_display'].grid(row=2, column=0, sticky='nsew')

    # --- Results Tab ---
    results_frame.columnconfigure(0, weight=1)
    results_frame.rowconfigure(0, weight=1)
    cols = ("Page", "FTO Number", "Timestamp")
    widgets['results_tree'] = ttk.Treeview(results_frame, columns=cols, show='headings', height=10)
    widgets['results_tree'].heading("Page", text="Page Processed")
    widgets['results_tree'].heading("FTO Number", text="FTO Number Generated")
    widgets['results_tree'].heading("Timestamp", text="Time")
    widgets['results_tree'].column("Page", width=150)
    widgets['results_tree'].column("FTO Number", width=400)
    widgets['results_tree'].column("Timestamp", width=100, anchor='center')
    widgets['results_tree'].grid(row=0, column=0, sticky='nsew')
    scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=widgets['results_tree'].yview)
    widgets['results_tree'].configure(yscroll=scrollbar.set)
    scrollbar.grid(row=0, column=1, sticky='ns')
    
    load_inputs()

def set_ui_state(running):
    """Enable or disable UI elements based on automation state."""
    state = "disabled" if running else "normal"
    widgets['start_button'].config(state=state)
    widgets['stop_button'].config(state="normal" if running else "disabled")
    widgets['reset_button'].config(state=state)
    for key in ['district_entry', 'block_entry', 'panchayat_entry', 'user_id_entry']:
        widgets[key].config(state=state)

def update_status(text, progress=None):
    """Update the status label and progress bar."""
    widgets['status_label'].config(text=f"Status: {text}")
    if progress is not None:
        widgets['progress_bar']['value'] = progress

def save_inputs():
    """Saves the current values from the entry fields to a JSON file."""
    data = {
        'district': widgets['district_entry'].get(),
        'block': widgets['block_entry'].get(),
        'panchayat': widgets['panchayat_entry'].get(),
        'user_id': widgets['user_id_entry'].get()
    }
    try:
        with open(CONFIG_FILE, 'w') as f: json.dump(data, f, indent=4)
    except Exception as e: print(f"Error saving FTO config: {e}")

def load_inputs():
    """Loads values from the JSON file into the entry fields."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
            widgets['district_entry'].insert(0, data.get('district', ''))
            widgets['block_entry'].insert(0, data.get('block', ''))
            widgets['panchayat_entry'].insert(0, data.get('panchayat', ''))
            widgets['user_id_entry'].insert(0, data.get('user_id', ''))
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading FTO config: {e}")

def reset_ui(app):
    """Resets the UI fields and logs."""
    if messagebox.askokcancel("Reset Form?", "This will clear all input fields, results, and logs."):
        for key in ['district_entry', 'block_entry', 'panchayat_entry', 'user_id_entry']:
            widgets[key].delete(0, tk.END)
        app.clear_log(widgets['log_display'])
        for item in widgets['results_tree'].get_children():
            widgets['results_tree'].delete(item)
        update_status("Ready", 0)
        app.log_message(widgets['log_display'], "Form has been reset.")
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)

def start_automation(app):
    """Starts the automation thread."""
    save_inputs()
    app.start_automation_thread("fto_gen", run_automation_logic)

def _log_result(app, page_name, fto_number):
    """Logs the extracted FTO number to the results table."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    app.after(0, lambda: widgets['results_tree'].insert("", "end", values=(page_name, fto_number, timestamp)))

# --- AUTOMATION LOGIC ---

def process_verification_page(app, driver, wait, verification_url, page_identifier):
    """The core logic for processing a single verification page."""
    alert_text = "No alert found or page did not load correctly."
    try:
        app.log_message(widgets['log_display'], f"Navigating to {page_identifier}...")
        driver.get(verification_url)
        wait.until(EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_wage_list_verify")))
        app.log_message(widgets['log_display'], "Verification page loaded.")

        if not driver.find_elements(By.XPATH, "//input[contains(@id, '_auth')]"):
            app.log_message(widgets['log_display'], "No records found to accept on this page.", "warning")
            return "No records to process on this page."
        
        app.log_message(widgets['log_display'], "Accepting all rows...")
        driver.execute_script("document.querySelectorAll('input[id*=\"_auth\"]').forEach(radio => radio.click());")
        app.log_message(widgets['log_display'], "All rows accepted.")

        app.log_message(widgets['log_display'], "Clicking 'Submit' button...")
        wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ch_verified"))).click()
        
        app.log_message(widgets['log_display'], "Clicking 'Authorise' button...")
        wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_btn"))).click()
        
        app.log_message(widgets['log_display'], "Waiting for confirmation alert...")
        alert = wait.until(EC.alert_is_present())
        alert_text = alert.text
        
        fto_match = re.search(r'FTO No : \((.*?)\)', alert_text)
        fto_number = fto_match.group(1) if fto_match else "Not Found"
        
        app.log_message(widgets['log_display'], f"Captured FTO: {fto_number}", "success")
        _log_result(app, page_identifier, fto_number)
        
        alert.accept()
        app.log_message(widgets['log_display'], "Alert accepted.", "success")
    except TimeoutException:
        app.log_message(widgets['log_display'], "Timed out waiting for page element. It may be empty.", "warning")
    except Exception as e:
        app.log_message(widgets['log_display'], f"An error occurred during verification: {e}", "error")
        alert_text = f"Error: {e}"
        
    return alert_text

def run_automation_logic(app):
    """Main automation thread function for FTO Generation."""
    app.after(0, set_ui_state, True)
    app.clear_log(widgets['log_display'])
    app.after(0, lambda: [widgets['results_tree'].delete(item) for item in widgets['results_tree'].get_children()])
    update_status("Starting...", 0)

    try:
        district_name = widgets['district_entry'].get().strip()
        block_name = widgets['block_entry'].get().strip()
        panchayat_name = widgets['panchayat_entry'].get().strip()
        user_id = widgets['user_id_entry'].get().strip()

        if not all([district_name, block_name, panchayat_name, user_id]):
            messagebox.showerror("Input Required", "District, Block, Panchayat, and User ID are required."); app.after(0, set_ui_state, False); return

        driver = app.connect_to_chrome()
        wait = WebDriverWait(driver, 20)

        login_url = "https://mnregaweb3.nic.in/Netnrega/FTO/Login.aspx?&level=HomeACGP&state_code=34"
        verification_url_1 = "https://mnregaweb3.nic.in/netnrega/FTO/ftoverify_aadhar.aspx?cate=Z&Digest=KfhSIdpgz01z37eG0dybsw"
        verification_url_2 = "https://mnregaweb3.nic.in/netnrega/FTO/ftoverify_aadhar.aspx?wg_topup=S"

        # --- LOGIN CHECK ---
        app.log_message(widgets['log_display'], "Checking login status...")
        current_url = driver.current_url.lower()
        if "ftoindexframe.aspx" in current_url:
            app.log_message(widgets['log_display'], "Already logged in. Skipping login process.", "success")
            update_status("Login detected. Starting verification...", 50)
        else:
            app.log_message(widgets['log_display'], "Not logged in. Navigating to Login Page...")
            driver.get(login_url)
            update_status("Filling login details...", 10)

            try:
                Select(wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddl_District")))).select_by_visible_text(district_name)
                app.log_message(widgets['log_display'], f"Selected District: {district_name}")

                wait.until(lambda d: len(Select(d.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_Block")).options) > 1)
                Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_Block")).select_by_visible_text(block_name)
                app.log_message(widgets['log_display'], f"Selected Block: {block_name}")

                wait.until(lambda d: len(Select(d.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_Panch")).options) > 1)
                Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_Panch")).select_by_visible_text(panchayat_name)
                app.log_message(widgets['log_display'], f"Selected Panchayat: {panchayat_name}")
                
            except NoSuchElementException as e:
                raise ValueError(f"A selection (District, Block, or Panchayat) was not found. Please check your spelling and try again.")

            wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_txt_UserID"))).send_keys(user_id)
            app.log_message(widgets['log_display'], "Login details filled.")
            update_status("Waiting for manual login...", 25)

            app.after(0, lambda: messagebox.showinfo("Action Required", "Please enter your Password and the CAPTCHA in the browser, then click 'Login'. The script will resume automatically."))
            WebDriverWait(driver, 300).until(EC.url_contains("ftoindexframe.aspx"))
            app.log_message(widgets['log_display'], "Login successful!", "success")
            update_status("Login successful. Starting verification...", 50)

        # --- PROCESS PAGES ---
        alert1_text = process_verification_page(app, driver, wait, verification_url_1, "Aadhaar FTO")
        update_status("First page processed. Starting second page...", 75)
        
        alert2_text = process_verification_page(app, driver, wait, verification_url_2, "Top-Up FTO")
        update_status("All tasks complete!", 100)

        final_summary = "Automation workflow has completed. Check the Results tab for generated FTO numbers."
        app.log_message(widgets['log_display'], final_summary)
        app.after(0, lambda: messagebox.showinfo("Workflow Complete", final_summary))

    except Exception as e:
        error_msg = f"A critical error occurred: {e}"
        app.log_message(widgets['log_display'], error_msg, "error")
        messagebox.showerror("Automation Error", error_msg)
    finally:
        app.after(0, set_ui_state, False)
        app.after(0, update_status, "Finished.")
