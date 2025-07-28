# tabs/mb_entry_tab.py (Updated with Autocomplete)
import tkinter
from tkinter import ttk, messagebox
import customtkinter as ctk
import time, os, json
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, NoSuchElementException, TimeoutException
import config
from .base_tab import BaseAutomationTab
from .autocomplete_widget import AutocompleteEntry # Import the new widget

class MbEntryTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="mb_entry")
        self.config_file = self.app.get_data_path("mb_entry_inputs.json")
        self.config_vars = {}
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)
        self._create_widgets(); self._load_inputs()

    def _create_widgets(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.grid(row=0, column=0, sticky='ew', padx=10, pady=(10,0))
        
        config_frame = ctk.CTkFrame(top_frame)
        config_frame.pack(pady=(0, 10), fill='x')
        config_frame.grid_columnconfigure((1, 3), weight=1)
        
        # Define fields to create, now using AutocompleteEntry where appropriate
        self.panchayat_entry = self._create_autocomplete_field(config_frame, "panchayat_name", "Panchayat Name", 0, 0)
        self.mb_no_entry = self._create_field(config_frame, "measurement_book_no", "MB No.", 1, 0)
        self.page_no_entry = self._create_field(config_frame, "page_no", "Page No.", 1, 2)
        self.meas_date_entry = self._create_field(config_frame, "measurement_date", "Meas. Date", 2, 0)
        self.unit_cost_entry = self._create_field(config_frame, "unit_cost", "Unit Cost (₹)", 2, 2)
        self.mate_name_entry = self._create_autocomplete_field(config_frame, "mate_name", "Mate Name", 3, 0)
        self.pit_count_entry = self._create_field(config_frame, "default_pit_count", "Pit Count", 3, 2)
        self.je_name_entry = self._create_autocomplete_field(config_frame, "je_name", "JE Name", 4, 0)
        self.je_desig_entry = self._create_autocomplete_field(config_frame, "je_designation", "JE Desig.", 4, 2)

        note = ctk.CTkLabel(config_frame, text="ℹ️ Note: 'Earth work' activity is auto-filled.", text_color="gray50", wraplength=450)
        note.grid(row=5, column=0, columnspan=4, sticky='w', padx=15, pady=(10, 15))

        action_frame_container = ctk.CTkFrame(top_frame)
        action_frame_container.pack(pady=10, fill='x')
        action_frame = self._create_action_buttons(parent_frame=action_frame_container)
        action_frame.pack(expand=True, fill='x')
        
        notebook = ctk.CTkTabview(self)
        notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10))
        work_codes_frame = notebook.add("Work Codes"); results_frame = notebook.add("Results")
        self._create_log_and_status_area(parent_notebook=notebook)

        # Work Codes Tab with Clear button
        work_codes_frame.grid_columnconfigure(0, weight=1); work_codes_frame.grid_rowconfigure(1, weight=1)
        wc_controls_frame = ctk.CTkFrame(work_codes_frame, fg_color="transparent")
        wc_controls_frame.grid(row=0, column=0, sticky='ew')
        clear_button = ctk.CTkButton(wc_controls_frame, text="Clear", width=80, command=lambda: self.work_codes_text.delete("1.0", tkinter.END))
        clear_button.pack(side='right', pady=(5,0), padx=(0,5))
        self.work_codes_text = ctk.CTkTextbox(work_codes_frame, wrap=tkinter.WORD)
        self.work_codes_text.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)

        # Results Tab
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(1, weight=1) # Make space for the button

        results_action_frame = ctk.CTkFrame(results_frame, fg_color="transparent")
        results_action_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(5, 10), padx=5)
        self.export_csv_button = ctk.CTkButton(results_action_frame, text="Export to CSV", command=lambda: self.export_treeview_to_csv(self.results_tree, "mb_entry_results.csv"))
        self.export_csv_button.pack(side="left")

        cols = ("Work Code", "Status", "Details", "Timestamp")
        self.results_tree = ttk.Treeview(results_frame, columns=cols, show='headings')
        for col in cols: self.results_tree.heading(col, text=col)
        self.results_tree.column("Work Code", width=200); self.results_tree.column("Status", width=100, anchor='center'); self.results_tree.column("Details", width=350); self.results_tree.column("Timestamp", width=100, anchor='center')
        self.results_tree.grid(row=1, column=0, sticky='nsew')
        scrollbar = ctk.CTkScrollbar(results_frame, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set); scrollbar.grid(row=1, column=1, sticky='ns')
        self.style_treeview(self.results_tree)
    
    # Helper methods to create fields, reducing repetition
    def _create_field(self, parent, key, text, r, c):
        ctk.CTkLabel(parent, text=text).grid(row=r, column=c, sticky='w', padx=15, pady=5)
        var = ctk.StringVar(); self.config_vars[key] = var
        entry = ctk.CTkEntry(parent, textvariable=var)
        entry.grid(row=r, column=c+1, sticky='ew', padx=15, pady=5)
        return entry

    def _create_autocomplete_field(self, parent, key, text, r, c):
        ctk.CTkLabel(parent, text=text).grid(row=r, column=c, sticky='w', padx=15, pady=5)
        var = ctk.StringVar(); self.config_vars[key] = var
        entry = AutocompleteEntry(parent, textvariable=var, suggestions_list=self.app.history_manager.get_suggestions(key))
        entry.grid(row=r, column=c+1, columnspan=3 if key=="panchayat_name" else 1, sticky='ew', padx=15, pady=5)
        return entry


    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running)
        state = "disabled" if running else "normal"
        self.work_codes_text.configure(state=state)
        
        # A simpler, more direct way to disable the input fields
        self.panchayat_entry.configure(state=state)
        self.mb_no_entry.configure(state=state)
        self.page_no_entry.configure(state=state)
        self.meas_date_entry.configure(state=state)
        self.unit_cost_entry.configure(state=state)
        self.mate_name_entry.configure(state=state)
        self.pit_count_entry.configure(state=state)
        self.je_name_entry.configure(state=state)
        self.je_desig_entry.configure(state=state)

    # ... All other methods like start_automation, reset_ui, run_automation_logic remain unchanged ...
    def reset_ui(self):
        if messagebox.askokcancel("Reset Form?", "Clear all inputs and logs?"):
            self._load_inputs()
            for key in ['panchayat_name', 'measurement_date']: self.config_vars[key].set("")
            self.config_vars['measurement_date'].set(datetime.now().strftime('%d/%m/%Y'))
            self.work_codes_text.configure(state="normal"); self.work_codes_text.delete("1.0", tkinter.END)
            for item in self.results_tree.get_children(): self.results_tree.delete(item)
            self.app.clear_log(self.log_display)
            self.update_status("Ready", 0.0)
            self.app.log_message(self.log_display, "Form has been reset.")
    def start_automation(self):
        cfg = {key: var.get().strip() for key, var in self.config_vars.items()}
        if any(not value for value in cfg.values()): messagebox.showwarning("Input Error", "All configuration fields are required."); return
        work_codes_raw = [line.strip() for line in self.work_codes_text.get("1.0", tkinter.END).strip().splitlines() if line.strip()]
        if not work_codes_raw: messagebox.showwarning("Input Required", "Please paste at least one work code."); return
        self._save_inputs(cfg)
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic, args=(cfg, work_codes_raw))
    def _save_inputs(self, cfg):
        try:
            with open(self.config_file, 'w') as f: json.dump(cfg, f, indent=4)
        except Exception as e: self.app.log_message(self.log_display, f"Could not save inputs: {e}", "warning")
    def _load_inputs(self):
        saved_data = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f: saved_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e: self.app.log_message(self.log_display, f"Could not load inputs: {e}", "warning")
        for key, var in self.config_vars.items():
            default_value = config.MB_ENTRY_CONFIG["defaults"].get(key, "")
            var.set(saved_data.get(key, default_value))
        if not self.config_vars['measurement_date'].get(): self.config_vars['measurement_date'].set(datetime.now().strftime('%d/%m/%Y'))
    def run_automation_logic(self, cfg, work_codes_raw):
        self.app.after(0, self.set_ui_state, True)
        self.app.clear_log(self.log_display)
        self.app.after(0, lambda: [self.results_tree.delete(item) for item in self.results_tree.get_children()])
        self.app.log_message(self.log_display, "Starting MB Entry automation...")
        try:
            driver = self.app.get_driver()
            if not driver: return
            
            # Save all successful config inputs to history once
            if not self.app.stop_events[self.automation_key].is_set():
                for key, value in cfg.items():
                    if key != "measurement_date": # Don't save the date
                        self.app.update_history(key, value)
            
            processed_codes = set()
            total = len(work_codes_raw)
            for i, work_code in enumerate(work_codes_raw):
                if self.app.stop_events[self.automation_key].is_set():
                    self.app.log_message(self.log_display, "Automation stopped.", "warning"); break
                self.app.after(0, self.update_status, f"Processing {i+1}/{total}: {work_code}", (i+1) / total)
                if work_code in processed_codes:
                    self._log_result(work_code, "Skipped", "Duplicate entry."); continue
                self._process_single_work_code(driver, work_code, cfg)
                processed_codes.add(work_code)
            final_msg = "Automation finished." if not self.app.stop_events[self.automation_key].is_set() else "Stopped."
            self.app.after(0, self.update_status, final_msg, 1.0)
            if not self.app.stop_events[self.automation_key].is_set():
                messagebox.showinfo("Complete", "e-MB Entry process has finished.")
        except Exception as e:
            self.app.log_message(self.log_display, f"A critical error occurred: {e}", "error")
            messagebox.showerror("Automation Error", f"An error occurred:\n\n{e}")
        finally:
            self.app.after(0, self.set_ui_state, False)

    def _log_result(self, work_code, status, details):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.app.after(0, lambda: self.results_tree.insert("", "end", values=(work_code, status, details, timestamp)))
    def _process_single_work_code(self, driver, work_code, cfg):
        wait = WebDriverWait(driver, 20)
        try:
            driver.get(config.MB_ENTRY_CONFIG["url"])

            # Attempt to select Panchayat if the dropdown exists
            try:
                panchayat_dropdown = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_ddl_panch')))
                page_body = driver.find_element(By.TAG_NAME, 'body')
                self.app.log_message(self.log_display, f"Selecting Panchayat '{cfg['panchayat_name']}'...")
                Select(panchayat_dropdown).select_by_visible_text(cfg['panchayat_name'])
                wait.until(EC.staleness_of(page_body))
            except (TimeoutException, NoSuchElementException):
                self.app.log_message(self.log_display, "Panchayat dropdown not needed.", "info")

            # Fill in the main details
            wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_txtMBNo'))).send_keys(cfg["measurement_book_no"])
            driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtpageno').send_keys(cfg["page_no"])
            driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtMDate').send_keys(cfg["measurement_date"])
            driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtWrkCode').send_keys(work_code)
            driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_imgButtonSearch').click()
            wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_ddlSelWrk')))
            time.sleep(1)

            # Select the work from the dropdown
            select_work = Select(driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_ddlSelWrk'))
            if len(select_work.options) <= 1:
                raise ValueError("Work code not found/processed.")
            select_work.select_by_index(1)

            # Select the measurement period
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_rddist_0").click()
            time.sleep(2) # Wait for period to load
            period_dropdown = Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlSelMPeriod"))
            if len(period_dropdown.options) <= 1:
                raise ValueError("No measurement period found.")
            period_dropdown.select_by_index(1)

            # --- NEW: Check if Persondays is zero ---
            total_persondays_str = driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_lbl_person_days').get_attribute('value').strip()
            total_persondays = int(total_persondays_str) if total_persondays_str else 0
            if total_persondays == 0:
                raise ValueError("eMB already Booked")

            # Find and fill the activity details
            prefix = self._find_activity_prefix(driver)
            driver.find_element(By.NAME, f'{prefix}$qty').send_keys(str(total_persondays))
            driver.find_element(By.NAME, f'{prefix}$unitcost').send_keys(cfg["unit_cost"])
            driver.find_element(By.NAME, f'{prefix}$labcomp').send_keys(str(total_persondays * int(cfg["unit_cost"])))

            # Fill optional pit count
            try:
                driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtpit").send_keys(cfg["default_pit_count"])
            except NoSuchElementException:
                pass # Pit count field is not always present

            # Fill Mate and JE details
            driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txt_mat_name').send_keys(cfg["mate_name"])
            driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txt_eng_name').send_keys(cfg["je_name"])
            driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txt_eng_desig').send_keys(cfg["je_designation"])

            # Save and handle confirmation
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
            driver.find_element(By.XPATH, '//input[@value="Save"]').click()

            try:
                alert = WebDriverWait(driver, 5).until(EC.alert_is_present())
                self._log_result(work_code, "Success", alert.text)
                alert.accept()
            except TimeoutException:
                self._log_result(work_code, "Success", "Saved (No confirmation alert).")

        except UnexpectedAlertPresentException:
            try:
                alert = driver.switch_to.alert
                self._log_result(work_code, "Failed", f"Unexpected Alert: {alert.text}")
                alert.accept()
            except:
                pass
        # --- Enhanced Error Handling ---
        except ValueError as e:
            error_message = str(e)
            if "No measurement period found" in error_message:
                self._log_result(work_code, "Failed", "MR Not Filled Yet")
            elif "eMB already Booked" in error_message:
                self._log_result(work_code, "Failed", "eMB already Booked.")
            else:
                self._log_result(work_code, "Failed", f"{type(e).__name__}: {error_message.splitlines()[0]}")
        except NoSuchElementException:
             # This error typically occurs when the activity grid is missing.
            self._log_result(work_code, "Failed", "Add Activity for PMAYG/ IAY Houses")
        except Exception as e:
            self._log_result(work_code, "Failed", f"{type(e).__name__}: {str(e).splitlines()[0]}")
            
    def _find_activity_prefix(self, driver):
        self.app.log_message(self.log_display, "Searching for 'Earth work' activity...")
        for i in range(1, 61):
            try:
                activity_id = f"ctl00_ContentPlaceHolder1_activity_ctl{str(i).zfill(2)}_act_name"
                if "earth work" in driver.find_element(By.ID, activity_id).text.lower():
                    self.app.log_message(self.log_display, f"✅ Found 'Earth work' in row #{i}.", "success"); return f"ctl00$ContentPlaceHolder1$activity$ctl{str(i).zfill(2)}"
            except NoSuchElementException: continue
        self.app.log_message(self.log_display, "⚠️ 'Earth work' not found, defaulting to first row.", "warning"); return "ctl00$ContentPlaceHolder1$activity$ctl01"