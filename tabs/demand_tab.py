# tabs/demand_tab.py
import tkinter
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import os, csv, time, threading, json
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys

import config
from .base_tab import BaseAutomationTab
from .autocomplete_widget import AutocompleteEntry
from .date_entry_widget import DateEntry

class DemandTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="demand")
        self.csv_path = None
        self.worker_thread = None
        self.stop_event = threading.Event()
        self.config_file = self.app.get_data_path("demand_inputs.json")
        
        self.all_applicants_data = [] # Holds all data from CSV
        self.displayed_checkboxes = [] # Holds only the currently visible checkbox widgets

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._create_widgets()
        self.load_inputs()

    def _create_widgets(self):
        # Main tab view to organize the entire UI
        notebook = ctk.CTkTabview(self)
        notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        settings_tab = notebook.add("Settings")
        results_tab = notebook.add("Results")
        self._create_log_and_status_area(notebook) # Adds "Logs & Status" tab

        settings_tab.grid_columnconfigure(0, weight=1)
        settings_tab.grid_rowconfigure(2, weight=1) 
        results_tab.grid_columnconfigure(0, weight=1); results_tab.grid_rowconfigure(0, weight=1)

        # 1. Populate the "Settings" Tab
        controls_frame = ctk.CTkFrame(settings_tab)
        controls_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        controls_frame.grid_columnconfigure(1, weight=1) # Configure for 2 columns
        
        ctk.CTkLabel(controls_frame, text="Panchayat:").grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        self.panchayat_entry = AutocompleteEntry(controls_frame, suggestions_list=self.app.history_manager.get_suggestions("panchayat"))
        self.panchayat_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(controls_frame, text="Demand/Work Date:").grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")
        self.demand_date_entry = DateEntry(controls_frame)
        self.demand_date_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(controls_frame, text="Days:").grid(row=2, column=0, padx=(10, 5), pady=5, sticky="w")
        self.days_entry = ctk.CTkEntry(controls_frame, validate="key", validatecommand=(self.register(lambda P: P.isdigit() or P == ""), '%P'))
        self.days_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.days_entry.insert(0, self.app.history_manager.get_suggestions("demand_days")[0] if self.app.history_manager.get_suggestions("demand_days") else "14")
        
        buttons_frame = ctk.CTkFrame(settings_tab); buttons_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        buttons_frame.grid_columnconfigure(0, weight=1)
        action_buttons = self._create_action_buttons(buttons_frame); action_buttons.pack(expand=True, fill="x")
        
        applicant_frame = ctk.CTkFrame(settings_tab); applicant_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        applicant_frame.grid_columnconfigure(0, weight=1); applicant_frame.grid_rowconfigure(2, weight=1)

        applicant_header = ctk.CTkFrame(applicant_frame, fg_color="transparent"); applicant_header.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        applicant_header.grid_columnconfigure(1, weight=1)
        
        # **IMPROVEMENT**: Frame for left-aligned buttons
        left_buttons_frame = ctk.CTkFrame(applicant_header, fg_color="transparent")
        left_buttons_frame.grid(row=0, column=0, sticky="w")
        
        self.select_csv_button = ctk.CTkButton(left_buttons_frame, text="Load Applicants CSV", command=self._select_csv_file)
        self.select_csv_button.pack(side="left", padx=(0, 10), pady=5)
        
        self.select_all_button = ctk.CTkButton(left_buttons_frame, text="Select All (≤100)", command=self._select_all_applicants)
        # Button is packed/unpacked dynamically in _select_csv_file

        self.clear_selection_button = ctk.CTkButton(left_buttons_frame, text="Clear", command=self._clear_selection, fg_color="gray", hover_color="gray50")
        # This button is also packed/unpacked dynamically

        self.file_label = ctk.CTkLabel(applicant_header, text="No file loaded.", text_color="gray", anchor="w")
        self.file_label.grid(row=0, column=1, pady=5, sticky="ew")
        
        # --- Row 1: Selection Summary ---
        self.selection_summary_label = ctk.CTkLabel(applicant_header, text="0 applicants selected", text_color="gray", anchor="w")
        self.selection_summary_label.grid(row=1, column=0, columnspan=2, pady=(0, 5), sticky="w")
        
        # --- Row 2: Search Entry ---
        self.search_entry = ctk.CTkEntry(applicant_header, placeholder_text="Load a CSV, then type here to search...")
        self.search_entry.grid(row=2, column=0, columnspan=2, pady=5, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._update_applicant_display)
        
        self.applicant_scroll_frame = ctk.CTkScrollableFrame(applicant_frame, label_text="Select Applicants to Process")
        self.applicant_scroll_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0,10))

        cols = ("#", "Job Card No", "Applicant Name", "Status")
        self.results_tree = ttk.Treeview(results_tab, columns=cols, show='headings', style="Custom.Treeview")
        self.results_tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        vsb = ttk.Scrollbar(results_tab, orient="vertical", command=self.results_tree.yview); vsb.grid(row=0, column=1, sticky='ns'); self.results_tree.configure(yscrollcommand=vsb.set)
        self._setup_results_treeview()

    # **IMPROVEMENT**: New "Select All" method
    def _select_all_applicants(self):
        if not self.all_applicants_data or len(self.all_applicants_data) > 100: return
        
        for applicant_data in self.all_applicants_data:
            if "*" not in applicant_data.get('Name of Applicant', ''):
                applicant_data['_selected'] = True

        for checkbox in self.displayed_checkboxes:
            applicant_data = checkbox.applicant_data
            if "*" not in applicant_data.get('Name of Applicant', ''):
                checkbox.select()

        self._update_selection_summary()
        self.app.log_message(self.log_display, f"Selected all {len(self.all_applicants_data)} valid applicants.")

    # **IMPROVEMENT**: Logic to show/hide "Select All" button
    def _select_csv_file(self):
        path = filedialog.askopenfilename(title="Select Applicants CSV File", filetypes=(("CSV Files", "*.csv"),))
        if not path: return
        self.csv_path = path; self.all_applicants_data.clear(); self._update_applicant_display()
        try:
            with open(self.csv_path, mode='r', encoding='utf-8') as infile:
                for row in csv.DictReader(infile):
                    row['_selected'] = False; self.all_applicants_data.append(row)
            
            self.file_label.configure(text=f"{os.path.basename(path)} ({len(self.all_applicants_data)} loaded)", text_color=ctk.ThemeManager.theme.get("CTkLabel")["text_color"])
            self.search_entry.configure(placeholder_text="Type 3+ characters to search...")
            
            # Show/hide buttons based on loaded data
            if len(self.all_applicants_data) > 0:
                if len(self.all_applicants_data) <= 100:
                    self.select_all_button.pack(side="left", padx=(0, 10), pady=5)
                else:
                    self.select_all_button.pack_forget()
                self.clear_selection_button.pack(side="left", pady=5)
            else:
                self.select_all_button.pack_forget()
                self.clear_selection_button.pack_forget()
            
            self._update_selection_summary()
        except Exception as e:
            messagebox.showerror("CSV Error", f"Failed to read CSV.\nError: {e}"); self.file_label.configure(text="Failed to load file.", text_color="red")
            
    def _update_applicant_display(self, event=None):
        for checkbox in self.displayed_checkboxes: checkbox.destroy()
        self.displayed_checkboxes.clear()
        search_term = self.search_entry.get().lower()
        if not self.all_applicants_data or len(search_term) < 3: return
        matching_applicants = [row for row in self.all_applicants_data if search_term in row.get('Job card number','').lower() or search_term in row.get('Name of Applicant','').lower()]
        for row_data in matching_applicants[:50]:
            display_text = f"{row_data['Job card number']}  -  {row_data['Name of Applicant']}"
            var = ctk.StringVar(value="on" if row_data['_selected'] else "off")
            checkbox = ctk.CTkCheckBox(self.applicant_scroll_frame, text=display_text, variable=var, onvalue="on", offvalue="off", command=lambda data=row_data, state=var: self._on_applicant_select(data, state.get()))
            checkbox.applicant_data = row_data
            if "*" in row_data.get('Name of Applicant', ''): checkbox.configure(text_color="red", state="disabled")
            checkbox.pack(anchor="w", padx=10, pady=2, fill="x"); self.displayed_checkboxes.append(checkbox)
            
    def _on_applicant_select(self, applicant_data, new_state):
        applicant_data['_selected'] = (new_state == "on")
        self._update_selection_summary()

    def _update_selection_summary(self):
        selected_rows = [row for row in self.all_applicants_data if row.get('_selected', False)]
        unique_job_cards = len(set(row.get('Job card number') for row in selected_rows))
        self.selection_summary_label.configure(text=f"{len(selected_rows)} applicants across {unique_job_cards} unique job cards selected")
    
    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running); state = "disabled" if running else "normal"
        self.panchayat_entry.configure(state=state)
        self.days_entry.configure(state=state); self.select_csv_button.configure(state=state)
        self.search_entry.configure(state=state); self.demand_date_entry.configure(state=state)
        self.select_all_button.configure(state=state)
        self.clear_selection_button.configure(state=state)
        for cb in self.displayed_checkboxes:
            if "*" not in cb.cget("text"): cb.configure(state=state)

    def start_automation(self):
        selected_applicants = [row for row in self.all_applicants_data if row.get('_selected', False)]
        panchayat = self.panchayat_entry.get().strip()
        days = self.days_entry.get().strip()
        
        try:
            demand_date = self.demand_date_entry.get()
            demand_from = datetime.strptime(demand_date, '%d/%m/%Y').strftime('%d/%m/%Y')
            work_start = demand_from
        except ValueError:
            messagebox.showerror("Invalid Date", "Date must be in DD/MM/YYYY format.")
            return

        if not days: messagebox.showerror("Missing Info", "Days field is required."); return
        if not self.csv_path: messagebox.showerror("Missing Info", "Please load an Applicants CSV file."); return
        if not selected_applicants: messagebox.showwarning("No Selection", "Please select at least one applicant to process."); return
            
        self.stop_event.clear(); self.app.clear_log(self.log_display)
        for i in self.results_tree.get_children(): self.results_tree.delete(i)
        self.app.log_message(self.log_display, f"Starting work demand for {len(selected_applicants)} selected applicant(s)...")
        self.app.set_status("Work demand automation is running..."); self.set_ui_state(running=True)

        self.app.history_manager.save_entry("panchayat", panchayat); self.app.history_manager.save_entry("demand_days", days)
        self.save_inputs({"panchayat": panchayat, "demand_date": self.demand_date_entry.get()})

        grouped_by_village = {}
        for app in selected_applicants:
            job_card = app.get('Job card number', '').strip()
            if not job_card: continue
            try:
                village_code = job_card.split('/')[0].split('-')[-1]
                if village_code not in grouped_by_village:
                    grouped_by_village[village_code] = {}
                if job_card not in grouped_by_village[village_code]:
                    grouped_by_village[village_code][job_card] = []
                grouped_by_village[village_code][job_card].append(app)
            except IndexError:
                self.app.log_message(self.log_display, f"Warning: Malformed Job Card number skipped: {job_card}")
                continue

        self.worker_thread = threading.Thread(target=self._process_demand, args=(panchayat, days, demand_from, work_start, grouped_by_village), daemon=True)
        self.worker_thread.start()

    def reset_ui(self):
        if not messagebox.askokcancel("Reset Form?", "Clear all inputs, selections, and logs?"): return
        self.panchayat_entry.delete(0, 'end'); self.days_entry.delete(0, 'end'); self.search_entry.delete(0, 'end')
        self.demand_date_entry.clear()
        self.csv_path = None; self.all_applicants_data.clear()
        self.file_label.configure(text="No file loaded.", text_color="gray")
        self.select_all_button.pack_forget()
        self.clear_selection_button.pack_forget()
        self._update_applicant_display(); self._update_selection_summary()
        for item in self.results_tree.get_children(): self.results_tree.delete(item)
        self.app.clear_log(self.log_display); self.app.after(0, self.update_status, "Ready", 0.0)
        self.app.log_message(self.log_display, "Form has been reset.")
    
    def _setup_results_treeview(self):
        self.results_tree["columns"] = ("#", "Job Card No", "Applicant Name", "Status")
        self.results_tree.column("#0", width=0, stretch=tkinter.NO); self.results_tree.column("#", anchor=tkinter.CENTER, width=40)
        self.results_tree.column("Job Card No", anchor=tkinter.W, width=180); self.results_tree.column("Applicant Name", anchor=tkinter.W, width=150)
        self.results_tree.column("Status", anchor=tkinter.W, width=250)
        self.results_tree.heading("#0", text="", anchor=tkinter.W); self.results_tree.heading("#", text="#", anchor=tkinter.CENTER)
        self.results_tree.heading("Job Card No", text="Job Card No", anchor=tkinter.W); self.results_tree.heading("Applicant Name", text="Applicant Name", anchor=tkinter.W)
        self.results_tree.heading("Status", text="Status", anchor=tkinter.W)
        self.style_treeview(self.results_tree)

    def _process_demand(self, panchayat, days, demand_from, work_start, grouped_by_village):
        driver = None
        try:
            driver = self.app.get_driver()
            if not driver:
                self.app.after(0, self.app.log_message, self.log_display, "ERROR: WebDriver not available.")
                return

            driver.get(config.DEMAND_CONFIG["url"])
            wait = WebDriverWait(driver, 20)
            
            panchayat_ids = ["ctl00_ContentPlaceHolder1_DDL_panchayat", "ctl00_ContentPlaceHolder1_ddlPanchayat"]
            village_ids = ["ctl00_ContentPlaceHolder1_DDL_Village", "ctl00_ContentPlaceHolder1_ddlvillage"]
            jobcard_ids = ["ctl00_ContentPlaceHolder1_DDL_Registration", "ctl00_ContentPlaceHolder1_ddlJobcard"]

            def find_and_select_by_text(ids, select_text):
                element = next((wait.until(EC.element_to_be_clickable((By.ID, eid))) for eid in ids if driver.find_elements(By.ID, eid)), None)
                if not element: raise TimeoutException(f"Could not find any element with IDs: {ids}")
                Select(element).select_by_visible_text(select_text)

            is_gp_mode = False
            try:
                WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, panchayat_ids[0])))
            except TimeoutException:
                is_gp_mode = True
                self.app.after(0, self.app.log_message, self.log_display, "Panchayat field not found. Assuming GP Login Mode.")

            if not is_gp_mode:
                if not panchayat: raise ValueError("Panchayat name is required for this login level.")
                self.app.after(0, self.app.log_message, self.log_display, f"Navigated. Selecting Panchayat: {panchayat}")
                find_and_select_by_text(panchayat_ids, panchayat)
                self.app.after(0, self.app.log_message, self.log_display, "Waiting for village list to load...")
                wait.until(EC.any_of(EC.presence_of_element_located((By.XPATH, f"//select[@id='{village_ids[0]}']/option[position()>1]")),EC.presence_of_element_located((By.XPATH, f"//select[@id='{village_ids[1]}']/option[position()>1]"))))

            for village_code, job_cards_in_village in grouped_by_village.items():
                if self.stop_event.is_set(): break
                try:
                    self.app.after(0, self.app.log_message, self.log_display, f"--- Processing Village Code: {village_code} ---")
                    village_select_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"#{village_ids[0]}, #{village_ids[1]}")))
                    village_select = Select(village_select_element)
                    
                    target_option_value = None
                    for option in village_select.options:
                        option_value = option.get_attribute('value')
                        if option_value and option_value.endswith(village_code):
                            target_option_value = option_value
                            break
                    
                    if target_option_value:
                        village_select.select_by_value(target_option_value)
                        selected_option_text = village_select.all_selected_options[0].text.strip()
                        self.app.after(0, self.app.log_message, self.log_display, f"Selected Village '{selected_option_text}' using value '{target_option_value}'.")
                    else:
                        raise NoSuchElementException(f"Could not find any village option whose value ends with code: {village_code}")


                    self.app.after(0, self.app.log_message, self.log_display, "Waiting for job cards to load...")
                    wait.until(EC.any_of(EC.presence_of_element_located((By.XPATH, f"//select[@id='{jobcard_ids[0]}']/option[position()>1]")), EC.presence_of_element_located((By.XPATH, f"//select[@id='{jobcard_ids[1]}']/option[position()>1]"))))

                    for job_card, applicants_in_jc in job_cards_in_village.items():
                        if self.stop_event.is_set(): break
                        self._process_single_job_card(driver, wait, job_card, applicants_in_jc, locals())

                except (ValueError, IndexError, TimeoutException, NoSuchElementException) as e:
                    self.app.after(0, self.app.log_message, self.log_display, f"ERROR processing village {village_code}: {e}. Skipping to next village.")
                    continue

            if not self.stop_event.is_set():
                self.app.after(0, self.app.log_message, self.log_display, "✅ All selected applicants processed.")
                self.app.set_status("Automation completed!")

        except Exception as e:
            self.app.after(0, self.app.log_message, self.log_display, f"A critical error occurred: {e}")
            self.app.set_status(f"Critical error occurred.")
        finally:
            if not self.stop_event.is_set(): self.app.after(100, lambda: messagebox.showinfo("Complete", "Work demand automation has finished."))
            self.app.after(0, self.set_ui_state, False)

    # **IMPROVEMENT**: Major overhaul for robust error handling
    def _process_single_job_card(self, driver, wait, job_card, applicants_in_jc, local_vars):
        days, demand_from, work_start = local_vars['days'], local_vars['demand_from'], local_vars['work_start']
        jobcard_ids = ["ctl00_ContentPlaceHolder1_DDL_Registration", "ctl00_ContentPlaceHolder1_ddlJobcard"]
        grid_ids = ["ctl00_ContentPlaceHolder1_gvData", "ctl00_ContentPlaceHolder1_GridView1"]
        button_ids = ["ctl00_ContentPlaceHolder1_btnProceed", "ctl00_ContentPlaceHolder1_btnSave"]
        
        try:
            jc_suffix = job_card.split('/')[-1]
            self.app.after(0, self.app.log_message, self.log_display, f"Processing Job Card Suffix: {jc_suffix}")
            
            jc_dropdown_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"#{jobcard_ids[0]}, #{jobcard_ids[1]}")))
            Select(jc_dropdown_element).select_by_visible_text(next(opt.text for opt in Select(jc_dropdown_element).options if opt.text.strip().startswith(f"{jc_suffix}-")))

            grid_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"#{grid_ids[0]}, #{grid_ids[1]}"))); grid_id_found = grid_element.get_attribute("id"); time.sleep(1.5)

            target_applicant_names_csv = [app.get('Name of Applicant', '').strip() for app in applicants_in_jc]
            processed_applicants_in_loop = []; filled_at_least_one = False
            all_rows_on_page = driver.find_elements(By.CSS_SELECTOR, f"table[id='{grid_id_found}'] > tbody > tr")

            for i, row in enumerate(all_rows_on_page):
                if i == 0: continue
                try:
                    applicant_name_web_span = row.find_element(By.CSS_SELECTOR, "span[id*='_job']")
                    applicant_name_web = applicant_name_web_span.text.strip()
                    normalized_web_name = "".join(applicant_name_web.lower().split())
                    is_target_applicant = any("".join(csv_name.lower().split()) in normalized_web_name for csv_name in target_applicant_names_csv)
                    row_id_prefix = f"{grid_id_found}_ctl{i+1:02d}_"; from_date_id, start_date_id, days_id, till_date_id = "dt_app", "dt_from", "d3", "dt_to"

                    if is_target_applicant:
                        from_date_val, start_date_val, days_val = [row.find_element(By.ID, row_id_prefix + eid).get_attribute('value') for eid in [from_date_id, start_date_id, days_id]]
                        is_fully_correct = (from_date_val == demand_from and start_date_val == work_start and days_val == days)
                        is_partially_filled = (from_date_val == '' and start_date_val == work_start and days_val == days)

                        if is_fully_correct: self.app.after(0, self.app.log_message, self.log_display, f"   -> Data for {applicant_name_web} is already correct.")
                        elif is_partially_filled:
                            self.app.after(0, self.app.log_message, self.log_display, f"   -> Partially filled. Completing data for {applicant_name_web}...")
                            from_date_input = wait.until(EC.element_to_be_clickable((By.ID, row_id_prefix + from_date_id))); from_date_input.send_keys(demand_from); from_date_input.send_keys(Keys.TAB); time.sleep(2)
                        else:
                            self.app.after(0, self.app.log_message, self.log_display, f"   -> Filling all data for {applicant_name_web}...")
                            from_date_input = wait.until(EC.element_to_be_clickable((By.ID, row_id_prefix + from_date_id))); from_date_input.send_keys(demand_from); from_date_input.send_keys(Keys.TAB)
                            start_date_input = wait.until(EC.element_to_be_clickable((By.ID, row_id_prefix + start_date_id))); start_date_input.send_keys(work_start); start_date_input.send_keys(Keys.TAB); time.sleep(2)
                            days_input = wait.until(EC.element_to_be_clickable((By.ID, row_id_prefix + days_id))); days_input.click(); time.sleep(0.5); days_input.clear(); days_input.send_keys(days); days_input.send_keys(Keys.TAB)
                        
                        wait.until(lambda d: d.find_element(By.ID, row_id_prefix + till_date_id).get_attribute("value") != "")
                        self.app.after(0, self.app.log_message, self.log_display, f"   SUCCESS: Filled data for {applicant_name_web}.")
                        filled_at_least_one = True; processed_applicants_in_loop.append(applicant_name_web)
                    else:
                        demand_date_field_to_clear = row.find_element(By.ID, row_id_prefix + from_date_id)
                        if demand_date_field_to_clear.get_attribute('value') != '': demand_date_field_to_clear.clear()
                except Exception as e:
                    self.app.after(0, self.app.log_message, self.log_display, f"   -> Warning: Skipped one row due to an error: {e}"); continue

            unprocessed_applicants = [name for name in target_applicant_names_csv if not any("".join(name.lower().split()) in "".join(p_name.lower().split()) for p_name in processed_applicants_in_loop)]
            for name in unprocessed_applicants:
                self.app.after(0, self.app.log_message, self.log_display, f"   ERROR: Could not find {name} in the grid.")
                self.app.after(0, self._update_results_tree, (job_card, name, "Skipped (Not Found on Page)"))

            if filled_at_least_one:
                self.app.after(0, self.app.log_message, self.log_display, f"Submitting demand for Job Card {jc_suffix}...")
                button_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"#{button_ids[0]}, #{button_ids[1]}")))
                button_element.click()
                
                result_text = ""
                try:
                    alert = WebDriverWait(driver, 5).until(EC.alert_is_present())
                    result_text = alert.text.strip(); self.app.after(0, self.app.log_message, self.log_display, f"   SUCCESS (Alert): {result_text}"); alert.accept()
                except TimeoutException:
                    self.app.after(0, self.app.log_message, self.log_display, "   -> No alert found, checking for on-page message...")
                    try:
                        error_font = driver.find_element(By.XPATH, "//font[@color='red']")
                        result_text = error_font.text.strip()
                        self.app.after(0, self.app.log_message, self.log_display, f"   RESULT (On-Page): {result_text}")
                    except NoSuchElementException:
                        try:
                           msg_label = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_lblmsg")
                           result_text = msg_label.text.strip()
                           self.app.after(0, self.app.log_message, self.log_display, f"   RESULT (On-Page): {result_text}")
                        except NoSuchElementException:
                           result_text = "Unknown result (No message found)"

                is_specific_error = "is already there" in result_text.lower() and "demand of" in result_text.lower()
                error_applicant_name = ""

                if is_specific_error:
                    try:
                        name_part = result_text.split("Demand of ")[1]
                        error_applicant_name = name_part.split("  ")[0].strip()
                        if " for period" in error_applicant_name:
                            error_applicant_name = error_applicant_name.split(" for period")[0].strip()
                        self.app.after(0, self.app.log_message, self.log_display, f"   -> Specific error detected for: {error_applicant_name}")
                    except IndexError:
                        is_specific_error = False
                        self.app.after(0, self.app.log_message, self.log_display, "   -> 'Already there' message found, but name couldn't be parsed.")

                for applicant_data in applicants_in_jc:
                    applicant_name_csv = applicant_data.get('Name of Applicant', 'N/A')
                    if applicant_name_csv in unprocessed_applicants: continue
                    status_to_display = result_text 

                    if is_specific_error and error_applicant_name:
                        normalized_error_name = "".join(error_applicant_name.lower().split())
                        normalized_csv_name = "".join(applicant_name_csv.lower().split())
                        
                        if normalized_error_name in normalized_csv_name:
                            status_to_display = result_text
                        else:
                            status_to_display = "Success (Processed in batch)"
                    
                    self.app.after(0, self._update_results_tree, (job_card, applicant_name_csv, status_to_display))
            
        except StaleElementReferenceException:
            self.app.after(0, self.app.log_message, self.log_display, f"   INFO: Page reloaded for {job_card}, retrying...")
            self._process_single_job_card(driver, wait, job_card, applicants_in_jc, local_vars)
        except Exception as e:
            self.app.after(0, self.app.log_message, self.log_display, f"ERROR processing {job_card}: {e}")
            for app_data in applicants_in_jc:
                self.app.after(0, self._update_results_tree, (app_data.get('Job card number'), app_data.get('Name of Applicant'), f"CRASH: {e}"))


    def _update_results_tree(self, data):
        job_card, name, status = data; row_count = len(self.results_tree.get_children()) + 1
        tags = ('failed',) if 'success' not in status.lower() and 'already correct' not in status.lower() and 'already there' not in status.lower() else ()
        self.results_tree.insert(parent="", index="end", iid=row_count, values=(row_count, job_card, name, status), tags=tags)
        self.results_tree.yview_moveto(1)

    def export_results(self):
        panchayat_name = self.panchayat_entry.get().strip().replace(" ", "_")
        default_filename = f"Demand_Report_{panchayat_name}_{datetime.now().strftime('%Y%m%d')}.csv"
        self.export_treeview_to_csv(self.results_tree, default_filename)

    def save_inputs(self, inputs):
        try:
            with open(self.config_file, 'w') as f: json.dump(inputs, f, indent=4)
        except Exception as e: print(f"Error saving demand inputs: {e}")

    def load_inputs(self):
        if not os.path.exists(self.config_file):
            today = datetime.now().strftime('%d/%m/%Y')
            self.demand_date_entry.set_date(today)
            return
        try:
            with open(self.config_file, 'r') as f: data = json.load(f)
            self.panchayat_entry.insert(0, data.get('panchayat', ''))
            self.demand_date_entry.set_date(data.get('demand_date', ''))
        except Exception as e: print(f"Error loading demand inputs: {e}")

    def _clear_selection(self):
        """Clears all selected applicants."""
        if not any(app.get('_selected', False) for app in self.all_applicants_data):
            self.app.log_message(self.log_display, "No applicants were selected.", "info")
            return

        for applicant_data in self.all_applicants_data:
            applicant_data['_selected'] = False

        for checkbox in self.displayed_checkboxes:
            checkbox.deselect()

        self._update_selection_summary()
        self.app.log_message(self.log_display, "Selection has been cleared.")
