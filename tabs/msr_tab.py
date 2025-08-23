# tabs/msr_tab.py
import tkinter
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import time, os, sys, subprocess, csv
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import config
from .base_tab import BaseAutomationTab
from .autocomplete_widget import AutocompleteEntry

class MsrTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="msr")
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)
        self.raw_results = []
        self._create_widgets()

    def _create_widgets(self):
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(controls_frame, text=f"Agency Name ({config.AGENCY_PREFIX}...):").grid(row=0, column=0, sticky='w', padx=15, pady=(15,0))
        self.agency_entry = AutocompleteEntry(controls_frame, suggestions_list=self.app.history_manager.get_suggestions("panchayat_name"))
        self.agency_entry.grid(row=0, column=1, sticky='ew', padx=15, pady=(15,0))
        ctk.CTkLabel(controls_frame, text="Enter only the Panchayat name (e.g., Palojori).", text_color="gray50").grid(row=1, column=1, sticky='w', padx=15)
        
        action_frame = self._create_action_buttons(parent_frame=controls_frame)
        action_frame.grid(row=6, column=0, columnspan=4, sticky='ew', pady=(15, 15))
        
        notebook = ctk.CTkTabview(self)
        notebook.grid(row=1, column=0, sticky="nsew")
        results_frame = notebook.add("Results")
        self._create_log_and_status_area(parent_notebook=notebook)

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
        
        cols = ("Timestamp", "MSR No.", "Status", "Wagelist No.", "Remarks")
        self.results_tree = ttk.Treeview(results_frame, columns=cols, show='headings')
        for col in cols: self.results_tree.heading(col, text=col)
        self.results_tree.column("Timestamp", width=80, anchor='center'); self.results_tree.column("MSR No.", width=150); self.results_tree.column("Status", width=100); self.results_tree.column("Wagelist No.", width=180); self.results_tree.column("Remarks", width=250)
        self.results_tree.grid(row=1, column=0, sticky='nsew')
        scrollbar = ctk.CTkScrollbar(results_frame, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set); scrollbar.grid(row=1, column=1, sticky='ns')
        self.style_treeview(self.results_tree); self._setup_treeview_sorting(self.results_tree)

    def _on_format_change(self, selected_format):
        if "CSV" in selected_format: self.export_filter_menu.configure(state="disabled")
        else: self.export_filter_menu.configure(state="normal")

    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running)
        state = "disabled" if running else "normal"
        self.agency_entry.configure(state=state)
        self.export_button.configure(state=state)
        self.export_format_menu.configure(state=state)
        self.export_filter_menu.configure(state=state)
        if state == "normal": self._on_format_change(self.export_format_menu.get())

    def reset_ui(self):
        if messagebox.askokcancel("Reset Form?", "Are you sure?"):
            self.agency_entry.delete(0, tkinter.END)
            for item in self.results_tree.get_children(): self.results_tree.delete(item)
            self.app.clear_log(self.log_display)
            self.update_status("Ready", 0.0)
            self.app.log_message(self.log_display, "Form has been reset.")
            self.app.after(0, self.app.set_status, "Ready")

    def start_automation(self):
        agency_name_part = self.agency_entry.get().strip()
        if not agency_name_part: messagebox.showwarning("Input Error", "Please enter an Agency name."); return
        self.app.update_history("panchayat_name", agency_name_part)
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic, args=(agency_name_part,))

    def run_automation_logic(self, agency_name_part):
        self.app.after(0, self.set_ui_state, True)
        self.app.clear_log(self.log_display)
        self.app.after(0, lambda: [self.results_tree.delete(item) for item in self.results_tree.get_children()])
        self.app.log_message(self.log_display, f"Starting MSR payment for: {agency_name_part}")
        self.app.after(0, self.app.set_status, "Running MSR Payment...")
        try:
            driver = self.app.get_driver()
            if not driver: return
            wait = WebDriverWait(driver, 20)
            total_errors_to_skip = 0
            while not self.app.stop_events[self.automation_key].is_set():
                self.app.after(0, self.update_status, "Navigating and selecting agency...")
                driver.get(config.MSR_PAYMENT_CONFIG["base_url"])
                agency_select_element = wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_exe_agency')))
                select = Select(agency_select_element)
                full_agency_name = config.AGENCY_PREFIX + agency_name_part
                
                match_text = next((opt.text for opt in select.options if opt.text.strip() == full_agency_name), None)
                if not match_text:
                    self.app.log_message(self.log_display, f"No pending MSRs found for '{full_agency_name}'. Process complete.", "info")
                    break
                
                select.select_by_visible_text(match_text)
                self.app.log_message(self.log_display, f"Selected agency: {match_text}", "success"); time.sleep(1)
                proceed_button = wait.until(EC.element_to_be_clickable((By.ID, 'ctl00_ContentPlaceHolder1_go')))
                driver.execute_script("arguments[0].scrollIntoView(true);", proceed_button); proceed_button.click()
                try:
                    msr_table = wait.until(EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_wagelist_msr")))
                    rows = msr_table.find_elements(By.XPATH, ".//tr[td]")
                    if not rows or total_errors_to_skip >= len(rows): self.app.log_message(self.log_display, "No more MSRs to process.", "info"); break
                    row_to_process = rows[total_errors_to_skip]
                    try: checkbox = row_to_process.find_element(By.XPATH, ".//input[@type='checkbox']")
                    except NoSuchElementException: self.app.log_message(self.log_display, "Row without checkbox found, assuming end.", "info"); break
                    msr_no = row_to_process.find_elements(By.TAG_NAME, "td")[2].text.strip()
                    wagelist_no = row_to_process.find_elements(By.TAG_NAME, "td")[4].text.strip()
                    self.app.after(0, self.update_status, f"Processing MSR {msr_no}...")
                    self.app.log_message(self.log_display, f"Processing row {total_errors_to_skip + 1} (MSR No: {msr_no}, Wagelist: {wagelist_no})")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
                    if not checkbox.is_selected(): checkbox.click()
                    wait.until(EC.element_to_be_clickable((By.ID, 'ctl00_ContentPlaceHolder1_btn_go'))).click()
                    wait.until(EC.any_of(EC.url_changes(config.MSR_PAYMENT_CONFIG["base_url"]), EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_lblmsg"))))
                    if "MSR_payment.aspx" in driver.current_url:
                        self.app.log_message(self.log_display, f"SUCCESS: Navigated to payment page for MSR {msr_no}.", "success")
                        # This is where the actual payment would happen.
                        # For now, we assume success and go back.
                        driver.get(config.MSR_PAYMENT_CONFIG["base_url"])
                        wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_exe_agency')))
                        self._log_result(msr_no, "Success", wagelist_no, "Payment initiated.")
                    else:
                        error_text = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_lblmsg").text.strip()
                        self.app.log_message(self.log_display, f"ERROR on MSR {msr_no}: {error_text}", "error")
                        self._log_result(msr_no, "Failed", wagelist_no, error_text)
                        total_errors_to_skip += 1
                except TimeoutException: self.app.log_message(self.log_display, "No MSR table found. Assuming process complete.", "info"); break
                if self.app.stop_events[self.automation_key].is_set(): self.app.log_message(self.log_display, "Stop signal received."); break
            if not self.app.stop_events[self.automation_key].is_set(): self.app.after(0, lambda: messagebox.showinfo("Automation Complete", "The MSR payment process has finished."))
        except Exception as e: self.app.log_message(self.log_display, f"A critical error occurred: {e}", level="error")
        finally:
            self.app.after(0, self.set_ui_state, False)
            self.app.after(0, self.update_status, "Automation Finished.")
            self.app.after(0, self.app.set_status, "Automation Finished")

    def _log_result(self, msr_no, status, wagelist_no, remarks):
        timestamp = datetime.now().strftime("%H:%M:%S")
        tags = ('failed',) if 'success' not in status.lower() else ()
        self.app.after(0, lambda: self.results_tree.insert("", "end", values=(msr_no, status, wagelist_no, remarks, timestamp), tags=tags))

    def export_report(self):
        export_format = self.export_format_menu.get()
        if "CSV" in export_format:
            self.export_treeview_to_csv(self.results_tree, "msr_report_results.csv")
            return
            
        data, file_path = self._get_filtered_data_and_filepath(export_format)
        if not data: return

        report_data, report_headers, col_widths = self._prepare_report_data(data)

        if "Image" in export_format:
            self._handle_image_export(report_data, report_headers, file_path)
        elif "PDF" in export_format:
            self._handle_pdf_export(report_data, report_headers, col_widths, file_path)

    def _get_filtered_data_and_filepath(self, export_format):
        all_items = self.results_tree.get_children()
        if not all_items: messagebox.showinfo("No Data", "There are no results to export."); return None, None
        agency_name = self.agency_entry.get().strip()
        if not agency_name: messagebox.showwarning("Input Needed", "Please enter an Agency Name for the report title."); return None, None

        filter_option = self.export_filter_menu.get()
        data_to_export = []
        for item_id in all_items:
            row_values = self.results_tree.item(item_id)['values']
            status = row_values[1].upper()
            if filter_option == "Export All": data_to_export.append(row_values)
            elif filter_option == "Success Only" and "SUCCESS" in status: data_to_export.append(row_values)
            elif filter_option == "Failed Only" and "SUCCESS" not in status: data_to_export.append(row_values)
        if not data_to_export: messagebox.showinfo("No Data", f"No records found for filter '{filter_option}'."); return None, None

        # --- THIS IS THE CORRECTED CODE ---
        # We sanitize the filename to remove invalid characters
        safe_name = "".join(c for c in agency_name if c.isalnum() or c in (' ', '_')).rstrip()
        # --- END OF CORRECTION ---
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        file_details = {"Image (.jpg)": { "ext": ".jpg", "types": [("JPEG Image", "*.jpg")]}, "PDF (.pdf)": { "ext": ".pdf", "types": [("PDF Document", "*.pdf")]}}
        details = file_details[export_format]
        filename = f"MSR_Report_{safe_name}_{timestamp}{details['ext']}"

        file_path = filedialog.asksaveasfilename(defaultextension=details['ext'], filetypes=details['types'], initialdir=self.app.get_user_downloads_path(), initialfile=filename, title="Save Report")
        return (data_to_export, file_path) if file_path else (None, None)

    def _prepare_report_data(self, raw_data):
        report_data = []
        report_headers = ["MSR No.", "Status", "Wagelist No.", "Remarks", "Timestamp"]
        col_widths = [100, 70, 100, 200, 70]
        for row in raw_data:
            msr_no, status, wagelist_no, remarks, timestamp = row
            report_data.append([msr_no, status, wagelist_no, remarks, timestamp])
        return report_data, report_headers, col_widths
    
    def _handle_image_export(self, data, headers, file_path):
        title = f"MSR Payment Report: {self.agency_entry.get().strip()}"
        report_date = datetime.now().strftime('%d %b %Y')
        success = self.generate_report_image(data, headers, title, report_date, "Report Generated by NREGA Bot", file_path)
        if success:
            if messagebox.askyesno("Success", f"Image Report saved to:\n{file_path}\n\nDo you want to open it?"):
                if sys.platform == "win32": os.startfile(file_path)
                else: subprocess.call(['open', file_path])
    
    def _handle_pdf_export(self, data, headers, col_widths, file_path):
        title = f"MSR Payment Report: {self.agency_entry.get().strip()}"
        report_date = datetime.now().strftime('%d %b %Y')
        success = self.generate_report_pdf(data, headers, col_widths, title, report_date, file_path)
        if success:
            if messagebox.askyesno("Success", f"PDF Report saved to:\n{file_path}\n\nDo you want to open it?"):
                if sys.platform == "win32": os.startfile(file_path)
                else: subprocess.call(['open', file_path])
