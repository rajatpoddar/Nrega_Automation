# tabs/mb_entry_tab.py
import tkinter
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import time, os, json, sys, subprocess
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, NoSuchElementException, TimeoutException
import config
from .base_tab import BaseAutomationTab
from .autocomplete_widget import AutocompleteEntry

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
        
        self.panchayat_entry = self._create_autocomplete_field(config_frame, "panchayat_name", "Panchayat Name", 0, 0)
        self.mb_no_entry = self._create_field(config_frame, "measurement_book_no", "MB No.", 1, 0)
        self.page_no_entry = self._create_field(config_frame, "page_no", "Page No.", 1, 2)
        self.meas_date_entry = self._create_field(config_frame, "measurement_date", "Meas. Date", 2, 0)
        self.unit_cost_entry = self._create_field(config_frame, "unit_cost", "Unit Cost (₹)", 2, 2)
        self.mate_name_entry = self._create_autocomplete_field(config_frame, "mate_name", "Mate Name", 3, 0)
        self.pit_count_entry = self._create_field(config_frame, "default_pit_count", "Pit Count", 3, 2)
        self.je_name_entry = self._create_autocomplete_field(config_frame, "je_name", "JE Name", 4, 0)
        self.je_desig_entry = self._create_autocomplete_field(config_frame, "je_designation", "JE Desig.", 4, 2)

        note = ctk.CTkLabel(config_frame, text="ℹ️ Note: Use this emb automation only for single activity works.", text_color="#E53E3E", wraplength=450)
        note.grid(row=5, column=0, columnspan=4, sticky='w', padx=15, pady=(10, 15))

        action_frame_container = ctk.CTkFrame(top_frame)
        action_frame_container.pack(pady=10, fill='x')
        action_frame = self._create_action_buttons(parent_frame=action_frame_container)
        action_frame.pack(expand=True, fill='x')
        
        notebook = ctk.CTkTabview(self)
        notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10))
        work_codes_frame = notebook.add("Work Codes"); results_frame = notebook.add("Results")
        self._create_log_and_status_area(parent_notebook=notebook)

        work_codes_frame.grid_columnconfigure(0, weight=1); work_codes_frame.grid_rowconfigure(1, weight=1)
        wc_controls_frame = ctk.CTkFrame(work_codes_frame, fg_color="transparent")
        wc_controls_frame.grid(row=0, column=0, sticky='ew')
        clear_button = ctk.CTkButton(wc_controls_frame, text="Clear", width=80, command=lambda: self.work_codes_text.delete("1.0", tkinter.END))
        clear_button.pack(side='right', pady=(5,0), padx=(0,5))
        self.work_codes_text = ctk.CTkTextbox(work_codes_frame, wrap=tkinter.WORD)
        self.work_codes_text.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)

        results_frame.grid_columnconfigure(0, weight=1); results_frame.grid_rowconfigure(1, weight=1)
        results_action_frame = ctk.CTkFrame(results_frame, fg_color="transparent")
        results_action_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(5, 10), padx=5)
        
        export_controls_frame = ctk.CTkFrame(results_action_frame, fg_color="transparent")
        export_controls_frame.pack(side='right', padx=(10, 0))
        self.export_button = ctk.CTkButton(export_controls_frame, text="Export Report", command=self.export_report)
        self.export_button.pack(side='left')
        self.export_format_menu = ctk.CTkOptionMenu(export_controls_frame, width=130, values=["Image (.jpg)", "PDF (.pdf)", "CSV (.csv)"], command=self._on_format_change)
        self.export_format_menu.pack(side='left', padx=5)
        self.export_filter_menu = ctk.CTkOptionMenu(export_controls_frame, width=150, values=["Export All", "Success Only", "Failed Only"])
        self.export_filter_menu.pack(side='left', padx=(0, 5))

        cols = ("Work Code", "Status", "Details", "Timestamp")
        self.results_tree = ttk.Treeview(results_frame, columns=cols, show='headings')
        for col in cols: self.results_tree.heading(col, text=col)
        self.results_tree.column("Work Code", width=200); self.results_tree.column("Status", width=100, anchor='center'); self.results_tree.column("Details", width=350); self.results_tree.column("Timestamp", width=100, anchor='center')
        self.results_tree.grid(row=1, column=0, sticky='nsew')
        scrollbar = ctk.CTkScrollbar(results_frame, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set); scrollbar.grid(row=1, column=1, sticky='ns')
        self.style_treeview(self.results_tree); self._setup_treeview_sorting(self.results_tree)
    
    def _on_format_change(self, selected_format):
        if "CSV" in selected_format: self.export_filter_menu.configure(state="disabled")
        else: self.export_filter_menu.configure(state="normal")

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
        for key, var in self.config_vars.items():
            entry_widget = self.nametowidget(var.get().lower()) # This is not reliable, direct is better
        self.panchayat_entry.configure(state=state); self.mb_no_entry.configure(state=state); self.page_no_entry.configure(state=state)
        self.meas_date_entry.configure(state=state); self.unit_cost_entry.configure(state=state); self.mate_name_entry.configure(state=state)
        self.pit_count_entry.configure(state=state); self.je_name_entry.configure(state=state); self.je_desig_entry.configure(state=state)
        self.export_button.configure(state=state); self.export_format_menu.configure(state=state); self.export_filter_menu.configure(state=state)
        if state == "normal": self._on_format_change(self.export_format_menu.get())

    def reset_ui(self):
        if messagebox.askokcancel("Reset Form?", "Clear all inputs and logs?"):
            self._load_inputs()
            for key in ['panchayat_name']: self.config_vars[key].set("")
            self.config_vars['measurement_date'].set(datetime.now().strftime('%d/%m/%Y'))
            self.work_codes_text.configure(state="normal"); self.work_codes_text.delete("1.0", tkinter.END)
            for item in self.results_tree.get_children(): self.results_tree.delete(item)
            self.app.clear_log(self.log_display); self.update_status("Ready", 0.0)
            self.app.log_message(self.log_display, "Form has been reset.")
            self.app.after(0, self.app.set_status, "Ready")

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
        self.app.after(0, self.set_ui_state, True); self.app.clear_log(self.log_display)
        self.app.after(0, lambda: [self.results_tree.delete(item) for item in self.results_tree.get_children()])
        self.app.log_message(self.log_display, "Starting MB Entry automation...")
        self.app.after(0, self.app.set_status, "Running eMB Entry...")
        try:
            driver = self.app.get_driver()
            if not driver: return
            if not self.app.stop_events[self.automation_key].is_set():
                for key, value in cfg.items():
                    if key != "measurement_date": self.app.update_history(key, value)
            processed_codes = set()
            total = len(work_codes_raw)
            for i, work_code in enumerate(work_codes_raw):
                if self.app.stop_events[self.automation_key].is_set(): self.app.log_message(self.log_display, "Automation stopped.", "warning"); break
                self.app.after(0, self.update_status, f"Processing {i+1}/{total}: {work_code}", (i+1) / total)
                if work_code in processed_codes: self._log_result(work_code, "Skipped", "Duplicate entry."); continue
                self._process_single_work_code(driver, work_code, cfg)
                processed_codes.add(work_code)
            final_msg = "Automation finished." if not self.app.stop_events[self.automation_key].is_set() else "Stopped."
            self.app.after(0, self.update_status, final_msg, 1.0)
            if not self.app.stop_events[self.automation_key].is_set(): messagebox.showinfo("Complete", "e-MB Entry process has finished.")
        except Exception as e:
            self.app.log_message(self.log_display, f"A critical error occurred: {e}", "error")
            messagebox.showerror("Automation Error", f"An error occurred:\n\n{e}")
        finally:
            self.app.after(0, self.set_ui_state, False)
            self.app.after(0, self.app.set_status, "Automation Finished")

    def _log_result(self, work_code, status, details):
        timestamp = datetime.now().strftime("%H:%M:%S")
        tags = ('failed',) if 'success' not in status.lower() else ()
        self.app.after(0, lambda: self.results_tree.insert("", "end", values=(work_code, status, details, timestamp), tags=tags))

    def _process_single_work_code(self, driver, work_code, cfg):
        wait = WebDriverWait(driver, 20)
        try:
            driver.get(config.MB_ENTRY_CONFIG["url"])
            try:
                panchayat_dropdown = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_ddl_panch')))
                page_body = driver.find_element(By.TAG_NAME, 'body')
                self.app.log_message(self.log_display, f"Selecting Panchayat '{cfg['panchayat_name']}'...")
                Select(panchayat_dropdown).select_by_visible_text(cfg['panchayat_name'])
                wait.until(EC.staleness_of(page_body))
            except (TimeoutException, NoSuchElementException): self.app.log_message(self.log_display, "Panchayat dropdown not needed.", "info")

            wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_txtMBNo'))).send_keys(cfg["measurement_book_no"])
            driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtpageno').send_keys(cfg["page_no"])
            driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtMDate').send_keys(cfg["measurement_date"])
            driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtWrkCode').send_keys(work_code)
            driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_imgButtonSearch').click()
            wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_ddlSelWrk'))); time.sleep(1)
            select_work = Select(driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_ddlSelWrk'))
            if len(select_work.options) <= 1: raise ValueError("Work code not found/processed.")
            select_work.select_by_index(1)
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_rddist_0").click()
            time.sleep(2)
            period_dropdown = Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlSelMPeriod"))
            if len(period_dropdown.options) <= 1: raise ValueError("No measurement period found.")
            period_dropdown.select_by_index(1)
            total_persondays_str = driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_lbl_person_days').get_attribute('value').strip()
            total_persondays = int(total_persondays_str) if total_persondays_str else 0
            if total_persondays == 0: raise ValueError("eMB already Booked")

            prefix = self._find_activity_prefix(driver)
            driver.find_element(By.NAME, f'{prefix}$qty').send_keys(str(total_persondays))
            driver.find_element(By.NAME, f'{prefix}$unitcost').send_keys(cfg["unit_cost"])
            driver.find_element(By.NAME, f'{prefix}$labcomp').send_keys(str(total_persondays * int(cfg["unit_cost"])))
            try: driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtpit").send_keys(cfg["default_pit_count"])
            except NoSuchElementException: pass
            driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txt_mat_name').send_keys(cfg["mate_name"])
            driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txt_eng_name').send_keys(cfg["je_name"])
            driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txt_eng_desig').send_keys(cfg["je_designation"])
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);"); time.sleep(0.5)
            driver.find_element(By.XPATH, '//input[@value="Save"]').click()
            try:
                alert = WebDriverWait(driver, 5).until(EC.alert_is_present())
                self._log_result(work_code, "Success", alert.text); alert.accept()
            except TimeoutException: self._log_result(work_code, "Success", "Saved (No confirmation alert).")
        except UnexpectedAlertPresentException:
            try:
                alert = driver.switch_to.alert; self._log_result(work_code, "Failed", f"Unexpected Alert: {alert.text}"); alert.accept()
            except: pass
        except ValueError as e:
            error_message = str(e)
            if "No measurement period found" in error_message: self._log_result(work_code, "Failed", "MR Not Filled Yet")
            elif "eMB already Booked" in error_message: self._log_result(work_code, "Failed", "eMB already Booked.")
            else: self._log_result(work_code, "Failed", f"{type(e).__name__}: {error_message.splitlines()[0]}")
        except NoSuchElementException: self._log_result(work_code, "Failed", "Add Activity for PMAYG/ IAY Houses")
        except Exception as e: self._log_result(work_code, "Failed", f"{type(e).__name__}: {str(e).splitlines()[0]}")
            
    def _find_activity_prefix(self, driver):
        self.app.log_message(self.log_display, "Searching for 'Earth work' activity...")
        for i in range(1, 61):
            try:
                activity_id = f"ctl00_ContentPlaceHolder1_activity_ctl{str(i).zfill(2)}_act_name"
                if "earth work" in driver.find_element(By.ID, activity_id).text.lower():
                    self.app.log_message(self.log_display, f"✅ Found 'Earth work' in row #{i}.", "success"); return f"ctl00$ContentPlaceHolder1$activity$ctl{str(i).zfill(2)}"
            except NoSuchElementException: continue
        self.app.log_message(self.log_display, "⚠️ 'Earth work' not found, defaulting to first row.", "warning"); return "ctl00$ContentPlaceHolder1$activity$ctl01"
    
    def export_report(self):
        export_format = self.export_format_menu.get()
        if "CSV" in export_format:
            self.export_treeview_to_csv(self.results_tree, "mb_entry_results.csv"); return
        data, file_path = self._get_filtered_data_and_filepath(export_format)
        if not data: return
        if "Image" in export_format: self._handle_image_export(data, file_path)
        elif "PDF" in export_format: self._handle_pdf_export(data, file_path)

    def _get_filtered_data_and_filepath(self, export_format):
        all_items = self.results_tree.get_children()
        if not all_items: messagebox.showinfo("No Data", "There are no results to export."); return None, None
        panchayat_name = self.panchayat_entry.get().strip()
        if not panchayat_name: messagebox.showwarning("Input Needed", "Please enter a Panchayat Name for the report title."); return None, None
        filter_option = self.export_filter_menu.get()
        data_to_export = []
        for item_id in all_items:
            row_values = self.results_tree.item(item_id)['values']
            status = row_values[1].upper()
            if filter_option == "Export All": data_to_export.append(row_values)
            elif filter_option == "Success Only" and "SUCCESS" in status: data_to_export.append(row_values)
            elif filter_option == "Failed Only" and "SUCCESS" not in status: data_to_export.append(row_values)
        if not data_to_export: messagebox.showinfo("No Data", f"No records found for filter '{filter_option}'."); return None, None

        safe_name = "".join(c for c in panchayat_name if c.isalnum() or c in (' ', '_')).rstrip()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_details = {"Image (.jpg)": { "ext": ".jpg", "types": [("JPEG Image", "*.jpg")]}, "PDF (.pdf)": { "ext": ".pdf", "types": [("PDF Document", "*.pdf")]}}
        details = file_details[export_format]
        filename = f"eMB_Entry_Report_{safe_name}_{timestamp}{details['ext']}"
        file_path = filedialog.asksaveasfilename(defaultextension=details['ext'], filetypes=details['types'], initialdir=self.app.get_user_downloads_path(), initialfile=filename, title="Save Report")
        return (data_to_export, file_path) if file_path else (None, None)

    def _handle_image_export(self, data, file_path):
        headers = self.results_tree['columns']
        title = f"eMB Entry Report: {self.panchayat_entry.get().strip()}"
        report_date = datetime.now().strftime('%d %b %Y')
        footer = "Report Generated by NREGA Bot"
        success = self.generate_report_image(data, headers, title, report_date, footer, file_path)
        if success:
            if messagebox.askyesno("Success", f"Image Report saved to:\n{file_path}\n\nDo you want to open it?"):
                if sys.platform == "win32": os.startfile(file_path)
                else: subprocess.call(['open', file_path])
    
    def _handle_pdf_export(self, data, file_path):
        headers = self.results_tree['columns']
        col_widths = [70, 45, 130, 25]
        title = f"eMB Entry Report: {self.panchayat_entry.get().strip()}"
        report_date = datetime.now().strftime('%d %b %Y')
        success = self.generate_report_pdf(data, headers, col_widths, title, report_date, file_path)
        if success:
            if messagebox.askyesno("Success", f"PDF Report saved to:\n{file_path}\n\nDo you want to open it?"):
                if sys.platform == "win32": os.startfile(file_path)
                else: subprocess.call(['open', file_path])