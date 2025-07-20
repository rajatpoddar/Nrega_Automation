# tabs/musterroll_gen_tab.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os, json, time, re
import base64
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import config

widgets = {}
LAST_INPUTS_FILE = "muster_roll_inputs.json"

def create_tab(parent_frame, app_instance):
    """Creates the Muster Roll Generation tab GUI with improved layout and bug fixes."""
    parent_frame.columnconfigure(0, weight=1)
    parent_frame.rowconfigure(1, weight=1)

    # --- Controls Frame ---
    controls_frame = ttk.LabelFrame(parent_frame, text="Muster Roll Generation Controls")
    controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    controls_frame.columnconfigure(1, weight=1)
    controls_frame.columnconfigure(3, weight=1)

    ttk.Label(controls_frame, text="Panchayat Name:").grid(row=0, column=0, sticky='w', padx=5, pady=(5,0))
    widgets['panchayat_entry'] = ttk.Entry(controls_frame)
    widgets['panchayat_entry'].grid(row=0, column=1, columnspan=3, sticky='ew', padx=5, pady=(5,0))
    instructional_label = ttk.Label(controls_frame, text="Note: Must exactly match the name of Panchayat & Staff on the NREGA website.", style="Instruction.TLabel")
    instructional_label.grid(row=1, column=1, columnspan=3, sticky='w', padx=5, pady=(0,5))

    ttk.Label(controls_frame, text="तारीख से (DD/MM/YYYY):").grid(row=2, column=0, sticky='w', padx=5, pady=5)
    widgets['start_date_entry'] = ttk.Entry(controls_frame)
    widgets['start_date_entry'].grid(row=2, column=1, sticky='ew', padx=5, pady=5)
    ttk.Label(controls_frame, text="तारीख को (DD/MM/YYYY):").grid(row=2, column=2, sticky='w', padx=5, pady=5)
    widgets['end_date_entry'] = ttk.Entry(controls_frame)
    widgets['end_date_entry'].grid(row=2, column=3, sticky='ew', padx=5, pady=5)

    ttk.Label(controls_frame, text="Select Designation:").grid(row=3, column=0, sticky='w', padx=5, pady=5)
    designation_options = [
        "Junior Engineer--BP", "Assistant Engineer--BP", "Technical Assistant--BP",
        "Acrited Engineer(AE)--GP", "Junior Engineer--GP", "Technical Assistant--GP"
    ]
    widgets['designation_combobox'] = ttk.Combobox(controls_frame, values=designation_options, state="readonly")
    widgets['designation_combobox'].grid(row=3, column=1, sticky='ew', padx=5, pady=5)
    ttk.Label(controls_frame, text="Select Technical Staff:").grid(row=3, column=2, sticky='w', padx=5, pady=5)
    widgets['staff_entry'] = ttk.Entry(controls_frame)
    widgets['staff_entry'].grid(row=3, column=3, sticky='ew', padx=5, pady=5)

    ttk.Label(controls_frame, text="Work Search Keys (or leave blank for auto):").grid(row=4, column=0, sticky='nw', padx=5, pady=5)
    widgets['work_codes_text'] = scrolledtext.ScrolledText(controls_frame, wrap=tk.WORD, height=6)
    widgets['work_codes_text'].grid(row=4, column=1, columnspan=3, sticky='ew', padx=5, pady=5)

    info_label = ttk.Label(controls_frame, text="ℹ️ All generated Muster Rolls are saved in a 'NREGA_MR_Output' folder inside your Downloads.", style="Instruction.TLabel")
    info_label.grid(row=5, column=1, columnspan=3, sticky='w', padx=5, pady=(5,0))

    action_frame = ttk.Frame(controls_frame)
    action_frame.grid(row=6, column=0, columnspan=4, sticky='ew', pady=(15, 5))
    action_frame.columnconfigure((0, 1, 2), weight=1)
    widgets['start_button'] = ttk.Button(action_frame, text="▶ Start Generation", style="Accent.TButton", command=lambda: start_automation(app_instance))
    widgets['stop_button'] = ttk.Button(action_frame, text="Stop", command=lambda: app_instance.stop_events["muster"].set(), state=tk.DISABLED)
    widgets['reset_button'] = ttk.Button(action_frame, text="Reset", style="Outline.TButton", command=lambda: reset_ui(app_instance))
    widgets['start_button'].grid(row=0, column=0, sticky="ew", padx=(0,5), ipady=5)
    widgets['stop_button'].grid(row=0, column=1, sticky="ew", padx=(5,5), ipady=5)
    widgets['reset_button'].grid(row=0, column=2, sticky='ew', padx=(5,0), ipady=5)
    
    data_notebook = ttk.Notebook(parent_frame, style="Modern.TNotebook")
    data_notebook.grid(row=1, column=0, sticky="nsew", pady=(10,0))
    
    results_tab_frame = ttk.Frame(data_notebook, padding=15)
    logs_tab_frame = ttk.Frame(data_notebook, padding=15)
    
    data_notebook.add(results_tab_frame, text="Results")
    data_notebook.add(logs_tab_frame, text="Logs & Status")
    
    # --- Results Tab ---
    results_tab_frame.columnconfigure(0, weight=1)
    results_tab_frame.rowconfigure(1, weight=1) 
    
    summary_frame = ttk.Frame(results_tab_frame)
    summary_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    summary_frame.columnconfigure((0, 1), weight=1)

    widgets['success_label'] = ttk.Label(summary_frame, text="Success: 0", foreground=config.STYLE_CONFIG["colors"]["light"]["success"], font=config.STYLE_CONFIG["font_bold"])
    widgets['success_label'].grid(row=0, column=0, sticky='w')
    
    widgets['skipped_label'] = ttk.Label(summary_frame, text="Skipped/Failed: 0", foreground=config.STYLE_CONFIG["colors"]["light"]["warning"], font=config.STYLE_CONFIG["font_bold"])
    widgets['skipped_label'].grid(row=0, column=1, sticky='w')

    cols = ("Timestamp", "Work Code/Key", "Status", "Details")
    widgets['results_tree'] = ttk.Treeview(results_tab_frame, columns=cols, show='headings')
    for col in cols:
        widgets['results_tree'].heading(col, text=col)
    widgets['results_tree'].column("Timestamp", width=80, anchor='center')
    widgets['results_tree'].column("Work Code/Key", width=250)
    widgets['results_tree'].column("Status", width=100, anchor='center')
    widgets['results_tree'].column("Details", width=400)
    widgets['results_tree'].grid(row=1, column=0, sticky='nsew')
    
    scrollbar = ttk.Scrollbar(results_tab_frame, orient="vertical", command=widgets['results_tree'].yview)
    widgets['results_tree'].configure(yscroll=scrollbar.set)
    scrollbar.grid(row=1, column=1, sticky='ns')

    # --- Logs Tab ---
    logs_tab_frame.columnconfigure(0, weight=1)
    logs_tab_frame.rowconfigure(1, weight=1)
    status_bar = ttk.Frame(logs_tab_frame)
    status_bar.grid(row=0, column=0, sticky='ew')
    status_bar.columnconfigure(0, weight=1)
    widgets['status_label'] = ttk.Label(status_bar, text="Status: Ready", style="Status.TLabel")
    widgets['status_label'].grid(row=0, column=0, sticky='ew')
    widgets['copy_logs_button'] = ttk.Button(status_bar, text="Copy Logs", style="Outline.TButton", command=lambda: copy_logs_to_clipboard(app_instance))
    widgets['copy_logs_button'].grid(row=0, column=1, sticky='e', padx=5)
    widgets['log_text'] = scrolledtext.ScrolledText(logs_tab_frame, wrap=tk.WORD, state=tk.DISABLED)
    widgets['log_text'].grid(row=1, column=0, sticky='nsew', pady=(10, 0))

    load_inputs(app_instance)

