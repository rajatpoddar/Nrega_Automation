# tabs/work_demand_tab.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import time, os, json
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, NoSuchElementException, TimeoutException, StaleElementReferenceException

import config

widgets = {}
LAST_INPUTS_FILE = "work_demand_inputs.json"

def create_tab(parent_frame, app_instance):
    """Creates the Work Demand tab UI with results and logging."""
    parent_frame.columnconfigure(0, weight=1)
    parent_frame.rowconfigure(3, weight=1) # Allow notebook to expand

    # --- Configuration Frame ---
    config_frame = ttk.LabelFrame(parent_frame, text="Work Demand Configuration")
    config_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10), padx=5)
    for i in range(4): config_frame.columnconfigure(i, weight=1)

    widgets['config_vars'] = {}
    fields = [
        ("panchayat_name", "Panchayat Name", 0, 0),
        ("village_name", "Village Name", 0, 2),
        ("application_date", "Application Date (DD/MM/YYYY)", 1, 0),
        ("demand_from_date", "Demand From Date (DD/MM/YYYY)", 1, 2),
        ("days_count", "Number of Days", 2, 0),
    ]
    for key, text, r, c in fields:
        ttk.Label(config_frame, text=text).grid(row=r, column=c, sticky='w', padx=5, pady=5)
        var = tk.StringVar()
        widgets['config_vars'][key] = var
        entry = ttk.Entry(config_frame, textvariable=var)
        entry.grid(row=r, column=c+1, sticky='ew', padx=5, pady=5)

    # --- Jobcard Input ---
    jobcard_frame = ttk.LabelFrame(parent_frame, text="Job Card Numbers (one per line)")
    jobcard_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10), padx=5)
    jobcard_frame.columnconfigure(0, weight=1)
    jobcard_frame.rowconfigure(0, weight=1)
    widgets['jobcards_text'] = scrolledtext.ScrolledText(jobcard_frame, height=8, wrap=tk.WORD)
    widgets['jobcards_text'].grid(row=0, column=0, sticky='nsew')
    
    # --- Action Buttons ---
    action_frame = ttk.Frame(parent_frame)
    action_frame.grid(row=2, column=0, sticky='ew', pady=(0, 10), padx=5)
    action_frame.columnconfigure((0, 1, 2), weight=1)

    widgets['start_button'] = ttk.Button(action_frame, text="▶ Start Automation", style="Accent.TButton", command=lambda: start_automation(app_instance))
    widgets['start_button'].grid(row=0, column=0, sticky='ew', padx=(0,5), ipady=5)
    widgets['stop_button'] = ttk.Button(action_frame, text="Stop", command=lambda: app_instance.stop_events["work_demand"].set(), state="disabled")
    widgets['stop_button'].grid(row=0, column=1, sticky='ew', padx=(5,5), ipady=5)
    widgets['reset_button'] = ttk.Button(action_frame, text="Reset", style="Outline.TButton", command=lambda: reset_ui(app_instance))
    widgets['reset_button'].grid(row=0, column=2, sticky='ew', padx=(5,0), ipady=5)

    # --- Notebook for Data and Logs ---
    notebook = ttk.Notebook(parent_frame, style="Modern.TNotebook")
    notebook.grid(row=3, column=0, sticky="nsew", padx=5)
    parent_frame.rowconfigure(3, weight=1)

    results_frame = ttk.Frame(notebook, padding=15)
    logs_frame = ttk.Frame(notebook, padding=15)

    notebook.add(results_frame, text="Results")
    notebook.add(logs_frame, text="Logs & Status")

    # --- Results Tab ---
    results_frame.columnconfigure(0, weight=1); results_frame.rowconfigure(1, weight=1)
    summary_frame = ttk.Frame(results_frame)
    summary_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    summary_frame.columnconfigure((0, 1), weight=1)
    widgets['success_label'] = ttk.Label(summary_frame, text="Success: 0", foreground=config.STYLE_CONFIG["colors"]["light"]["success"], font=config.STYLE_CONFIG["font_bold"])
    widgets['success_label'].grid(row=0, column=0, sticky='w')
    widgets['failed_label'] = ttk.Label(summary_frame, text="Failed: 0", foreground=config.STYLE_CONFIG["colors"]["light"]["danger"], font=config.STYLE_CONFIG["font_bold"])
    widgets['failed_label'].grid(row=0, column=1, sticky='w')

    cols = ("Timestamp", "Job Card", "Status", "Details")
    widgets['results_tree'] = ttk.Treeview(results_frame, columns=cols, show='headings', height=5)
    for col in cols: widgets['results_tree'].heading(col, text=col)
    widgets['results_tree'].column("Timestamp", width=80, anchor='center')
    widgets['results_tree'].column("Job Card", width=150)
    widgets['results_tree'].column("Status", width=100, anchor='center')
    widgets['results_tree'].column("Details", width=450)
    widgets['results_tree'].grid(row=1, column=0, sticky='nsew')
    scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=widgets['results_tree'].yview)
    widgets['results_tree'].configure(yscroll=scrollbar.set); scrollbar.grid(row=1, column=1, sticky='ns')

    # --- Logs & Status Tab ---
    logs_frame.columnconfigure(0, weight=1); logs_frame.rowconfigure(1, weight=1)
    status_bar = ttk.Frame(logs_frame)
    status_bar.grid(row=0, column=0, sticky='ew')
    status_bar.columnconfigure(0, weight=1)
    widgets['status_label'] = ttk.Label(status_bar, text="Status: Ready", style="Status.TLabel")
    widgets['status_label'].grid(row=0, column=0, sticky='ew')
    widgets['copy_logs_button'] = ttk.Button(status_bar, text="Copy Log", style="Outline.TButton", command=lambda: copy_logs_to_clipboard(app_instance))
    widgets['copy_logs_button'].grid(row=0, column=1, sticky='e', padx=5)
    widgets['log_display'] = scrolledtext.ScrolledText(logs_frame, wrap=tk.WORD, state="disabled", height=5)
    widgets['log_display'].grid(row=1, column=0, sticky='nsew', pady=(10, 0))

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
        if not widgets['config_vars']['application_date'].get():
            widgets['config_vars']['application_date'].set(datetime.now().strftime('%d/%m/%Y'))
        if not widgets['config_vars']['demand_from_date'].get():
            widgets['config_vars']['demand_from_date'].set(datetime.now().strftime('%d/%m/%Y'))

