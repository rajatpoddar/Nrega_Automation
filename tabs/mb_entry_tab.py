# tabs/mb_entry_tab.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import time, os, json
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, NoSuchElementException, TimeoutException, StaleElementReferenceException

import config

# Use a dictionary to hold widgets for easy access
widgets = {}
# Define a file to store the last used inputs
LAST_INPUTS_FILE = "mb_entry_inputs.json"

def create_tab(parent_frame, app_instance):
    """Creates the e-MB Entry tab UI with improved layout and features."""
    parent_frame.columnconfigure(0, weight=1)
    parent_frame.rowconfigure(2, weight=1)

    # --- Configuration Frame ---
    config_frame = ttk.LabelFrame(parent_frame, text="Configuration")
    config_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10), padx=5)
    for i in range(4): config_frame.columnconfigure(i, weight=1)

    widgets['config_vars'] = {}
    # ADDED: Panchayat Name field at the top
    fields = [
        ("panchayat_name", "Panchayat Name", 0, 0),
        ("measurement_book_no", "MB No.", 1, 0), ("page_no", "Page No.", 1, 2),
        ("measurement_date", "Meas. Date", 2, 0), ("unit_cost", "Unit Cost (₹)", 2, 2),
        ("mate_name", "Mate Name", 3, 0), ("default_pit_count", "Pit Count", 3, 2),
        ("je_name", "JE Name", 4, 0), ("je_designation", "JE Desig.", 4, 2)
    ]
    for key, text, r, c in fields:
        # Span Panchayat Name across the full width
        colspan = 3 if key == "panchayat_name" else 1
        ttk.Label(config_frame, text=text).grid(row=r, column=c, sticky='w', padx=5, pady=5)
        var = tk.StringVar()
        widgets['config_vars'][key] = var
        ttk.Entry(config_frame, textvariable=var).grid(row=r, column=c+1, columnspan=colspan, sticky='ew', padx=5, pady=5)

    note_label = ttk.Label(config_frame,
                           text="ℹ️ Note: The script automatically fills the activity for 'Earth work'. If not found, it defaults to the first activity row.",
                           style="Instruction.TLabel", wraplength=450)
    note_label.grid(row=5, column=0, columnspan=4, sticky='w', padx=5, pady=(10, 5))

    # --- Action Buttons ---
    action_frame = ttk.Frame(parent_frame)
    action_frame.grid(row=1, column=0, sticky='ew', pady=(0, 10), padx=5)
    action_frame.columnconfigure((0, 1, 2), weight=1)

    widgets['start_button'] = ttk.Button(action_frame, text="▶ Start Automation", style="Accent.TButton", command=lambda: start_automation(app_instance))
    widgets['start_button'].grid(row=0, column=0, sticky='ew', padx=(0,5), ipady=5)
    widgets['stop_button'] = ttk.Button(action_frame, text="Stop", command=lambda: app_instance.stop_events["mb_entry"].set(), state="disabled")
    widgets['stop_button'].grid(row=0, column=1, sticky='ew', padx=(5,5), ipady=5)
    widgets['reset_button'] = ttk.Button(action_frame, text="Reset", style="Outline.TButton", command=lambda: reset_ui(app_instance))
    widgets['reset_button'].grid(row=0, column=2, sticky='ew', padx=(5,0), ipady=5)

    # --- Notebook for Data and Logs ---
    notebook = ttk.Notebook(parent_frame, style="Modern.TNotebook")
    notebook.grid(row=2, column=0, sticky="nsew", padx=5)

    work_codes_frame = ttk.Frame(notebook, padding=15)
    results_frame = ttk.Frame(notebook, padding=15)
    logs_frame = ttk.Frame(notebook, padding=15)

    notebook.add(work_codes_frame, text="Work Codes")
    notebook.add(results_frame, text="Results")
    notebook.add(logs_frame, text="Logs & Status")

    # --- Work Codes Tab ---
    work_codes_frame.columnconfigure(0, weight=1); work_codes_frame.rowconfigure(0, weight=1)
    widgets['work_codes_text'] = scrolledtext.ScrolledText(work_codes_frame, height=10, wrap=tk.WORD)
    widgets['work_codes_text'].grid(row=0, column=0, sticky='nsew')

    # --- Results Tab ---
    results_frame.columnconfigure(0, weight=1); results_frame.rowconfigure(0, weight=1)
    cols = ("Work Code", "Status", "Details", "Timestamp")
    widgets['results_tree'] = ttk.Treeview(results_frame, columns=cols, show='headings', height=10)
    for col in cols: widgets['results_tree'].heading(col, text=col)
    widgets['results_tree'].column("Work Code", width=200); widgets['results_tree'].column("Status", width=100, anchor='center')
    widgets['results_tree'].column("Details", width=350); widgets['results_tree'].column("Timestamp", width=100, anchor='center')
    widgets['results_tree'].grid(row=0, column=0, sticky='nsew')
    scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=widgets['results_tree'].yview)
    widgets['results_tree'].configure(yscroll=scrollbar.set); scrollbar.grid(row=0, column=1, sticky='ns')

    # --- Logs & Status Tab ---
    logs_frame.columnconfigure(1, weight=1); logs_frame.rowconfigure(2, weight=1)
    def on_copy_log_click():
        log_content = widgets['log_display'].get("1.0", tk.END); parent_frame.clipboard_clear()
        parent_frame.clipboard_append(log_content); messagebox.showinfo("Copied", "Log content has been copied.")
    widgets['copy_log_button'] = ttk.Button(logs_frame, text="Copy Log", command=on_copy_log_click)
    widgets['copy_log_button'].grid(row=0, column=0, sticky='w')
    widgets['progress_bar'] = ttk.Progressbar(logs_frame, mode='determinate')
    widgets['progress_bar'].grid(row=0, column=1, sticky='ew', padx=(10,0))
    widgets['status_label'] = ttk.Label(logs_frame, text="Status: Ready", style="Status.TLabel")
    widgets['status_label'].grid(row=1, column=0, columnspan=2, sticky='ew', pady=(5,0))
    widgets['log_display'] = scrolledtext.ScrolledText(logs_frame, wrap=tk.WORD, state="disabled")
    widgets['log_display'].grid(row=2, column=0, columnspan=2, sticky='nsew', pady=(10, 0))

    # Load saved inputs and set the date
    _load_inputs(app_instance)

