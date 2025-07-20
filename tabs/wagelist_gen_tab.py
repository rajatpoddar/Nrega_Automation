# tabs/wagelist_gen_tab.py (Upgraded to CustomTkinter)
import tkinter
from tkinter import ttk, messagebox
import customtkinter as ctk
import re, time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

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
    parent_frame.grid_rowconfigure(1, weight=1)

    controls_frame = ctk.CTkFrame(parent_frame)
    controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    controls_frame.grid_columnconfigure(1, weight=1)
    
    ctk.CTkLabel(controls_frame, text="Agency Name: Gram Panchayat -").grid(row=0, column=0, sticky='w', padx=15, pady=(15,0))
    widgets['agency_entry'] = ctk.CTkEntry(controls_frame)
    widgets['agency_entry'].grid(row=0, column=1, sticky='ew', padx=15, pady=(15,0))
    ctk.CTkLabel(controls_frame, text="Enter Panchayat name exactly as on the NREGA website.", text_color="gray50").grid(row=1, column=1, sticky='w', padx=15)

    action_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
    action_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=15)
    action_frame.grid_columnconfigure((0, 1, 2), weight=1)

    widgets['start_button'] = ctk.CTkButton(action_frame, text="▶ Start Generation", command=lambda: start_automation(app_instance))
    widgets['start_button'].grid(row=0, column=0, sticky="ew", padx=(0,5))
    widgets['stop_button'] = ctk.CTkButton(action_frame, text="Stop", command=lambda: app_instance.stop_events["gen"].set(), state=tkinter.DISABLED, fg_color="gray50")
    widgets['stop_button'].grid(row=0, column=1, sticky="ew", padx=5)
    widgets['reset_button'] = ctk.CTkButton(action_frame, text="Reset", fg_color="transparent", border_width=2, border_color=("gray70", "gray40"), text_color=("gray10", "#DCE4EE"), command=lambda: reset_ui(app_instance))
    widgets['reset_button'].grid(row=0, column=2, sticky='ew', padx=(5,0))

    notebook = ctk.CTkTabview(parent_frame)
    notebook.grid(row=1, column=0, sticky="nsew")

    results_frame = notebook.add("Results")
    logs_frame = notebook.add("Logs & Status")

    results_frame.grid_columnconfigure(0, weight=1); results_frame.grid_rowconfigure(0, weight=1)
    cols = ("Timestamp", "Work Code", "Status", "Job Card No.", "Applicant Name")
    widgets['results_tree'] = ttk.Treeview(results_frame, columns=cols, show='headings')
    for col in cols: widgets['results_tree'].heading(col, text=col)
    widgets['results_tree'].column("Timestamp", width=80, anchor='center'); widgets['results_tree'].column("Work Code", width=220)
    widgets['results_tree'].column("Status", width=150); widgets['results_tree'].column("Job Card No.", width=200)
    widgets['results_tree'].column("Applicant Name", width=150)
    widgets['results_tree'].grid(row=0, column=0, sticky='nsew')
    scrollbar = ctk.CTkScrollbar(results_frame, command=widgets['results_tree'].yview)
    widgets['results_tree'].configure(yscroll=scrollbar.set); scrollbar.grid(row=0, column=1, sticky='ns')
    style_treeview(app_instance)

    logs_frame.grid_columnconfigure(0, weight=1); logs_frame.grid_rowconfigure(2, weight=1)
    
    widgets['copy_log_button'] = ctk.CTkButton(logs_frame, text="Copy Log", width=100, command=lambda: on_copy_log_click(parent_frame))
    widgets['copy_log_button'].grid(row=0, column=0, sticky='w')
    widgets['progress_bar'] = ctk.CTkProgressBar(logs_frame)
    widgets['progress_bar'].start() if False else widgets['progress_bar'].set(0) # Init
    widgets['progress_bar'].grid(row=0, column=1, sticky='ew', padx=(10,0))
    widgets['status_label'] = ctk.CTkLabel(logs_frame, text="Status: Ready")
    widgets['status_label'].grid(row=1, column=0, columnspan=2, sticky='ew', pady=5)
    widgets['log_text'] = ctk.CTkTextbox(logs_frame, wrap=tkinter.WORD, state=tkinter.DISABLED)
    widgets['log_text'].grid(row=2, column=0, columnspan=2, sticky='nsew', pady=(10, 0))

def on_copy_log_click(parent_frame):
    parent_frame.clipboard_clear()
    parent_frame.clipboard_append(widgets['log_text'].get("1.0", tkinter.END))
    messagebox.showinfo("Copied", "Log content has been copied.")

def reset_ui(app):
    if messagebox.askokcancel("Reset Form?", "Are you sure?"):
        widgets['agency_entry'].delete(0, tkinter.END)
        for item in widgets['results_tree'].get_children(): widgets['results_tree'].delete(item)
        app.clear_log(widgets['log_text']); widgets['status_label'].configure(text="Status: Ready")
        app.log_message(widgets['log_text'], "Form has been reset.")

def set_ui_state(running):
    state = "disabled" if running else "normal"
    if running: widgets['progress_bar'].start()
    else: widgets['progress_bar'].stop(); widgets['progress_bar'].set(0)
    widgets['start_button'].configure(state=state)
    widgets['agency_entry'].configure(state=state)
    widgets['reset_button'].configure(state=state)
    widgets['stop_button'].configure(state="normal" if running else "disabled")

