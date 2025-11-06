# tabs/zero_mr_tab.py
import tkinter
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import json
import os, sys, subprocess, time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoAlertPresentException
import config
from .base_tab import BaseAutomationTab
from .autocomplete_widget import AutocompleteEntry

class ZeroMrTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="zero_mr")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._create_widgets()
        self.load_inputs()

    def _create_widgets(self):
        # Frame for all user input controls
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        controls_frame.grid_columnconfigure((1, 3), weight=1)

        # --- Row 0: Financial Year ---
        ctk.CTkLabel(controls_frame, text="Financial Year:").grid(row=0, column=0, sticky='w', padx=15, pady=(15, 5))
        # Get current year and create a list for the past few years
        current_year = datetime.now().year
        fin_year_list = [f"{year}-{year+1}" for year in range(current_year + 1, current_year - 5, -1)]
        self.fin_year_menu = ctk.CTkOptionMenu(controls_frame, values=fin_year_list)
        self.fin_year_menu.grid(row=0, column=1, sticky='ew', padx=15, pady=(15, 5))

        # --- Row 1: Panchayat Name ---
        ctk.CTkLabel(controls_frame, text="Panchayat Name:").grid(row=1, column=0, sticky='w', padx=15, pady=5)
        self.panchayat_entry = AutocompleteEntry(controls_frame,
                                                 suggestions_list=self.app.history_manager.get_suggestions("panchayat_name"),
                                                 app_instance=self.app,
                                                 history_key="panchayat_name")
        self.panchayat_entry.grid(row=1, column=1, columnspan=3, sticky='ew', padx=15, pady=5)
        ctk.CTkLabel(controls_frame, text="Note: Must exactly match the name on the NREGA website.", text_color="gray50").grid(row=2, column=1, columnspan=3, sticky='w', padx=15, pady=(0,10))

        # --- Row 3: Action Buttons ---
        action_frame = self._create_action_buttons(parent_frame=controls_frame)
        action_frame.grid(row=3, column=0, columnspan=4, sticky='ew', pady=15)

        # --- Data Tabs (Work List, Results, Logs) ---
        data_notebook = ctk.CTkTabview(self)
        data_notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        work_list_tab = data_notebook.add("Work List")
        results_tab = data_notebook.add("Results")
        self._create_log_and_status_area(parent_notebook=data_notebook)

        # --- 1. Work List Tab ---
        work_list_tab.grid_columnconfigure(0, weight=1)
        work_list_tab.grid_rowconfigure(1, weight=1)
        
        wc_controls_frame = ctk.CTkFrame(work_list_tab, fg_color="transparent")
        wc_controls_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=(5,0))
        
        ctk.CTkLabel(wc_controls_frame, text="Enter one item per line. Format: SearchKey,MSRNo").pack(side='left', padx=5)
        clear_button = ctk.CTkButton(wc_controls_frame, text="Clear", width=80, command=lambda: self.work_list_text.delete("1.0", tkinter.END))
        clear_button.pack(side='right', padx=5)

        self.work_list_text = ctk.CTkTextbox(work_list_tab)
        self.work_list_text.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        # self.work_list_text.insert("1.0", "Example: 58744,32158") # <-- Placeholder removed

        # --- 2. Results Tab ---
        results_tab.grid_columnconfigure(0, weight=1)
        results_tab.grid_rowconfigure(1, weight=1)
        
        results_action_frame = ctk.CTkFrame(results_tab, fg_color="transparent")
        results_action_frame.grid(row=0, column=0, sticky='ew', pady=(5, 10))
        
        export_controls_frame = ctk.CTkFrame(results_action_frame, fg_color="transparent")
        export_controls_frame.pack(side='right', padx=(10, 0))
        self.export_button = ctk.CTkButton(export_controls_frame, text="Export Report", command=self.export_report)
        self.export_button.pack(side='left')
        self.export_format_menu = ctk.CTkOptionMenu(export_controls_frame, width=130, values=["PDF (.pdf)", "CSV (.csv)"], command=self._on_format_change)
        self.export_format_menu.pack(side='left', padx=5)
        self.export_filter_menu = ctk.CTkOptionMenu(export_controls_frame, width=150, values=["Export All", "Success Only", "Failed Only"])
        self.export_filter_menu.pack(side='left', padx=(0, 5))

        # --- Results Treeview ---
        cols = ("Search Key", "MSR No", "Status", "Details", "Timestamp")
        self.results_tree = ttk.Treeview(results_tab, columns=cols, show='headings')
        for col in cols: self.results_tree.heading(col, text=col)
        self.results_tree.column("Search Key", anchor='center', width=100)
        self.results_tree.column("MSR No", anchor='center', width=100)
        self.results_tree.column("Status", anchor='center', width=100)
        self.results_tree.column("Details", width=350)
        self.results_tree.column("Timestamp", anchor='center', width=100)
        self.results_tree.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        scrollbar = ctk.CTkScrollbar(results_tab, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set); scrollbar.grid(row=1, column=1, sticky='ns')
        self.style_treeview(self.results_tree)
        self._setup_treeview_sorting(self.results_tree)

    def _on_format_change(self, selected_format):
        if "CSV" in selected_format:
            self.export_filter_menu.configure(state="disabled")
        else:
            self.export_filter_menu.configure(state="normal")

    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running)
        state = "disabled" if running else "normal"
        self.fin_year_menu.configure(state=state)
        self.panchayat_entry.configure(state=state)
        self.work_list_text.configure(state=state)
        self.export_button.configure(state=state)
        self.export_format_menu.configure(state=state)
        self.export_filter_menu.configure(state=state)
        if state == "normal": self._on_format_change(self.export_format_menu.get())

    def reset_ui(self):
        self.panchayat_entry.delete(0, tkinter.END)
        self.work_list_text.delete("1.0", tkinter.END)
        for item in self.results_tree.get_children(): self.results_tree.delete(item)
        self.app.clear_log(self.log_display)
        self.update_status("Ready", 0.0)
        self.app.log_message(self.log_display, "Form has been reset.")
        self.app.after(0, self.app.set_status, "Ready")

    def start_automation(self):
        for item in self.results_tree.get_children(): self.results_tree.delete(item)
        self.app.clear_log(self.log_display)

        inputs = {
            'fin_year': self.fin_year_menu.get(),
            'panchayat_name': self.panchayat_entry.get().strip(),
            'work_list_raw': self.work_list_text.get("1.0", tkinter.END).strip()
        }

        if not inputs['panchayat_name'] or not inputs['work_list_raw']:
            messagebox.showwarning("Input Error", "Panchayat Name and Work List are required.")
            return

        # Parse the work list
        work_items = []
        try:
            lines = inputs['work_list_raw'].splitlines()
            for i, line in enumerate(lines):
                if not line.strip() or "Example:" in line:
                    continue
                parts = line.split(',')
                if len(parts) != 2:
                    raise ValueError(f"Line {i+1} is not in the correct 'SearchKey,MSRNo' format.")
                work_key = parts[0].strip()
                msr_no = parts[1].strip()
                if not work_key or not msr_no:
                    raise ValueError(f"Line {i+1} has missing data.")
                work_items.append((work_key, msr_no))
        except Exception as e:
            messagebox.showerror("Input Error", f"Failed to parse Work List:\n{e}")
            return

        if not work_items:
            messagebox.showwarning("Input Error", "No valid items found in the Work List.")
            return

        inputs['work_items'] = work_items
        self.app.update_history("panchayat_name", inputs['panchayat_name'])
        self._save_inputs(inputs)
        
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic, args=(inputs,))

    def run_automation_logic(self, inputs):
        self.app.after(0, self.set_ui_state, True)
        self.app.after(0, self.app.set_status, "Starting Zero MR...")
        self.app.log_message(self.log_display, "Starting Zero MR automation...")
        
        try:
            driver = self.app.get_driver()
            if not driver:
                self.app.after(0, self.set_ui_state, False)
                return
                
            wait = WebDriverWait(driver, 20)
            
            self.app.log_message(self.log_display, f"Navigating to Zero MR page...")
            driver.get(config.ZERO_MR_CONFIG["url"])

            # --- Set Fin Year and Panchayat (only once) ---
            self.app.after(0, self.app.set_status, "Setting Financial Year...")
            self.app.log_message(self.log_display, f"Selecting Financial Year: {inputs['fin_year']}")
            fin_year_select = Select(wait.until(EC.element_to_be_clickable((By.ID, "ddlfin"))))
            if fin_year_select.first_selected_option.text != inputs['fin_year']:
                fin_year_select.select_by_visible_text(inputs['fin_year'])
                self.app.log_message(self.log_display, "Waiting for Fin Year postback...")
                time.sleep(2) # Wait for postback

            self.app.after(0, self.app.set_status, "Setting Panchayat...")
            self.app.log_message(self.log_display, f"Selecting Panchayat: {inputs['panchayat_name']}")
            panchayat_select = Select(wait.until(EC.element_to_be_clickable((By.ID, "ddlpanch"))))
            match = next((opt.text for opt in panchayat_select.options if inputs['panchayat_name'].strip().lower() in opt.text.lower()), None)
            if not match:
                raise ValueError(f"Panchayat '{inputs['panchayat_name']}' not found in dropdown.")
            
            if panchayat_select.first_selected_option.text != match:
                panchayat_select.select_by_visible_text(match)
                self.app.log_message(self.log_display, "Waiting for Panchayat postback...")
                time.sleep(2) # Wait for postback
            
            self.app.log_message(self.log_display, "Setup complete. Starting item processing...", "success")
            
            # --- Process each item ---
            total_items = len(inputs['work_items'])
            for i, (work_key, msr_no) in enumerate(inputs['work_items']):
                if self.app.stop_events[self.automation_key].is_set():
                    self.app.log_message(self.log_display, "Stop signal received.", "warning")
                    break
                
                status_msg = f"Processing {i+1}/{total_items}: Key={work_key}, MSR={msr_no}"
                self.app.after(0, self.app.set_status, status_msg)
                self.app.after(0, self.update_status, status_msg, (i+1)/total_items)
                
                self._process_single_item(driver, wait, work_key, msr_no)

        except Exception as e:
            error_msg = f"A critical error occurred: {e}"
            self.app.log_message(self.log_display, error_msg, "error")
            messagebox.showerror("Critical Error", error_msg)
            self.app.after(0, self.app.set_status, "Error")
        finally:
            self.app.after(0, self.set_ui_state, False)
            final_status = "Automation Finished"
            if self.app.stop_events[self.automation_key].is_set():
                final_status = "Automation Stopped"
            self.app.after(0, self.app.set_status, final_status)
            self.app.after(0, self.update_status, final_status, 1.0)
            self.app.after(100, lambda: messagebox.showinfo("Complete", f"{final_status}. Check results."))

    def _process_single_item(self, driver, wait, work_key, msr_no):
        try:
            self.app.log_message(self.log_display, f"   - Processing Key: {work_key}, MSR: {msr_no}")
            
            # 1. Enter Search Key
            search_box = wait.until(EC.element_to_be_clickable((By.ID, "txtsearch_work")))
            search_box.clear()
            search_box.send_keys(work_key)
            
            # 2. Trigger postback (by clicking body) and wait
            driver.find_element(By.TAG_NAME, 'body').click()
            self.app.log_message(self.log_display, "   - Waiting for work code...")
            
            # 3. Select Work Code (wait for options to appear)
            # --- BUG FIX: Wait for options, then initialize Select on the <select> element ---
            wait.until(EC.presence_of_element_located((By.XPATH, "//select[@id='ddlworkcode']/option[position()>1]")))
            work_code_select = Select(driver.find_element(By.ID, "ddlworkcode"))
            # --- END FIX ---
            
            # Select the first work code found (index 1, as index 0 is "Select work")
            work_code_select.select_by_index(1)
            self.app.log_message(self.log_display, "   - Waiting for MSR list...")

            # 4. Select MSR No (wait for options to appear)
            # --- BUG FIX: Wait for options, then initialize Select on the <select> element ---
            wait.until(EC.presence_of_element_located((By.XPATH, "//select[@id='ddlmustroll']/option[position()>1]")))
            msr_select = Select(driver.find_element(By.ID, "ddlmustroll"))
            # --- END FIX ---
            
            msr_select.select_by_visible_text(msr_no)
            self.app.log_message(self.log_display, "   - MSR selected. Clicking save.")

            # 5. Click Save
            wait.until(EC.element_to_be_clickable((By.ID, "btnSave"))).click()
            
            # 6. Handle Alert
            alert = WebDriverWait(driver, 10).until(EC.alert_is_present())
            alert_text = alert.text
            alert.accept()
            self.app.log_message(self.log_display, f"   - Alert accepted: {alert_text}", "success")
            
            self._log_result(work_key, msr_no, "Success", alert_text)

        except (TimeoutException, NoSuchElementException) as e:
            error_msg = f"Element not found or timeout. MSR/WorkCode valid? {str(e).splitlines()[0]}"
            self.app.log_message(self.log_display, f"   - FAILED: {error_msg}", "error")
            self._log_result(work_key, msr_no, "Failed", error_msg)
        except Exception as e:
            error_msg = f"An unexpected error occurred: {e}"
            self.app.log_message(self.log_display, f"   - FAILED: {error_msg}", "error")
            self._log_result(work_key, msr_no, "Failed", error_msg)

    def _log_result(self, work_key, msr_no, status, details):
        timestamp = datetime.now().strftime("%H:%M:%S")
        values = (work_key, msr_no, status, details, timestamp)
        tags = ('failed',) if 'success' not in status.lower() else ()
        self.app.after(0, lambda: self.results_tree.insert("", "end", values=values, tags=tags))

    def export_report(self):
        export_format = self.export_format_menu.get()
        panchayat_name = self.panchayat_entry.get().strip()

        if not panchayat_name:
            messagebox.showwarning("Input Needed", "Please enter a Panchayat Name for the report filename.", parent=self)
            return

        if "CSV" in export_format:
            safe_name = "".join(c for c in panchayat_name if c.isalnum() or c in (' ', '_')).rstrip()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_filename = f"Zero_MR_Report_{safe_name}_{timestamp}.csv"
            self.export_treeview_to_csv(self.results_tree, default_filename)
            return
            
        data, file_path = self._get_filtered_data_and_filepath(export_format)
        if not data: return

        if "PDF" in export_format:
            self._handle_pdf_export(data, file_path)

    def _get_filtered_data_and_filepath(self, export_format):
        all_items = self.results_tree.get_children()
        if not all_items: messagebox.showinfo("No Data", "There are no results to export."); return None, None
        
        filter_option = self.export_filter_menu.get()
        data_to_export = []
        for item_id in all_items:
            row_values = self.results_tree.item(item_id)['values']
            status = row_values[2].upper()
            if filter_option == "Export All": data_to_export.append(row_values)
            elif filter_option == "Success Only" and "SUCCESS" in status: data_to_export.append(row_values)
            elif filter_option == "Failed Only" and "SUCCESS" not in status: data_to_export.append(row_values)
        if not data_to_export: messagebox.showinfo("No Data", f"No records found for filter '{filter_option}'."); return None, None

        safe_name = "".join(c for c in self.panchayat_entry.get().strip() if c.isalnum() or c in (' ', '_')).rstrip()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        file_details = {"PDF (.pdf)": { "ext": ".pdf", "types": [("PDF Document", "*.pdf")], "title": "Save Report as PDF"}}
        details = file_details[export_format]
        filename = f"Zero_MR_Report_{safe_name}_{timestamp}{details['ext']}"

        file_path = filedialog.asksaveasfilename(defaultextension=details['ext'], filetypes=details['types'], initialdir=self.app.get_user_downloads_path(), initialfile=filename, title=details['title'])
        return (data_to_export, file_path) if file_path else (None, None)
    
    def _handle_pdf_export(self, data, file_path):
        try:
            headers = self.results_tree['columns']
            col_widths = [40, 40, 40, 130, 40] # Adjusted widths for A4 Landscape
            title = f"Zero MR Status Report: {self.panchayat_entry.get().strip()}"
            report_date = datetime.now().strftime('%d %b %Y')
            
            success = self.generate_report_pdf(data, headers, col_widths, title, report_date, file_path)
            
            if success:
                if messagebox.askyesno("Success", f"PDF Report exported to:\n{file_path}\n\nDo you want to open the file?"):
                    if sys.platform == "win32":
                        os.startfile(file_path)
                    else:
                        subprocess.call(['open', file_path])
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to create PDF file.\n\nError: {e}")

    def load_data_from_mr_tracking(self, data_list: list):
        """
        Receives data from the MR Tracking tab and populates the form.
        NOTE: This tab processes one panchayat at a time. If data for multiple
        panchayats is received, it will load data for the *first* panchayat
        and notify the user.
        """
        if not data_list:
            messagebox.showwarning("No Data", "No data was received from the MR Tracking tab.", parent=self)
            return

        self.app.log_message(self.log_display, f"Received {len(data_list)} items from MR Tracking.")
        
        # Clear current form and results
        self.panchayat_entry.delete(0, tkinter.END)
        self.work_list_text.delete("1.0", tkinter.END)
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        # Get the first panchayat from the list
        target_panchayat = data_list[0].get("panchayat")
        if not target_panchayat:
            messagebox.showerror("Data Error", "Received data is missing Panchayat name.", parent=self)
            return
            
        self.panchayat_entry.insert(0, target_panchayat)
        self.app.log_message(self.log_display, f"Set Panchayat to: {target_panchayat}")

        work_list_entries = []
        other_panchayats_found = []

        for item in data_list:
            panchayat = item.get("panchayat")
            work_code = item.get("work_code")
            msr_no = item.get("msr_no")

            if not all([panchayat, work_code, msr_no]):
                self.app.log_message(self.log_display, f"Skipping invalid item: {item}", "warning")
                continue

            if panchayat == target_panchayat:
                # Format: SearchKey,MSRNo
                work_list_entries.append(f"{work_code},{msr_no}")
            else:
                if panchayat not in other_panchayats_found:
                    other_panchayats_found.append(panchayat)

        # Populate the textbox
        if work_list_entries:
            self.work_list_text.insert("1.0", "\n".join(work_list_entries))
            self.app.log_message(self.log_display, f"Loaded {len(work_list_entries)} items for {target_panchayat}.", "success")
        
        # Show warning if other panchayats were skipped
        if other_panchayats_found:
            skipped_panchayats_str = ", ".join(other_panchayats_found[:3])
            if len(other_panchayats_found) > 3:
                skipped_panchayats_str += ", ..."
            
            messagebox.showwarning(
                "Partial Data Loaded",
                f"Successfully loaded {len(work_list_entries)} items for Panchayat:\n{target_panchayat}\n\n"
                f"Data for other panchayats ({skipped_panchayats_str}) was found but not loaded. "
                f"Please run the 'T+8 to T+15' filter again for those panchayats individually.",
                parent=self
            )
            self.app.log_message(self.log_display, f"Skipped items for other panchayats: {skipped_panchayats_str}", "warning")

    def _save_inputs(self, inputs):
        """Saves the financial year and panchayat name."""
        save_data = {
            'fin_year': inputs.get('fin_year'),
            'panchayat_name': inputs.get('panchayat_name')
        }
        try:
            config_file = self.app.get_data_path("zero_mr_inputs.json")
            with open(config_file, 'w') as f:
                json.dump(save_data, f, indent=4)
        except Exception as e:
            print(f"Error saving Zero MR inputs: {e}")

    def load_inputs(self):
        """Loads the saved financial year and panchayat name."""
        try:
            config_file = self.app.get_data_path("zero_mr_inputs.json")
            if not os.path.exists(config_file):
                return
            
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            saved_fin_year = data.get('fin_year')
            if saved_fin_year:
                # Check if the saved year is still in the list of options
                if saved_fin_year in self.fin_year_menu.cget("values"):
                    self.fin_year_menu.set(saved_fin_year)
            
            self.panchayat_entry.delete(0, tkinter.END)
            self.panchayat_entry.insert(0, data.get('panchayat_name', ''))
        except Exception as e:
            print(f"Error loading Zero MR inputs: {e}")