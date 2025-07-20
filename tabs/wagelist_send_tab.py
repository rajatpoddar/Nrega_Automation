# tabs/wagelist_send_tab.py (Upgraded to CustomTkinter)
import tkinter
from tkinter import ttk, messagebox
import customtkinter as ctk
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import config

widgets = {}

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

def create_tab(parent_frame, app_instance):
    parent_frame.grid_columnconfigure(0, weight=1)
    parent_frame.grid_rowconfigure(2, weight=1)
    
    note_frame = ctk.CTkFrame(parent_frame)
    note_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
    instruction_text = "IMPORTANT: Before starting, please manually:\n" \
                       "1. Go to the 'Send Wagelist For Payment' page.\n" \
                       "2. Select the correct 'Financial Year'.\n" \
                       "3. Wait for the 'Wagelist No.' list to populate, then click 'Start Sending'."
    ctk.CTkLabel(note_frame, text=instruction_text, justify="left", wraplength=850).pack(fill='x', pady=10, padx=15)
    
    controls = ctk.CTkFrame(parent_frame)
    controls.grid(row=1, column=0, sticky='ew')
    
    row_frame = ctk.CTkFrame(controls, fg_color="transparent")
    row_frame.pack(fill='x', pady=5, padx=15)
    ctk.CTkLabel(row_frame, text="Start Row:").pack(side="left")
    widgets['row_start_entry'] = ctk.CTkEntry(row_frame, width=60)
    widgets['row_start_entry'].insert(0, "3")
    widgets['row_start_entry'].pack(side="left", padx=5)
    ctk.CTkLabel(row_frame, text="End Row:").pack(side="left", padx=(10,0))
    widgets['row_end_entry'] = ctk.CTkEntry(row_frame, width=60)
    widgets['row_end_entry'].insert(0, "19")
    widgets['row_end_entry'].pack(side="left", padx=5)
    
    action_frame = ctk.CTkFrame(controls, fg_color="transparent")
    action_frame.pack(pady=10, padx=15, fill='x')
    action_frame.grid_columnconfigure((0, 1, 2), weight=1)
    
    widgets['start_button'] = ctk.CTkButton(action_frame, text="▶ Start Sending", command=lambda: start_automation(app_instance))
    widgets['start_button'].grid(row=0, column=0, sticky="ew", padx=(0,5))
    widgets['stop_button'] = ctk.CTkButton(action_frame, text="Stop", command=lambda: app_instance.stop_events["send"].set(), state="disabled", fg_color="gray50")
    widgets['stop_button'].grid(row=0, column=1, sticky="ew", padx=5)
    widgets['reset_button'] = ctk.CTkButton(action_frame, text="Reset", fg_color="transparent", border_width=2, border_color=("gray70", "gray40"), text_color=("gray10", "#DCE4EE"), command=lambda: reset_ui(app_instance))
    widgets['reset_button'].grid(row=0, column=2, sticky='ew', padx=(5,0))
    
    data_notebook = ctk.CTkTabview(parent_frame)
    data_notebook.grid(row=2, column=0, sticky="nsew", pady=(10,0))
    results_frame = data_notebook.add("Results")
    log_frame = data_notebook.add("Logs & Status")

    results_frame.grid_columnconfigure(0, weight=1); results_frame.grid_rowconfigure(0, weight=1)
    cols = ("Wagelist No.", "Status", "Timestamp")
    widgets['results_tree'] = ttk.Treeview(results_frame, columns=cols, show='headings')
    for col in cols: widgets['results_tree'].heading(col, text=col)
    widgets['results_tree'].grid(row=0, column=0, sticky='nsew')
    scrollbar = ctk.CTkScrollbar(results_frame, command=widgets['results_tree'].yview)
    widgets['results_tree'].configure(yscroll=scrollbar.set); scrollbar.grid(row=0, column=1, sticky='ns')
    style_treeview(app_instance)

    log_frame.grid_columnconfigure(1, weight=1); log_frame.grid_rowconfigure(1, weight=1)
    widgets['status_label'] = ctk.CTkLabel(log_frame, text="Status: Ready")
    widgets['status_label'].grid(row=0, column=0, sticky='ew', pady=(0, 5))
    widgets['progress_bar'] = ctk.CTkProgressBar(log_frame)
    widgets['progress_bar'].set(0)
    widgets['progress_bar'].grid(row=0, column=1, sticky='ew', pady=(0, 5), padx=(10,0))
    widgets['log_display'] = ctk.CTkTextbox(log_frame, state="disabled", wrap=tkinter.WORD)
    widgets['log_display'].grid(row=1, column=0, columnspan=2, sticky='nsew', pady=(10, 0))

