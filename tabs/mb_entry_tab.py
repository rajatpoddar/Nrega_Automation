# tabs/mb_entry_tab.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, NoSuchElementException, TimeoutException
import config

widgets = {}

def create_tab(parent_frame, app_instance):
    parent_frame.columnconfigure(0, weight=1)
    parent_frame.rowconfigure(2, weight=1)
    config_frame = ttk.LabelFrame(parent_frame, text="Configuration")
    config_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    for i in range(4): config_frame.columnconfigure(i, weight=1)
    
    widgets['config_vars'] = {}
    fields = [("measurement_book_no", "MB No.", 0, 0), ("page_no", "Page No.", 0, 2), ("measurement_date", "Meas. Date", 1, 0), ("unit_cost", "Unit Cost (₹)", 1, 2), ("mate_name", "Mate Name", 2, 0), ("default_pit_count", "Pit Count", 2, 2), ("je_name", "JE Name", 3, 0), ("je_designation", "JE Desig.", 3, 2)]
    for key, text, r, c in fields:
        ttk.Label(config_frame, text=text).grid(row=r, column=c, sticky='w', padx=5, pady=5)
        var = tk.StringVar(value=config.MB_ENTRY_CONFIG.get(key, "")); widgets['config_vars'][key] = var
        ttk.Entry(config_frame, textvariable=var).grid(row=r, column=c+1, sticky='ew', padx=5, pady=5)
    
    action_frame = ttk.Frame(parent_frame)
    action_frame.grid(row=1, column=0, sticky='ew', pady=(0, 10))
    # Updated: Column configuration for three buttons
    action_frame.columnconfigure((0, 1, 2), weight=1)
    
    def on_start_click():
        start_automation(app_instance)
    def on_stop_click():
        app_instance.stop_events["mb_entry"].set()
    # New: Reset function call
    def on_reset_click():
        reset_ui(app_instance)

    widgets['start_button'] = ttk.Button(action_frame, text="▶ Start Automation", style="Accent.TButton", command=on_start_click)
    widgets['start_button'].grid(row=0, column=0, sticky='ew', padx=(0,5), ipady=5)
    widgets['stop_button'] = ttk.Button(action_frame, text="Stop", command=on_stop_click, state="disabled")
    widgets['stop_button'].grid(row=0, column=1, sticky='ew', padx=(5,5), ipady=5)
    # New: Reset button added
    widgets['reset_button'] = ttk.Button(action_frame, text="Reset", style="Outline.TButton", command=on_reset_click)
    widgets['reset_button'].grid(row=0, column=2, sticky='ew', padx=(5,0), ipady=5)

    data_log_notebook = ttk.Notebook(parent_frame, style="Modern.TNotebook")
    data_log_notebook.grid(row=2, column=0, sticky="nsew")
    work_codes_frame = ttk.Frame(data_log_notebook, padding=15)
    log_frame = ttk.Frame(data_log_notebook, padding=15)
    data_log_notebook.add(work_codes_frame, text="Work Codes")
    data_log_notebook.add(log_frame, text="Logs & Status")
    work_codes_frame.columnconfigure(0, weight=1); work_codes_frame.rowconfigure(0, weight=1)
    widgets['work_codes_text'] = scrolledtext.ScrolledText(work_codes_frame, height=10, wrap=tk.WORD)
    widgets['work_codes_text'].grid(row=0, column=0, sticky='nsew')
    log_frame.columnconfigure(1, weight=1); log_frame.rowconfigure(1, weight=1)
    widgets['status_label'] = ttk.Label(log_frame, text="Status: Ready", style="Status.TLabel")
    widgets['status_label'].grid(row=0, column=0, sticky='ew', pady=(0, 5))
    widgets['progress_bar'] = ttk.Progressbar(log_frame, mode="determinate")
    widgets['progress_bar'].grid(row=0, column=1, sticky='ew', pady=(0, 5), padx=(10,0))
    widgets['log_display'] = scrolledtext.ScrolledText(log_frame, height=12, state="disabled", wrap=tk.WORD)
    widgets['log_display'].grid(row=1, column=0, columnspan=2, sticky='nsew', pady=(10, 0))

# New: Function to reset the UI for this tab
def reset_ui(app):
    if messagebox.askokcancel("Reset Form?", "Are you sure you want to clear all inputs and logs for this tab?"):
        # Reset configuration fields to their default values
        for key, var in widgets['config_vars'].items():
            var.set(config.MB_ENTRY_CONFIG.get(key, ""))
        # Clear the work codes text area
        widgets['work_codes_text'].config(state="normal")
        widgets['work_codes_text'].delete("1.0", tk.END)
        widgets['work_codes_text'].config(state="disabled")
        # Clear logs and reset status
        app.clear_log(widgets['log_display'])
        update_status("Ready", 0)
        app.log_message(widgets['log_display'], "Form has been reset.")

def set_ui_state(running):
    state = "disabled" if running else "normal"
    widgets['start_button'].config(state=state)
    widgets['stop_button'].config(state="normal" if running else "disabled")
    widgets['reset_button'].config(state=state)
    widgets['work_codes_text'].config(state=state)

def update_status(text, progress=None):
    widgets['status_label'].config(text=f"Status: {text}")
    if progress is not None:
        widgets['progress_bar']['value'] = progress