def reset_ui(app):
    if messagebox.askokcancel("Reset Form?", "Are you sure you want to clear all inputs, results, and logs?"):
        for key, var in widgets['config_vars'].items(): var.set("")
        widgets['jobcards_text'].delete("1.0", tk.END)
        for item in widgets['results_tree'].get_children(): widgets['results_tree'].delete(item)
        app.clear_log(widgets['log_display'])
        update_status("Ready")
        widgets['success_label'].config(text="Success: 0")
        widgets['failed_label'].config(text="Failed: 0")
        _load_inputs(app)
        app.log_message(widgets['log_display'], "Form has been reset.")

def set_ui_state(running):
    state = "disabled" if running else "normal"
    widgets['start_button'].config(state=state)
    widgets['stop_button'].config(state="normal" if running else "disabled")
    widgets['reset_button'].config(state=state)
    widgets['jobcards_text'].config(state=state)
    config_frame = widgets['start_button'].master.master.winfo_children()[0]
    for child in config_frame.winfo_children():
        if isinstance(child, ttk.Entry):
            child.config(state=state)

def update_status(text):
    widgets['status_label'].config(text=f"Status: {text}")

def copy_logs_to_clipboard(app):
    log_content = widgets['log_display'].get('1.0', tk.END).strip()
    if log_content:
        app.clipboard_clear()
        app.clipboard_append(log_content)
        messagebox.showinfo("Copied", "Logs have been copied to the clipboard.")

def _log_result(app, jobcard, status, details, counters):
    success_counter, failed_counter = counters
    timestamp = datetime.now().strftime("%H:%M:%S")
    values = (timestamp, jobcard, status, details)
    
    if status == "Success":
        success_counter[0] += 1
        app.after(0, lambda: widgets['success_label'].config(text=f"Success: {success_counter[0]}"))
    else:
        failed_counter[0] += 1
        app.after(0, lambda: widgets['failed_label'].config(text=f"Failed: {failed_counter[0]}"))
        
    app.after(0, lambda: widgets['results_tree'].insert("", "end", values=values))

def start_automation(app):
    cfg = {key: var.get().strip() for key, var in widgets['config_vars'].items()}
    
    missing_fields = [key.replace('_', ' ').title() for key, value in cfg.items() if not value]
    if missing_fields:
        messagebox.showwarning("Input Error", f"The following fields are required:\n\n- {', '.join(missing_fields)}")
        return

    jobcards = [line.strip() for line in widgets['jobcards_text'].get("1.0", tk.END).strip().splitlines() if line.strip()]
    if not jobcards:
        messagebox.showwarning("Input Required", "Please enter at least one Job Card number.")
        return

    _save_inputs(app, cfg)
    app.start_automation_thread("work_demand", run_automation_logic, args=(cfg, jobcards))

def run_automation_logic(app, cfg, jobcards):
    app.after(0, set_ui_state, True)
    app.clear_log(widgets['log_display'])
    app.after(0, lambda: [widgets['results_tree'].delete(item) for item in widgets['results_tree'].get_children()])
    app.log_message(widgets['log_display'], "Starting Work Demand automation...")
    
    counters = ([0], [0])
    jobcard_process_counts = {} 

    try:
        driver = app.connect_to_chrome()
        wait = WebDriverWait(driver, 60)
        
        for i, jobcard_num in enumerate(jobcards):
            if app.stop_events["work_demand"].is_set():
                app.log_message(widgets['log_display'], "Automation stopped by user.", "warning"); break
            
            update_status(f"Processing Job Card {i+1}/{len(jobcards)}: {jobcard_num}")
            app.log_message(widgets['log_display'], f"--- Processing Job Card: {jobcard_num} ---")
            _process_single_jobcard(app, driver, wait, cfg, jobcard_num, counters, jobcard_process_counts)
            
    except Exception as e:
        app.log_message(widgets['log_display'], f"A critical error occurred: {e}", "error")
        messagebox.showerror("Automation Error", f"An error occurred during the process:\n\n{e}")
    finally:
        final_msg = "Automation finished." if not app.stop_events["work_demand"].is_set() else "Automation stopped by user."
        update_status(final_msg)
        if not app.stop_events["work_demand"].is_set():
            app.after(0, lambda: messagebox.showinfo("Automation Complete", "The Work Demand process has finished."))
        app.after(0, set_ui_state, False)

