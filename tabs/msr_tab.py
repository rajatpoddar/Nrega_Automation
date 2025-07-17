# tabs/msr_tab.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import os, random, time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException, UnexpectedAlertPresentException, NoAlertPresentException
import config
from fpdf import FPDF # Import the PDF library

widgets = {}

def create_tab(parent_frame, app_instance):
    """Creates the MSR Processor tab UI with improved controls and logging."""
    parent_frame.columnconfigure(0, weight=1)
    parent_frame.rowconfigure(1, weight=1)

    controls_frame = ttk.LabelFrame(parent_frame, text="MSR Controls")
    controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    controls_frame.columnconfigure(0, weight=1)

    ttk.Label(controls_frame, text="Panchayat Name").grid(row=0, column=0, sticky='w', pady=(0, 5))
    widgets['panchayat_entry'] = ttk.Entry(controls_frame)
    widgets['panchayat_entry'].grid(row=1, column=0, sticky='ew', pady=(0, 5))
    ttk.Label(controls_frame, text="e.g., Palojori (must exactly match the name on the website)", style="Instruction.TLabel").grid(row=2, column=0, sticky='w')

    action_frame = ttk.Frame(controls_frame)
    action_frame.grid(row=3, column=0, sticky='ew', pady=(15, 0))
    action_frame.columnconfigure((0, 1, 2), weight=1)

    def on_start_click(): start_automation(app_instance)
    def on_stop_click(): app_instance.stop_events["msr"].set()
    def on_reset_click(): reset_ui(app_instance)

    widgets['start_button'] = ttk.Button(action_frame, text="▶ Start Processing", style="Accent.TButton", command=on_start_click)
    widgets['start_button'].grid(row=0, column=0, sticky='ew', padx=(0, 5), ipady=5)
    widgets['stop_button'] = ttk.Button(action_frame, text="Stop", state="disabled", command=on_stop_click)
    widgets['stop_button'].grid(row=0, column=1, sticky='ew', padx=5, ipady=5)
    widgets['reset_button'] = ttk.Button(action_frame, text="Reset", style="Outline.TButton", command=on_reset_click)
    widgets['reset_button'].grid(row=0, column=2, sticky='ew', padx=(5, 0), ipady=5)

    data_notebook = ttk.Notebook(parent_frame, style="Modern.TNotebook")
    data_notebook.grid(row=1, column=0, sticky="nsew")

    work_codes_frame = ttk.Frame(data_notebook, padding=15)
    results_frame = ttk.Frame(data_notebook, padding=15)
    log_frame = ttk.Frame(data_notebook, padding=15)

    data_notebook.add(work_codes_frame, text="Work Codes")
    data_notebook.add(results_frame, text="Results")
    data_notebook.add(log_frame, text="Logs & Status")

    # --- Work Codes Tab ---
    work_codes_frame.columnconfigure(0, weight=1); work_codes_frame.rowconfigure(0, weight=1)
    widgets['work_key_text'] = scrolledtext.ScrolledText(work_codes_frame, height=10)
    widgets['work_key_text'].grid(row=0, column=0, sticky='nsew')

    # --- Results Tab ---
    results_frame.columnconfigure(0, weight=1); results_frame.rowconfigure(1, weight=1)
    
    results_action_frame = ttk.Frame(results_frame)
    results_action_frame.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 10))
    widgets['export_pdf_button'] = ttk.Button(results_action_frame, text="Export Results to PDF", command=lambda: export_to_pdf(app_instance))
    widgets['export_pdf_button'].pack(side='left')

    cols = ("Workcode", "Status", "Details", "Timestamp")
    widgets['results_tree'] = ttk.Treeview(results_frame, columns=cols, show='headings', height=10)
    for col in cols: widgets['results_tree'].heading(col, text=col)
    widgets['results_tree'].column("Status", anchor='center', width=150)
    widgets['results_tree'].column("Details", width=350)
    widgets['results_tree'].grid(row=1, column=0, sticky='nsew')
    scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=widgets['results_tree'].yview)
    widgets['results_tree'].configure(yscroll=scrollbar.set)
    scrollbar.grid(row=1, column=1, sticky='ns')

    # --- Logs & Status Tab ---
    log_frame.columnconfigure(1, weight=1); log_frame.rowconfigure(2, weight=1)
    
    def on_copy_log_click():
        log_content = widgets['log_display'].get("1.0", tk.END)
        parent_frame.clipboard_clear()
        parent_frame.clipboard_append(log_content)
        messagebox.showinfo("Copied", "Log content has been copied to the clipboard.")
        
    widgets['copy_log_button'] = ttk.Button(log_frame, text="Copy Log", command=on_copy_log_click)
    widgets['copy_log_button'].grid(row=0, column=0, sticky='w')

    widgets['progress_bar'] = ttk.Progressbar(log_frame, mode="determinate")
    widgets['progress_bar'].grid(row=0, column=1, sticky='ew', pady=(0, 5), padx=(10,0))
    widgets['status_label'] = ttk.Label(log_frame, text="Status: Ready", style="Status.TLabel")
    widgets['status_label'].grid(row=1, column=0, columnspan=2, sticky='ew')
    widgets['log_display'] = scrolledtext.ScrolledText(log_frame, height=8, state="disabled")
    widgets['log_display'].grid(row=2, column=0, columnspan=2, sticky='nsew', pady=(10, 0))