def _log_result(app, item_key, status, details, success_counter, skipped_counter):
    timestamp = datetime.now().strftime("%H:%M:%S")
    values = (timestamp, item_key, status, details)
    
    if status == "Success":
        success_counter[0] += 1
        app.after(0, lambda: widgets['success_label'].config(text=f"Success: {success_counter[0]}"))
    else:
        skipped_counter[0] += 1
        app.after(0, lambda: widgets['skipped_label'].config(text=f"Skipped/Failed: {skipped_counter[0]}"))
        
    app.after(0, lambda: widgets['results_tree'].insert("", "end", values=values))

def copy_logs_to_clipboard(app):
    log_content = widgets['log_text'].get('1.0', tk.END).strip()
    if log_content:
        app.clipboard_clear()
        app.clipboard_append(log_content)
        messagebox.showinfo("Copied", "Logs have been copied to the clipboard.")

def get_inputs_path(app):
    return app.get_data_path(LAST_INPUTS_FILE)

def save_inputs(app, inputs):
    try:
        with open(get_inputs_path(app), 'w') as f:
            json.dump({k: v for k, v in inputs.items() if 'work' not in k}, f)
    except Exception as e:
        print(f"Error saving inputs: {e}")

def load_inputs(app):
    try:
        path = get_inputs_path(app)
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                widgets['panchayat_entry'].insert(0, data.get('panchayat', ''))
                widgets['start_date_entry'].insert(0, data.get('start_date', ''))
                widgets['end_date_entry'].insert(0, data.get('end_date', ''))
                widgets['designation_combobox'].set(data.get('designation', ''))
                widgets['staff_entry'].insert(0, data.get('staff', ''))
    except Exception as e:
        print(f"Error loading inputs: {e}")

