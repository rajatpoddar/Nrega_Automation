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
    """Creates the Muster Roll Generation tab GUI."""
    parent_frame.columnconfigure(0, weight=1)
    parent_frame.rowconfigure(2, weight=1)

    controls_frame = ttk.LabelFrame(parent_frame, text="Muster Roll Generation Controls")
    controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    controls_frame.columnconfigure(1, weight=1)
    controls_frame.columnconfigure(3, weight=1)

    # Row 0: Panchayat Name
    ttk.Label(controls_frame, text="Panchayat Name: Gram Panchayat -").grid(row=0, column=0, sticky='w', padx=5, pady=5)
    panchayat_var = tk.StringVar()
    panchayat_var.trace_add("write", lambda n, i, m, v=panchayat_var: v.set(v.get().upper()))
    widgets['panchayat_entry'] = ttk.Entry(controls_frame, textvariable=panchayat_var)
    widgets['panchayat_entry'].grid(row=0, column=1, columnspan=3, sticky='ew', padx=5, pady=5)

    # Row 1: Dates
    ttk.Label(controls_frame, text="तारीख से (DD/MM/YYYY):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
    widgets['start_date_entry'] = ttk.Entry(controls_frame)
    widgets['start_date_entry'].grid(row=1, column=1, sticky='ew', padx=5, pady=5)
    ttk.Label(controls_frame, text="तारीख को (DD/MM/YYYY):").grid(row=1, column=2, sticky='w', padx=5, pady=5)
    widgets['end_date_entry'] = ttk.Entry(controls_frame)
    widgets['end_date_entry'].grid(row=1, column=3, sticky='ew', padx=5, pady=5)

    # Row 2: Designation and Staff
    ttk.Label(controls_frame, text="Select Designation:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
    designation_options = [
        "Junior Engineer--BP", "Assistant Engineer--BP", "Technical Assistant--BP",
        "Acrited Engineer(AE)--GP", "Junior Engineer--GP", "Technical Assistant--GP"
    ]
    widgets['designation_combobox'] = ttk.Combobox(controls_frame, values=designation_options, state="readonly")
    widgets['designation_combobox'].grid(row=2, column=1, sticky='ew', padx=5, pady=5)
    ttk.Label(controls_frame, text="Select Technical Staff:").grid(row=2, column=2, sticky='w', padx=5, pady=5)
    widgets['staff_entry'] = ttk.Entry(controls_frame)
    widgets['staff_entry'].grid(row=2, column=3, sticky='ew', padx=5, pady=5)

    # Row 3: Work Search Keys
    ttk.Label(controls_frame, text="Work Search Keys (or leave blank for auto):").grid(row=3, column=0, sticky='nw', padx=5, pady=5)
    widgets['work_codes_text'] = scrolledtext.ScrolledText(controls_frame, wrap=tk.WORD, height=8)
    widgets['work_codes_text'].grid(row=3, column=1, columnspan=3, sticky='ew', padx=5, pady=5)

    # --- NEW: Instructional text for save location ---
    # Row 4: Informational Label
    info_label = ttk.Label(controls_frame, text="ℹ️ All generated Muster Rolls are saved in a 'NREGA_MR_Output' folder inside your Downloads.", style="Instruction.TLabel")
    info_label.grid(row=4, column=1, columnspan=3, sticky='w', padx=5, pady=(5,0))

    # Row 5: Action Buttons
    action_frame = ttk.Frame(controls_frame)
    action_frame.grid(row=5, column=0, columnspan=4, sticky='ew', pady=(15, 5))
    action_frame.columnconfigure((0, 1, 2), weight=1)
    widgets['start_button'] = ttk.Button(action_frame, text="▶ Start Generation", style="Accent.TButton", command=lambda: start_automation(app_instance))
    widgets['stop_button'] = ttk.Button(action_frame, text="Stop", command=lambda: app_instance.stop_events["muster"].set(), state=tk.DISABLED)
    widgets['reset_button'] = ttk.Button(action_frame, text="Reset", style="Outline.TButton", command=lambda: reset_ui(app_instance))
    widgets['start_button'].grid(row=0, column=0, sticky="ew", padx=(0,5), ipady=5)
    widgets['stop_button'].grid(row=0, column=1, sticky="ew", padx=(5,5), ipady=5)
    widgets['reset_button'].grid(row=0, column=2, sticky='ew', padx=(5,0), ipady=5)

    # --- Results Frame ---
    results_frame = ttk.LabelFrame(parent_frame, text="Results")
    results_frame.grid(row=1, column=0, sticky="ew", pady=10)
    results_frame.columnconfigure((0, 1), weight=1)
    
    widgets['success_label'] = ttk.Label(results_frame, text="Successfully Generated: 0", style="Success.TLabel")
    widgets['success_label'].grid(row=0, column=0, sticky='w', padx=10, pady=5)
    
    widgets['skipped_label'] = ttk.Label(results_frame, text="Skipped (No Workers): 0", style="Warning.TLabel")
    widgets['skipped_label'].grid(row=0, column=1, sticky='w', padx=10, pady=5)

    # --- Log Frame ---
    log_frame = ttk.LabelFrame(parent_frame, text="Logs & Status")
    log_frame.grid(row=2, column=0, sticky="nsew")
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(1, weight=1)
    status_bar = ttk.Frame(log_frame)
    status_bar.grid(row=0, column=0, sticky='ew')
    status_bar.columnconfigure(0, weight=1)
    widgets['status_label'] = ttk.Label(status_bar, text="Status: Ready", style="Status.TLabel")
    widgets['status_label'].grid(row=0, column=0, sticky='ew')
    widgets['copy_logs_button'] = ttk.Button(status_bar, text="Copy Logs", style="Outline.TButton", command=lambda: copy_logs_to_clipboard(app_instance))
    widgets['copy_logs_button'].grid(row=0, column=1, sticky='e', padx=5)
    widgets['log_text'] = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state=tk.DISABLED)
    widgets['log_text'].grid(row=1, column=0, sticky='nsew', pady=(10, 0))

    load_inputs()

def copy_logs_to_clipboard(app):
    log_content = widgets['log_text'].get('1.0', tk.END).strip()
    if log_content:
        app.clipboard_clear()
        app.clipboard_append(log_content)
        app.log_message(widgets['log_text'], "Logs copied to clipboard.", "info")

def save_inputs(inputs):
    try:
        with open(LAST_INPUTS_FILE, 'w') as f:
            data_to_save = {k: v for k, v in inputs.items() if k not in ['work_codes_raw', 'work_codes', 'auto_mode']}
            json.dump(data_to_save, f)
    except Exception as e:
        print(f"Error saving inputs: {e}")

def load_inputs():
    try:
        if os.path.exists(LAST_INPUTS_FILE):
            with open(LAST_INPUTS_FILE, 'r') as f:
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
        app.clear_log(widgets['log_text'])
        widgets['status_label'].config(text="Status: Ready")
        widgets['success_label'].config(text="Successfully Generated: 0")
        widgets['skipped_label'].config(text="Skipped (No Workers): 0")
        app.log_message(widgets['log_text'], "Form has been reset.")

def set_ui_state(running):
    state = "disabled" if running else "normal"
    for widget_name in ['panchayat_entry', 'start_date_entry', 'end_date_entry',
                        'designation_combobox', 'staff_entry', 'work_codes_text',
                        'start_button', 'reset_button', 'copy_logs_button']:
        if widget_name in widgets:
            if widget_name == 'designation_combobox':
                 widgets[widget_name].config(state="disabled" if running else "readonly")
            else:
                widgets[widget_name].config(state=state)
    widgets['stop_button'].config(state="normal" if running else "disabled")

def start_automation(app):
    widgets['success_label'].config(text="Successfully Generated: 0")
    widgets['skipped_label'].config(text="Skipped (No Workers or Errors): 0")

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

    save_inputs(inputs)
    app.start_automation_thread("muster", run_automation_logic, args=(inputs,))

def run_automation_logic(app, inputs):
    app.after(0, set_ui_state, True)
    app.clear_log(widgets['log_text'])
    app.log_message(widgets['log_text'], f"Starting Muster Roll generation for Panchayat: {inputs['panchayat']}")

    success_count = 0
    skipped_count = 0

    try:
        driver = app.connect_to_chrome()
        wait = WebDriverWait(driver, 20)
        
        downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
        base_output_dir = os.path.join(downloads_dir, 'NREGA_MR_Output')
        current_date_str = datetime.now().strftime('%Y-%m-%d')
        date_folder = os.path.join(base_output_dir, current_date_str)
        panchayat_folder = os.path.join(date_folder, inputs['panchayat'])
        os.makedirs(panchayat_folder, exist_ok=True)
        app.log_message(widgets['log_text'], f"PDFs will be saved to: {panchayat_folder}", "info")
        
        items_to_process = []
        if inputs['auto_mode']:
            app.log_message(widgets['log_text'], "No search keys provided. Entering Automatic Mode.", "info")
            try:
                driver.get(config.MUSTER_ROLL_CONFIG["base_url"])
                Select(wait.until(EC.presence_of_element_located((By.ID, "exe_agency")))).select_by_visible_text(f"Gram Panchayat -{inputs['panchayat']}")
                wait.until(lambda d: len(Select(d.find_element(By.ID, "ddlWorkCode")).options) > 1)
                all_options = Select(driver.find_element(By.ID, "ddlWorkCode")).options
                items_to_process = [opt.text for opt in all_options if opt.get_attribute("value")]
                app.log_message(widgets['log_text'], f"Found {len(items_to_process)} available work codes to process.")
            except Exception as e:
                app.log_message(widgets['log_text'], f"Could not fetch work codes for auto-mode: {e}", "error")
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
                        app.log_message(widgets['log_text'], f"Work '{full_work_code_text}' is in the session skip list. Skipping.", "warning")
                        skipped_count += 1
                        continue
                    
                    wait.until(lambda d: len(Select(d.find_element(By.ID, "ddlWorkCode")).options) > 1)
                    work_code_dropdown = Select(driver.find_element(By.ID, "ddlWorkCode"))
                    work_code_dropdown.select_by_visible_text(full_work_code_text)
                    app.log_message(widgets['log_text'], f"Selected work (Auto-Mode): {full_work_code_text}")
                else: 
                    search_key = item
                    search_box = wait.until(EC.presence_of_element_located((By.ID, "txtWork")))
                    search_box.clear()
                    search_box.send_keys(search_key)
                    driver.find_element(By.ID, "imgButtonSearch").click()
                    app.log_message(widgets['log_text'], f"Searching for key: {search_key}")

                    for attempt in range(3):
                        try:
                            wait.until(lambda d: len(Select(d.find_element(By.ID, "ddlWorkCode")).options) > 1)
                            work_code_dropdown = Select(driver.find_element(By.ID, "ddlWorkCode"))
                            options = work_code_dropdown.options
                            found_option_text = next((opt.text for opt in options if search_key in opt.text and opt.get_attribute("value")), None)
                            if found_option_text:
                                full_work_code_text = found_option_text
                                if full_work_code_text in session_skip_list:
                                    app.log_message(widgets['log_text'], f"Work '{full_work_code_text}' is in session skip list. Skipping.", "warning")
                                    full_work_code_text = "SKIPPED"
                                    break
                                work_code_dropdown.select_by_visible_text(full_work_code_text)
                                app.log_message(widgets['log_text'], f"Found and selected work: {full_work_code_text}")
                                break
                            else: time.sleep(0.5)
                        except StaleElementReferenceException:
                            app.log_message(widgets['log_text'], f"Stale element detected, retrying... ({attempt+1}/3)", "warning")
                            time.sleep(1)
                    if full_work_code_text: break
                
                if not full_work_code_text:
                    raise NoSuchElementException(f"Could not find work for '{item}'.")
                if full_work_code_text == "SKIPPED":
                    skipped_count += 1
                    continue

                driver.find_element(By.ID, "txtDateFrom").send_keys(inputs['start_date'])
                driver.find_element(By.ID, "txtDateTo").send_keys(inputs['end_date'])
                Select(driver.find_element(By.ID, "ddldesg")).select_by_visible_text(inputs['designation'])
                
                time.sleep(1) 
                Select(wait.until(EC.element_to_be_clickable((By.ID, "ddlstaff")))).select_by_visible_text(inputs['staff'])
                app.log_message(widgets['log_text'], "Technical Staff selected.")
                
                body_element = driver.find_element(By.TAG_NAME, 'body')
                driver.find_element(By.ID, "btnProceed").click()
                
                app.log_message(widgets['log_text'], "Waiting for page to reload...")
                wait.until(EC.staleness_of(body_element))
                app.log_message(widgets['log_text'], "Page reloaded. Checking for content...")
                time.sleep(1)
                
                try:
                    short_wait = WebDriverWait(driver, 2)
                    short_wait.until(EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'No Worker Available')]")))
                    
                    app.log_message(widgets['log_text'], f"Page displays 'No Worker Available' for '{full_work_code_text}'.", "warning")
                    session_skip_list.add(full_work_code_text)
                    skipped_count += 1
                    app.log_message(widgets['log_text'], f"'{full_work_code_text}' added to skip list for this session.")
                    continue
                except TimeoutException:
                    app.log_message(widgets['log_text'], "Muster Roll is valid. Saving PDF...")
                
                pdf_filename = f"{full_work_code_text.replace('/', '_')}.pdf"
                save_path = os.path.join(panchayat_folder, pdf_filename)

                print_options = {
                    'landscape': False, 'displayHeaderFooter': False, 'printBackground': False,
                    'preferCSSPageSize': False, 'paperWidth': 8.27, 'paperHeight': 11.69, 'scale': 0.9
                }
                result = driver.execute_cdp_cmd("Page.printToPDF", print_options)
                pdf_data = base64.b64decode(result['data'])
                
                with open(save_path, 'wb') as f:
                    f.write(pdf_data)
                
                app.log_message(widgets['log_text'], f"Successfully saved PDF: {pdf_filename}", "success")
                success_count += 1
                session_skip_list.add(full_work_code_text)
                time.sleep(1)

            except (NoSuchElementException, ValueError, TimeoutException) as e:
                app.log_message(widgets['log_text'], f"ERROR processing '{item}': {e}", "error")
                skipped_count += 1
                continue

    except Exception as e:
        app.log_message(widgets['log_text'], f"A critical error occurred: {e}", "error")
    finally:
        app.after(0, set_ui_state, False)
        app.after(0, lambda: widgets['status_label'].config(text="Status: Automation Finished."))
        
        app.after(0, lambda: widgets['success_label'].config(text=f"Successfully Generated: {success_count}"))
        app.after(0, lambda: widgets['skipped_label'].config(text=f"Skipped (No Workers or Errors): {skipped_count}"))

        summary_message = f"Automation complete.\n\nSuccessfully generated: {success_count}\nSkipped: {skipped_count}"
        app.after(0, lambda: messagebox.showinfo("Task Finished", summary_message))