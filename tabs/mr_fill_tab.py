# tabs/mr_fill_tab.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException

import config

widgets = {}

def create_tab(parent_frame, app_instance):
    """Creates the MR Fill & Absent tab UI."""
    parent_frame.columnconfigure(0, weight=1)
    parent_frame.rowconfigure(1, weight=1)

    # --- Controls Frame ---
    controls_frame = ttk.LabelFrame(parent_frame, text="MR Fill Controls")
    controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    controls_frame.columnconfigure(1, weight=1)

    ttk.Label(controls_frame, text="Panchayat Name:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
    widgets['panchayat_entry'] = ttk.Entry(controls_frame)
    widgets['panchayat_entry'].grid(row=0, column=1, sticky='ew', padx=5, pady=5)

    action_frame = ttk.Frame(controls_frame)
    action_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(15, 5))
    action_frame.columnconfigure((0, 1, 2), weight=1)

    def on_start_click(): start_automation(app_instance)
    def on_stop_click(): app_instance.stop_events["mr_fill"].set()
    def on_reset_click(): reset_ui(app_instance)

    widgets['start_button'] = ttk.Button(action_frame, text="▶ Start Filling", style="Accent.TButton", command=on_start_click)
    widgets['start_button'].grid(row=0, column=0, sticky="ew", padx=(0,5), ipady=5)
    widgets['stop_button'] = ttk.Button(action_frame, text="Stop", command=on_stop_click, state="disabled")
    widgets['stop_button'].grid(row=0, column=1, sticky="ew", padx=(5,5), ipady=5)
    widgets['reset_button'] = ttk.Button(action_frame, text="Reset", style="Outline.TButton", command=on_reset_click)
    widgets['reset_button'].grid(row=0, column=2, sticky='ew', padx=(5,0), ipady=5)

    # --- Notebook for Work Codes, Results, and Logs ---
    notebook = ttk.Notebook(parent_frame, style="Modern.TNotebook")
    notebook.grid(row=1, column=0, sticky="nsew")

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
    cols = ("Work Code", "Muster Roll No.", "Status", "Timestamp")
    widgets['results_tree'] = ttk.Treeview(results_frame, columns=cols, show='headings', height=10)
    for col in cols:
        widgets['results_tree'].heading(col, text=col)
    widgets['results_tree'].column("Work Code", width=250)
    widgets['results_tree'].column("Muster Roll No.", width=150, anchor='center')
    widgets['results_tree'].column("Status", width=250)
    widgets['results_tree'].column("Timestamp", width=100, anchor='center')
    widgets['results_tree'].grid(row=0, column=0, sticky='nsew')
    scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=widgets['results_tree'].yview)
    widgets['results_tree'].configure(yscroll=scrollbar.set)
    scrollbar.grid(row=0, column=1, sticky='ns')

    # --- Logs & Status Tab ---
    logs_frame.columnconfigure(0, weight=1); logs_frame.rowconfigure(2, weight=1)
    
    def on_copy_log_click():
        log_content = widgets['log_display'].get("1.0", tk.END)
        parent_frame.clipboard_clear()
        parent_frame.clipboard_append(log_content)
        messagebox.showinfo("Copied", "Log content has been copied to the clipboard.")
        
    widgets['copy_log_button'] = ttk.Button(logs_frame, text="Copy Log", command=on_copy_log_click)
    widgets['copy_log_button'].grid(row=0, column=0, sticky='w')
    widgets['progress_bar'] = ttk.Progressbar(logs_frame, mode='determinate')
    widgets['progress_bar'].grid(row=0, column=1, sticky='ew', padx=(10,0))
    widgets['status_label'] = ttk.Label(logs_frame, text="Status: Ready", style="Status.TLabel")
    widgets['status_label'].grid(row=1, column=0, columnspan=2, sticky='ew', pady=(5,0))
    widgets['log_display'] = scrolledtext.ScrolledText(logs_frame, wrap=tk.WORD, state="disabled")
    widgets['log_display'].grid(row=2, column=0, columnspan=2, sticky='nsew', pady=(10, 0))

def reset_ui(app):
    if messagebox.askokcancel("Reset Form?", "Are you sure you want to clear all inputs, results, and logs?"):
        widgets['panchayat_entry'].delete(0, tk.END)
        widgets['work_codes_text'].delete("1.0", tk.END)
        for item in widgets['results_tree'].get_children():
            widgets['results_tree'].delete(item)
        app.clear_log(widgets['log_display'])
        update_status("Ready", 0)
        app.log_message(widgets['log_display'], "Form has been reset.")

def set_ui_state(running):
    state = "disabled" if running else "normal"
    widgets['start_button'].config(state=state)
    widgets['stop_button'].config(state="normal" if running else "disabled")
    widgets['reset_button'].config(state=state)
    widgets['panchayat_entry'].config(state=state)
    widgets['work_codes_text'].config(state=state)

def update_status(text, progress=None):
    widgets['status_label'].config(text=f"Status: {text}")
    if progress is not None:
        widgets['progress_bar']['value'] = progress

def start_automation(app):
    app.start_automation_thread("mr_fill", run_automation_logic)

