# tabs/demand_tab.py
import tkinter
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import os, csv, time, threading, json, re
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, UnexpectedAlertPresentException
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
        self.displayed_checkboxes = [] # Holds currently visible widgets (checkboxes, labels)
        self.next_jc_separator_shown = False # Flag for sequential display
        self.next_jc_separator = None # Placeholder for separator label

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._create_widgets()
        self.load_inputs()

    def _create_widgets(self):
        # Main tab view
        notebook = ctk.CTkTabview(self)
        notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        settings_tab = notebook.add("Settings")
        results_tab = notebook.add("Results")
        self._create_log_and_status_area(notebook)

        settings_tab.grid_columnconfigure(0, weight=1)
        settings_tab.grid_rowconfigure(2, weight=1)
        results_tab.grid_columnconfigure(0, weight=1); results_tab.grid_rowconfigure(0, weight=1)

        # Settings Tab Widgets
        controls_frame = ctk.CTkFrame(settings_tab)
        controls_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        controls_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(controls_frame, text="State:").grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        self.state_combobox = ctk.CTkComboBox(controls_frame, values=list(config.STATE_DEMAND_CONFIG.keys()))
        self.state_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(controls_frame, text="Panchayat:").grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")
        self.panchayat_entry = AutocompleteEntry(controls_frame, suggestions_list=self.app.history_manager.get_suggestions("panchayat"))
        self.panchayat_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(controls_frame, text="Demand/Work Date:").grid(row=2, column=0, padx=(10, 5), pady=5, sticky="w")
        self.demand_date_entry = DateEntry(controls_frame)
        self.demand_date_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(controls_frame, text="Days:").grid(row=3, column=0, padx=(10, 5), pady=5, sticky="w")
        self.days_entry = ctk.CTkEntry(controls_frame, validate="key", validatecommand=(self.register(lambda P: P.isdigit() or P == ""), '%P'))
        self.days_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.days_entry.insert(0, self.app.history_manager.get_suggestions("demand_days")[0] if self.app.history_manager.get_suggestions("demand_days") else "14")

        buttons_frame = ctk.CTkFrame(settings_tab); buttons_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        buttons_frame.grid_columnconfigure(0, weight=1)
        action_buttons = self._create_action_buttons(buttons_frame); action_buttons.pack(expand=True, fill="x")

        applicant_frame = ctk.CTkFrame(settings_tab); applicant_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        applicant_frame.grid_columnconfigure(0, weight=1); applicant_frame.grid_rowconfigure(3, weight=1)

        applicant_header = ctk.CTkFrame(applicant_frame, fg_color="transparent"); applicant_header.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        applicant_header.grid_columnconfigure(1, weight=1)

        left_buttons_frame = ctk.CTkFrame(applicant_header, fg_color="transparent")
        left_buttons_frame.grid(row=0, column=0, sticky="w")

        self.select_csv_button = ctk.CTkButton(left_buttons_frame, text="Load Applicants CSV", command=self._select_csv_file)
        self.select_csv_button.pack(side="left", padx=(0, 10), pady=5)
        self.demo_csv_button = ctk.CTkButton(left_buttons_frame, text="Download Demo CSV", command=lambda: self.app.save_demo_csv("demand"), fg_color="#2E8B57", hover_color="#257247")
        self.demo_csv_button.pack(side="left", padx=(0, 10), pady=5)

        self.select_all_button = ctk.CTkButton(left_buttons_frame, text="Select All (≤200)", command=self._select_all_applicants)
        self.clear_selection_button = ctk.CTkButton(left_buttons_frame, text="Clear", command=self._clear_selection, fg_color="gray", hover_color="gray50")

        self.file_label = ctk.CTkLabel(applicant_header, text="No file loaded.", text_color="gray", anchor="w")
        self.file_label.grid(row=0, column=1, pady=5, sticky="ew")
        self.selection_summary_label = ctk.CTkLabel(applicant_header, text="0 applicants selected", text_color="gray", anchor="w")
        self.selection_summary_label.grid(row=1, column=0, columnspan=2, pady=(0, 5), sticky="w")
        self.search_entry = ctk.CTkEntry(applicant_header, placeholder_text="Load a CSV, then type here to search...")
        self.search_entry.grid(row=2, column=0, columnspan=2, pady=5, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._update_applicant_display)

        self.applicant_scroll_frame = ctk.CTkScrollableFrame(applicant_frame, label_text="Select Applicants to Process")
        self.applicant_scroll_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0,10))

        # Results Tab Widgets
        cols = ("#", "Job Card No", "Applicant Name", "Status")
        self.results_tree = ttk.Treeview(results_tab, columns=cols, show='headings', style="Custom.Treeview")
        self.results_tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        vsb = ttk.Scrollbar(results_tab, orient="vertical", command=self.results_tree.yview); vsb.grid(row=0, column=1, sticky='ns'); self.results_tree.configure(yscrollcommand=vsb.set)
        self._setup_results_treeview()

    def _select_all_applicants(self):
        if not self.all_applicants_data: return
        # Increased limit check
        if len(self.all_applicants_data) > 200:
             messagebox.showinfo("Limit Exceeded", f"Cannot Select All (>200 applicants loaded: {len(self.all_applicants_data)}).")
             return

        selected_count = 0
        for applicant_data in self.all_applicants_data:
            if "*" not in applicant_data.get('Name of Applicant', ''):
                applicant_data['_selected'] = True; selected_count += 1

        for checkbox in self.displayed_checkboxes:
             # Ensure it's a checkbox before calling select
             if isinstance(checkbox, ctk.CTkCheckBox):
                applicant_data = checkbox.applicant_data
                if "*" not in applicant_data.get('Name of Applicant', ''):
                    checkbox.select()

        self._update_selection_summary()
        self.app.log_message(self.log_display, f"Selected all {selected_count} valid applicants.")

    def _clear_processed_selection(self):
        self.app.log_message(self.log_display, "Clearing processed selection...", "info")
        for app_data in self.all_applicants_data: app_data['_selected'] = False
        for widget in self.displayed_checkboxes:
            if isinstance(widget, ctk.CTkCheckBox) and widget.get() == "on":
                widget.deselect()
        self._update_selection_summary()

    def _select_csv_file(self):
        path = filedialog.askopenfilename(title="Select Demand CSV", filetypes=[("CSV", "*.csv")])
        if not path: return
        self.csv_path = path
        self.file_label.configure(text=os.path.basename(path))
        self.all_applicants_data = []

        try:
            with open(path, mode='r', encoding='utf-8-sig') as csvfile:
                reader = csv.reader(csvfile)
                try: header = next(reader)
                except StopIteration: raise ValueError("CSV empty.")
                norm_headers = [h.lower().replace(" ", "").replace("_", "") for h in header]
                try: name_idx, jc_idx = norm_headers.index("nameofapplicant"), norm_headers.index("jobcardnumber")
                except ValueError: raise ValueError("CSV Headers missing 'Name of Applicant' or 'Job card number'.")

                for row_num, row in enumerate(reader, 1):
                     if not row or len(row) <= max(name_idx, jc_idx): continue
                     name, job_card = row[name_idx].strip(), row[jc_idx].strip()
                     if name and job_card:
                        self.all_applicants_data.append({'original_index': row_num, 'Name of Applicant': name, 'Job card number': job_card, '_selected': False})

            loaded_count = len(self.all_applicants_data)
            self.app.log_message(self.log_display, f"Loaded {loaded_count} applicants.")
            self._update_applicant_display()

            if 0 < loaded_count <= 200: self.select_all_button.pack(side="left", padx=(0, 10), pady=5)
            else: self.select_all_button.pack_forget();
            if loaded_count > 200: self.app.log_message(self.log_display, "Select All hidden (>200).", "info")
            self.clear_selection_button.pack(side="left", pady=5) # Always show Clear

        except Exception as e:
            messagebox.showerror("Error Reading CSV", f"Could not read CSV.\nError: {e}"); self.csv_path = None; self.all_applicants_data = []
            self.file_label.configure(text="No file"); self.select_all_button.pack_forget(); self.clear_selection_button.pack_forget()
            self._update_applicant_display(); self._update_selection_summary()

    def _update_applicant_display(self, event=None):
        # Clear existing widgets
        for widget in self.displayed_checkboxes: widget.destroy()
        if self.next_jc_separator: self.next_jc_separator.destroy(); self.next_jc_separator = None
        self.displayed_checkboxes.clear(); self.next_jc_separator_shown = False

        search = self.search_entry.get().lower().strip()
        if not self.all_applicants_data: return
        if not search and len(self.all_applicants_data) > 50: return # Avoid showing all if > 50 and no search
        if search and len(search) < 3: return # Min search length

        matches = [row for row in self.all_applicants_data if
                   (search in row.get('Job card number','').lower() or
                    search in row.get('Name of Applicant','').lower())] if search else self.all_applicants_data[:50]

        limit = 50
        for row in matches[:limit]: self._create_applicant_checkbox(row)
        if len(matches) > limit:
             label = ctk.CTkLabel(self.applicant_scroll_frame, text=f"... (first {limit} matches)", text_color="gray")
             label.pack(anchor="w", padx=10, pady=2); self.displayed_checkboxes.append(label)

    def _create_applicant_checkbox(self, row_data, is_next_jc=False):
        text = f"{row_data['Job card number']}  -  {row_data['Name of Applicant']}"
        var = ctk.StringVar(value="on" if row_data['_selected'] else "off")
        cmd = lambda data=row_data, state=var: self._on_applicant_select(data, state.get())
        cb = ctk.CTkCheckBox(self.applicant_scroll_frame, text=text, variable=var, onvalue="on", offvalue="off", command=cmd)
        cb.applicant_data = row_data

        if "*" in row_data.get('Name of Applicant', ''): cb.configure(text_color="gray50", state="disabled")
        elif is_next_jc: cb.configure(text_color="#a0a0ff")

        cb.pack(anchor="w", padx=10, pady=2, fill="x"); self.displayed_checkboxes.append(cb)

    def _on_applicant_select(self, applicant_data, new_state):
        applicant_data['_selected'] = (new_state == "on")
        self._update_selection_summary()
        if new_state == "on": self._add_next_jobcards_to_display(applicant_data)

    def _add_next_jobcards_to_display(self, selected_applicant_data):
        try:
            sel_idx = next((i for i, d in enumerate(self.all_applicants_data) if d['original_index'] == selected_applicant_data['original_index']), -1)
            if sel_idx == -1: return

            sel_jc = selected_applicant_data['Job card number']; next_jcs = set(); apps_to_add = []
            max_next = 5 # Show applicants from the next 5 unique job cards

            for i in range(sel_idx + 1, len(self.all_applicants_data)):
                curr_app = self.all_applicants_data[i]; curr_jc = curr_app['Job card number']
                if curr_jc == sel_jc: continue
                if curr_jc not in next_jcs:
                    if len(next_jcs) >= max_next: break
                    next_jcs.add(curr_jc)
                if curr_jc in next_jcs: apps_to_add.append(curr_app)

            if not apps_to_add: return

            if not self.next_jc_separator_shown:
                self.next_jc_separator = ctk.CTkLabel(self.applicant_scroll_frame, text=f"--- Applicants from Next {max_next} Job Card(s) ---", text_color="gray") # Updated text
                self.next_jc_separator.pack(anchor="w", padx=10, pady=(10, 2)); self.displayed_checkboxes.append(self.next_jc_separator); self.next_jc_separator_shown = True

            displayed_indices = {cb.applicant_data['original_index'] for cb in self.displayed_checkboxes if hasattr(cb, 'applicant_data')}
            for app_data in apps_to_add:
                if app_data['original_index'] not in displayed_indices: self._create_applicant_checkbox(app_data, is_next_jc=True)

        except Exception as e: self.app.log_message(self.log_display, f"Error adding next JCs: {e}", "warning")

    def _update_selection_summary(self):
        selected = [r for r in self.all_applicants_data if r.get('_selected', False)]
        unique_jcs = len(set(r.get('Job card number') for r in selected))
        self.selection_summary_label.configure(text=f"{len(selected)} applicants / {unique_jcs} unique job cards")

    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running); state = "disabled" if running else "normal"
        self.state_combobox.configure(state=state); self.panchayat_entry.configure(state=state)
        self.days_entry.configure(state=state); self.select_csv_button.configure(state=state)
        self.search_entry.configure(state=state); self.demand_date_entry.configure(state=state)
        self.select_all_button.configure(state=state); self.clear_selection_button.configure(state=state)
        for widget in self.displayed_checkboxes:
             if isinstance(widget, ctk.CTkCheckBox) and "*" not in widget.cget("text"):
                 widget.configure(state=state)

    def _get_village_code(self, job_card, state_logic_key):
        try:
            jc = job_card.split('/')[0]
            if state_logic_key == "jh": return jc.split('-')[-1]
            elif state_logic_key == "rj": return jc[-3:]
            else: self.app.log_message(self.log_display, f"Warn: Unknown state logic '{state_logic_key}'."); return jc.split('-')[-1]
        except IndexError: return None

    def start_automation(self):
        state = self.state_combobox.get()
        if not state: messagebox.showerror("Input Error", "Select state."); return
        try: cfg = config.STATE_DEMAND_CONFIG[state]; logic_key = cfg["village_code_logic"]; url = cfg["base_url"]
        except KeyError: messagebox.showerror("Config Error", f"Demand config missing for: {state}"); return

        selected = [r for r in self.all_applicants_data if r.get('_selected', False)]
        panchayat = self.panchayat_entry.get().strip(); days_str = self.days_entry.get().strip()
        try: 
            demand_dt_str = self.demand_date_entry.get()
            demand_dt = datetime.strptime(demand_dt_str, '%d/%m/%Y').date() # Get as date object
            work_start = demand_dt.strftime('%d/%m/%Y') # String for selenium
        except ValueError: messagebox.showerror("Invalid Date", "Use DD/MM/YYYY."); return

        # --- ENHANCEMENT: Date Check ---
        if demand_dt < datetime.now().date():
            messagebox.showerror("Invalid Date", "Demand/Work Date cannot be in the past. Please select today or a future date.")
            return
        # --- End Enhancement ---

        if not days_str: messagebox.showerror("Missing Info", "Days required."); return
        if not self.csv_path: messagebox.showerror("Missing Info", "Load CSV."); return
        if not selected: messagebox.showwarning("No Selection", "Select applicants."); return
        try: days_int = int(days_str); assert days_int > 0
        except (ValueError, AssertionError): messagebox.showerror("Invalid Input", "Days must be positive number."); return

        self.stop_event.clear(); self.app.clear_log(self.log_display)
        for i in self.results_tree.get_children(): self.results_tree.delete(i)
        self.app.log_message(self.log_display, f"Starting demand: {len(selected)} applicant(s), State: {state}...")
        self.app.set_status("Running..."); self.set_ui_state(running=True)

        self.app.history_manager.save_entry("panchayat", panchayat); self.app.history_manager.save_entry("demand_days", days_str)
        self.save_inputs({"state": state, "panchayat": panchayat, "demand_date": demand_dt_str})

        grouped = {}; skipped_malformed = 0
        for app in selected:
            jc = app.get('Job card number', '').strip()
            if not jc: continue
            vc = self._get_village_code(jc, logic_key)
            if not vc: skipped_malformed += 1; continue
            if vc not in grouped: grouped[vc] = {}
            if jc not in grouped[vc]: grouped[vc][jc] = []
            grouped[vc][jc].append(app)
        if skipped_malformed: self.app.log_message(self.log_display, f"Warn: Skipped {skipped_malformed} malformed Job Cards.", "warning")

        self.worker_thread = threading.Thread(target=self._process_demand, args=(state, panchayat, days_int, work_start, work_start, grouped, url), daemon=True)
        self.worker_thread.start()

    def reset_ui(self):
        if not messagebox.askokcancel("Reset?", "Clear inputs, selections, logs?"): return
        self.state_combobox.set(""); self.panchayat_entry.delete(0, 'end'); self.days_entry.delete(0, 'end'); self.search_entry.delete(0, 'end')
        self.demand_date_entry.clear(); self.csv_path = None; self.all_applicants_data.clear()
        self.file_label.configure(text="No file loaded.", text_color="gray")
        self.select_all_button.pack_forget(); self.clear_selection_button.pack_forget()
        self._update_applicant_display(); self._update_selection_summary()
        for i in self.results_tree.get_children(): self.results_tree.delete(i)
        self.app.clear_log(self.log_display); self.app.after(0, self.update_status, "Ready", 0.0); self.app.log_message(self.log_display, "Form reset.")

    def _setup_results_treeview(self):
        cols = ("#", "Job Card No", "Applicant Name", "Status")
        self.results_tree["columns"] = cols
        self.results_tree.column("#0", width=0, stretch=tkinter.NO); self.results_tree.column("#", anchor='c', width=40)
        self.results_tree.column("Job Card No", anchor='w', width=180); self.results_tree.column("Applicant Name", anchor='w', width=150)
        self.results_tree.column("Status", anchor='w', width=250)
        self.results_tree.heading("#0", text=""); self.results_tree.heading("#", text="#")
        self.results_tree.heading("Job Card No", text="Job Card No"); self.results_tree.heading("Applicant Name", text="Applicant Name")
        self.results_tree.heading("Status", text="Status")
        self.style_treeview(self.results_tree) # Apply custom styling

    def _process_demand(self, state, panchayat, user_days, demand_from, work_start, grouped, base_url):
        driver = None
        try:
            driver = self.app.get_driver();
            if not driver: self.app.after(0, self.app.log_message, self.log_display, "ERROR: WebDriver unavailable."); return
            driver.get(base_url)
            wait, short_wait = WebDriverWait(driver, 20), WebDriverWait(driver, 5)

            # Define IDs
            p_ids = ["ctl00_ContentPlaceHolder1_DDL_panchayat", "ctl00_ContentPlaceHolder1_ddlPanchayat"]
            v_ids = ["ctl00_ContentPlaceHolder1_DDL_Village", "ctl00_ContentPlaceHolder1_ddlvillage"]
            j_ids = ["ctl00_ContentPlaceHolder1_DDL_Registration", "ctl00_ContentPlaceHolder1_ddlJobcard"]
            days_worked_ids = ["ctl00_ContentPlaceHolder1_Lbldays"]
            grid_ids = ["ctl00_ContentPlaceHolder1_gvData", "ctl00_ContentPlaceHolder1_GridView1"]
            btn_ids = ["ctl00_ContentPlaceHolder1_btnProceed", "ctl00_ContentPlaceHolder1_btnSave"]
            err_msg_ids = ["ctl00_ContentPlaceHolder1_Lblmsgerr"]

            # --- REMOVED find_select function definition ---

            is_gp = False
            
            # --- MODIFICATION: Using mb_entry_tab.py logic for GP check ---
            try:
                # 1. Try to find any panchayat dropdown with a 3-second timeout
                panchayat_selector = ", ".join([f"#{pid}" for pid in p_ids])
                panchayat_dropdown = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, panchayat_selector)))
                
                # 2. If found, check for panchayat name and try to select
                if not panchayat:
                    self.app.after(0, self.app.log_message, self.log_display, "ERROR: Panchayat name required for this login level.", "error")
                    for vc, jcs_in_v in grouped.items():
                        for jc_err, apps_err in jcs_in_v.items():
                            for app_data_err in apps_err: self.app.after(0, self._update_results_tree, (jc_err, app_data_err.get('Name of Applicant'), "FAIL: Panchayat Name Required"))
                    return # Stop
                
                self.app.after(0, self.app.log_message, self.log_display, f"Selecting Panchayat: {panchayat}")
                page_body = driver.find_element(By.TAG_NAME, 'body') # For staleness check
                Select(panchayat_dropdown).select_by_visible_text(panchayat)
                
                # 3. Wait for page to reload after selection (using staleness)
                self.app.after(0, self.app.log_message, self.log_display, "Waiting for villages...")
                wait.until(EC.staleness_of(page_body))
                wait.until(EC.any_of(EC.presence_of_element_located((By.XPATH, f"//select[@id='{v_ids[0]}']/option[position()>1]")), EC.presence_of_element_located((By.XPATH, f"//select[@id='{v_ids[1]}']/option[position()>1]"))))

            except (TimeoutException, NoSuchElementException) as e:
                # This block catches:
                # 1. Dropdown not found (TimeoutException in 3s)
                # 2. Panchayat name not in list (NoSuchElementException from Select)
                self.app.after(0, self.app.log_message, self.log_display, f"GP Login Mode assumed (Panchayat not found or not selectable: {type(e).__name__}).", "info")
                is_gp = True
            # --- END MODIFICATION ---

            if is_gp: # GP Mode
                 self.app.after(0, self.app.log_message, self.log_display, "Waiting for villages (GP Mode)...")
                 wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"#{v_ids[0]}, #{v_ids[1]}")))
                 wait.until(EC.any_of(EC.presence_of_element_located((By.XPATH, f"//select[@id='{v_ids[0]}']/option[position()>1]")), EC.presence_of_element_located((By.XPATH, f"//select[@id='{v_ids[1]}']/option[position()>1]"))))

            # Village and Job Card processing loop
            total_v, proc_v = len(grouped), 0
            for vc, jcs_in_v in grouped.items():
                proc_v += 1
                if self.stop_event.is_set(): break
                try:
                    self.app.after(0, self.app.log_message, self.log_display, f"--- Village {proc_v}/{total_v} (Code: {vc}) ---")
                    v_el = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"#{v_ids[0]}, #{v_ids[1]}"))); v_sel = Select(v_el); found_v = False
                    for opt in v_sel.options:
                        if opt.get_attribute('value').endswith(vc): v_sel.select_by_value(opt.get_attribute('value')); self.app.after(0, self.app.log_message, self.log_display, f"Selected Village '{opt.text}' (...{vc})."); found_v = True; break
                    if not found_v: raise NoSuchElementException(f"Village code {vc} not found.")

                    self.app.after(0, self.app.log_message, self.log_display, "Waiting for job cards..."); time.sleep(0.5)
                    wait.until(EC.any_of(EC.presence_of_element_located((By.XPATH, f"//select[@id='{j_ids[0]}']/option[position()>1]")), EC.presence_of_element_located((By.XPATH, f"//select[@id='{j_ids[1]}']/option[position()>1]"))))

                    total_jc, proc_jc = len(jcs_in_v), 0
                    for jc, apps in jcs_in_v.items():
                        proc_jc += 1
                        if self.stop_event.is_set(): break
                        self.app.after(0, self.update_status, f"V {proc_v}/{total_v}, JC {proc_jc}/{total_jc}", (proc_v-1 + proc_jc/total_jc)/total_v)
                        # --- MODIFICATION: Pass err_msg_ids ---
                        self._process_single_job_card(driver, wait, short_wait, jc, apps, user_days, demand_from, work_start, days_worked_ids, j_ids, grid_ids, btn_ids, err_msg_ids, base_url, state)

                except Exception as e: # Catch errors during village processing
                    self.app.after(0, self.app.log_message, self.log_display, f"ERROR Village {vc}: {type(e).__name__} - {e}. Skipping.", "error")
                    for jc_err, apps_err in jcs_in_v.items():
                         for app_data_err in apps_err: self.app.after(0, self._update_results_tree, (jc_err, app_data_err.get('Name of Applicant'), f"Skipped (Village Error)"))
                    continue # Next village

            if not self.stop_event.is_set():
                self.app.after(0, self.app.log_message, self.log_display, "✅ All processed.")
                self.app.after(0, self.app.set_status, "Automation completed!") # Set completion status

        except Exception as e:
            self.app.after(0, self.app.log_message, self.log_display, f"CRITICAL ERROR: {type(e).__name__} - {e}", "error")
            self.app.after(0, self.app.set_status, f"Error: {type(e).__name__}") # Set error status
            self.app.after(0, lambda: messagebox.showerror("Error", f"Automation stopped: {e}"))
        finally:
            # Show completion message only on normal finish without critical error
            if not self.stop_event.is_set() and 'e' not in locals():
                self.app.after(100, lambda: messagebox.showinfo("Complete", "Demand automation finished."))
                self.app.after(0, self._clear_processed_selection)
            elif self.stop_event.is_set():
                 self.app.after(0, self.app.log_message, self.log_display, "Stopped by user.", "warning")
                 self.app.after(0, self.app.set_status, "Automation stopped") # Set stopped status

            # These run regardless
            self.app.after(0, self.set_ui_state, False)
            self.app.after(0, self.update_status, "Finished" if not self.stop_event.is_set() else "Stopped", 1.0)
            # --- FIX: Removed the line below to allow main_app's 5-second delay to work ---
            # self.app.after(0, self.app.set_status, "Ready")

    # --- Updated _process_single_job_card Function ---
    def _process_single_job_card(self, driver, wait, short_wait, jc, apps_in_jc,
                                 user_days, demand_from, work_start,
                                 days_worked_ids, jc_ids, grid_ids, btn_ids,
                                 err_msg_ids, # <-- MODIFICATION: Receive err_msg_ids
                                 base_url, state): # Receive base_url and state

        # Helper: Read Worked Days (single attempt)
        def get_worked_days_robustly():
            time.sleep(0.3)
            try:
                days_el = short_wait.until(EC.visibility_of_element_located((By.ID, days_worked_ids[0])))
                worked_str = days_el.text.strip(); worked = int(worked_str) if worked_str and worked_str.isdigit() else 0
                self.app.after(0, self.app.log_message, self.log_display, f"   -> Read Worked Days: {worked}")
                return worked
            except Exception as e:
                self.app.after(0, self.app.log_message, self.log_display, f"   Warn: Failed reading worked days ({type(e).__name__}). Assuming 0.", "warning")
                return -1 # Failure

        # --- Helper: Fill Demand Data ---
        def fill_demand_data(days_to_fill):
            nonlocal filled, processed
            applicants_not_found = set(targets)
            fill_success = False
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"table[id='{grid_id}'] > tbody > tr")))
                rows = driver.find_elements(By.CSS_SELECTOR, f"table[id='{grid_id}'] > tbody > tr")
            except Exception: self.app.after(0, self.app.log_message, self.log_display, f"   ERROR: Grid not found.", "error"); return False

            for target in targets:
                if self.stop_event.is_set(): return False
                found = False
                rows = driver.find_elements(By.CSS_SELECTOR, f"table[id='{grid_id}'] > tbody > tr") # Re-find for robustness

                for i, r in enumerate(rows):
                    if i == 0: continue
                    try:
                        name_span = short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"#{grid_id}_ctl{i+1:02d}_job")))
                        name_web = name_span.text.strip()
                        if "".join(target.lower().split()) in "".join(name_web.lower().split()):
                            applicants_not_found.discard(target)
                            pfx = f"{grid_id}_ctl{i+1:02d}_"; ids = {k: pfx+v for k,v in {'from':'dt_app','start':'dt_from','days':'d3','till':'dt_to'}.items()}
                            from_in = wait.until(EC.element_to_be_clickable((By.ID, ids['from'])))
                            start_in = wait.until(EC.element_to_be_clickable((By.ID, ids['start'])))

                            days_in_val = ""
                            try: # try block starts on a new line
                                days_in_chk = driver.find_element(By.ID, ids['days'])
                                days_in_val = days_in_chk.get_attribute('value')
                            except NoSuchElementException: pass

                            needs_upd = (from_in.get_attribute('value') != demand_from or start_in.get_attribute('value') != work_start or days_in_val != str(days_to_fill))

                            if not needs_upd: self.app.after(0, self.app.log_message, self.log_display, f"   -> Correct: '{name_web}' ({days_to_fill}d).")
                            else:
                                self.app.after(0, self.app.log_message, self.log_display, f"   -> Updating: '{name_web}' ({days_to_fill}d)...")
                                if from_in.get_attribute('value') != demand_from: from_in.clear(); from_in.send_keys(demand_from + Keys.TAB); time.sleep(0.1)
                                start_in = wait.until(EC.element_to_be_clickable((By.ID, ids['start']))) # Re-find start
                                if start_in.get_attribute('value') != work_start: start_in.clear(); start_in.send_keys(work_start + Keys.TAB); time.sleep(1.0) # Pause
                                else: start_in.send_keys(Keys.TAB); time.sleep(1.0) # Tab + Pause

                                days_in = wait.until(EC.element_to_be_clickable((By.ID, ids['days']))) # Re-find days
                                days_after = days_in.get_attribute('value')
                                if days_after != str(days_to_fill):
                                    days_in.click(); time.sleep(0.1); cvl = len(days_after or ""); [(days_in.send_keys(Keys.BACKSPACE), time.sleep(0.05)) for _ in range(cvl + 2)] # List Comp OK
                                    days_in.send_keys(str(days_to_fill) + Keys.TAB)
                                    wait.until(lambda d: d.find_element(By.ID, ids['till']).get_attribute("value") != "")
                                self.app.after(0, self.app.log_message, self.log_display, f"   SUCCESS (Fill): '{name_web}'.")

                            filled = True; processed.add(target); found = True; fill_success = True; break
                    except UnexpectedAlertPresentException as alert_e:
                        alert_txt = "Unknown"
                        try: # try block starts on a new line
                            al = driver.switch_to.alert
                            alert_txt=al.text
                            al.accept()
                            self.app.after(0, self.app.log_message, self.log_display, f"   WARN: Alert during fill '{target}': '{alert_txt}'.", "warning")
                            found = False # Mark to retry finding row/target
                            break # Break inner loop
                        except Exception as iae:
                            # Handle failure to switch/accept alert
                            self.app.after(0, self.app.log_message, self.log_display, f"   ERROR handling alert: {iae}", "error")
                            processed.add(target) # Mark as processed (failed)
                            self.app.after(0, self._update_results_tree, (jc, target, f"FAIL: Alert ({alert_txt})"))
                            found = True # Mark as 'handled' by failing
                            break # Break inner loop
                    except StaleElementReferenceException: self.app.after(0, self.app.log_message, self.log_display, f"   Warn: Stale fill '{target}', retry find...", "warning"); found = False; break
                    except Exception as e_fill: self.app.after(0, self.app.log_message, self.log_display, f"   Warn: Error fill '{target}': {type(e_fill).__name__}"); continue

                if not found and (StaleElementReferenceException or UnexpectedAlertPresentException): self.app.after(0, self.app.log_message, self.log_display, f"   -> Retrying search '{target}'..."); time.sleep(0.5); continue

            for nf in applicants_not_found: self.app.after(0, self.app.log_message, self.log_display, f"   ERROR: Not found: '{nf}'.", "error"); self.app.after(0, self._update_results_tree, (jc, nf, "Failed (Not found)"))
            return fill_success
        # --- End fill helper ---

        # ======================== Main Logic ========================
        try:
            # Select JC (with skip logic)
            jc_suffix = jc.split('/')[-1]; self.app.after(0, self.app.log_message, self.log_display, f"Processing JC Suffix: {jc_suffix}")
            try:
                jc_el = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"#{jc_ids[0]}, #{jc_ids[1]}"))); jc_val = jc.split('/')[0]
                try: Select(jc_el).select_by_value(jc_val); self.app.after(0, self.app.log_message, self.log_display, f"   -> Selected by value: '{jc_val}'")
                except NoSuchElementException:
                    self.app.after(0, self.app.log_message, self.log_display, f"   -> Value fail, trying text: {jc_suffix}")
                    prefixes = list(dict.fromkeys([f"{s}-" for s in [jc_suffix, jc_suffix.zfill(2), jc_suffix.zfill(3)]])); xpath = f".//option[" + " or ".join([f"starts-with(normalize-space(.), '{p}')" for p in prefixes]) + "]"
                    try: opt = jc_el.find_element(By.XPATH, xpath); Select(jc_el).select_by_visible_text(opt.text); self.app.after(0, self.app.log_message, self.log_display, f"   -> Selected by text: '{opt.text}'")
                    except NoSuchElementException: raise NoSuchElementException(f"Couldn't find JC '{jc_val}' or '{jc_suffix}'.")
            except NoSuchElementException as e_jc_select:
                self.app.after(0, self.app.log_message, self.log_display, f"   ERROR: Job Card '{jc}' not found. Skipping.", "error"); [self.app.after(0, self._update_results_tree, (jc, a.get('Name of Applicant'), "FAIL: JC Not Found")) for a in apps_in_jc]; return

            # Adjust Days
            worked = get_worked_days_robustly(); adj_days = user_days; avail = 100 - worked
            if worked != -1 and avail <= 0: self.app.after(0, self.app.log_message, self.log_display, f"   SKIPPED: >= 100 days ({worked}).", "warning"); [self.app.after(0, self._update_results_tree, (jc, a.get('Name of Applicant'), "Skipped (100 days)")) for a in apps_in_jc]; return
            if worked != -1 and user_days > avail: adj_days = avail; self.app.after(0, self.app.log_message, self.log_display, f"   ADJUSTED: Demand -> {adj_days} days (Limit: {avail}).", "info")
            else: limit_str = f"Limit: {avail}" if worked != -1 else "Limit: Unknown"; self.app.after(0, self.app.log_message, self.log_display, f"   -> Demanding {adj_days} days ({limit_str}).")

            # Check Grid
            grid_id = "";
            try: 
                grid_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"#{grid_ids[0]}, #{grid_ids[1]}"))); 
                grid_id = grid_el.get_attribute("id"); 
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"table[id='{grid_id}'] > tbody > tr"))); 
                time.sleep(0.5)
            except TimeoutException:
                # --- MODIFICATION: Improved Error Checking ---
                msg = "Skipped (Table fail)"; err_found = False
                try:
                    # Try finding the specific error span first (e.g., ctl00_ContentPlaceHolder1_Lblmsgerr)
                    err_el = short_wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, f"#{err_msg_ids[0]}")))
                    err = err_el.text.strip()
                    if "not yet issued" in err.lower():
                        msg = "Skipped (JC Not Issued)"
                    else:
                        msg = f"Skipped ({err[:50]}...)" # Get first 50 chars of error
                    self.app.after(0, self.app.log_message, self.log_display, f"   ERROR: {err}", "error")
                    err_found = True
                except (NoSuchElementException, TimeoutException):
                    # Fallback to the old method if the span isn't found
                    try: 
                        err = driver.find_element(By.XPATH, "//font[contains(text(), 'not yet issued')]").text.strip()
                        msg = "Skipped (JC Not Issued)"
                        self.app.after(0, self.app.log_message, self.log_display, f"   ERROR: {err}", "error")
                        err_found = True
                    except NoSuchElementException:
                        pass # msg remains "Skipped (Table fail)"

                if not err_found:
                    self.app.after(0, self.app.log_message, self.log_display, "   ERROR: Table fail (Grid not found and no error message detected).", "error")
                
                [self.app.after(0, self._update_results_tree, (jc, a.get('Name of Applicant'), msg)) for a in apps_in_jc]; 
                return
                # --- END MODIFICATION ---

            # Process Applicants
            targets = [a.get('Name of Applicant', '').strip() for a in apps_in_jc]; processed = set(); filled = False;
            # Clear non-targets
            rows = driver.find_elements(By.CSS_SELECTOR, f"table[id='{grid_id}'] > tbody > tr")
            for i, r in enumerate(rows):
                if i == 0: continue
                try:
                    name_span = short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"#{grid_id}_ctl{i+1:02d}_job")))
                    name_web = name_span.text.strip(); is_target = any("".join(tn.lower().split()) in "".join(name_web.lower().split()) for tn in targets)
                    if not is_target: date_fld = short_wait.until(EC.presence_of_element_located((By.ID, f"{grid_id}_ctl{i+1:02d}_dt_app")));
                    if date_fld.get_attribute('value'): date_fld.clear()
                except Exception: pass
            filled = fill_demand_data(adj_days) # Initial fill

            # --- Submit ---
            if filled:
                self.app.after(0, self.app.log_message, self.log_display, f"Submitting (Attempt 1) JC {jc_suffix} with {adj_days} days...")
                btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"#{btn_ids[0]}, #{btn_ids[1]}"))); body = driver.find_element(By.TAG_NAME, 'body'); btn.click()
                res = ""; alert_ok = False; is_100_day_error = False; actual_worked_from_error = -1; remaining_days_calc = -1; is_aadhaar_error = False; reason = "" # Added reason

                try: # Check Alert
                    alert = short_wait.until(EC.alert_is_present()); res = alert.text.strip(); self.app.after(0, self.app.log_message, self.log_display, f"   RESULT (Alert): {res}"); alert.accept(); alert_ok = True
                    try: wait.until(EC.staleness_of(body)); time.sleep(0.5)
                    except TimeoutException: time.sleep(1.5)
                except TimeoutException: # No Alert
                    self.app.after(0, self.app.log_message, self.log_display, "   -> No alert...")
                    # --- Error Message Checking ---
                    try:
                        # Find all potential error/status messages (red font or specific span)
                        potential_messages = short_wait.until(EC.visibility_of_all_elements_located((By.XPATH, "//font[@color='red'] | //span[contains(@id, '_lblmsg')] | //span[contains(text(), 'Kindly Authenticate Aadhaar')]")))
                        full_error_text = " ".join([el.text.strip() for el in potential_messages if el.text.strip()]) # Combine non-empty text
                        res = full_error_text if full_error_text else "Unknown (No message)" # Default if empty

                        # Check for specific errors within the combined text
                        if "Kindly Authenticate Aadhaar first" in res:
                            self.app.after(0, self.app.log_message, self.log_display, f"   RESULT (Aadhaar Error): {res}", "error")
                            is_aadhaar_error = True
                        elif "Record NOT Saved" in res and "exceeding 100 days limit" in res:
                            self.app.after(0, self.app.log_message, self.log_display, f"   RESULT (100-Day Error): {res}", "error")
                            is_100_day_error = True
                            match = re.search(r'\(Demand-Absent\)\s*=\s*(\d+)', res, re.IGNORECASE) or re.search(r'Muster-roll\s*=\s*(\d+)', res, re.IGNORECASE)
                            if match: actual_worked_from_error = int(match.group(1)); self.app.after(0, self.app.log_message, self.log_display, f"      -> Parsed Actual Worked = {actual_worked_from_error}")
                            else: actual_worked_from_error = -1; self.app.after(0, self.app.log_message, self.log_display, f"      -> Could not parse worked days.", "warning")
                        else: # Generic error or info message found
                            level = "error" if any(e in res.lower() for e in ['error','not saved']) else "info"
                            self.app.after(0, self.app.log_message, self.log_display, f"   RESULT: {res}", level)

                    except TimeoutException: # No relevant message elements found
                        res = "Unknown (No message)"; self.app.after(0, self.app.log_message, self.log_display, f"   RESULT: {res}", "warning")
                    time.sleep(1.0)
                except Exception as alert_e: self.app.after(0, self.app.log_message, self.log_display, f"   Alert Error: {alert_e}")

                # --- Retry Logic (Only for 100-Day Error) ---
                if is_100_day_error:
                    remaining_days_calc = 100 - actual_worked_from_error if actual_worked_from_error != -1 else -1
                    if remaining_days_calc > 0:
                        self.app.after(0, self.app.log_message, self.log_display, f"   RETRYING: 100d error. Actual: {actual_worked_from_error}. Retrying with {remaining_days_calc} days.", "info")
                        processed = set() # Reset processed for retry
                        filled_retry = fill_demand_data(remaining_days_calc)
                        if filled_retry:
                            self.app.after(0, self.app.log_message, self.log_display, f"Submitting (Retry) JC {jc_suffix} with {remaining_days_calc} days...")
                            btn_retry = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"#{btn_ids[0]}, #{btn_ids[1]}"))); body_retry = driver.find_element(By.TAG_NAME, 'body'); btn_retry.click()
                            alert_ok = False # Reset for retry result
                            try:
                                alert_retry = short_wait.until(EC.alert_is_present()); res = alert_retry.text.strip(); self.app.after(0, self.app.log_message, self.log_display, f"   RESULT (Retry Alert): {res}"); alert_retry.accept(); alert_ok = True
                                try: wait.until(EC.staleness_of(body_retry)); time.sleep(0.5)
                                except TimeoutException: time.sleep(1.5)
                            except TimeoutException:
                                self.app.after(0, self.app.log_message, self.log_display, "   -> No alert on retry.", "warning")
                                xpaths_retry = ["//font[contains(text(), 'Record NOT Saved')]", "//font[@color='red']", "//span[contains(@id, '_lblmsg') and normalize-space(text())]"]
                                for xp_r in xpaths_retry:
                                    try: msg_r = short_wait.until(EC.visibility_of_element_located((By.XPATH, xp_r))); res = msg_r.text.strip(); level = "error"; self.app.after(0, self.app.log_message, self.log_display, f"   RESULT (Retry Fail): {res}", level); break
                                    except TimeoutException: continue
                                else: res = "Retry Failed (Unknown)"; self.app.after(0, self.app.log_message, self.log_display, f"   RESULT: {res}", "error")
                                time.sleep(1.0)
                            except Exception as retry_alert_e: self.app.after(0, self.app.log_message, self.log_display, f"   Retry Alert Error: {retry_alert_e}")
                        else: res = "Retry Failed (Re-fill error)"; self.app.after(0, self.app.log_message, self.log_display, f"   ERROR: {res}", "error"); alert_ok = False
                    else:
                        reason = f"({actual_worked_from_error} pending)" if actual_worked_from_error != -1 else "(parse fail)"
                        self.app.after(0, self.app.log_message, self.log_display, f"   SKIPPED: 100d error, <=0 days left {reason}.", "warning")
                        res = f"Skipped (100 days {reason})"; alert_ok = False

                # --- Final Result Logging ---
                spec_err = "is already there" in res.lower() and "demand of" in res.lower(); err_name = ""
                if spec_err and not alert_ok:
                    try: err_name = res.split("Demand of ")[1].split(" for period")[0].split("  ")[0].strip(); self.app.after(0, self.app.log_message, self.log_display, f"   -> Parsed 'already demanded': '{err_name}'")
                    except Exception: spec_err = False; self.app.after(0, self.app.log_message, self.log_display, "   -> Couldn't parse name.")

                current_submit_days = remaining_days_calc if is_100_day_error and alert_ok and remaining_days_calc > 0 else adj_days

                for app_data in apps_in_jc:
                    name = app_data.get('Name of Applicant', 'N/A')
                    if name not in processed: continue
                    status = res
                    if alert_ok: status = f"Success (Adj: {current_submit_days}d)" if current_submit_days != user_days else "Success"
                    elif is_aadhaar_error: status = "FAIL: Aadhaar Auth Required" # Specific status
                    elif spec_err and err_name: status = res if "".join(err_name.lower().split()) in "".join(name.lower().split()) else f"Success (Batch, Adj: {current_submit_days}d)" if current_submit_days != user_days else "Success (Batch)"
                    elif is_100_day_error and remaining_days_calc <= 0 : status = f"Skipped (100 days {reason})"
                    elif is_100_day_error and not alert_ok : status = f"Retry Failed: {res} ({current_submit_days}d)"
                    elif current_submit_days != user_days and not any(e in status.lower() for e in ['fail', 'error', 'unknown', 'skip', 'record not saved', 'aadhaar']): status += f" (Adj: {current_submit_days}d)"
                    self.app.after(0, self._update_results_tree, (jc, name, status))
            else:
                 self.app.after(0, self.app.log_message, self.log_display, f"   -> No submission for JC {jc_suffix} (all correct, not found, or fill error).")
                 for app_data in apps_in_jc:
                     name = app_data.get('Name of Applicant', 'N/A')
                     if name in processed: self.app.after(0, self._update_results_tree, (jc, name, f"Already Correct ({adj_days}d)"))

        except StaleElementReferenceException:
            self.app.after(0, self.app.log_message, self.log_display, f"   INFO: Stale element {jc}, retrying...", "warning"); time.sleep(1.0)
            self._process_single_job_card(driver, wait, short_wait, jc, apps_in_jc, user_days, demand_from, work_start, days_worked_ids, jc_ids, grid_ids, btn_ids, err_msg_ids, base_url, state)
        except Exception as e:
            self.app.after(0, self.app.log_message, self.log_display, f"CRITICAL ERROR processing {jc}: {type(e).__name__} - {e}", "error")
            [self.app.after(0, self._update_results_tree, (jc, a.get('Name of Applicant'), f"FAIL: {type(e).__name__}")) for a in apps_in_jc]
            try: driver.get(base_url); self.app.after(0, self.app.log_message, self.log_display, f"   Recovering: Navigating start...", "warning"); time.sleep(1)
            except Exception as nav_e: self.app.after(0, self.app.log_message, self.log_display, f"   Recovery failed: {nav_e}", "error")


    def _update_results_tree(self, data):
        jc, name, status = data; row_id = len(self.results_tree.get_children()) + 1
        status_str, status_low = str(status), str(status).lower(); tags = ()
        if any(e in status_low for e in ['fail','error','crash','not found','invalid','aadhaar','not saved', 'not issued']): tags = ('failed',)
        elif any(w in status_low for w in ['skip','adjust','already there','limit']): tags = ('warning',)
        disp_status = (status_str[:100] + '...') if len(status_str) > 100 else status_str
        self.results_tree.insert("", "end", iid=row_id, values=(row_id, jc, name, disp_status), tags=tags)
        self.results_tree.yview_moveto(1)

    def export_results(self):
        if not self.results_tree.get_children(): messagebox.showinfo("Export", "No results."); return
        p = self.panchayat_entry.get().strip().replace(" ", "_") or "UnknownPanchayat"; s = self.state_combobox.get() or "UnknownState"
        fname = f"Demand_Report_{s}_{p}_{datetime.now():%Y%m%d_%H%M}.csv"; self.export_treeview_to_csv(self.results_tree, fname)

    def save_inputs(self, inputs):
        try:
            with open(self.config_file, 'w') as f: json.dump(inputs, f, indent=4)
        except Exception as e: print(f"Err saving demand inputs: {e}")

    def load_inputs(self):
        today = datetime.now().strftime('%d/%m/%Y'); date_to_set = today
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f: data = json.load(f)
                self.state_combobox.set(data.get('state', '')); self.panchayat_entry.insert(0, data.get('panchayat', ''))
                loaded = data.get('demand_date', '');
                try: datetime.strptime(loaded, '%d/%m/%Y'); date_to_set = loaded
                except ValueError: pass
            except Exception as e: print(f"Err loading demand inputs: {e}")
        self.demand_date_entry.set_date(date_to_set)

    def _clear_selection(self):
        if not any(a.get('_selected', False) for a in self.all_applicants_data): self.app.log_message(self.log_display, "No selection.", "info"); return
        for a in self.all_applicants_data: a['_selected'] = False
        for w in self.displayed_checkboxes:
             if isinstance(w, ctk.CTkCheckBox) and w.get() == "on": w.deselect()
        self._update_selection_summary(); self.app.log_message(self.log_display, "Selection cleared.")

    def style_treeview(self, tree):
        # Apply styling as before (including 'warning' tag)
        style = ttk.Style()
        try: style.theme_use("clam")
        except tkinter.TclError: pass # Fallback
        bg = self.app._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        fg = self.app._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
        sel = self.app._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        hdr = self.app._apply_appearance_mode(ctk.ThemeManager.theme["CTkTextbox"]["fg_color"])
        fail_fg, warn_fg = "#FF6B6B", "#FFD700"

        style.configure("Treeview", background=bg, foreground=fg, fieldbackground=bg, rowheight=25, borderwidth=0)
        style.map('Treeview', background=[('selected', sel)], foreground=[('selected', fg)]) # Use fg for selected text too
        style.configure("Treeview.Heading", background=hdr, foreground=fg, relief="flat", font=('Calibri', 10,'bold'))
        style.map("Treeview.Heading", background=[('active', '#555555')])

        tree.tag_configure('failed', foreground=fail_fg)
        tree.tag_configure('warning', foreground=warn_fg)
        style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})]) # Remove borders