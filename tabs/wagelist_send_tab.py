# tabs/wagelist_send_tab.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import config

widgets = {}

def create_tab(parent_frame, app_instance):
    parent_frame.columnconfigure(0, weight=1)
    parent_frame.rowconfigure(3, weight=1) # Updated row configure for notebook
    
    note_frame = ttk.LabelFrame(parent_frame, text="Instructions", padding=10)
    note_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
    instruction_text = "IMPORTANT: Before starting, please perform these steps manually in Chrome:\n" \
                       "1. Go to the 'Send Wagelist For Payment' page.\n" \
                       "2. Select the correct 'Financial Year' from the dropdown.\n" \
                       "3. Wait for the 'Wagelist No.' list to populate.\n" \
                       "4. Now, you can click 'Start Sending' below."
    instruction_label = ttk.Label(note_frame, text=instruction_text, justify=tk.LEFT, wraplength=850)
    instruction_label.pack(fill='x', pady=5, padx=5)
    
    controls = ttk.LabelFrame(parent_frame, text="Wagelist Sending Controls")
    controls.grid(row=1, column=0, sticky='ew')
    row_frame = ttk.Frame(controls)
    row_frame.pack(fill='x', pady=5, padx=10)
    ttk.Label(row_frame, text="Start Row:").pack(side="left")
    widgets['row_start_entry'] = ttk.Entry(row_frame, width=5)
    widgets['row_start_entry'].insert(0, "3")
    widgets['row_start_entry'].pack(side="left", padx=5)
    ttk.Label(row_frame, text="End Row:").pack(side="left")
    widgets['row_end_entry'] = ttk.Entry(row_frame, width=5)
    widgets['row_end_entry'].insert(0, "19")
    widgets['row_end_entry'].pack(side="left", padx=5)
    
    action_frame = ttk.Frame(controls)
    action_frame.pack(pady=(10,5), padx=10, fill='x')
    action_frame.columnconfigure((0, 1, 2), weight=1)
    
    def on_start_click(): start_automation(app_instance)
    def on_stop_click(): app_instance.stop_events["send"].set()
    def on_reset_click(): reset_ui(app_instance)

    widgets['start_button'] = ttk.Button(action_frame, text="▶ Start Sending", style="Accent.TButton", command=on_start_click)
    widgets['start_button'].grid(row=0, column=0, sticky="ew", padx=(0,5), ipady=5)
    widgets['stop_button'] = ttk.Button(action_frame, text="Stop", command=on_stop_click, state="disabled")
    widgets['stop_button'].grid(row=0, column=1, sticky="ew", padx=(5,5), ipady=5)
    widgets['reset_button'] = ttk.Button(action_frame, text="Reset", style="Outline.TButton", command=on_reset_click)
    widgets['reset_button'].grid(row=0, column=2, sticky='ew', padx=(5,0), ipady=5)
    
    data_notebook = ttk.Notebook(parent_frame, style="Modern.TNotebook")
    data_notebook.grid(row=3, column=0, sticky="nsew", pady=(10,0))
    
    results_frame = ttk.Frame(data_notebook, padding=15)
    log_frame = ttk.Frame(data_notebook, padding=15)
    
    data_notebook.add(results_frame, text="Results")
    data_notebook.add(log_frame, text="Logs & Status")

    # --- Results Tab ---
    results_frame.columnconfigure(0, weight=1)
    results_frame.rowconfigure(0, weight=1)
    cols = ("Wagelist No.", "Status", "Timestamp")
    widgets['results_tree'] = ttk.Treeview(results_frame, columns=cols, show='headings', height=10)
    for col in cols:
        widgets['results_tree'].heading(col, text=col)
    widgets['results_tree'].grid(row=0, column=0, sticky='nsew')
    scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=widgets['results_tree'].yview)
    widgets['results_tree'].configure(yscroll=scrollbar.set)
    scrollbar.grid(row=0, column=1, sticky='ns')

    # --- Logs & Status Tab ---
    log_frame.columnconfigure(1, weight=1)
    log_frame.rowconfigure(1, weight=1)
    widgets['status_label'] = ttk.Label(log_frame, text="Status: Ready", style="Status.TLabel")
    widgets['status_label'].grid(row=0, column=0, sticky='ew', pady=(0, 5))
    widgets['progress_bar'] = ttk.Progressbar(log_frame, mode="determinate")
    widgets['progress_bar'].grid(row=0, column=1, sticky='ew', pady=(0, 5), padx=(10,0))
    widgets['log_display'] = scrolledtext.ScrolledText(log_frame, height=8, state="disabled")
    widgets['log_display'].grid(row=1, column=0, columnspan=2, sticky='nsew', pady=(10, 0))