def get_inputs_path(app):
    return app.get_data_path(LAST_INPUTS_FILE)

def _save_inputs(app, cfg):
    try:
        with open(get_inputs_path(app), 'w') as f:
            json.dump(cfg, f, indent=4)
    except Exception as e:
        app.log_message(widgets['log_display'], f"Could not save inputs: {e}", "warning")

def _load_inputs(app):
    try:
        inputs_path = get_inputs_path(app)
        if os.path.exists(inputs_path):
            with open(inputs_path, 'r') as f:
                saved_data = json.load(f)
                for key, var in widgets['config_vars'].items():
                    var.set(saved_data.get(key, ''))
    except Exception as e:
        app.log_message(widgets['log_display'], f"Could not load inputs: {e}", "warning")
    finally:
        widgets['config_vars']['measurement_date'].set(datetime.now().strftime('%d/%m/%Y'))

def reset_ui(app):
    if messagebox.askokcancel("Reset Form?", "Are you sure you want to clear all inputs, results, and logs?"):
        for key, var in widgets['config_vars'].items():
            var.set("")
        widgets['config_vars']['measurement_date'].set(datetime.now().strftime('%d/%m/%Y'))
        widgets['work_codes_text'].config(state="normal"); widgets['work_codes_text'].delete("1.0", tk.END)
        widgets['work_codes_text'].config(state="disabled")
        for item in widgets['results_tree'].get_children(): widgets['results_tree'].delete(item)
        app.clear_log(widgets['log_display']); update_status("Ready", 0)
        app.log_message(widgets['log_display'], "Form has been reset.")