def set_ui_state(running):
    state = "disabled" if running else "normal"
    widgets['start_button'].config(state=state)
    widgets['panchayat_entry'].config(state=state)
    widgets['work_key_text'].config(state=state)
    widgets['reset_button'].config(state=state)
    widgets['copy_log_button'].config(state=state)
    widgets['export_pdf_button'].config(state=state)
    stop_state = "normal" if running else "disabled"
    widgets['stop_button'].config(state=stop_state)

def export_to_pdf(app):
    """Exports the contents of the results Treeview to a PDF file."""
    data = []
    if not widgets['results_tree'].get_children():
        messagebox.showinfo("No Data", "There are no results to export.")
        return
        
    for item_id in widgets['results_tree'].get_children():
        data.append(widgets['results_tree'].item(item_id)['values'])
    
    file_path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")],
        initialdir=app.get_user_downloads_path(),
        title="Save Results As PDF"
    )
    if not file_path: return

    try:
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Add a title
        pdf.cell(0, 10, 'MSR Processing Results', 0, 1, 'C')
        
        # Table Headers
        pdf.set_font("Arial", 'B', 9)
        col_widths = [55, 35, 155, 25]
        headers = ["Workcode", "Status", "Details", "Timestamp"]
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
        pdf.ln()
        
        # Table Data
        pdf.set_font("Arial", '', 8)
        for row in data:
            for i, item in enumerate(row):
                pdf.cell(col_widths[i], 6, str(item), 1, 0)
            pdf.ln()
            
        pdf.output(file_path)
        if messagebox.askyesno("Success", f"Results successfully exported to:\n{file_path}\n\nDo you want to open the file?"):
            os.startfile(file_path)
            
    except Exception as e:
        messagebox.showerror("Export Error", f"Failed to create PDF file.\n\nError: {e}")

# The rest of the functions remain the same as the user's provided file...
def update_status(text, progress_val=None):
    widgets['status_label'].config(text=f"Status: {text}")
    if progress_val is not None:
        widgets['progress_bar']['value'] = progress_val
def reset_ui(app):
    if messagebox.askokcancel("Reset Form?", "Are you sure you want to clear all inputs, results, and logs for this tab?"):
        widgets['panchayat_entry'].delete(0, tk.END)
        widgets['work_key_text'].config(state="normal")
        widgets['work_key_text'].delete("1.0", tk.END)
        for item in widgets['results_tree'].get_children():
            widgets['results_tree'].delete(item)
        app.clear_log(widgets['log_display'])
        update_status("Status: Ready", 0)
        app.log_message(widgets['log_display'], "Form has been reset.")
def start_automation(app):
    app.start_automation_thread("msr", run_automation_logic)
def run_automation_logic(app):
    app.after(0, set_ui_state, True)
    app.after(0, lambda: [widgets['results_tree'].delete(item) for item in widgets['results_tree'].get_children()])
    app.clear_log(widgets['log_display'])
    app.log_message(widgets['log_display'], "Starting MSR processing...")
    panchayat_name = widgets['panchayat_entry'].get().strip()
    if not panchayat_name:
        messagebox.showerror("Input Error", "Please enter a Panchayat name."); app.after(0, set_ui_state, False); return
    work_keys = [line.strip() for line in widgets['work_key_text'].get("1.0", tk.END).strip().splitlines() if line.strip()]
    if not work_keys:
        messagebox.showerror("Input Error", "No work keys provided."); app.after(0, set_ui_state, False); return
    try:
        driver = app.connect_to_chrome()
        wait = WebDriverWait(driver, 15)
        if driver.current_url != config.MSR_CONFIG["url"]:
            driver.get(config.MSR_CONFIG["url"])
        panchayat_select = Select(wait.until(EC.presence_of_element_located((By.NAME, "ddlPanchayat"))))
        match = next((opt.text for opt in panchayat_select.options if panchayat_name.strip().lower() in opt.text.lower()), None)
        if not match: raise ValueError(f"Panchayat '{panchayat_name}' not found.")
        panchayat_select.select_by_visible_text(match)
        app.log_message(widgets['log_display'], f"Successfully selected Panchayat: {match}", "success")
        time.sleep(2)
        total = len(work_keys)
        for i, work_key in enumerate(work_keys, 1):
            if app.stop_events["msr"].is_set():
                app.log_message(widgets['log_display'], "Automation stopped by user.", "warning"); break
            app.after(0, update_status, f"Processing {i}/{total}: {work_key}", int((i/total)*100))
            _process_single_work_code(app, driver, wait, work_key)
        if not app.stop_events["msr"].is_set():
            messagebox.showinfo("Completed", "Automation finished! Check the 'Results' tab for details.")
    except Exception as e:
        app.log_message(widgets['log_display'], f"A critical error occurred: {e}", "error")
        messagebox.showerror("MSR Error", f"An error occurred: {e}")
    finally:
        app.after(0, set_ui_state, False)
        app.after(0, update_status, "Automation Finished.")