def reset_ui(app):
    if messagebox.askokcancel("Reset Form?", "Are you sure you want to clear all inputs, results, and logs for this tab?"):
        widgets['row_start_entry'].delete(0, tk.END)
        widgets['row_start_entry'].insert(0, "3")
        widgets['row_end_entry'].delete(0, tk.END)
        widgets['row_end_entry'].insert(0, "19")
        for item in widgets['results_tree'].get_children():
            widgets['results_tree'].delete(item)
        app.clear_log(widgets['log_display'])
        update_status("Ready", 0)
        app.log_message(widgets['log_display'], "Form has been reset.")

def set_ui_state(running):
    state = "disabled" if running else "normal"
    widgets['start_button'].config(state=state)
    widgets['row_start_entry'].config(state=state)
    widgets['row_end_entry'].config(state=state)
    widgets['reset_button'].config(state=state)
    widgets['stop_button'].config(state="normal" if running else "disabled")

def update_status(text, progress_val=None):
    widgets['status_label'].config(text=f"Status: {text}")
    if progress_val is not None:
        widgets['progress_bar']['value'] = progress_val

def start_automation(app):
    app.start_automation_thread("send", run_automation_logic)

def run_automation_logic(app):
    app.after(0, set_ui_state, True)
    app.after(0, lambda: [widgets['results_tree'].delete(*widgets['results_tree'].get_children())])
    app.clear_log(widgets['log_display'])
    app.log_message(widgets['log_display'], "Starting automation...")
    
    try:
        start_row = int(widgets['row_start_entry'].get())
        end_row = int(widgets['row_end_entry'].get())
    except ValueError:
        messagebox.showerror("Input Error", "Row numbers must be integers."); app.after(0, set_ui_state, False); return
        
    try:
        driver = app.connect_to_chrome()
        wait = WebDriverWait(driver, 10)
        app.log_message(widgets['log_display'], "Fetching wagelists from the current page...")
        wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddl_sel")))
        all_wagelists = [o.get_attribute("value") for o in Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_sel")).options if o.get_attribute("value") != "select"]
        
        if not all_wagelists:
            app.log_message(widgets['log_display'], "No wagelists found. Please check Financial Year.", "error"); app.after(0, set_ui_state, False); return
        
        app.log_message(widgets['log_display'], f"Found {len(all_wagelists)} wagelists to process.")
        total = len(all_wagelists)
        app.after(0, lambda: widgets['progress_bar'].config(maximum=total))
        
        for idx, wagelist in enumerate(all_wagelists, 1):
            if app.stop_events["send"].is_set(): break
            app.after(0, update_status, f"Processing {idx}/{total}: {wagelist}", idx)
            success = _process_single_wagelist(app, driver, wait, wagelist, start_row, end_row)
            
            status_text = "Success" if success else "Failed"
            timestamp = datetime.now().strftime("%H:%M:%S")
            app.after(0, lambda w=wagelist, s=status_text, t=timestamp: widgets['results_tree'].insert("", tk.END, values=(w, s, t)))

            time.sleep(1)
            
    except Exception as e:
        app.log_message(widgets['log_display'], f"A critical error occurred: {e}", "error"); messagebox.showerror("Automation Error", f"An error occurred: {e}")
    finally:
        stopped_by_user = app.stop_events["send"].is_set()
        final_msg = "Process stopped by user." if stopped_by_user else "✅ All wagelists processed."
        app.after(0, update_status, final_msg)
        app.after(0, set_ui_state, False)
        
        # ADDED: Completion alert
        if not stopped_by_user:
            app.after(0, lambda: messagebox.showinfo("Automation Complete", "The wagelist sending process has finished."))

def _process_single_wagelist(app, driver, wait, wagelist, start_row, end_row):
    for attempt in range(2):
        if app.stop_events["send"].is_set(): return False
        try:
            old_html = driver.page_source
            Select(wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ddl_sel")))).select_by_value(wagelist)
            wait.until(lambda d: d.page_source != old_html)
            start_row_radio_id = f"ctl00_ContentPlaceHolder1_GridView1_ctl{str(start_row).zfill(2)}_rdbPayment_2"
            wait.until(EC.element_to_be_clickable((By.ID, start_row_radio_id)))
            for i in range(start_row, end_row + 1):
                if app.stop_events["send"].is_set(): return False
                try:
                    radio_id = f"ctl00_ContentPlaceHolder1_GridView1_ctl{str(i).zfill(2)}_rdbPayment_2"
                    driver.find_element(By.ID, radio_id).click()
                    time.sleep(0.2)
                except NoSuchElementException: break
            if app.stop_events["send"].is_set(): return False
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btnsubmit").click()
            WebDriverWait(driver, 5).until(EC.alert_is_present()).accept()
            app.log_message(widgets['log_display'], f"✅ {wagelist} submitted successfully.", "success")
            return True
        except Exception as e:
            app.log_message(widgets['log_display'], f"[WARN] Attempt {attempt+1} failed for {wagelist}: {type(e).__name__}", "warning"); time.sleep(2)
    return False