def reset_ui(app):
    if messagebox.askokcancel("Reset Form?", "Are you sure you want to clear all inputs and logs?"):
        for key in ['panchayat_entry', 'start_date_entry', 'end_date_entry', 'staff_entry']:
            widgets[key].delete(0, tk.END)
        widgets['designation_combobox'].set('')
        widgets['work_codes_text'].delete('1.0', tk.END)
        for item in widgets['results_tree'].get_children():
            widgets['results_tree'].delete(item)
        app.clear_log(widgets['log_text'])
        widgets['status_label'].config(text="Status: Ready")
        widgets['success_label'].config(text="Success: 0")
        widgets['skipped_label'].config(text="Skipped/Failed: 0")
        app.log_message(widgets['log_text'], "Form has been reset.")

def set_ui_state(running):
    state = "disabled" if running else "normal"
    for name in ['panchayat_entry', 'start_date_entry', 'end_date_entry', 'staff_entry',
                 'work_codes_text', 'start_button', 'reset_button', 'copy_logs_button']:
        widgets[name].config(state=state)
    widgets['designation_combobox'].config(state="readonly" if not running else "disabled")
    widgets['stop_button'].config(state="normal" if running else "disabled")

def start_automation(app):
    for item in widgets['results_tree'].get_children():
        widgets['results_tree'].delete(item)
    widgets['success_label'].config(text="Success: 0")
    widgets['skipped_label'].config(text="Skipped/Failed: 0")

    inputs = {
        'panchayat': widgets['panchayat_entry'].get().strip(),
        'start_date': widgets['start_date_entry'].get().strip(),
        'end_date': widgets['end_date_entry'].get().strip(),
        'designation': widgets['designation_combobox'].get().strip(),
        'staff': widgets['staff_entry'].get().strip(),
        'work_codes_raw': widgets['work_codes_text'].get("1.0", tk.END).strip()
    }
    
    if not all(inputs[k] for k in ['panchayat', 'start_date', 'end_date', 'designation', 'staff']):
        messagebox.showwarning("Input Error", "All fields are required (except Work Search Keys for auto mode).")
        return
        
    inputs['work_codes'] = [line.strip() for line in inputs['work_codes_raw'].split('\n') if line.strip()]
    inputs['auto_mode'] = not bool(inputs['work_codes'])

    save_inputs(app, inputs)
    app.start_automation_thread("muster", run_automation_logic, args=(inputs,))