def _process_single_jobcard(app, driver, wait, cfg, jobcard_num, counters, jobcard_process_counts):
    try:
        driver.get(config.WORK_DEMAND_CONFIG["url"])
        app.log_message(widgets['log_display'], "Navigated to Work Demand page.")

        app.log_message(widgets['log_display'], f"Selecting Panchayat: {cfg['panchayat_name']}...")
        panchayat_dropdown = wait.until(EC.element_to_be_clickable((By.ID, 'ctl00_ContentPlaceHolder1_DDL_panchayat')))
        Select(panchayat_dropdown).select_by_visible_text(cfg['panchayat_name'])
        
        wait.until(EC.presence_of_element_located((By.XPATH, "//select[@id='ctl00_ContentPlaceHolder1_DDL_Village']/option[2]")))
        app.log_message(widgets['log_display'], "Panchayat selected and village list loaded.")

        app.log_message(widgets['log_display'], f"Selecting Village: {cfg['village_name']}...")
        village_dropdown = wait.until(EC.element_to_be_clickable((By.ID, 'ctl00_ContentPlaceHolder1_DDL_Village')))
        Select(village_dropdown).select_by_visible_text(cfg['village_name'])
        
        wait.until(EC.presence_of_element_located((By.XPATH, "//select[@id='ctl00_ContentPlaceHolder1_DDL_Registration']/option[2]")))
        app.log_message(widgets['log_display'], "Village selected and job card list loaded.")

        reg_dropdown = wait.until(EC.element_to_be_clickable((By.ID, 'ctl00_ContentPlaceHolder1_DDL_Registration')))
        reg_select = Select(reg_dropdown)
        option_found = False
        for option in reg_select.options:
            if option.text.strip().startswith(f"{jobcard_num}-"):
                reg_select.select_by_visible_text(option.text)
                option_found = True
                break
        
        if not option_found: raise NoSuchElementException(f"Jobcard No. not found.")

        wait.until(EC.staleness_of(driver.find_element(By.TAG_NAME, 'body')))
        app.log_message(widgets['log_display'], f"Job Card {jobcard_num} selected. Page reloaded.")
        
        worker_index = jobcard_process_counts.get(jobcard_num, 0)
        jobcard_process_counts[jobcard_num] = worker_index + 1
        row_num = worker_index + 2
        row_id = f"ctl{str(row_num).zfill(2)}"

        app.log_message(widgets['log_display'], f"Processing worker #{worker_index + 1} for this job card (using table row {row_id}).")

        app_date_input_id = f'ctl00_ContentPlaceHolder1_gvData_{row_id}_dt_app'
        from_date_input_id = f'ctl00_ContentPlaceHolder1_gvData_{row_id}_dt_from'
        days_input_id = f'ctl00_ContentPlaceHolder1_gvData_{row_id}_d3'
        
        wait.until(EC.presence_of_element_located((By.ID, app_date_input_id)))
        
        driver.execute_script(f"document.getElementById('{app_date_input_id}').value = '{cfg['application_date']}';")
        driver.execute_script(f"document.getElementById('{from_date_input_id}').value = '{cfg['demand_from_date']}';")
        
        days_input_script = f"""
            var daysInput = document.getElementById('{days_input_id}');
            daysInput.value = '{cfg['days_count']}';
            var event = new Event('change', {{ 'bubbles': true, 'cancelable': true }});
            daysInput.dispatchEvent(event);
        """
        driver.execute_script(days_input_script)
        
        app.log_message(widgets['log_display'], f"Filled details for Job Card {jobcard_num}. Waiting for date calculation...")
        time.sleep(3) 

        driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_btnProceed').click()
        app.log_message(widgets['log_display'], "Proceed button clicked.")
        
        alert = wait.until(EC.alert_is_present())
        alert_text = alert.text
        alert.accept()
        app.log_message(widgets['log_display'], f"SUCCESS for {jobcard_num}: {alert_text}", "success")
        _log_result(app, jobcard_num, "Success", alert_text, counters)
        
        time.sleep(2) 

    except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
        error_msg = f"{type(e).__name__}: {str(e).splitlines()[0]}"
        app.log_message(widgets['log_display'], error_msg, "error")
        _log_result(app, jobcard_num, "Failed", error_msg, counters)
    except UnexpectedAlertPresentException as e:
        alert_text = e.alert_text
        app.log_message(widgets['log_display'], f"Unexpected alert on {jobcard_num}: {alert_text}", "warning")
        _log_result(app, jobcard_num, "Failed", f"Unexpected Alert: {alert_text}", counters)
        try: driver.switch_to.alert.accept()
        except: pass