# The rest of the file (logic) is included for completeness but is unchanged.
def start_automation(app):
    agency_name_part = widgets['agency_entry'].get().strip()
    if not agency_name_part: messagebox.showwarning("Input Error", "Please enter an Agency name."); return
    app.start_automation_thread("gen", run_automation_logic, args=(agency_name_part,))

def run_automation_logic(app, agency_name_part):
    app.after(0, set_ui_state, True)
    app.clear_log(widgets['log_text'])
    app.after(0, lambda: [widgets['results_tree'].delete(item) for item in widgets['results_tree'].get_children()])
    full_agency_to_find = "Gram Panchayat -" + agency_name_part
    app.log_message(widgets['log_text'], f"Starting wagelist generation for: {full_agency_to_find}")
    
    try:
        driver = app.connect_to_chrome()
        wait = WebDriverWait(driver, 20)
        total_errors_to_skip = 0

        while not app.stop_events["gen"].is_set():
            app.after(0, lambda: widgets['status_label'].configure(text="Status: Navigating and selecting agency..."))
            driver.get(config.WAGELIST_GEN_CONFIG["base_url"])
            agency_select_element = wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_exe_agency')))
            select = Select(agency_select_element)
            match_text = next((opt.text for opt in select.options if agency_name_part.lower() in opt.text.lower()), None)

            if not match_text:
                error_msg = f"Agency '{agency_name_part}' not found."; app.log_message(widgets['log_text'], error_msg, "error"); messagebox.showerror("Agency Not Found", error_msg); break
            
            select.select_by_visible_text(match_text); app.log_message(widgets['log_text'], f"Selected agency: {match_text}", "success"); time.sleep(1)
            proceed_button = wait.until(EC.element_to_be_clickable((By.ID, 'ctl00_ContentPlaceHolder1_go')))
            driver.execute_script("arguments[0].scrollIntoView(true);", proceed_button); proceed_button.click()

            try:
                wagelist_table = wait.until(EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_wagelist_msr")))
                rows = wagelist_table.find_elements(By.XPATH, ".//tr[td]")

                if not rows or total_errors_to_skip >= len(rows): app.log_message(widgets['log_text'], "No more wagelists to process.", "info"); break
                row_to_process = rows[total_errors_to_skip]
                try: checkbox = row_to_process.find_element(By.XPATH, ".//input[@type='checkbox']")
                except NoSuchElementException: app.log_message(widgets['log_text'], "Found a row without a checkbox, assuming end of data.", "info"); break

                cells = row_to_process.find_elements(By.TAG_NAME, "td"); work_code = cells[2].text.strip()
                app.after(0, lambda: widgets['status_label'].configure(text=f"Status: Processing work code {work_code}..."))
                app.log_message(widgets['log_text'], f"Processing row {total_errors_to_skip + 1} (Work Code: {work_code})")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
                if not checkbox.is_selected(): checkbox.click()
                wait.until(EC.element_to_be_clickable((By.ID, 'ctl00_ContentPlaceHolder1_btn_go'))).click()
                wait.until(EC.any_of(EC.url_changes(config.WAGELIST_GEN_CONFIG["base_url"]), EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_lblmsg"))))
                
                if driver.current_url != config.WAGELIST_GEN_CONFIG["base_url"]:
                    app.log_message(widgets['log_text'], f"SUCCESS: Wagelist generated for {work_code}.", "success"); _log_result(app, work_code, "Success", "", "")
                else:
                    error_text = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_lblmsg").text.strip(); app.log_message(widgets['log_text'], f"ERROR on {work_code}: {error_text}", "error")
                    try:
                        job_cards, applicant_names = [], []
                        unfrozen_table = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_GridView1")
                        for u_row in unfrozen_table.find_elements(By.XPATH, ".//tr[td]"):
                            u_cells = u_row.find_elements(By.TAG_NAME, "td"); job_cards.append(u_cells[1].text.strip()); applicant_names.append(u_cells[3].text.strip())
                        _log_result(app, work_code, "Unfrozen Account", ", ".join(job_cards), ", ".join(applicant_names))
                    except NoSuchElementException: _log_result(app, work_code, "Failed (Unknown Error)", "", "")
                    total_errors_to_skip += 1
            except TimeoutException: app.log_message(widgets['log_text'], "No wagelist table found. Assuming process is complete.", "info"); break
            if app.stop_events["gen"].is_set(): app.log_message(widgets['log_text'], "Stop signal received."); break
        if not app.stop_events["gen"].is_set(): app.after(0, lambda: messagebox.showinfo("Automation Complete", "The wagelist generation process has finished."))
    except Exception as e: app.log_message(widgets['log_text'], f"A critical error occurred: {e}", level="error")
    finally:
        app.after(0, set_ui_state, False)
        app.after(0, lambda: widgets['status_label'].configure(text="Status: Automation Finished."))

def _log_result(app, work_code, status, job_card, applicant_name):
    timestamp = datetime.now().strftime("%H:%M:%S")
    app.after(0, lambda: widgets['results_tree'].insert("", "end", values=(timestamp, work_code, status, job_card, applicant_name)))