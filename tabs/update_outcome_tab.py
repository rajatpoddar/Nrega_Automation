# tabs/update_outcome_tab.py
import tkinter
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import config
from .base_tab import BaseAutomationTab
from .autocomplete_widget import AutocompleteEntry
from .date_entry_widget import DateEntry

class UpdateOutcomeTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="update_outcome")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._create_widgets()

    def _create_widgets(self):
        # --- Top Frame for Configuration ---
        config_frame = ctk.CTkFrame(self)
        config_frame.grid(row=0, column=0, sticky='ew', padx=10, pady=10)
        config_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(config_frame, text="Panchayat Name:").grid(row=0, column=0, sticky='w', padx=15, pady=5)
        self.panchayat_entry = AutocompleteEntry(config_frame, placeholder_text="Enter Panchayat name as on website")
        self.panchayat_entry.grid(row=0, column=1, sticky='ew', padx=15, pady=5)
        
        ctk.CTkLabel(config_frame, text="Completion Date:").grid(row=1, column=0, sticky='w', padx=15, pady=5)
        self.completion_date_entry = DateEntry(config_frame)
        self.completion_date_entry.grid(row=1, column=1, sticky='ew', padx=15, pady=5)

        # Action buttons
        action_frame = self._create_action_buttons(parent_frame=self)
        action_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0,10))

        # --- Bottom Frame for Data Tabs ---
        notebook = ctk.CTkTabview(self)
        notebook.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        work_codes_tab = notebook.add("Work Codes")
        results_tab = notebook.add("Results")
        self._create_log_and_status_area(parent_notebook=notebook)
        
        # --- Work Codes Tab Content ---
        work_codes_tab.grid_columnconfigure(0, weight=1)
        work_codes_tab.grid_rowconfigure(1, weight=1)
        
        wc_header_frame = ctk.CTkFrame(work_codes_tab, fg_color="transparent")
        wc_header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(5,0))
        
        ctk.CTkLabel(wc_header_frame, text="Enter Work Codes (one per line).").pack(side="left", padx=5)
        
        # --- NEW: Clear Button ---
        clear_wc_button = ctk.CTkButton(wc_header_frame, text="Clear", width=80, command=lambda: self.work_codes_text.delete("1.0", "end"))
        clear_wc_button.pack(side="right")
        
        self.work_codes_text = ctk.CTkTextbox(work_codes_tab, height=150)
        self.work_codes_text.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)

        # --- Results Tab UI ---
        results_tab.grid_columnconfigure(0, weight=1)
        results_tab.grid_rowconfigure(1, weight=1)

        # --- NEW: Unified Export Controls ---
        results_action_frame = ctk.CTkFrame(results_tab, fg_color="transparent")
        results_action_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(5, 10), padx=5)
        
        export_controls_frame = ctk.CTkFrame(results_action_frame, fg_color="transparent")
        export_controls_frame.pack(side='right', padx=(10, 0))
        self.export_button = ctk.CTkButton(export_controls_frame, text="Export Report", command=self.export_report)
        self.export_button.pack(side='left')
        self.export_format_menu = ctk.CTkOptionMenu(export_controls_frame, width=130, values=["Image (.jpg)", "PDF (.pdf)", "CSV (.csv)"], command=self._on_format_change)
        self.export_format_menu.pack(side='left', padx=5)
        self.export_filter_menu = ctk.CTkOptionMenu(export_controls_frame, width=150, values=["Export All", "Success Only", "Failed Only"])
        self.export_filter_menu.pack(side='left', padx=(0, 5))

        cols = ('Work Code', 'Status', 'Details', 'Timestamp')
        self.results_tree = ttk.Treeview(results_tab, columns=cols, show='headings')
        for col in cols: self.results_tree.heading(col, text=col)
        
        self.results_tree.column("Work Code", width=200); self.results_tree.column("Status", width=100, anchor='center'); self.results_tree.column("Details", width=350); self.results_tree.column("Timestamp", width=120, anchor='center')

        # --- NEW: Setup Sorting ---
        self._setup_treeview_sorting(self.results_tree)
        self.style_treeview(self.results_tree)
        
        self.results_tree.grid(row=1, column=0, sticky='nsew')
        scrollbar = ctk.CTkScrollbar(results_tab, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set); scrollbar.grid(row=1, column=1, sticky='ns')

    def _on_format_change(self, selected_format):
        if "CSV" in selected_format:
            self.export_filter_menu.configure(state="disabled")
        else:
            self.export_filter_menu.configure(state="normal")
            
    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running)
        state = "disabled" if running else "normal"
        self.panchayat_entry.configure(state=state)
        self.completion_date_entry.configure(state=state)
        self.work_codes_text.configure(state=state)
        # --- NEW: Manage state for export controls ---
        self.export_button.configure(state=state)
        self.export_format_menu.configure(state=state)
        self.export_filter_menu.configure(state=state)
        if state == "normal": self._on_format_change(self.export_format_menu.get())

    def reset_ui(self):
        if messagebox.askokcancel("Reset Form?", "This will clear all inputs and results. Continue?"):
            self.panchayat_entry.delete(0, tkinter.END)
            self.completion_date_entry.clear()
            self.work_codes_text.delete("1.0", tkinter.END)
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            self.app.clear_log(self.log_display)
            self.update_status("Ready", 0.0)
            self.app.log_message(self.log_display, "Form has been reset.")
            self.app.after(0, self.app.set_status, "Ready")

    def start_automation(self):
        panchayat = self.panchayat_entry.get().strip()
        completion_date = self.completion_date_entry.get().strip()
        work_codes = [line.strip() for line in self.work_codes_text.get("1.0", "end-1c").splitlines() if line.strip()]

        if not panchayat or not completion_date or not work_codes:
            messagebox.showwarning("Input Error", "Panchayat Name, Completion Date, and at least one Work Code are required.")
            return

        self.app.start_automation_thread(self.automation_key, self.run_automation_logic, args=(panchayat, completion_date, work_codes))

    def _log_result(self, work_code, status, details):
        timestamp = datetime.now().strftime("%H:%M:%S")
        tags = ('failed',) if 'success' not in status.lower() else ()
        self.app.after(0, lambda: self.results_tree.insert("", "end", values=(work_code, status, details, timestamp), tags=tags))

    def run_automation_logic(self, panchayat, completion_date, work_codes):
        self.app.after(0, self.set_ui_state, True)
        self.app.clear_log(self.log_display)
        self.app.after(0, lambda: [self.results_tree.delete(item) for item in self.results_tree.get_children()])
        self.app.log_message(self.log_display, f"Starting Update Outcome for Panchayat: {panchayat}")
        self.app.after(0, self.app.set_status, "Running Update Outcome...")

        try:
            driver = self.app.get_driver()
            if not driver: return
            
            total = len(work_codes)
            for i, work_code in enumerate(work_codes):
                if self.app.stop_events[self.automation_key].is_set():
                    self.app.log_message(self.log_display, "Automation stopped by user.", "warning")
                    break
                
                self.app.after(0, self.update_status, f"Processing {i+1}/{total}: {work_code}", (i+1)/total)
                self._process_single_work_code(driver, panchayat, work_code, completion_date)

            final_msg = "Automation finished." if not self.app.stop_events[self.automation_key].is_set() else "Stopped."
            self.app.after(0, self.update_status, final_msg, 1.0)
            if not self.app.stop_events[self.automation_key].is_set():
                messagebox.showinfo("Complete", "Update Outcome process has finished.")

        except Exception as e:
            self.app.log_message(self.log_display, f"An error occurred: {e}", "error")
        finally:
            self.app.after(0, self.set_ui_state, False)
            self.app.after(0, self.app.set_status, "Automation Finished")

    def _process_single_work_code(self, driver, panchayat, work_code, completion_date):
        try:
            driver.get(config.UPDATE_OUTCOME_CONFIG["url"])
            wait = WebDriverWait(driver, 20)
            
            self.app.log_message(self.log_display, f"Selecting Panchayat: {panchayat}")
            Select(wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddl_panchayat_code")))).select_by_visible_text(panchayat)
            
            self.app.log_message(self.log_display, f"Searching for Work Code: {work_code}")
            wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_txt_search"))).send_keys(work_code)
            wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_btn_search"))).click()
            
            try:
                # Assuming the grid has a checkbox to select the work
                checkbox = wait.until(EC.element_to_be_clickable((By.XPATH, f"//a[contains(text(),'{work_code}')]/preceding-sibling::input[@type='checkbox']")))
                checkbox.click()
            except TimeoutException:
                return self._log_result(work_code, "Failed", "Work code not found in search results.")
            except NoSuchElementException:
                return self._log_result(work_code, "Failed", "Work code checkbox not found.")

            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btn_view").click()
            
            # Outcome page
            outcome_select = Select(wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_DDl_Outcome"))))
            outcome_select.select_by_index(1)
            
            date_input = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txt_date")
            date_input.clear()
            date_input.send_keys(completion_date)

            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btn_update").click()

            try:
                alert = WebDriverWait(driver, 5).until(EC.alert_is_present())
                alert_text = alert.text
                alert.accept()
                if "updated successfully" in alert_text.lower():
                    self._log_result(work_code, "Success", "Outcome updated successfully.")
                else:
                    self._log_result(work_code, "Failed", f"Unexpected alert message: {alert_text}")
            except TimeoutException:
                self._log_result(work_code, "Failed", "No confirmation alert after update.")

        except (TimeoutException, NoSuchElementException) as e:
            error_msg = str(e).split('\n')[0]
            self.app.log_message(self.log_display, f"Failed for {work_code}: {error_msg}", "error")
            self._log_result(work_code, "Failed", f"Error: {error_msg}")
        except Exception as e:
            error_msg = str(e).split('\n')[0]
            self.app.log_message(self.log_display, f"An unexpected error occurred for {work_code}: {error_msg}", "error")
            self._log_result(work_code, "Failed", f"Unexpected error: {error_msg}")

    def export_report(self):
        export_format = self.export_format_menu.get()
        if "CSV" in export_format:
            self.export_treeview_to_csv(self.results_tree, "update_outcome_results.csv")
            return
            
        data, file_path = self._get_filtered_data_and_filepath(export_format)
        if not data: return
        
        headers = self.results_tree['columns']
        col_widths = [70, 35, 140, 25]

        if "Image" in export_format:
            self._handle_image_export(data, headers, file_path)
        elif "PDF" in export_format:
            self._handle_pdf_export(data, headers, col_widths, file_path)

    def _get_filtered_data_and_filepath(self, export_format):
        if not self.results_tree.get_children(): messagebox.showinfo("No Data", "No results to export."); return None, None
        panchayat_name = self.panchayat_entry.get().strip()
        if not panchayat_name: messagebox.showwarning("Input Needed", "Panchayat Name is required for report title."); return None, None
        
        filter_option = self.export_filter_menu.get()
        data_to_export = []
        for item_id in self.results_tree.get_children():
            row_values = self.results_tree.item(item_id)['values']
            status = row_values[1].upper()
            if filter_option == "Export All": data_to_export.append(row_values)
            elif filter_option == "Success Only" and "SUCCESS" in status: data_to_export.append(row_values)
            elif filter_option == "Failed Only" and "SUCCESS" not in status: data_to_export.append(row_values)
        if not data_to_export: messagebox.showinfo("No Data", f"No records found for filter '{filter_option}'."); return None, None

        safe_name = "".join(c for c in panchayat_name if c.isalnum() or c in (' ', '_')).rstrip()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        details = {"Image (.jpg)": { "ext": ".jpg", "types": [("JPEG Image", "*.jpg")]}, "PDF (.pdf)": { "ext": ".pdf", "types": [("PDF Document", "*.pdf")]}}[export_format]
        filename = f"Update_Outcome_Report_{safe_name}_{timestamp}{details['ext']}"
        file_path = filedialog.asksaveasfilename(defaultextension=details['ext'], filetypes=details['types'], initialdir=self.app.get_user_downloads_path(), initialfile=filename, title="Save Report")
        return (data_to_export, file_path) if file_path else (None, None)

    def _handle_image_export(self, data, headers, file_path):
        title = f"Update Outcome Report: {self.panchayat_entry.get().strip()}"
        report_date = datetime.now().strftime('%d %b %Y')
        success = self.generate_report_image(data, headers, title, report_date, "Report Generated by NREGA Bot", file_path)
        if success and messagebox.askyesno("Success", f"Image Report saved to:\n{file_path}\n\nDo you want to open it?"):
            self.app.open_folder(file_path)
    
    def _handle_pdf_export(self, data, headers, col_widths, file_path):
        title = f"Update Outcome Report: {self.panchayat_entry.get().strip()}"
        report_date = datetime.now().strftime('%d %b %Y')
        success = self.generate_report_pdf(data, headers, col_widths, title, report_date, file_path)
        if success and messagebox.askyesno("Success", f"PDF Report saved to:\n{file_path}\n\nDo you want to open it?"):
            self.app.open_folder(file_path)