def run_automation_logic(app, inputs):
    app.after(0, set_ui_state, True)
    app.clear_log(widgets['log_text'])
    app.log_message(widgets['log_text'], f"Starting Muster Roll generation for Panchayat: {inputs['panchayat']}")

    success_count = [0]
    skipped_count = [0]

    try:
        driver = app.connect_to_chrome()
        wait = WebDriverWait(driver, 20)
        
        downloads_dir = app.get_user_downloads_path()
        output_dir = os.path.join(downloads_dir, 'NREGA_MR_Output', datetime.now().strftime('%Y-%m-%d'), inputs['panchayat'])
        os.makedirs(output_dir, exist_ok=True)
        app.log_message(widgets['log_text'], f"PDFs will be saved to: {output_dir}", "info")
        
        # --- PRE-VALIDATION for Panchayat Name ---
        try:
            app.log_message(widgets['log_text'], "Validating Panchayat name...")
            driver.get(config.MUSTER_ROLL_CONFIG["base_url"])
            panchayat_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "exe_agency"))))
            panchayat_options = [opt.text for opt in panchayat_dropdown.options]
            target_panchayat = f"Gram Panchayat -{inputs['panchayat']}"
            if target_panchayat not in panchayat_options:
                messagebox.showerror("Validation Error", f"Panchayat or Agency name '{inputs['panchayat']}' not found.\n\nPlease check the spelling and try again.")
                raise ValueError("Panchayat not found")
            app.log_message(widgets['log_text'], "Panchayat name is valid.", "success")
        except Exception as e:
            app.log_message(widgets['log_text'], f"Validation failed: {e}", "error")
            app.after(0, set_ui_state, False)
            return
        # --- END PRE-VALIDATION ---

        items_to_process = []
        if inputs['auto_mode']:
            app.log_message(widgets['log_text'], "Auto Mode: Fetching available work codes...")
            Select(driver.find_element(By.ID, "exe_agency")).select_by_visible_text(f"Gram Panchayat -{inputs['panchayat']}")
            wait.until(lambda d: len(Select(d.find_element(By.ID, "ddlWorkCode")).options) > 1)
            all_options = Select(driver.find_element(By.ID, "ddlWorkCode")).options
            items_to_process = [opt.text for opt in all_options if opt.get_attribute("value")]
            app.log_message(widgets['log_text'], f"Found {len(items_to_process)} available work codes.")
        else:
            items_to_process = inputs['work_codes']
            app.log_message(widgets['log_text'], f"Processing {len(items_to_process)} work keys from user input.")
        
        session_skip_list = set()

        for index, item in enumerate(items_to_process):
            if app.stop_events["muster"].is_set():
                app.log_message(widgets['log_text'], "Stop signal received.", "warning"); break
            
            full_work_code_text = ""
            app.log_message(widgets['log_text'], f"\n--- Processing item ({index+1}/{len(items_to_process)}): {item} ---", "info")
            app.after(0, lambda i=item: widgets['status_label'].config(text=f"Status: Processing {i}"))
            
            try:
                driver.get(config.MUSTER_ROLL_CONFIG["base_url"])
                Select(wait.until(EC.presence_of_element_located((By.ID, "exe_agency")))).select_by_visible_text(f"Gram Panchayat -{inputs['panchayat']}")
                
                if inputs['auto_mode']:
                    full_work_code_text = item
                    if full_work_code_text in session_skip_list:
                        _log_result(app, item, "Skipped", "Already processed", success_count, skipped_count)
                        continue
                    wait.until(lambda d: len(Select(d.find_element(By.ID, "ddlWorkCode")).options) > 1)
                    Select(driver.find_element(By.ID, "ddlWorkCode")).select_by_visible_text(full_work_code_text)
                else: 
                    search_key = item
                    search_box = wait.until(EC.presence_of_element_located((By.ID, "txtWork")))
                    search_box.clear(); search_box.send_keys(search_key)
                    driver.find_element(By.ID, "imgButtonSearch").click()
                    app.log_message(widgets['log_text'], f"Searching for key: {search_key}")
                    time.sleep(2) # Added wait time
                    wait.until(lambda d: len(Select(d.find_element(By.ID, "ddlWorkCode")).options) > 1)
                    work_code_dropdown = Select(driver.find_element(By.ID, "ddlWorkCode"))
                    found_option = next((opt for opt in work_code_dropdown.options if search_key in opt.text and opt.get_attribute("value")), None)
                    if found_option:
                        full_work_code_text = found_option.text
                        if full_work_code_text in session_skip_list:
                            _log_result(app, item, "Skipped", "Already processed", success_count, skipped_count)
                            continue
                        Select(driver.find_element(By.ID, "ddlWorkCode")).select_by_visible_text(full_work_code_text)
                        app.log_message(widgets['log_text'], f"Found and selected work: {full_work_code_text}")
                    else:
                        raise NoSuchElementException(f"Could not find work for search key '{item}'.")
                
                driver.find_element(By.ID, "txtDateFrom").send_keys(inputs['start_date'])
                driver.find_element(By.ID, "txtDateTo").send_keys(inputs['end_date'])
                
                Select(wait.until(EC.element_to_be_clickable((By.ID, "ddldesg")))).select_by_visible_text(inputs['designation'])
                time.sleep(1) 
                
                staff_dropdown = Select(wait.until(EC.element_to_be_clickable((By.ID, "ddlstaff"))))
                staff_options = [opt.text for opt in staff_dropdown.options]
                if inputs['staff'] not in staff_options:
                    messagebox.showerror("Automation Stopped", f"Technical Staff Name Not Matched: '{inputs['staff']}'\n\nPlease check the spelling and try again.")
                    raise ValueError(f"Staff name '{inputs['staff']}' not found. Stopping automation.")
                staff_dropdown.select_by_visible_text(inputs['staff'])
                
                body_element = driver.find_element(By.TAG_NAME, 'body')
                driver.find_element(By.ID, "btnProceed").click()
                
                app.log_message(widgets['log_text'], "Waiting for page to reload...")
                wait.until(EC.staleness_of(body_element))
                time.sleep(1)
                
                page_error = None
                if driver.find_elements(By.XPATH, "//*[contains(text(), 'Geotag is not received')]"):
                    page_error = "Geotag status error"
                elif driver.find_elements(By.XPATH, "//*[contains(text(), 'greater than allowed limit')]"):
                    page_error = "Work limit error"
                
                if page_error:
                    _log_result(app, item, "Skipped", page_error, success_count, skipped_count)
                    session_skip_list.add(full_work_code_text)
                    continue

                try:
                    short_wait = WebDriverWait(driver, 2)
                    short_wait.until(EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'No Worker Available')]")))
                    _log_result(app, item, "Skipped", "No Worker Available", success_count, skipped_count)
                    session_skip_list.add(full_work_code_text)
                    continue
                except TimeoutException:
                    app.log_message(widgets['log_text'], "Muster Roll is valid. Saving PDF...")

                work_id_part = full_work_code_text.split('/')[-1]
                short_name = work_id_part[-6:]
                pdf_filename = f"{short_name}.pdf"
                save_path = os.path.join(output_dir, pdf_filename)

                print_options = {'landscape': False, 'displayHeaderFooter': False, 'printBackground': False, 'preferCSSPageSize': True}
                result = driver.execute_cdp_cmd("Page.printToPDF", print_options)
                pdf_data = base64.b64decode(result['data'])
                
                with open(save_path, 'wb') as f: f.write(pdf_data)
                
                _log_result(app, item, "Success", f"Saved as {pdf_filename}", success_count, skipped_count)
                session_skip_list.add(full_work_code_text)
                time.sleep(1)

            except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
                error_message = str(e).split('\n')[0]
                app.log_message(widgets['log_text'], f"ERROR processing '{item}': {error_message}", "error")
                _log_result(app, item, "Failed", error_message, success_count, skipped_count)
                continue
            except ValueError as e: 
                error_message = str(e).split('\n')[0]
                app.log_message(widgets['log_text'], f"CRITICAL ERROR: {error_message}", "error")
                _log_result(app, item, "Failed", error_message, success_count, skipped_count)
                break 

    except Exception as e:
        app.log_message(widgets['log_text'], f"A critical error occurred: {e}", "error")
        if "in str" not in str(e):
            messagebox.showerror("Critical Error", f"An unexpected error stopped the automation:\n\n{e}")
    finally:
        app.after(0, set_ui_state, False)
        app.after(0, lambda: widgets['status_label'].config(text="Status: Automation Finished."))
        
        summary_message = f"Automation complete.\n\nSuccessfully generated: {success_count[0]}\nSkipped/Failed: {skipped_count[0]}"
        app.after(0, lambda: messagebox.showinfo("Task Finished", summary_message))