def reset_ui(app):
    if messagebox.askokcancel("Reset Form?", "Are you sure?"):
        widgets['row_start_entry'].delete(0, tkinter.END); widgets['row_start_entry'].insert(0, "3")
        widgets['row_end_entry'].delete(0, tkinter.END); widgets['row_end_entry'].insert(0, "19")
        for item in widgets['results_tree'].get_children(): widgets['results_tree'].delete(item)
        app.clear_log(widgets['log_display']); update_status("Ready", 0)
        app.log_message(widgets['log_display'], "Form has been reset.")

def set_ui_state(running):
    state = "disabled" if running else "normal"
    widgets['start_button'].configure(state=state)
    widgets['row_start_entry'].configure(state=state)
    widgets['row_end_entry'].configure(state=state)
    widgets['reset_button'].configure(state=state)
    widgets['stop_button'].configure(state="normal" if running else "disabled")

def update_status(text, progress_val=None):
    widgets['status_label'].configure(text=f"Status: {text}")
    if progress_val is not None: widgets['progress_bar'].set(progress_val)

# Automation logic remains the same
def start_automation(app):
    app.start_automation_thread("send", run_automation_logic)

def run_automation_logic(app):
    app.after(0, set_ui_state, True)
    app.after(0, lambda: [widgets['results_tree'].delete(item) for item in widgets['results_tree'].get_children()])
    app.clear_log(widgets['log_display'])
    app.log_message(widgets['log_display'], "Starting automation...")
    
    try: start_row, end_row = int(widgets['row_start_entry'].get()), int(widgets['row_end_entry'].get())
    except ValueError: messagebox.showerror("Input Error", "Row numbers must be integers."); app.after(0, set_ui_state, False); return
        
    try:
        driver = app.connect_to_chrome()
        wait = WebDriverWait(driver, 10)
        app.log_message(widgets['log_display'], "Fetching wagelists from the current page...")
        wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddl_sel")))
        all_wagelists = [o.get_attribute("value") for o in Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_sel")).options if o.get_attribute("value") != "select"]
        
        if not all_wagelists:
            app.log_message(widgets['log_display'], "No wagelists found. Please check Financial Year.", "error"); app.after(0, set_ui_state, False); return
        
        app.log_message(widgets['log_display'], f"Found {len(all_wagelists)} wagelists.")
        total = len(all_wagelists)
        
        for idx, wagelist in enumerate(all_wagelists, 1):
            if app.stop_events["send"].is_set(): break
            app.after(0, update_status, f"Processing {idx}/{total}: {wagelist}", idx / total)
            success = _process_single_wagelist(app, driver, wait, wagelist, start_row, end_row)
            app.after(0, lambda w=wagelist, s="Success" if success else "Failed", t=datetime.now().strftime("%H:%M:%S"): widgets['results_tree'].insert("", tkinter.END, values=(w, s, t)))
            time.sleep(1)
            
    except Exception as e:
        app.log_message(widgets['log_display'], f"A critical error occurred: {e}", "error"); messagebox.showerror("Automation Error", f"An error occurred: {e}")
    finally:
        stopped_by_user = app.stop_events["send"].is_set()
        final_msg = "Process stopped by user." if stopped_by_user else "✅ All wagelists processed."
        app.after(0, update_status, final_msg)
        app.after(0, set_ui_state, False)
        if not stopped_by_user: app.after(0, lambda: messagebox.showinfo("Automation Complete", "Wagelist sending process finished."))

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
                try: driver.find_element(By.ID, f"ctl00_ContentPlaceHolder1_GridView1_ctl{str(i).zfill(2)}_rdbPayment_2").click(); time.sleep(0.2)
                except NoSuchElementException: break
            if app.stop_events["send"].is_set(): return False
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btnsubmit").click()
            WebDriverWait(driver, 5).until(EC.alert_is_present()).accept()
            app.log_message(widgets['log_display'], f"✅ {wagelist} submitted successfully.", "success")
            return True
        except Exception as e:
            app.log_message(widgets['log_display'], f"[WARN] Attempt {attempt+1} failed for {wagelist}: {type(e).__name__}", "warning"); time.sleep(2)
    return False