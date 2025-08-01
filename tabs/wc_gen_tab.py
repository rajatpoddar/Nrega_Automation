# tabs/wc_gen_tab.py (Corrected crash on error and missing function)
import tkinter
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import os, csv, time, pyperclip, sys, threading, json
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from collections import defaultdict
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import config
from .base_tab import BaseAutomationTab
from .date_entry_widget import DateEntry

class WcGenTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="wc_gen")
        self.csv_path = None
        self.ui_fields = {}
        self.profiles = {}
        self.profile_file = self.app.get_data_path("wc_gen_profiles.json")
        self.saved_config = {}
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self._create_widgets()
        self._load_profiles_from_file()

    def _create_widgets(self):
        main_container = ctk.CTkFrame(self)
        main_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_container.grid_columnconfigure(0, weight=1)

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

        loader_frame = ctk.CTkFrame(main_container)
        loader_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=10)
        loader_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(loader_frame, text="Panchayat Name:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=15, pady=(10,0), sticky="w")
        self.panchayat_entry = ctk.CTkEntry(loader_frame)
        self.panchayat_entry.grid(row=0, column=1, padx=15, pady=(10,0), sticky="ew")
        self.load_button = ctk.CTkButton(loader_frame, text="Load Categories from Website", command=self._start_category_loading_thread)
        self.load_button.grid(row=1, column=0, columnspan=2, padx=15, pady=10, sticky="ew")

        scrollable_frame = ctk.CTkScrollableFrame(main_container, label_text="Work Generation Details")
        scrollable_frame.grid(row=2, column=0, sticky='ew', padx=10, pady=10)
        scrollable_frame.grid_columnconfigure(1, weight=1)
        
        self._create_field(scrollable_frame, "master_category", "Master Category", 0, is_dropdown=True)
        self._create_field(scrollable_frame, "work_category", "Work Category", 1, is_dropdown=True)
        self._create_field(scrollable_frame, "beneficiary_type", "Beneficiary Type", 2, is_dropdown=True)
        self._create_field(scrollable_frame, "activity_type", "Activity Type", 3, is_dropdown=True)
        self._create_field(scrollable_frame, "work_type", "Work Type", 4, is_dropdown=True)
        self._create_field(scrollable_frame, "pro_status", "Proposal Status", 5, is_dropdown=True)
        self._create_field(scrollable_frame, "executing_agency", "Executing Agency", 7, is_dropdown=True)
        ctk.CTkLabel(scrollable_frame, text="--- Dates & Costs ---", font=ctk.CTkFont(weight="bold")).grid(row=8, column=0, columnspan=2, pady=(10,0))
        ctk.CTkLabel(scrollable_frame, text="Proposal Date (DD/MM/YYYY)").grid(row=9, column=0, sticky="w", padx=15, pady=5)
        self.ui_fields['proposal_date'] = DateEntry(scrollable_frame, state="disabled")
        self.ui_fields['proposal_date'].grid(row=9, column=1, sticky="ew", padx=15, pady=5)
        ctk.CTkLabel(scrollable_frame, text="Work Start Date (DD/MM/YYYY)").grid(row=10, column=0, sticky="w", padx=15, pady=5)
        self.ui_fields['start_date'] = DateEntry(scrollable_frame, state="disabled")
        self.ui_fields['start_date'].grid(row=10, column=1, sticky="ew", padx=15, pady=5)
        self._create_field(scrollable_frame, "est_labour_cost", "Est. Labour Cost (Lakhs)", 11)
        self._create_field(scrollable_frame, "est_material_cost", "Est. Material Cost (Lakhs)", 12)

        csv_frame = ctk.CTkFrame(main_container)
        csv_frame.grid(row=3, column=0, sticky='ew', padx=10, pady=10)
        csv_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(csv_frame, text="Data File:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", pady=10, padx=15)
        self.select_button = ctk.CTkButton(csv_frame, text="Select workcode_data.csv", command=self.select_csv_file)
        self.select_button.grid(row=0, column=1, sticky="w", padx=15)
        self.file_label = ctk.CTkLabel(csv_frame, text="No file selected", text_color="gray")
        self.file_label.grid(row=0, column=2, sticky="w", padx=10)
        ctk.CTkLabel(csv_frame, text="ℹ️ NOTE: Your CSV must have 9 columns for dynamic data (total_plants, etc.).", text_color="gray50").grid(row=1, column=1, columnspan=2, sticky="w", padx=15, pady=(0, 10))

        action_frame = self._create_action_buttons(parent_frame=main_container)
        action_frame.grid(row=4, column=0, sticky="ew", pady=15, padx=10)
        
        notebook = ctk.CTkTabview(self)
        notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10))
        
        results_frame = notebook.add("Results")
        self._create_log_and_status_area(notebook)

        results_frame.grid_columnconfigure(0, weight=1); results_frame.grid_rowconfigure(1, weight=1)
        results_action_frame = ctk.CTkFrame(results_frame, fg_color="transparent")
        results_action_frame.grid(row=0, column=0, sticky="ew", pady=(5, 10), padx=5)
        self.export_csv_button = ctk.CTkButton(results_action_frame, text="Export to CSV", command=lambda: self.export_treeview_to_csv(self.results_tree, "wc_gen_results.csv"))
        self.export_csv_button.pack(side="left")

        cols = ("Timestamp", "Generated Work Code")
        self.results_tree = ttk.Treeview(results_frame, columns=cols, show='headings')
        for col in cols: self.results_tree.heading(col, text=col)
        self.results_tree.column("Timestamp", width=100, anchor="center")
        self.results_tree.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        scrollbar = ctk.CTkScrollbar(results_frame, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set); scrollbar.grid(row=1, column=1, sticky='ns')
        self.style_treeview(self.results_tree)

    def _log_result(self, work_code):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.app.after(0, lambda: self.results_tree.insert("", "end", values=(timestamp, work_code)))

    def _create_field(self, parent, key, text, row, is_dropdown=False):
        ctk.CTkLabel(parent, text=text).grid(row=row, column=0, sticky="w", padx=15, pady=5)
        if is_dropdown: widget = ctk.CTkComboBox(parent, values=[], state="disabled", command=lambda choice, k=key: self._on_dropdown_select(k, choice))
        else: widget = ctk.CTkEntry(parent, state="disabled")
        widget.grid(row=row, column=1, sticky="ew", padx=15, pady=5)
        self.ui_fields[key] = widget
        
    def _populate_defaults(self):
        cfg = config.WC_GEN_CONFIG["defaults"]; current_year = str(datetime.now().year)
        for key, value in cfg.items():
            if key in self.ui_fields:
                field = self.ui_fields[key]
                formatted_value = value.format(year=current_year) if "{year}" in value else value
                if isinstance(field, DateEntry): field.set_date(formatted_value)
                elif isinstance(field, ctk.CTkEntry): field.delete(0, tkinter.END); field.insert(0, formatted_value)

    def _load_profiles_from_file(self):
        if not os.path.exists(self.profile_file): self.profiles = {}; self._populate_defaults(); return
        try:
            with open(self.profile_file, 'r') as f: self.profiles = json.load(f)
            profile_names = list(self.profiles.keys())
            self.profile_combobox.configure(values=profile_names)
            last_used = "Last Used Config"
            if last_used in profile_names:
                self.profile_combobox.set(last_used); self._load_profile(last_used)
            elif profile_names:
                self.profile_combobox.set(profile_names[0]); self._load_profile(profile_names[0])
            else: self._populate_defaults()
        except Exception as e:
            self.app.log_message(self.log_display, f"Could not load profiles: {e}", "warning"); self.profiles = {}

    def _save_profile(self, profile_name=None, is_autosave=False):
        if not is_autosave:
            profile_name = self.profile_name_entry.get().strip()
            if not profile_name: messagebox.showwarning("Input Error", "Please enter a name for the profile."); return
        if not profile_name: return

        config_data = {key: field.get() for key, field in self.ui_fields.items()}
        config_data["panchayat_name"] = self.panchayat_entry.get().strip()
        self.profiles[profile_name] = config_data
        
        try:
            with open(self.profile_file, 'w') as f: json.dump(self.profiles, f, indent=4)
            profile_names = list(self.profiles.keys())
            if not "Last Used Config" in profile_names:
                profile_names.insert(0, "Last Used Config")
            self.profile_combobox.configure(values=profile_names); self.profile_combobox.set(profile_name)
            if not is_autosave:
                self.profile_name_entry.delete(0, tkinter.END)
                messagebox.showinfo("Success", f"Profile '{profile_name}' saved successfully.")
        except Exception as e: 
            if not is_autosave: messagebox.showerror("Error", f"Failed to save profile: {e}")

    def _load_profile(self, profile_name):
        if not profile_name or not self.profiles: return
        self.saved_config = self.profiles.get(profile_name, {})
        if not self.saved_config: return
        
        # Load Panchayat and static fields
        self.panchayat_entry.delete(0, tkinter.END)
        self.panchayat_entry.insert(0, self.saved_config.get("panchayat_name", ""))
        
        for key in ["proposal_date", "start_date", "est_labour_cost", "est_material_cost"]:
            if key in self.saved_config and key in self.ui_fields:
                field = self.ui_fields[key]
                value = self.saved_config[key]
                if isinstance(field, DateEntry):
                    field.set_date(value)
                elif isinstance(field, ctk.CTkEntry):
                    field.delete(0, tkinter.END)
                    field.insert(0, value)
        
        # --- MODIFIED: Removed the automatic call to load categories ---
        # The user now has full manual control to click the "Load Categories" button.
        self.app.log_message(self.log_display, f"Profile '{profile_name}' loaded. Click 'Load Categories' to continue.")

    def _delete_profile(self):
        profile_name = self.profile_combobox.get()
        if not profile_name or profile_name not in self.profiles or profile_name == "Last Used Config": messagebox.showwarning("Selection Error", "Please select a valid, user-saved profile to delete."); return
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the profile '{profile_name}'?"): return
        del self.profiles[profile_name]
        try:
            with open(self.profile_file, 'w') as f: json.dump(self.profiles, f, indent=4)
            profile_names = list(self.profiles.keys()); self.profile_combobox.configure(values=profile_names)
            if profile_names:
                self.profile_combobox.set(profile_names[0]); self._load_profile(profile_names[0])
            else:
                self.profile_combobox.set(""); self._populate_defaults()
            messagebox.showinfo("Success", f"Profile '{profile_name}' deleted.")
        except Exception as e: messagebox.showerror("Error", f"Failed to delete profile: {e}")

    def _start_category_loading_thread(self):
        panchayat = self.panchayat_entry.get().strip();
        if not panchayat: messagebox.showwarning("Input Required", "Please enter a Panchayat Name first."); return
        self.load_button.configure(state="disabled", text="Loading...")
        threading.Thread(target=self._load_initial_categories, daemon=True).start()

    def _load_initial_categories(self):
        try:
            driver = self.app.get_driver()
            if not driver:
                self.app.after(0, lambda: self.load_button.configure(state="normal", text="Load Categories from Website"))
                return
            driver.get(config.WC_GEN_CONFIG["url"]); wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_ddlMastercategory")))
            master_cat_options = self._get_options(driver, "ContentPlaceHolder1_ddlMastercategory")
            agency_options = self._get_options(driver, "ContentPlaceHolder1_ddlExeAgency")
            self.app.after(0, self._update_ui_after_load, master_cat_options, agency_options)
        except Exception as e:
            error_message = str(e).splitlines()[0]
            self.app.after(0, lambda msg=error_message: messagebox.showerror("Error", f"Failed to load categories from website: {msg}"))
        finally:
            self.app.after(0, lambda: self.load_button.configure(state="normal", text="Load Categories from Website"))

    def _update_ui_after_load(self, master_cat_options, agency_options):
        self.ui_fields['master_category'].configure(values=master_cat_options, state="normal")
        self.ui_fields['executing_agency'].configure(values=agency_options, state="normal")
        for key in ["proposal_date", "start_date", "est_labour_cost", "est_material_cost"]:
            if key in self.ui_fields: self.ui_fields[key].configure(state="normal")
        self.app.log_message(self.log_display, "Categories loaded. Restoring saved selections...")
        saved_master_cat = self.saved_config.get('master_category')
        if saved_master_cat and saved_master_cat in master_cat_options:
            self.ui_fields['master_category'].set(saved_master_cat)
            self._on_dropdown_select('master_category', saved_master_cat)
        saved_agency = self.saved_config.get('executing_agency')
        if saved_agency and saved_agency in agency_options: self.ui_fields['executing_agency'].set(saved_agency)

    def _on_dropdown_select(self, dropdown_key, selection):
        if not selection: return
        self.app.log_message(self.log_display, f"Selected {dropdown_key}: '{selection}'. Fetching next options...")
        threading.Thread(target=self._update_dependent_dropdown, args=(dropdown_key, selection), daemon=True).start()
    
    def _update_dependent_dropdown(self, dropdown_key, selection):
        dependency_map = {'master_category':{'next':'work_category','id':'ContentPlaceHolder1_ddlMastercategory','next_id':'ContentPlaceHolder1_ddlproposed_work_category'},'work_category':{'next':'beneficiary_type','id':'ContentPlaceHolder1_ddlproposed_work_category','next_id':'ContentPlaceHolder1_ddlbeneficiary_type'},'beneficiary_type':{'next':'activity_type','id':'ContentPlaceHolder1_ddlbeneficiary_type','next_id':'ContentPlaceHolder1_ddlactivity_type'},'activity_type':{'next':'work_type','id':'ContentPlaceHolder1_ddlactivity_type','next_id':'ContentPlaceHolder1_ddlproposed_work_type'},'work_type':{'next':'pro_status','id':'ContentPlaceHolder1_ddlproposed_work_type','next_id':'ContentPlaceHolder1_ddlprostatus'}}
        if dropdown_key not in dependency_map: return
        current = dependency_map[dropdown_key]
        try:
            driver = self.app.get_driver();
            if not driver: self.app.after(0, lambda: self.app.log_message(self.log_display, "Browser not available for dropdown update.", "warning")); return
            wait = WebDriverWait(driver, 20)
            select_element = wait.until(EC.element_to_be_clickable((By.ID, current['id']))); body = driver.find_element(By.TAG_NAME, 'body')
            Select(select_element).select_by_visible_text(selection); wait.until(EC.staleness_of(body))
            wait.until(EC.element_to_be_clickable((By.ID, current['next_id'])))
            new_options = self._get_options(driver, current['next_id'])
            self.app.after(0, self._update_next_combobox, current['next'], new_options, list(dependency_map.keys()))
        except Exception as e:
            error_message = str(e).splitlines()[0]
            self.app.after(0, lambda msg=error_message: self.app.log_message(self.log_display, f"Error updating dropdown: {msg}", "error"))

    def _update_next_combobox(self, next_key, options, all_keys):
        self.ui_fields[next_key].configure(values=options, state="normal")
        saved_value = self.saved_config.get(next_key); current_selection = ""
        if saved_value and saved_value in options: self.ui_fields[next_key].set(saved_value); current_selection = saved_value
        else:
            current_selection = options[0] if options else ""; self.ui_fields[next_key].set(current_selection)
        if current_selection: self._on_dropdown_select(next_key, current_selection)
        start_resetting = False
        for key in all_keys:
            if start_resetting:
                if isinstance(self.ui_fields[key], ctk.CTkComboBox): self.ui_fields[key].configure(values=[], state="disabled"); self.ui_fields[key].set("")
            if key == next_key: start_resetting = True
    
    def _get_options(self, driver, element_id):
        select_element = Select(driver.find_element(By.ID, element_id))
        return [option.text for option in select_element.options if option.get_attribute("value") not in ["00", "0"]]

    def _process_single_row(self, driver, form_config, row_data):
        try:
            (priority, work_name, khata_no, plot_no, village_name, total_plants, covered_area, area_plantation, total_saplings) = row_data
        except ValueError: self.app.log_message(self.log_display, "ERROR: CSV row has incorrect number of columns. Expected 9.", "error"); return
        driver.get(config.WC_GEN_CONFIG["url"]); wait = WebDriverWait(driver, 25)
        def select_and_wait(element_id, value):
            self.app.log_message(self.log_display, f"  > Selecting '{value}'..."); html_element = driver.find_element(By.TAG_NAME, 'html')
            Select(wait.until(EC.element_to_be_clickable((By.ID, element_id)))).select_by_visible_text(value)
            wait.until(EC.staleness_of(html_element)); self.app.log_message(self.log_display, f"  > OK.")
        self.app.log_message(self.log_display, "Step 1: Selecting Categories...")
        select_and_wait("ContentPlaceHolder1_ddlMastercategory", form_config['master_category'])
        select_and_wait("ContentPlaceHolder1_ddlproposed_work_category", form_config['work_category'])
        select_and_wait("ContentPlaceHolder1_ddlbeneficiary_type", form_config['beneficiary_type'])
        select_and_wait("ContentPlaceHolder1_ddlactivity_type", form_config['activity_type'])
        select_and_wait("ContentPlaceHolder1_ddlproposed_work_type", form_config['work_type'])
        select_and_wait("ContentPlaceHolder1_ddlprostatus", form_config['pro_status'])
        self.app.log_message(self.log_display, "Step 2: Filling Dynamic Plantation/Area Fields...")
        dynamic_fields = {"ContentPlaceHolder1_txtdist": total_plants, "ContentPlaceHolder1_txtAdd_dis": covered_area,"ContentPlaceHolder1_txtEst_output": area_plantation, "ContentPlaceHolder1_txtJSA_Inst_unit": total_saplings}
        for field_id, value in dynamic_fields.items():
            if value.strip(): 
                try:
                    field = wait.until(EC.presence_of_element_located((By.ID, field_id))); field.clear(); field.send_keys(value)
                except (NoSuchElementException, TimeoutException): pass 
        self.app.log_message(self.log_display, "Step 3: Selecting Location...")
        select_and_wait("ContentPlaceHolder1_ddlpanch", form_config['panchayat_name'])
        Select(wait.until(EC.element_to_be_clickable((By.ID, "ContentPlaceHolder1_ddlvillage")))).select_by_visible_text(village_name)
        self.app.log_message(self.log_display, "Step 4: Filling Final Details...")
        Select(wait.until(EC.element_to_be_clickable((By.ID, "ContentPlaceHolder1_ddlridgetype")))).select_by_value(config.WC_GEN_CONFIG["defaults"]["ridge_type"])
        driver.find_element(By.ID, "ContentPlaceHolder1_txtPriority").send_keys(priority)
        driver.find_element(By.ID, "ContentPlaceHolder1_txtPropDate").send_keys(form_config['proposal_date'])
        driver.find_element(By.ID, "ContentPlaceHolder1_txtstartdate").send_keys(form_config['start_date'])
        driver.find_element(By.ID, "ContentPlaceHolder1_TxtEstlb").send_keys(form_config['est_labour_cost'])
        driver.find_element(By.ID, "ContentPlaceHolder1_txtEstMat").send_keys(form_config['est_material_cost'])
        driver.find_element(By.ID, "ContentPlaceHolder1_txtkhtano").send_keys(khata_no)
        driver.find_element(By.ID, "ContentPlaceHolder1_txtPlotNo").send_keys(plot_no)
        work_name_field = driver.find_element(By.ID, "ContentPlaceHolder1_txtworkname")
        pyperclip.copy(work_name); paste_key = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL
        work_name_field.send_keys(paste_key, 'v'); time.sleep(0.5)
        self.app.log_message(self.log_display, "Step 5: Selecting Agency and Saving...")
        Select(wait.until(EC.element_to_be_clickable((By.ID, "ContentPlaceHolder1_ddlExeAgency")))).select_by_visible_text(form_config['executing_agency'])
        driver.find_element(By.ID, "ContentPlaceHolder1_btSave").click()
        try:
            wait.until(EC.url_contains("ifedit.aspx?work_code="))
            final_url = driver.current_url; parsed_url = urlparse(final_url)
            work_code = parse_qs(parsed_url.query).get('work_code', [None])[0]
            if work_code: self.app.log_message(self.log_display, f"SUCCESS! Generated Work Code: {work_code}", "success"); self._log_result(work_code)
            else: self.app.log_message(self.log_display, "Row submitted, but could not extract work code from URL.", "warning")
        except TimeoutException: self.app.log_message(self.log_display, "Row submitted, but URL did not change to the success page.", "warning")
        
    def start_automation(self):
        if not self.csv_path: messagebox.showwarning("Missing File", "Please select a CSV data file first."); return
        form_config = {key: field.get() for key, field in self.ui_fields.items()}
        form_config["panchayat_name"] = self.panchayat_entry.get().strip()
        required_fields = ["panchayat_name", "master_category", "work_category", "beneficiary_type", "activity_type", "work_type", "pro_status", "executing_agency", "proposal_date", "start_date", "est_labour_cost", "est_material_cost"]
        if any(not form_config.get(key) for key in required_fields):
            messagebox.showwarning("Input Error", "Please load categories and ensure all configuration fields are filled."); return
        self._save_profile(profile_name="Last Used Config", is_autosave=True)
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic, args=(form_config,))
        
    def run_automation_logic(self, form_config):
        self.app.after(0, self.set_ui_state, True); self.app.clear_log(self.log_display)
        for item in self.results_tree.get_children(): self.results_tree.delete(item)
        self.app.log_message(self.log_display, "--- Starting Workcode Generation ---")
        try:
            driver = self.app.get_driver();
            if not driver: return
            with open(self.csv_path, mode='r', encoding='utf-8') as csvfile:
                rows = list(csv.reader(csvfile))[1:]
                total = len(rows)
                for i, row in enumerate(rows):
                    if self.app.stop_events[self.automation_key].is_set(): self.app.log_message(self.log_display, "Automation stopped by user."); break
                    if not any(field.strip() for field in row): continue
                    self.app.log_message(self.log_display, f"--- Processing Row {i+1}/{total} ---")
                    try: self._process_single_row(driver, form_config, row)
                    except Exception as e: self.app.log_message(self.log_display, f"ERROR processing row {i+1}: {e}", "error")
        except FileNotFoundError: self.app.log_message(self.log_display, "ERROR: CSV file not found.", "error")
        except Exception as e: self.app.log_message(self.log_display, f"An unexpected error occurred: {e}", "error")
        finally:
            self.app.after(0, self.set_ui_state, False)
            self.app.log_message(self.log_display, "\n--- Automation Finished ---")
            messagebox.showinfo("Complete", "Workcode generation process has finished.")
            
    def select_csv_file(self):
        path = filedialog.askopenfilename(title="Select your CSV data file", filetypes=[("CSV files", "*.csv")])
        if path: self.csv_path = path; self.file_label.configure(text=os.path.basename(path))
        
    def set_ui_state(self, running: bool):
        state = "disabled" if running else "normal"
        self.start_button.configure(state=state); self.stop_button.configure(state="normal" if running else "disabled"); self.reset_button.configure(state=state)
        self.select_button.configure(state=state); self.panchayat_entry.configure(state=state); self.load_button.configure(state=state)
        self.save_profile_button.configure(state=state); self.delete_profile_button.configure(state=state); self.profile_combobox.configure(state=state)
        if hasattr(self, 'copy_logs_button'): self.copy_logs_button.configure(state=state)
        if running:
            for field in self.ui_fields.values(): field.configure(state="disabled")
        else:
            for field in self.ui_fields.values():
                if field.winfo_exists(): field.configure(state="normal")
            if self.ui_fields['master_category'].get():
                self._on_dropdown_select('master_category', self.ui_fields['master_category'].get())

    def reset_ui(self):
        if messagebox.askokcancel("Reset Form?", "Are you sure?"):
            self.panchayat_entry.delete(0, tkinter.END)
            self.file_label.configure(text="No file selected"); self.csv_path = None
            self.app.clear_log(self.log_display)
            for key, field in self.ui_fields.items():
                if isinstance(field, ctk.CTkComboBox): field.configure(values=[], state="disabled"); field.set("")
                elif isinstance(field, (ctk.CTkEntry, DateEntry)): field.configure(state="disabled")
            self._populate_defaults()
            self.app.log_message(self.log_display, "Form has been reset.")