def run_automation_logic(app):
    app.after(0, set_ui_state, True)
    app.clear_log(widgets['log_display'])
    app.after(0, lambda: [item for item in widgets['results_tree'].get_children() if widgets['results_tree'].delete(item)])
    app.log_message(widgets['log_display'], "Starting MR Fill automation...")
    
    try:
        panchayat_name = widgets['panchayat_entry'].get().strip()
        work_codes = [line.strip() for line in widgets['work_codes_text'].get("1.0", tk.END).strip().splitlines() if line.strip()]
        if not work_codes or not panchayat_name:
            messagebox.showwarning("Input Required", "Please provide a Panchayat name and at least one Work Code."); app.after(0, set_ui_state, False); return
        
        driver = app.connect_to_chrome()
        wait = WebDriverWait(driver, 20)
        total = len(work_codes)
        
        for i, work_code in enumerate(work_codes):
            if app.stop_events["mr_fill"].is_set():
                app.log_message(widgets['log_display'], "Automation stopped by user.", "warning"); break
            
            app.after(0, update_status, f"Processing {i+1}/{total}: {work_code}", ((i+1) / total) * 100)
            _process_single_mr(app, driver, wait, panchayat_name, work_code)
        
        final_msg = "Automation finished." if not app.stop_events["mr_fill"].is_set() else "Automation stopped by user."
        app.after(0, update_status, final_msg, 100)
        if not app.stop_events["mr_fill"].is_set():
            app.after(0, lambda: messagebox.showinfo("Automation Complete", "The MR Fill process has finished."))
            
    except Exception as e:
        app.log_message(widgets['log_display'], f"A critical error occurred: {e}", "error")
        messagebox.showerror("Automation Error", f"An error occurred during the process:\n\n{e}")
    finally:
        app.after(0, set_ui_state, False)

def _log_result(app, work_code, msr_no, status):
    timestamp = datetime.now().strftime("%H:%M:%S")
    values = (work_code, msr_no, status, timestamp)
    app.after(0, lambda: widgets['results_tree'].insert("", "end", values=values))

def _process_single_mr(app, driver, wait, panchayat_name, work_code):
    msr_no_text = "N/A"
    try:
        app.log_message(widgets['log_display'], f"--- Processing {work_code} ---")
        driver.get("https://nregade4.nic.in/netnrega/mustrollattend.aspx")
        
        html_element = driver.find_element(By.TAG_NAME, "html")
        Select(wait.until(EC.element_to_be_clickable((By.ID, "ddlPanchayat")))).select_by_visible_text(panchayat_name)
        wait.until(EC.staleness_of(html_element))
        app.log_message(widgets['log_display'], f"Selected Panchayat: {panchayat_name}")

        wait.until(EC.element_to_be_clickable((By.ID, "txtSearch"))).send_keys(work_code)
        wait.until(EC.element_to_be_clickable((By.ID, "ImgbtnSearch"))).click()
        
        html_element = driver.find_element(By.TAG_NAME, "html")
        work_code_select = Select(wait.until(EC.element_to_be_clickable((By.ID, "ddlWorkCode"))))
        if len(work_code_select.options) <= 1: raise ValueError("No work codes found after search.")
        work_code_select.select_by_index(1)
        wait.until(EC.staleness_of(html_element))

        html_element = driver.find_element(By.TAG_NAME, "html")
        msr_select = Select(wait.until(EC.element_to_be_clickable((By.ID, "ddlMsrNo"))))
        if len(msr_select.options) <= 1: raise ValueError("No Muster Rolls found in dropdown.")
        msr_no_text = msr_select.options[1].text
        app.log_message(widgets['log_display'], f"Selected MSR No: {msr_no_text}")
        msr_select.select_by_index(1)
        wait.until(EC.staleness_of(html_element))
        
        # NEW: Check for page-level errors after MSR selection
        time.sleep(1) # Brief pause for error message to render
        if "No Future Dates Plz in Date To Field" in driver.page_source:
            error_msg = "Skipped: 'No Future Dates' error displayed on page."
            app.log_message(widgets['log_display'], error_msg, "warning")
            _log_result(app, work_code, msr_no_text, error_msg)
            return # Exit this function and move to the next work code

        try:
            short_wait = WebDriverWait(driver, 2)
            day_7_checkbox = short_wait.until(EC.element_to_be_clickable((By.ID, "c_p7")))
            if not day_7_checkbox.is_selected():
                day_7_checkbox.click()
                app.log_message(widgets['log_display'], "Marked 7th day as absent.", "success")
        except TimeoutException:
            app.log_message(widgets['log_display'], "Day 7 checkbox not found, skipping.", "warning")

        app.log_message(widgets['log_display'], "--- PAUSED: WAITING FOR YOU TO CLICK SAVE ---", "warning")
        app.log_message(widgets['log_display'], "Please make any edits and click 'Save' on the webpage. The script will handle the alerts.")

        long_wait = WebDriverWait(driver, timeout=900)
        confirm_alert = long_wait.until(EC.alert_is_present())

        app.log_message(widgets['log_display'], "Alert detected! Resuming automation...")
        confirm_text = confirm_alert.text.strip()
        app.log_message(widgets['log_display'], f"Accepted confirm dialog: '{confirm_text}'")
        confirm_alert.accept()

        final_alert = WebDriverWait(driver, 10).until(EC.alert_is_present())
        final_alert_text = final_alert.text.strip()
        app.log_message(widgets['log_display'], f"Accepted final confirmation: '{final_alert_text}'")
        final_alert.accept()
        _log_result(app, work_code, msr_no_text, f"Success: {final_alert_text}")

    except TimeoutException:
        error_msg = "Timed out waiting for user to click 'Save'."
        app.log_message(widgets['log_display'], f"Error processing {work_code}: {error_msg}", "error")
        _log_result(app, work_code, msr_no_text, f"Failed: {error_msg}")

    except (ValueError, NoSuchElementException, StaleElementReferenceException) as e:
        error_msg = f"{type(e).__name__}: {str(e).splitlines()[0]}"
        app.log_message(widgets['log_display'], f"Error processing {work_code}: {error_msg}", "error")
        _log_result(app, work_code, msr_no_text, f"Failed: {error_msg}")