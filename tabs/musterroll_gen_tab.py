# tabs/musterroll_gen_tab.py (Updated with Autocomplete)
import tkinter
from tkinter import ttk, messagebox
import customtkinter as ctk
import os, json, time, base64, sys, subprocess
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import config
from .base_tab import BaseAutomationTab
from .autocomplete_widget import AutocompleteEntry # Import the new widget

class MusterrollGenTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="muster")
        self.config_file = self.app.get_data_path("muster_roll_inputs.json")
        self.success_count = 0; self.skipped_count = 0
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(2, weight=1)
        self._create_widgets(); self.load_inputs()

    def _create_widgets(self):
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10,0))
        controls_frame.grid_columnconfigure((1,3), weight=1)
        
        # --- UPDATED: Use AutocompleteEntry for text fields ---
        ctk.CTkLabel(controls_frame, text="Panchayat Name:").grid(row=0, column=0, sticky='w', padx=15, pady=(15,0))
        self.panchayat_entry = AutocompleteEntry(controls_frame, suggestions_list=self.app.history_manager.get_suggestions("panchayat_name"))
        self.panchayat_entry.grid(row=0, column=1, columnspan=3, sticky='ew', padx=15, pady=(15,0))
        
        ctk.CTkLabel(controls_frame, text="Note: Must exactly match the name on the NREGA website.", text_color="gray50").grid(row=1, column=1, columnspan=3, sticky='w', padx=15, pady=(0,10))
        ctk.CTkLabel(controls_frame, text="तारीख से (DD/MM/YYYY):").grid(row=2, column=0, sticky='w', padx=15, pady=5)
        self.start_date_entry = ctk.CTkEntry(controls_frame)
        self.start_date_entry.grid(row=2, column=1, sticky='ew', padx=(15,5), pady=5)
        ctk.CTkLabel(controls_frame, text="तारीख को (DD/MM/YYYY):").grid(row=2, column=2, sticky='w', padx=10, pady=5)
        self.end_date_entry = ctk.CTkEntry(controls_frame)
        self.end_date_entry.grid(row=2, column=3, sticky='ew', padx=(5,15), pady=5)
        
        ctk.CTkLabel(controls_frame, text="Select Designation:").grid(row=3, column=0, sticky='w', padx=15, pady=5)
        designation_options = ["Junior Engineer--BP", "Assistant Engineer--BP", "Technical Assistant--BP", "Acrited Engineer(AE)--GP", "Junior Engineer--GP", "Technical Assistant--GP"]
        self.designation_combobox = ctk.CTkComboBox(controls_frame, values=designation_options)
        self.designation_combobox.grid(row=3, column=1, sticky='ew', padx=(15,5), pady=5)
        
        ctk.CTkLabel(controls_frame, text="Select Technical Staff:").grid(row=3, column=2, sticky='w', padx=10, pady=5)
        self.staff_entry = AutocompleteEntry(controls_frame, suggestions_list=self.app.history_manager.get_suggestions("staff_name"))
        self.staff_entry.grid(row=3, column=3, sticky='ew', padx=(5,15), pady=5)
        ctk.CTkLabel(controls_frame, text="PDF Orientation:").grid(row=4, column=0, sticky='w', padx=15, pady=5)
        self.orientation_combobox = ctk.CTkComboBox(controls_frame, values=["Landscape", "Portrait"])
        self.orientation_combobox.set("Landscape")
        self.orientation_combobox.grid(row=4, column=1, sticky='ew', padx=(15,5), pady=5)
        ctk.CTkLabel(controls_frame, text="ℹ️ Generated Muster Rolls are saved in 'Downloads/NREGA_MR_Output'.", text_color="gray50").grid(row=5, column=1, columnspan=3, sticky='w', padx=15, pady=(10,15))
        
        action_frame_container = ctk.CTkFrame(self)
        action_frame_container.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        action_frame = self._create_action_buttons(parent_frame=action_frame_container)
        action_frame.pack(expand=True, fill='x')

        data_notebook = ctk.CTkTabview(self)
        data_notebook.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0,10))
        work_codes_tab = data_notebook.add("Work Search Keys (or auto)"); results_tab = data_notebook.add("Results")
        self._create_log_and_status_area(parent_notebook=data_notebook)
        
        # Work Codes tab with Clear button
        work_codes_tab.grid_columnconfigure(0, weight=1); work_codes_tab.grid_rowconfigure(1, weight=1)
        wc_controls = ctk.CTkFrame(work_codes_tab, fg_color="transparent")
        wc_controls.grid(row=0, column=0, sticky='ew')
        clear_button = ctk.CTkButton(wc_controls, text="Clear", width=80, command=lambda: self.work_codes_text.delete("1.0", tkinter.END))
        clear_button.pack(side='right', pady=(5,0), padx=(0,5))
        self.work_codes_text = ctk.CTkTextbox(work_codes_tab, height=100); self.work_codes_text.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        
        # Results tab
        results_tab.grid_columnconfigure(0, weight=1); results_tab.grid_rowconfigure(1, weight=1)
        summary_frame = ctk.CTkFrame(results_tab, fg_color="transparent"); summary_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        summary_frame.grid_columnconfigure((0, 1), weight=1)
        self.success_label = ctk.CTkLabel(summary_frame, text="Success: 0", text_color="#2E8B57", font=ctk.CTkFont(weight="bold")); self.success_label.grid(row=0, column=0, sticky='w')
        self.skipped_label = ctk.CTkLabel(summary_frame, text="Skipped/Failed: 0", text_color="#DAA520", font=ctk.CTkFont(weight="bold")); self.skipped_label.grid(row=0, column=1, sticky='w')
        cols = ("Timestamp", "Work Code/Key", "Status", "Details"); self.results_tree = ttk.Treeview(results_tab, columns=cols, show='headings')
        for col in cols: self.results_tree.heading(col, text=col)
        self.results_tree.column("Timestamp", width=80, anchor='center'); self.results_tree.column("Work Code/Key", width=250); self.results_tree.column("Status", width=100, anchor='center'); self.results_tree.column("Details", width=400)
        self.results_tree.grid(row=1, column=0, sticky='nsew')
        scrollbar = ctk.CTkScrollbar(results_tab, command=self.results_tree.yview); self.results_tree.configure(yscroll=scrollbar.set); scrollbar.grid(row=1, column=1, sticky='ns')
        self.style_treeview(self.results_tree)

    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running)
        state = "disabled" if running else "normal"
        self.panchayat_entry.configure(state=state); self.start_date_entry.configure(state=state)
        self.end_date_entry.configure(state=state); self.staff_entry.configure(state=state)
        self.designation_combobox.configure(state=state); self.orientation_combobox.configure(state=state)
        self.work_codes_text.configure(state=state)

    # ... The rest of the file (start_automation, reset_ui, run_automation_logic, etc.) remains unchanged ...
    def start_automation(self):
        for item in self.results_tree.get_children(): self.results_tree.delete(item)
        self.success_count = 0; self.skipped_count = 0
        self.success_label.configure(text="Success: 0"); self.skipped_label.configure(text="Skipped/Failed: 0")
        inputs = {'panchayat': self.panchayat_entry.get().strip(), 'start_date': self.start_date_entry.get().strip(), 'end_date': self.end_date_entry.get().strip(), 'designation': self.designation_combobox.get().strip(), 'staff': self.staff_entry.get().strip(), 'orientation': self.orientation_combobox.get(), 'work_codes_raw': self.work_codes_text.get("1.0", tkinter.END).strip()}
        if not all(inputs[k] for k in ['panchayat', 'start_date', 'end_date', 'designation', 'staff']):
            messagebox.showwarning("Input Error", "All fields are required (except Work Search Keys)."); return
        inputs['work_codes'] = [line.strip() for line in inputs['work_codes_raw'].split('\n') if line.strip()]
        inputs['auto_mode'] = not bool(inputs['work_codes'])
        self.save_inputs(inputs)
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic, args=(inputs,))
    def reset_ui(self):
        if messagebox.askokcancel("Reset Form?", "Clear all inputs and logs?"):
            self.panchayat_entry.delete(0, tkinter.END); self.start_date_entry.delete(0, tkinter.END)
            self.end_date_entry.delete(0, tkinter.END); self.staff_entry.delete(0, tkinter.END)
            self.designation_combobox.set(''); self.orientation_combobox.set('Landscape')
            self.work_codes_text.delete('1.0', tkinter.END)
            for item in self.results_tree.get_children(): self.results_tree.delete(item)
            self.app.clear_log(self.log_display)
            self.update_status("Ready", 0.0)
            self.success_label.configure(text="Success: 0"); self.skipped_label.configure(text="Skipped/Failed: 0")
            self.app.log_message(self.log_display, "Form has been reset.")
    def save_inputs(self, inputs):
        try:
            with open(self.config_file, 'w') as f: json.dump({k: v for k, v in inputs.items() if 'work' not in k}, f, indent=4)
        except Exception as e: print(f"Error saving inputs: {e}")
    def load_inputs(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f: data = json.load(f)
                self.panchayat_entry.insert(0, data.get('panchayat', '')); self.start_date_entry.insert(0, data.get('start_date', ''))
                self.end_date_entry.insert(0, data.get('end_date', '')); self.designation_combobox.set(data.get('designation', ''))
                self.staff_entry.insert(0, data.get('staff', '')); self.orientation_combobox.set(data.get('orientation', 'Landscape'))
        except Exception as e: print(f"Error loading inputs: {e}")
    # In tabs/musterroll_gen_tab.py, inside the MusterrollGenTab class

    def run_automation_logic(self, inputs):
        self.app.after(0, self.set_ui_state, True)
        self.app.clear_log(self.log_display)
        self.app.log_message(self.log_display, f"Starting MR generation for: {inputs['panchayat']}")
        
        output_dir = None # Initialize here to be accessible in 'finally'
        
        try:
            driver = self.app.connect_to_chrome()
            if not driver: self.app.after(0, self.set_ui_state, False); return
            wait = WebDriverWait(driver, 20)
            
            downloads_dir = self.app.get_user_downloads_path()
            output_dir = os.path.join(downloads_dir, config.MUSTER_ROLL_CONFIG['output_folder_name'], datetime.now().strftime('%Y-%m-%d'), inputs['panchayat'])
            os.makedirs(output_dir, exist_ok=True)
            self.app.log_message(self.log_display, f"PDFs will be saved to: {output_dir}", "info")
            
            if not self._validate_panchayat(driver, wait, inputs['panchayat']):
                self.app.after(0, self.set_ui_state, False); return
            
            self.app.update_history("panchayat_name", inputs['panchayat'])
            self.app.update_history("designation", inputs['designation'])
            self.app.update_history("staff_name", inputs['staff'])

            items_to_process = self._get_items_to_process(driver, wait, inputs)
            session_skip_list = set()
            total_items = len(items_to_process)

            for index, item in enumerate(items_to_process):
                if self.app.stop_events[self.automation_key].is_set(): 
                    self.app.log_message(self.log_display, "Stop signal received.", "warning"); break
                
                self.app.log_message(self.log_display, f"\n--- Processing item ({index+1}/{total_items}): {item} ---", "info")
                self.app.after(0, self.update_status, f"Processing {item}", (index+1)/total_items)
                self._process_single_item(driver, wait, inputs, item, output_dir, session_skip_list)
        
        except Exception as e:
            self.app.log_message(self.log_display, f"A critical error occurred: {e}", "error")
            if "in str" not in str(e): messagebox.showerror("Critical Error", f"An unexpected error stopped the automation:\n\n{e}")
        
        finally:
            self.app.after(0, self.set_ui_state, False)
            self.app.after(0, self.update_status, "Automation Finished.", 1.0)
            
            summary = f"Automation complete.\n\nSuccess: {self.success_count}\nSkipped/Failed: {self.skipped_count}"
            
            # --- NEW: ASK TO OPEN THE OUTPUT FOLDER ---
            if self.success_count > 0 and output_dir and os.path.exists(output_dir):
                if messagebox.askyesno("Task Finished", f"{summary}\n\nDo you want to open the output folder?"):
                    try:
                        if sys.platform == "win32":
                            os.startfile(output_dir)
                        elif sys.platform == "darwin": # macOS
                            subprocess.call(["open", output_dir])
                        else: # linux
                            subprocess.call(["xdg-open", output_dir])
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not open the folder automatically.\n\nPath: {output_dir}\nError: {e}")
            else:
                messagebox.showinfo("Task Finished", summary)
            
    def _validate_panchayat(self, driver, wait, panchayat_name):
        try:
            self.app.log_message(self.log_display, "Validating Panchayat name...")
            driver.get(config.MUSTER_ROLL_CONFIG["base_url"])
            panchayat_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "exe_agency"))))
            target_panchayat = config.AGENCY_PREFIX + panchayat_name
            if target_panchayat not in [opt.text for opt in panchayat_dropdown.options]: messagebox.showerror("Validation Error", f"Panchayat name '{panchayat_name}' not found."); return False
            self.app.log_message(self.log_display, "Panchayat name is valid.", "success"); return True
        except Exception as e: self.app.log_message(self.log_display, f"Validation failed: {e}", "error"); return False
    def _get_items_to_process(self, driver, wait, inputs):
        if inputs['auto_mode']:
            self.app.log_message(self.log_display, "Auto Mode: Fetching available work codes...")
            Select(driver.find_element(By.ID, "exe_agency")).select_by_visible_text(config.AGENCY_PREFIX + inputs['panchayat'])
            wait.until(lambda d: len(Select(d.find_element(By.ID, "ddlWorkCode")).options) > 1)
            items = [opt.text for opt in Select(driver.find_element(By.ID, "ddlWorkCode")).options if opt.get_attribute("value")]
            self.app.log_message(self.log_display, f"Found {len(items)} available work codes."); return items
        else: self.app.log_message(self.log_display, f"Processing {len(inputs['work_codes'])} work keys."); return inputs['work_codes']
    def _process_single_item(self, driver, wait, inputs, item, output_dir, session_skip_list):
        try:
            driver.get(config.MUSTER_ROLL_CONFIG["base_url"])
            Select(wait.until(EC.presence_of_element_located((By.ID, "exe_agency")))).select_by_visible_text(config.AGENCY_PREFIX + inputs['panchayat'])
            full_work_code_text = self._select_work_code(driver, wait, item, inputs['auto_mode'])
            if full_work_code_text in session_skip_list: self._log_result(item, "Skipped", "Already processed this session"); return
            driver.find_element(By.ID, "txtDateFrom").send_keys(inputs['start_date'])
            driver.find_element(By.ID, "txtDateTo").send_keys(inputs['end_date'])
            Select(wait.until(EC.element_to_be_clickable((By.ID, "ddldesg")))).select_by_visible_text(inputs['designation'])
            wait.until(EC.element_to_be_clickable((By.XPATH, "//select[@id='ddlstaff']/option[position()>1]")))
            staff_dropdown = Select(driver.find_element(By.ID, "ddlstaff"))
            if inputs['staff'] not in [opt.text for opt in staff_dropdown.options]: raise ValueError(f"Staff name '{inputs['staff']}' not found for the selected designation. Stopping.")
            staff_dropdown.select_by_visible_text(inputs['staff'])
            body_element = driver.find_element(By.TAG_NAME, 'body')
            driver.find_element(By.ID, "btnProceed").click()
            self.app.log_message(self.log_display, "Waiting for page to reload..."); wait.until(EC.staleness_of(body_element)); time.sleep(2) 
            if self._check_for_page_errors(driver): self._log_result(item, "Skipped", "Page error (Geotag/Limit/No Worker)"); session_skip_list.add(full_work_code_text); return
            self.app.log_message(self.log_display, "Muster Roll is valid. Saving PDF...")
            pdf_filename = f"{full_work_code_text.split('/')[-1][-6:]}.pdf"
            save_path = os.path.join(output_dir, pdf_filename)
            print_options = config.MUSTER_ROLL_CONFIG['pdf_options'] if inputs['orientation'] == 'Landscape' else config.MUSTER_ROLL_CONFIG['pdf_options_portrait']
            result = driver.execute_cdp_cmd("Page.printToPDF", print_options)
            pdf_data = base64.b64decode(result['data'])
            with open(save_path, 'wb') as f: f.write(pdf_data)
            self._log_result(item, "Success", f"Saved as {pdf_filename}"); session_skip_list.add(full_work_code_text); time.sleep(1)
        except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
            error_message = str(e).split('\n')[0]; self.app.log_message(self.log_display, f"ERROR on '{item}': {error_message}", "error"); self._log_result(item, "Failed", error_message)
        except ValueError as e: 
            error_message = str(e).split('\n')[0]; self.app.log_message(self.log_display, f"CRITICAL ERROR: {error_message}", "error"); self._log_result(item, "Failed", error_message); raise e
    def _select_work_code(self, driver, wait, item, is_auto_mode):
        if is_auto_mode:
            wait.until(lambda d: len(Select(d.find_element(By.ID, "ddlWorkCode")).options) > 1)
            Select(driver.find_element(By.ID, "ddlWorkCode")).select_by_visible_text(item)
            return item
        else:
            search_key = item
            search_box = wait.until(EC.presence_of_element_located((By.ID, "txtWork")))
            search_box.clear(); search_box.send_keys(search_key)
            driver.find_element(By.ID, "imgButtonSearch").click()
            self.app.log_message(self.log_display, f"Searching for key: {search_key}"); time.sleep(2)
            wait.until(lambda d: len(Select(d.find_element(By.ID, "ddlWorkCode")).options) > 1)
            work_code_dropdown = Select(driver.find_element(By.ID, "ddlWorkCode"))
            found_option = next((opt for opt in work_code_dropdown.options if search_key in opt.text and opt.get_attribute("value")), None)
            if found_option:
                full_work_code_text = found_option.text
                work_code_dropdown.select_by_visible_text(full_work_code_text)
                self.app.log_message(self.log_display, f"Found and selected work: {full_work_code_text}"); return full_work_code_text
            else: raise NoSuchElementException(f"Could not find work for search key '{item}'.")
    def _check_for_page_errors(self, driver):
        page_source = driver.page_source
        if "Geotag is not received" in page_source: return True
        if "greater than allowed limit" in page_source: return True
        if "No Worker Available" in page_source: return True
        return False
    def _log_result(self, item_key, status, details):
        timestamp = datetime.now().strftime("%H:%M:%S")
        values = (timestamp, item_key, status, details)
        if status == "Success":
            self.success_count += 1
            self.app.after(0, lambda: self.success_label.configure(text=f"Success: {self.success_count}"))
        else:
            self.skipped_count += 1
            self.app.after(0, lambda: self.skipped_label.configure(text=f"Skipped/Failed: {self.skipped_count}"))
        self.app.after(0, lambda: self.results_tree.insert("", "end", values=values))