def set_ui_state(running):
    state = "disabled" if running else "normal"
    widgets['start_button'].config(state=state)
    widgets['stop_button'].config(state="normal" if running else "disabled")
    widgets['reset_button'].config(state=state)
    widgets['work_codes_text'].config(state=state)
    config_frame = widgets['start_button'].master.master.winfo_children()[0] # Navigate to config_frame
    for child in config_frame.winfo_children():
        if isinstance(child, ttk.Entry):
            child.config(state=state)

def update_status(text, progress=None):
    widgets['status_label'].config(text=f"Status: {text}")
    if progress is not None: widgets['progress_bar']['value'] = progress

def start_automation(app):
    cfg = {key: var.get().strip() for key, var in widgets['config_vars'].items()}
    
    # All fields are now required
    missing_fields = [key.replace('_', ' ').title() for key, value in cfg.items() if not value]
    if missing_fields:
        messagebox.showwarning("Input Error", f"The following fields are required:\n\n- {', '.join(missing_fields)}")
        return

    work_codes_raw = [line.strip() for line in widgets['work_codes_text'].get("1.0", tk.END).strip().splitlines() if line.strip()]
    if not work_codes_raw:
        messagebox.showwarning("Input Required", "Please paste at least one work code.")
        return

    _save_inputs(app, cfg)
    app.start_automation_thread("mb_entry", run_automation_logic, args=(cfg, work_codes_raw))

def run_automation_logic(app, cfg, work_codes_raw):
    app.after(0, set_ui_state, True)
    app.clear_log(widgets['log_display'])
    app.after(0, lambda: [widgets['results_tree'].delete(item) for item in widgets['results_tree'].get_children()])
    app.log_message(widgets['log_display'], "Starting MB Entry automation...")
    
    try:
        driver = app.connect_to_chrome()
        wait = WebDriverWait(driver, 20)
        
        processed_codes = set()
        total = len(work_codes_raw)

        for i, work_code in enumerate(work_codes_raw):
            if app.stop_events["mb_entry"].is_set():
                app.log_message(widgets['log_display'], "Automation stopped by user.", "warning"); break
            
            app.after(0, update_status, f"Processing {i+1}/{total}: {work_code}", ((i+1) / total) * 100)
            
            if work_code in processed_codes:
                app.log_message(widgets['log_display'], f"Skipping duplicate work code: {work_code}", "warning")
                _log_result(app, work_code, "Skipped", "Duplicate entry.")
                continue

            _process_single_work_code(app, driver, wait, work_code, cfg)
            processed_codes.add(work_code)
        
        final_msg = "Automation finished." if not app.stop_events["mb_entry"].is_set() else "Automation stopped by user."
        app.after(0, update_status, final_msg, 100)
        if not app.stop_events["mb_entry"].is_set():
            app.after(0, lambda: messagebox.showinfo("Automation Complete", "The e-MB Entry process has finished."))
            
    except Exception as e:
        app.log_message(widgets['log_display'], f"A critical error occurred: {e}", "error")
        messagebox.showerror("Automation Error", f"An error occurred during the process:\n\n{e}")
    finally:
        app.after(0, set_ui_state, False)

def _log_result(app, work_code, status, details):
    timestamp = datetime.now().strftime("%H:%M:%S")
    app.after(0, lambda: widgets['results_tree'].insert("", "end", values=(work_code, status, details, timestamp)))