def start_automation(app):
    app.start_automation_thread("mb_entry", run_automation_logic)

def run_automation_logic(app):
    app.after(0, set_ui_state, True)
    app.clear_log(widgets['log_display'])
    app.log_message(widgets['log_display'], "Starting MB Entry automation...")
    try:
        cfg = {key: var.get() for key, var in widgets['config_vars'].items()}
        work_codes = [line.strip() for line in widgets['work_codes_text'].get("1.0", tk.END).strip().splitlines() if line.strip()]
        if not work_codes:
            messagebox.showwarning("Input Required", "Please paste at least one work code."); app.after(0, set_ui_state, False); return
        driver = app.connect_to_chrome()
        wait = WebDriverWait(driver, 20)
        total = len(work_codes)
        for i, work_code in enumerate(work_codes):
            if app.stop_events["mb_entry"].is_set():
                app.log_message(widgets['log_display'], "Automation stopped.", "warning"); break
            app.after(0, update_status, f"Processing {i+1}/{total}: {work_code}", (i / total) * 100)
            _process_single_work_code(app, driver, wait, work_code, cfg)
        final_msg = "Automation finished." if not app.stop_events["mb_entry"].is_set() else "Automation stopped."
        app.after(0, update_status, final_msg, 100)
    except Exception as e:
        app.log_message(widgets['log_display'], f"A critical error occurred: {e}", "error")
    finally:
        app.after(0, set_ui_state, False)

def _process_single_work_code(app, driver, wait, work_code, cfg):
    try:
        driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtMBNo').clear(); driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtMBNo').send_keys(cfg["measurement_book_no"])
        driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtpageno').clear(); driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtpageno').send_keys(cfg["page_no"])
        driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtMDate').clear(); driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtMDate').send_keys(cfg["measurement_date"])
        driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtWrkCode').clear(); driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtWrkCode').send_keys(work_code)
        driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_imgButtonSearch').click()
        wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_ddlSelWrk'))); time.sleep(1)
        select_work = Select(driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_ddlSelWrk'))
        if len(select_work.options) <= 1:
            app.log_message(widgets['log_display'], f"No work options for {work_code}", "warning"); return
        select_work.select_by_index(1)
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_rddist_0").click(); time.sleep(2)
        period_dropdown = Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlSelMPeriod"))
        if len(period_dropdown.options) <= 1:
            app.log_message(widgets['log_display'], f"No measurement period for {work_code}", "warning"); return
        period_dropdown.select_by_index(1)
        total_persondays = int(driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_lbl_person_days').get_attribute('value').strip())
        prefix = _find_activity_prefix(app, driver)
        driver.find_element(By.NAME, f'{prefix}$qty').clear(); driver.find_element(By.NAME, f'{prefix}$qty').send_keys(str(total_persondays))
        driver.find_element(By.NAME, f'{prefix}$unitcost').clear(); driver.find_element(By.NAME, f'{prefix}$unitcost').send_keys(cfg["unit_cost"])
        driver.find_element(By.NAME, f'{prefix}$labcomp').clear(); driver.find_element(By.NAME, f'{prefix}$labcomp').send_keys(str(total_persondays * int(cfg["unit_cost"])))
        try:
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtpit").clear(); driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtpit").send_keys(cfg["default_pit_count"])
        except NoSuchElementException: pass
        driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txt_mat_name').clear(); driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txt_mat_name').send_keys(cfg["mate_name"])
        driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txt_eng_name').clear(); driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txt_eng_name').send_keys(cfg["je_name"])
        driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txt_eng_desig').clear(); driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txt_eng_desig').send_keys(cfg["je_designation"])
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);"); time.sleep(0.5)
        driver.find_element(By.XPATH, '//input[@value="Save"]').click()
        try:
            alert = WebDriverWait(driver, 5).until(EC.alert_is_present())
            app.log_message(widgets['log_display'], f"Success for {work_code}: {alert.text}", "success"); alert.accept()
        except TimeoutException:
            app.log_message(widgets['log_display'], f"Success for {work_code} (No alert).", "success")
    except UnexpectedAlertPresentException:
        try:
            alert = driver.switch_to.alert; app.log_message(widgets['log_display'], f"Unexpected alert for {work_code}: {alert.text}", "warning"); alert.accept()
        except: pass
    except Exception as e:
        app.log_message(widgets['log_display'], f"Error on {work_code}: {type(e).__name__}", "error")

def _find_activity_prefix(app, driver):
    app.log_message(widgets['log_display'], "Searching for 'Earthwork' activity row...")
    for i in range(1, 61):
        try:
            activity_id = f"ctl00_ContentPlaceHolder1_activity_ctl{str(i).zfill(2)}_act_name"
            if "Earthwork" in driver.find_element(By.ID, activity_id).text:
                app.log_message(widgets['log_display'], f"✅ Found 'Earthwork' in row #{i}.", "success")
                return f"ctl00$ContentPlaceHolder1$activity$ctl{str(i).zfill(2)}"
        except NoSuchElementException: continue
    app.log_message(widgets['log_display'], "⚠️ 'Earthwork' row not found. Defaulting to first row.", "warning")
    return "ctl00$ContentPlaceHolder1$activity$ctl01"