def _process_single_work_code(app, driver, wait, work_key):
    try:
        try:
            alert = driver.switch_to.alert
            app.log_message(widgets['log_display'], f"Clearing stale alert: '{alert.text}'", "warning")
            alert.accept()
        except NoAlertPresentException:
            pass
        wait.until(EC.presence_of_element_located((By.ID, "txtSearch"))).clear()
        driver.find_element(By.ID, "txtSearch").send_keys(work_key)
        wait.until(EC.element_to_be_clickable((By.ID, "ImgbtnSearch"))).click()
        time.sleep(1)
        error_span = driver.find_element(By.ID, "lblError")
        if error_span and error_span.text.strip():
            raise ValueError(f"Site error: '{error_span.text.strip()}'")
        work_code_select = Select(wait.until(EC.presence_of_element_located((By.ID, "ddlWorkCode"))))
        if len(work_code_select.options) <= config.MSR_CONFIG["work_code_index"]:
            raise IndexError("Work code not found in dropdown.")
        work_code_select.select_by_index(config.MSR_CONFIG["work_code_index"])
        time.sleep(1.5)
        msr_select = Select(wait.until(EC.presence_of_element_located((By.ID, "ddlMsrNo"))))
        if len(msr_select.options) <= config.MSR_CONFIG["muster_roll_index"]:
            raise IndexError("Muster Roll (MSR) number not found.")
        msr_select.select_by_index(config.MSR_CONFIG["muster_roll_index"])
        time.sleep(1.5)
        wait.until(EC.element_to_be_clickable((By.ID, "btnSave"))).click()
        confirm_alert = WebDriverWait(driver, 10).until(EC.alert_is_present())
        app.log_message(widgets['log_display'], f"Accepted confirm dialog: '{confirm_alert.text.strip()}'")
        confirm_alert.accept()
        outcome_found = False
        for _ in range(3): 
            try:
                final_alert = driver.switch_to.alert
                final_alert_text = final_alert.text.strip()
                final_alert.accept()
                if "Muster Roll Payment has been saved" in final_alert_text:
                    _log_result(app, "Success", work_key, final_alert_text)
                elif "and hence it is not saved" in final_alert_text:
                    _log_result(app, "Success", work_key, "Saved (with ignorable attendance error)")
                else:
                    _log_result(app, "Failed", work_key, f"Unknown Alert: {final_alert_text}")
                outcome_found = True
                break
            except NoAlertPresentException:
                if "Expenditure on unskilled labours exceeds sanction amount" in driver.page_source:
                    _log_result(app, "Failed", work_key, "Exceeds Labour Payment")
                    outcome_found = True
                    break
                time.sleep(1)
        if not outcome_found:
            _log_result(app, "Failed", work_key, "No final confirmation found after save (Timeout).")
        delay = random.uniform(config.MSR_CONFIG["min_delay"], config.MSR_CONFIG["max_delay"])
        app.after(0, update_status, f"âœ… {work_key} done. Waiting {delay:.1f}s...")
        time.sleep(delay)
    except (ValueError, IndexError, NoSuchElementException, TimeoutException) as e:
        error_str = str(e)
        if isinstance(e, IndexError) and "Muster Roll" in error_str:
            display_msg = "MR not Filled yet."
        elif isinstance(e, TimeoutException):
            display_msg = "Page timed out or element not found."
        else:
            display_msg = f"{type(e).__name__}: {error_str}"
        _log_result(app, "Failed", work_key, display_msg)
    except Exception as e:
        _log_redirected_log(app, "failed", work_key, f"CRITICAL ERROR: {type(e).__name__} - {e}")
def _log_result(app, status, work_key, msg):
    """Logs the outcome to the log display and the results table with user-friendly messages."""
    level = "success" if status.lower() == "success" else "error"
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # --- Translate raw messages to user-friendly text ---
    details = msg.replace("\n", " ").replace("\r", " ")
    if "No final confirmation found" in msg:
        details = "Pending for JE & AE Approval"
    elif "Muster Roll (MSR) number not found" in msg:
        details = "MR not Filled yet."
    elif "work code not found" in msg:
        details = "Work Code not found."
    
    app.log_message(widgets['log_display'], f"'{work_key}' - {status.upper()}: {details}", level=level)
    app.after(0, lambda: widgets['results_tree'].insert("", "end", values=(work_key, status.upper(), details, timestamp)))
def _log_redirected_log(app, status, work_key, msg):
    level = "error"
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_msg = "An unexpected error occurred. See logs for details."
    app.log_message(widgets['log_display'], f"'{work_key}' - {status.upper()}: {msg}", level=level)
    app.after(0, lambda: widgets['results_tree'].insert("", "end", values=(work_key, "Failed", log_msg, timestamp)))
