# tabs/if_edit_tab.py (Patched to prevent post-automation crash on macOS)
import tkinter
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import os, csv, time, pyperclip, json
from datetime import datetime
from collections import defaultdict
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import config
from .base_tab import BaseAutomationTab

class IfEditTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="if_edit")
        self.csv_path = None
        self.csv_headers = []
        self.column_map = {}
        self.ui_fields = {}

        # --- Profile Management Attributes ---
        self.profiles = {}
        self.profile_file = self.app.get_data_path("if_edit_profiles.json")
        self.saved_config = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._create_widgets()
        self._load_profiles_from_file()

    def _create_widgets(self):
        main_container = ctk.CTkFrame(self)
        main_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_container.grid_columnconfigure(0, weight=1)

        # --- NEW: Profile Management Frame ---
        profile_frame = ctk.CTkFrame(main_container)
        profile_frame.grid(row=0, column=0, sticky='ew', padx=10, pady=10)
        profile_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(profile_frame, text="Configuration Profile:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=15, pady=10, sticky="w")
        self.profile_combobox = ctk.CTkComboBox(profile_frame, values=[], command=self._load_profile)
        self.profile_combobox.grid(row=0, column=1, padx=15, pady=10, sticky="ew")

        self.profile_name_entry = ctk.CTkEntry(profile_frame, placeholder_text="Enter new profile name to save")
        self.profile_name_entry.grid(row=1, column=1, padx=15, pady=5, sticky="ew")

        profile_actions = ctk.CTkFrame(profile_frame, fg_color="transparent")
        profile_actions.grid(row=1, column=0, padx=15, pady=5)
        self.save_profile_button = ctk.CTkButton(profile_actions, text="Save", command=self._save_profile)
        self.save_profile_button.pack(side="left", padx=(0, 5))
        self.delete_profile_button = ctk.CTkButton(profile_actions, text="Delete", fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE"), command=self._delete_profile)
        self.delete_profile_button.pack(side="left")
        # --- End Profile Frame ---

        csv_frame = ctk.CTkFrame(main_container)
        csv_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(10,0))
        csv_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(csv_frame, text="1. Select Data File:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=15, pady=10)
        file_frame = ctk.CTkFrame(csv_frame, fg_color="transparent")
        file_frame.grid(row=0, column=1, sticky='ew', pady=10, padx=15)
        self.select_button = ctk.CTkButton(file_frame, text="Select CSV File", command=self.select_csv_file)
        self.select_button.pack(side="left", padx=(0, 10))
        self.file_label = ctk.CTkLabel(file_frame, text="No file selected", text_color="gray")
        self.file_label.pack(side="left")

        switch_frame = ctk.CTkFrame(main_container)
        switch_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.convergence_switch = ctk.CTkSwitch(switch_frame, text="Enable Page 2 & 3 (Convergence Work)", command=self._toggle_page_settings)
        self.convergence_switch.grid(row=0, column=0, padx=15, pady=10)
        self.ui_fields['run_convergence'] = self.convergence_switch

        self.settings_notebook = ctk.CTkTabview(main_container)
        self.settings_notebook.grid(row=3, column=0, sticky="ew", padx=10, pady=(0,10))
        tab_p1 = self.settings_notebook.add("Page 1 Settings")
        tab_p2 = self.settings_notebook.add("Page 2 Settings")
        tab_p3 = self.settings_notebook.add("Page 3 Settings")

        self._create_page1_widgets(tab_p1)
        self._create_page2_widgets(tab_p2)
        self._create_page3_widgets(tab_p3)
        self._toggle_page_settings()

        action_frame = self._create_action_buttons(parent_frame=main_container)
        action_frame.grid(row=4, column=0, sticky="ew", pady=15, padx=10)

        notebook = ctk.CTkTabview(self)
        notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        results_frame = notebook.add("Results")
        self._create_log_and_status_area(parent_notebook=notebook)

        results_frame.grid_columnconfigure(0, weight=1); results_frame.grid_rowconfigure(1, weight=1)
        results_action_frame = ctk.CTkFrame(results_frame, fg_color="transparent")
        results_action_frame.grid(row=0, column=0, sticky="ew", pady=(5, 10), padx=5)
        self.export_csv_button = ctk.CTkButton(results_action_frame, text="Export to CSV", command=lambda: self.export_treeview_to_csv(self.results_tree, "if_edit_results.csv"))
        self.export_csv_button.pack(side="left")

        cols = ("Work Code", "Job Card", "Status", "Details")
        self.results_tree = ttk.Treeview(results_frame, columns=cols, show='headings')
        for col in cols: self.results_tree.heading(col, text=col)
        self.results_tree.column("Work Code", width=200); self.results_tree.column("Job Card", width=200); self.results_tree.column("Status", width=100, anchor="center"); self.results_tree.column("Details", width=300)
        self.results_tree.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        scrollbar = ctk.CTkScrollbar(results_frame, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set); scrollbar.grid(row=1, column=1, sticky='ns')
        self.style_treeview(self.results_tree)

    def _create_field(self, parent, key, text, row, col=0, widget_type='entry', values=None, **kwargs):
        ctk.CTkLabel(parent, text=text).grid(row=row, column=col, sticky="w", padx=15, pady=5)
        if widget_type == 'entry':
            widget = ctk.CTkEntry(parent, **kwargs)
        elif widget_type == 'combo':
            widget = ctk.CTkComboBox(parent, values=values or [], **kwargs)
        widget.grid(row=row, column=col+1, sticky="ew", padx=15, pady=5)
        self.ui_fields[key] = widget

    def _create_page1_widgets(self, parent):
        parent.grid_columnconfigure(1, weight=1)
        self._create_field(parent, "estimated_pd", "Estimated PD:", 0)
        self._create_field(parent, "beneficiaries_count", "Beneficiaries Count:", 1)

        ctk.CTkLabel(parent, text="--- Convergence Settings (If Enabled) ---", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, columnspan=2, pady=(15,5))
        self._create_field(parent, "convergence_scheme_type", "Scheme Type:", 4, widget_type='combo', values=["State", "Centre"], command=self._toggle_scheme_dropdowns)

        state_schemes = ["ABUA AWAS YOJNA", "Agriculture", "Anganbari kendra Dumaria, Dahijor", "Animal Husbandry", "B.R.G.F", "Baba Saheb Bhim Rao Ambedkar Awaas Yojna", "Birsa Sichai Kup Samvardhan Yojana", "CONST. OF PANCHAYAT BHAWAN", "Department of School Education and Literacy", "Department of Tourism, Arts, Culture, Sports & You", "Diary Development", "EAST SINGHBHUM(DUMARIA BLOCK) ST BENIFIRIES", "Fisheries", "Integrated Action Plan", "IRRIGATION WELL", "JSLPS- Jharkhand State Livelihood Promotion Societ", "Mukhyamantri Grameen Path Yojna", "SINCHAI KUP NIRMAN , PESARDAH(BICHGARHA)", "Soil Conservation", "ST Benifiries", "TestScheme", "Water Harvestig"]
        self._create_field(parent, "state_scheme_name", "State Scheme Name:", 5, widget_type='combo', values=state_schemes)

        centre_schemes = ["B.R.G.F (NON)", "B.R.G.F (R.D.MINISTRY)", "bhart health nirman yojna (gramin health department)", "DMFT (Department of Mines & Geology)", "Fifteen Finance Commission (Ministry of Panchayati Raj)", "Fourteenth Finance Commission(FFC) (Ministry of Panchayati Raj)", "IAY (R.D.MINISTRY)", "ICDS (Ministry Of Women & Child Development)", "Integrated Action Plan (R.D.MINISTRY)", "Land Levling (NON)", "niramal bhart abhiyan (R.D.MINISTRY)", "NIRMAL BHART NIRMAN (R.D.MINISTRY)", "P.H.E.D. (R.D.MINISTRY)", "PMAY-G (R.D.MINISTRY)", "RKVY (MINISTRY OF AGRICULTURE)", "rural sanitation (R.D.MINISTRY)", "RURAL SANITATION (NON)", "WELL (NON)"]
        self._create_field(parent, "centre_scheme_name", "Centre Scheme Name:", 6, widget_type='combo', values=centre_schemes)

    def _create_page2_widgets(self, parent):
        parent.grid_columnconfigure((1, 3), weight=1)
        self._create_field(parent, "sanction_no", "Tech Sanction No:", 0, 0)
        self._create_field(parent, "sanction_date", "Tech Sanction Date:", 0, 2)
        self._create_field(parent, "est_time_completion", "Est. Time Completion:", 1, 0)
        self._create_field(parent, "avg_labour_per_day", "Avg. Labour/Day:", 1, 2)
        self._create_field(parent, "expected_mandays", "Expected Mandays:", 2, 0)
        self._create_field(parent, "tech_sanction_amount", "Tech Sanction Amt:", 2, 2)

        ctk.CTkLabel(parent, text="--- Estimated Cost (in Lakhs) ---", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, columnspan=4, pady=(15,5))
        self._create_field(parent, "unskilled_labour_cost", "Unskilled Labour:", 4, 0)
        self._create_field(parent, "mgnrega_material_cost", "MGNREGA Material:", 4, 2)
        self._create_field(parent, "skilled_labour_cost", "Skilled Labour:", 5, 0)
        self._create_field(parent, "semi_skilled_labour_cost", "Semi-Skilled Labour:", 5, 2)
        self._create_field(parent, "scheme1_cost", "Scheme 1 Cost:", 6, 0)

        ctk.CTkLabel(parent, text="--- Financial Sanction ---", font=ctk.CTkFont(weight="bold")).grid(row=7, column=0, columnspan=4, pady=(15,5))
        self._create_field(parent, "fin_sanction_no", "Fin. Sanction No:", 8, 0)
        self._create_field(parent, "fin_sanction_date", "Fin. Sanction Date:", 8, 2)
        self._create_field(parent, "fin_sanction_amount", "Fin. Sanction Amt:", 9, 0)
        self._create_field(parent, "fin_scheme_input", "Fin. Scheme Input:", 9, 2)

    def _create_page3_widgets(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(parent, text="Page 3 settings are controlled by the CSV file.", font=ctk.CTkFont(size=14)).pack(pady=20, padx=10)
        ctk.CTkLabel(parent, text="Automation will only process items with type 'activity'.\nEnsure CSV has columns: `item_type`, `item_code_or_name`, `unit_price`, `quantity`", text_color="gray50", wraplength=400).pack(pady=10, padx=10)

    def _populate_defaults(self):
        cfg = {**config.IF_EDIT_CONFIG["page1"], **config.IF_EDIT_CONFIG["page2"]}
        for key, value in cfg.items():
            if key in self.ui_fields:
                widget = self.ui_fields[key]
                if isinstance(widget, ctk.CTkEntry):
                    widget.delete(0, tkinter.END); widget.insert(0, value)
                elif isinstance(widget, ctk.CTkComboBox):
                     widget.set(value)
                elif isinstance(widget, ctk.CTkSwitch):
                    pass
        self.convergence_switch.select()
        self._toggle_page_settings()

    def _load_profiles_from_file(self):
        if not os.path.exists(self.profile_file):
            self.profiles = {}
            self._populate_defaults()
            return
        try:
            with open(self.profile_file, 'r') as f:
                self.profiles = json.load(f)
            profile_names = list(self.profiles.keys())
            self.profile_combobox.configure(values=profile_names)
            last_used = "Last Used Config"
            if last_used in profile_names:
                self.profile_combobox.set(last_used)
                self._load_profile(last_used)
            elif profile_names:
                self.profile_combobox.set(profile_names[0])
                self._load_profile(profile_names[0])
            else:
                self._populate_defaults()
        except Exception as e:
            self.app.log_message(self.log_display, f"Could not load profiles: {e}", "warning")
            self.profiles = {}
            self._populate_defaults()

    def _save_profile(self, profile_name=None, is_autosave=False):
        if not is_autosave:
            profile_name = self.profile_name_entry.get().strip()
            if not profile_name:
                messagebox.showwarning("Input Error", "Please enter a name for the profile.")
                return
        if not profile_name:
            return

        config_data = {}
        for key, field in self.ui_fields.items():
            if isinstance(field, ctk.CTkSwitch):
                config_data[key] = field.get()
            else:
                config_data[key] = field.get()

        self.profiles[profile_name] = config_data

        try:
            with open(self.profile_file, 'w') as f:
                json.dump(self.profiles, f, indent=4)
            profile_names = list(self.profiles.keys())
            if "Last Used Config" not in profile_names:
                profile_names.insert(0, "Last Used Config")
            self.profile_combobox.configure(values=profile_names)
            self.profile_combobox.set(profile_name)
            if not is_autosave:
                self.profile_name_entry.delete(0, tkinter.END)
                messagebox.showinfo("Success", f"Profile '{profile_name}' saved successfully.")
        except Exception as e:
            if not is_autosave:
                messagebox.showerror("Error", f"Failed to save profile: {e}")

    def _load_profile(self, profile_name):
        if not profile_name or not self.profiles:
            return
        self.saved_config = self.profiles.get(profile_name, {})
        if not self.saved_config:
            self._populate_defaults()
            return

        for key, value in self.saved_config.items():
            if key in self.ui_fields:
                field = self.ui_fields[key]
                if isinstance(field, ctk.CTkEntry):
                    field.delete(0, tkinter.END)
                    field.insert(0, value)
                elif isinstance(field, ctk.CTkComboBox):
                    field.set(value)
                elif isinstance(field, ctk.CTkSwitch):
                    if value == 1:
                        field.select()
                    else:
                        field.deselect()

        self._toggle_page_settings()
        self.app.log_message(self.log_display, f"Profile '{profile_name}' loaded.")

    def _delete_profile(self):
        profile_name = self.profile_combobox.get()
        if not profile_name or profile_name not in self.profiles or profile_name == "Last Used Config":
            messagebox.showwarning("Selection Error", "Please select a valid, user-saved profile to delete.")
            return
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the profile '{profile_name}'?"):
            return
        del self.profiles[profile_name]
        try:
            with open(self.profile_file, 'w') as f:
                json.dump(self.profiles, f, indent=4)
            profile_names = list(self.profiles.keys())
            self.profile_combobox.configure(values=profile_names)
            if profile_names:
                self.profile_combobox.set(profile_names[0])
                self._load_profile(profile_names[0])
            else:
                self.profile_combobox.set("")
                self._populate_defaults()
            messagebox.showinfo("Success", f"Profile '{profile_name}' deleted.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete profile: {e}")

    def _toggle_page_settings(self):
        is_enabled = self.convergence_switch.get() == 1
        state = "normal" if is_enabled else "disabled"

        page2_keys = ["sanction_no", "sanction_date", "est_time_completion", "avg_labour_per_day",
                      "expected_mandays", "tech_sanction_amount", "unskilled_labour_cost",
                      "mgnrega_material_cost", "skilled_labour_cost", "semi_skilled_labour_cost", "scheme1_cost",
                      "fin_sanction_no", "fin_sanction_date", "fin_sanction_amount", "fin_scheme_input"]

        convergence_keys = ["convergence_scheme_type", "state_scheme_name", "centre_scheme_name"]

        for key in page2_keys + convergence_keys:
            if key in self.ui_fields:
                self.ui_fields[key].configure(state=state)

        if is_enabled:
            self._toggle_scheme_dropdowns()

    def _toggle_scheme_dropdowns(self, _=None):
        if self.convergence_switch.get() == 0:
            self.ui_fields['state_scheme_name'].configure(state="disabled")
            self.ui_fields['centre_scheme_name'].configure(state="disabled")
            return

        is_state_selected = self.ui_fields['convergence_scheme_type'].get() == "State"
        self.ui_fields['state_scheme_name'].configure(state="normal" if is_state_selected else "disabled")
        self.ui_fields['centre_scheme_name'].configure(state="normal" if not is_state_selected else "disabled")

    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running)
        state = "disabled" if running else "normal"
        self.select_button.configure(state=state)
        self.profile_combobox.configure(state=state)
        self.profile_name_entry.configure(state=state)
        self.save_profile_button.configure(state=state)
        self.delete_profile_button.configure(state=state)

        for field in self.ui_fields.values():
            if field.winfo_exists(): field.configure(state=state)
        if not running:
            for key in ['estimated_pd', 'beneficiaries_count']:
                 self.ui_fields[key].configure(state="normal")
            self._toggle_page_settings()

    def reset_ui(self):
        if messagebox.askokcancel("Reset Form?", "Are you sure?"):
            self.file_label.configure(text="No file selected"); self.csv_path = None; self.column_map = {}
            self._populate_defaults()
            for item in self.results_tree.get_children(): self.results_tree.delete(item)
            self.app.clear_log(self.log_display)

    def select_csv_file(self):
        path = filedialog.askopenfilename(title="Select CSV", filetypes=[("CSV files", "*.csv")])
        if path:
            self.csv_path = path; self.file_label.configure(text=os.path.basename(path))
            try:
                with open(path, 'r', encoding='utf-8-sig') as f: self.csv_headers = next(csv.reader(f))
                required_cols = ['work_code', 'beneficiary_type', 'job_card', 'item_type', 'item_code_or_name', 'unit_price', 'quantity']
                self.column_map = {col: self.csv_headers.index(col) for col in required_cols}
                self.app.log_message(self.log_display, f"CSV loaded successfully. Required columns found.", "success")
            except Exception as e:
                messagebox.showerror("CSV Error", f"Could not find all required columns in the CSV header.\nRequired: {', '.join(required_cols)}\n\nError: {e}")
                self.csv_path = None; self.column_map = {}; self.file_label.configure(text="No file selected")

    def start_automation(self):
        if not self.csv_path or not self.column_map:
            messagebox.showwarning("Input Missing", "Please select a valid CSV file with the required columns."); return

        self._save_profile(profile_name="Last Used Config", is_autosave=True)

        form_config = {key: field.get() for key, field in self.ui_fields.items()}
        form_config['convergence_scheme_name'] = form_config['state_scheme_name'] if form_config['convergence_scheme_type'] == "State" else form_config['centre_scheme_name']
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic, args=(form_config,))

    def run_automation_logic(self, form_config):
        self.app.after(0, self.set_ui_state, True)
        self.app.clear_log(self.log_display)
        for item in self.results_tree.get_children(): self.results_tree.delete(item)
        try:
            driver = self.app.get_driver();
            if not driver: return
            with open(self.csv_path, mode='r', encoding='utf-8-sig') as csvfile: rows = list(csv.reader(csvfile))[1:]
            grouped_tasks = defaultdict(list)
            for row in rows: grouped_tasks[row[self.column_map['work_code']]].append(row)
            self.app.log_message(self.log_display, f"--- Starting IF Editor: {len(grouped_tasks)} unique work codes to process ---")
            total = len(grouped_tasks); i = 0
            for work_code, items in grouped_tasks.items():
                i += 1
                if self.app.stop_events[self.automation_key].is_set():
                    self.app.log_message(self.log_display, "Automation stopped.", "warning"); break
                self.app.log_message(self.log_display, f"--- Processing {i}/{total}: WC={work_code} ---")
                self.app.after(0, self.update_status, f"Processing {i}/{total}: {work_code}", i/total)
                self._process_single_work_code(driver, work_code, items, form_config)
        except Exception as e:
            self.app.log_message(self.log_display, f"A critical error occurred: {e}", "error")
        finally:
            # --- CRASH FIX: All UI updates from the worker thread must be scheduled with 'after' ---
            self.app.after(0, self.app.log_message, self.log_display, "--- Automation Finished ---")
            self.app.after(0, self.set_ui_state, False)
            # Schedule the final message box to appear after a short delay to prevent UI conflicts
            self.app.after(100, lambda: messagebox.showinfo("Complete", "IF Editor process has finished."))

    def _log_result(self, work_code, job_card, status, details):
        self.app.after(0, lambda: self.results_tree.insert("", "end", values=(work_code, job_card, status, details)))
        level = "success" if status.lower() == "success" else "error" if status.lower() == "failed" else "info"
        self.app.log_message(self.log_display, f"'{work_code}' - {status}: {details}", level)

    def _get_existing_items(self, driver):
        """Scans the page for already added activities."""
        existing_items = set()
        try:
            activity_table = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_grdDisplayAct")
            rows = activity_table.find_elements(By.XPATH, ".//tbody/tr")
            for row in rows:
                try:
                    item_code_span = row.find_element(By.XPATH, ".//span[contains(@id, '_lblActCode')]")
                    item_name = item_code_span.text.strip()
                    if item_name:
                        existing_items.add(('activity', item_name))
                except NoSuchElementException:
                    continue
        except NoSuchElementException:
            self.app.log_message(self.log_display, "No existing activities table found.", "info")

        if existing_items:
            self.app.log_message(self.log_display, f"Found {len(existing_items)} existing items on the page.")
        return existing_items

    def _process_single_work_code(self, driver, work_code, items, cfg):
        first_item = items[0]
        beneficiary_type = first_item[self.column_map['beneficiary_type']]
        job_card = first_item[self.column_map['job_card']]
        try:
            current_year = datetime.now().year; wait = WebDriverWait(driver, 20)
            driver.get(config.IF_EDIT_CONFIG["url"])

            self.app.log_message(self.log_display, "Page 1: Entering work details...")

            work_code_input = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_txtwrksearchkey")))
            work_code_input.send_keys(work_code)
            work_code_input.send_keys(Keys.TAB)
            self.app.log_message(self.log_display, "   - Waiting for work name list to populate...")
            time.sleep(3) 

            self.app.log_message(self.log_display, "   - Selecting work name.")
            work_name_dropdown = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ddlworkName")))
            Select(work_name_dropdown).select_by_index(1)
            time.sleep(2)

            wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_TxtEstpd"))).clear()
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_TxtEstpd").send_keys(cfg["estimated_pd"])
            beneficiaries_input = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txt_nofobenificary")
            beneficiaries_input.clear(); beneficiaries_input.send_keys(cfg["beneficiaries_count"])
            beneficiaries_input.send_keys(Keys.TAB); time.sleep(2)
            Select(wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_grdData_ctl02_ddljobcard")))).select_by_value(job_card); time.sleep(1)
            Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlTypeBenif")).select_by_visible_text(beneficiary_type)
            Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlpresentstatus")).select_by_visible_text("Not Exist")

            if cfg['run_convergence'] == 1:
                driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_UCconverg_rblConverg_0").click(); time.sleep(1)
                scheme_type = "State" if cfg['convergence_scheme_type'] == "State" else "Centre"
                Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_UCconverg_ddlSchemeType1")).select_by_visible_text(scheme_type); time.sleep(1)
                Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_UCconverg_ddlScheme1")).select_by_visible_text(cfg["convergence_scheme_name"])
            else:
                driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_UCconverg_rblConverg_1").click()

            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btupdate").click()

            # --- ENHANCED: Check for both alerts and on-page error messages ---
            time.sleep(1) # Wait a moment for page to respond
            # 1. Check for pop-up alert
            try:
                alert = WebDriverWait(driver, 2).until(EC.alert_is_present())
                alert_text = alert.text
                self.app.log_message(self.log_display, f"   - Alert detected: {alert_text}", "warning")
                alert.accept()
                self._log_result(work_code, job_card, "Failed", f"Page 1 Alert: {alert_text}")
                return
            except TimeoutException:
                pass # No alert, continue to check for on-page text
            
            # 2. Check for on-page text error
            try:
                error_element = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_lblmsg")
                if error_element.is_displayed() and error_element.text.strip():
                    error_text = error_element.text.strip()
                    self.app.log_message(self.log_display, f"   - On-page error found: {error_text}", "error")
                    self._log_result(work_code, job_card, "Failed", error_text)
                    return
            except NoSuchElementException:
                pass # No on-page error, this is the expected success path
            # --- END ENHANCEMENT ---

            if cfg['run_convergence'] == 0:
                self._log_result(work_code, job_card, "Success", "Page 1 submitted (non-convergence)."); return

            self.app.log_message(self.log_display, "Page 2: Entering sanction details...")
            wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_txtsanctionno")))

            def fill_input(element_id, text):
                element = driver.find_element(By.ID, element_id)
                element.clear()
                element.send_keys(text)

            fill_input("ctl00_ContentPlaceHolder1_txtsanctionno", cfg["sanction_no"].format(year=current_year))
            fill_input("ctl00_ContentPlaceHolder1_txtsanctionDate", cfg["sanction_date"].format(year=current_year))
            fill_input("ctl00_ContentPlaceHolder1_txtEstTimecompWork", cfg["est_time_completion"])
            fill_input("ctl00_ContentPlaceHolder1_txtAvglabourperday", cfg["avg_labour_per_day"])
            fill_input("ctl00_ContentPlaceHolder1_txtExcpectedmanday", cfg["expected_mandays"])
            fill_input("ctl00_ContentPlaceHolder1_txtTechsancAmt", cfg["tech_sanction_amount"])

            fill_input("ctl00_ContentPlaceHolder1_Sanc_Tech_Labr_Unskilled", cfg["unskilled_labour_cost"])
            fill_input("ctl00_ContentPlaceHolder1_Est_Cost_Material", cfg["mgnrega_material_cost"])
            fill_input("ctl00_ContentPlaceHolder1_skilled", cfg["skilled_labour_cost"])
            fill_input("ctl00_ContentPlaceHolder1_txt_semiskilled", cfg["semi_skilled_labour_cost"])
            fill_input("ctl00_ContentPlaceHolder1_scheme_val1", cfg["scheme1_cost"])

            fill_input("ctl00_ContentPlaceHolder1_txtFinsan_no", cfg["fin_sanction_no"].format(year=current_year))
            fill_input("ctl00_ContentPlaceHolder1_sanc_fin_date", cfg["fin_sanction_date"].format(year=current_year))
            fill_input("ctl00_ContentPlaceHolder1_sanc_fin_Amt", cfg["fin_sanction_amount"])

            fin_scheme_input = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_fin_scheme1")
            fin_scheme_input.clear()
            fin_scheme_input.send_keys(cfg["fin_scheme_input"])

            fin_scheme_input.send_keys(Keys.TAB); time.sleep(1)

            try:
                update_button = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btUpdate")
                driver.execute_script("arguments[0].click();", update_button)
                self.app.log_message(self.log_display, "Page 2 'Update' clicked.", "success")
            except NoSuchElementException:
                save_button = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btSave")
                driver.execute_script("arguments[0].click();", save_button)
                self.app.log_message(self.log_display, "Page 2 'Save' clicked.", "success")

            self.app.log_message(self.log_display, "Page 3: Adding activities...")
            wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddlAct")))

            existing_items = self._get_existing_items(driver)

            for item_row in items:
                if self.app.stop_events[self.automation_key].is_set(): break
                item_type = item_row[self.column_map['item_type']].strip().lower()

                if item_type != 'activity':
                    self.app.log_message(self.log_display, f"  > Skipping non-activity item (type: {item_type})", "info")
                    continue

                item_name_from_csv = item_row[self.column_map['item_code_or_name']].strip()
                unit_price = item_row[self.column_map['unit_price']].strip()
                quantity = item_row[self.column_map['quantity']].strip()

                lookup_key = ('activity', item_name_from_csv)
                if lookup_key in existing_items:
                    self.app.log_message(self.log_display, f"  > Skipping duplicate activity: {item_name_from_csv}", "warning")
                    continue

                self.app.log_message(self.log_display, f"  > Adding activity: {item_name_from_csv}")

                Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlAct")).select_by_value(item_name_from_csv)
                time.sleep(2)

                unit_price_input = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_txtAct_UnitPrice")))
                unit_price_input.clear(); unit_price_input.send_keys(unit_price)
                unit_price_input.send_keys(Keys.TAB)
                time.sleep(2)

                qty_input = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_txtAct_Qty")))
                qty_input.clear(); qty_input.send_keys(quantity)
                qty_input.send_keys(Keys.TAB)
                time.sleep(1)

                save_button = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btsave")
                save_button.click()

                wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_btsave")))
                time.sleep(2)
                existing_items = self._get_existing_items(driver)

            self._log_result(work_code, job_card, "Success", "All activities processed.")
            time.sleep(2)
        except Exception as e:
            # --- ENHANCED: Provide clearer error messages for timeouts and other exceptions ---
            error_message = str(e)
            if "Message: " in error_message:
                error_message = error_message.split("Message: ", 1)[-1]
                
            final_detail = error_message.splitlines()[0].strip()
            
            if not final_detail:
                final_detail = "Process timed out waiting for the next page or element."

            self._log_result(work_code, job_card, "Failed", final_detail)
            self.app.log_message(self.log_display, f"   ERROR on {work_code}: {final_detail}", "error")
            # --- END ENHANCEMENT ---