def _process_single_work_code(app, driver, wait, work_code, cfg):
    try:
        driver.get(config.MB_ENTRY_CONFIG["url"])
        
        # --- NEW: Conditional Panchayat Selection Logic ---
        try:
            panchayat_dropdown = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_ddl_panch'))
            )
            page_body = driver.find_element(By.TAG_NAME, 'body')
            app.log_message(widgets['log_display'], f"Found Panchayat dropdown. Selecting '{cfg['panchayat_name']}'...")
            Select(panchayat_dropdown).select_by_visible_text(cfg['panchayat_name'])
            app.log_message(widgets['log_display'], "Waiting for page to repopulate after Panchayat selection...")
            wait.until(EC.staleness_of(page_body))
            app.log_message(widgets['log_display'], "Page reloaded successfully.")
        except (TimeoutException, NoSuchElementException):
            app.log_message(widgets['log_display'], "Panchayat dropdown not found on this page, skipping.", "info")
            pass
        # --- End of new logic ---

        wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_txtMBNo')))
        driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtMBNo').send_keys(cfg["measurement_book_no"])
        driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtpageno').send_keys(cfg["page_no"])
        driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtMDate').send_keys(cfg["measurement_date"])
        driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtWrkCode').send_keys(work_code)
        driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_imgButtonSearch').click()
        
        wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_ddlSelWrk'))); time.sleep(1)
        
        select_work = Select(driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_ddlSelWrk'))
        if len(select_work.options) <= 1: raise ValueError(f"Work code not found or already processed.")
        select_work.select_by_index(1)
        
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_rddist_0").click(); time.sleep(2)
        
        period_dropdown = Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlSelMPeriod"))
        if len(period_dropdown.options) <= 1: raise ValueError(f"No measurement period found.")
        period_dropdown.select_by_index(1)
        
        total_persondays = int(driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_lbl_person_days').get_attribute('value').strip())
        
        prefix = _find_activity_prefix(app, driver)
        
        driver.find_element(By.NAME, f'{prefix}$qty').send_keys(str(total_persondays))
        driver.find_element(By.NAME, f'{prefix}$unitcost').send_keys(cfg["unit_cost"])
        driver.find_element(By.NAME, f'{prefix}$labcomp').send_keys(str(total_persondays * int(cfg["unit_cost"])))
        
        try:
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtpit").send_keys(cfg["default_pit_count"])
        except NoSuchElementException: pass
        
        driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txt_mat_name').send_keys(cfg["mate_name"])
        driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txt_eng_name').send_keys(cfg["je_name"])
        driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txt_eng_desig').send_keys(cfg["je_designation"])
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);"); time.sleep(0.5)
        driver.find_element(By.XPATH, '//input[@value="Save"]').click()
        
        try:
            alert = WebDriverWait(driver, 5).until(EC.alert_is_present())
            alert_text = alert.text
            app.log_message(widgets['log_display'], f"Success for {work_code}: {alert_text}", "success")
            _log_result(app, work_code, "Success", alert_text)
            alert.accept()
        except TimeoutException:
            _log_result(app, work_code, "Success", "Saved (No confirmation alert).")

    except UnexpectedAlertPresentException:
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            app.log_message(widgets['log_display'], f"Unexpected alert for {work_code}: {alert_text}", "warning")
            _log_result(app, work_code, "Failed", f"Unexpected Alert: {alert_text}")
            alert.accept()
        except: pass
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e).splitlines()[0]}"
        app.log_message(widgets['log_display'], f"Error on {work_code}: {error_msg}", "error")
        _log_result(app, work_code, "Failed", error_msg)

def _find_activity_prefix(app, driver):
    app.log_message(widgets['log_display'], "Searching for 'Earth work' activity row...")
    for i in range(1, 61):
        try:
            activity_id = f"ctl00_ContentPlaceHolder1_activity_ctl{str(i).zfill(2)}_act_name"
            activity_element = driver.find_element(By.ID, activity_id)
            if "earth work" in activity_element.text.lower():
                app.log_message(widgets['log_display'], f"✅ Found 'Earth work' in row #{i}.", "success")
                return f"ctl00$ContentPlaceHolder1$activity$ctl{str(i).zfill(2)}"
        except NoSuchElementException: continue
    app.log_message(widgets['log_display'], "⚠️ 'Earth work' row not found. Defaulting to first row.", "warning")
    return "ctl00$ContentPlaceHolder1$activity$ctl01"