# tabs/work_allocation_tab.py
import tkinter
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import json
import os, sys, subprocess, time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoAlertPresentException, StaleElementReferenceException

import config
from .base_tab import BaseAutomationTab
from .autocomplete_widget import AutocompleteEntry

class WorkAllocationTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="work_allocation")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ID for the "Please Wait..." overlay
        self.wait_overlay_id = "ctl00_ContentPlaceHolder1_PageUpdateProgress"
        self.has_failures = False # Flag to track errors

        self._create_widgets()
        self.load_inputs()

    def _create_widgets(self):
        # Frame for all user input controls
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        controls_frame.grid_columnconfigure(1, weight=1)

        # --- Row 0: Panchayat Name ---
        ctk.CTkLabel(controls_frame, text="Panchayat Name:").grid(row=0, column=0, sticky='w', padx=15, pady=(15, 5))
        self.panchayat_entry = AutocompleteEntry(controls_frame,
                                                 placeholder_text="Enter the Panchayat name as it appears on the website",
                                                 suggestions_list=self.app.history_manager.get_suggestions("panchayat_name"),
                                                 app_instance=self.app,
                                                 history_key="panchayat_name")
        self.panchayat_entry.grid(row=0, column=1, sticky='ew', padx=15, pady=(15, 5))

        # --- Row 1: Work Category ---
        ctk.CTkLabel(controls_frame, text="Work Category:").grid(row=1, column=0, padx=15, pady=5, sticky="w")
        # Options extracted from your provided 'Work Allocation.htm'
        work_category_options = [
            "Anganwadi/Other Rural Infrastructure", "Coastal Areas", "Drought Proofing", "Rural Drinking Water",
            "Food Grain", "Flood Control and Protection", "Fisheries", "Micro Irrigation Works",
            "Provision of Irrigation facility to Land Owned by SC/ST/LR or IAY Beneficiaries/Small or Marginal Farmers",
            "Land Development", "Other Works", "Play Ground", "Rural Connectivity", "Rural Sanitation",
            "Bharat Nirman Sewa Kendra", "Water Conservation and Water Harvesting", "Renovation of traditional water bodies"
        ]
        self.work_category_var = ctk.StringVar(value=work_category_options[8]) # Default to 'Provision of Irrigation...'
        self.work_category_menu = ctk.CTkOptionMenu(controls_frame, variable=self.work_category_var, values=work_category_options)
        self.work_category_menu.grid(row=1, column=1, sticky="ew", padx=15, pady=5)


        # --- Row 2: Action Buttons ---
        action_frame = self._create_action_buttons(parent_frame=controls_frame)
        action_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=15)

        # --- Data Tabs (Work List, Results, Logs) ---
        data_notebook = ctk.CTkTabview(self)
        data_notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        work_list_tab = data_notebook.add("Work Key List")
        results_tab = data_notebook.add("Results")
        self._create_log_and_status_area(parent_notebook=data_notebook)

        # --- 1. Work Key List Tab ---
        work_list_tab.grid_columnconfigure(0, weight=1)
        work_list_tab.grid_rowconfigure(1, weight=1)
        
        wc_controls_frame = ctk.CTkFrame(work_list_tab, fg_color="transparent")
        wc_controls_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=(5,0))
        
        ctk.CTkLabel(wc_controls_frame, text="Enter one Work Key (Search Key) per line.").pack(side='left', padx=5)
        clear_button = ctk.CTkButton(wc_controls_frame, text="Clear", width=80, command=lambda: self.work_list_text.delete("1.0", tkinter.END))
        clear_button.pack(side='right', padx=5)

        self.work_list_text = ctk.CTkTextbox(work_list_tab)
        self.work_list_text.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)

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
        cols = ("Work Key", "Selected Work Code", "Status", "Details", "Timestamp")
        self.results_tree = ttk.Treeview(results_tab, columns=cols, show='headings')
        for col in cols: self.results_tree.heading(col, text=col)
        self.results_tree.column("Work Key", anchor='center', width=100)
        self.results_tree.column("Selected Work Code", width=250)
        self.results_tree.column("Status", anchor='center', width=100)
        self.results_tree.column("Details", width=250)
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
        self.panchayat_entry.configure(state=state)
        self.work_category_menu.configure(state=state)
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

    def run_automation_from_demand(self, panchayat_name, work_key):
        """
        Starts the Work Allocation automation externally, e.g., from DemandTab.
        """
        self.app.log_message(self.log_display, "--- Starting Auto-Allocation from Demand Tab ---")
        
        # 1. Clear/Reset UI
        for item in self.results_tree.get_children(): self.results_tree.delete(item)
        self.app.clear_log(self.log_display)
        self.panchayat_entry.delete(0, tkinter.END)
        self.work_list_text.delete("1.0", tkinter.END)

        # 2. Set Inputs
        self.panchayat_entry.insert(0, panchayat_name)
        self.work_list_text.insert("1.0", work_key)
        
        # Use the currently selected work category from the UI
        work_category = self.work_category_var.get()
        
        self.app.log_message(self.log_display, f"Panchayat set to: {panchayat_name}")
        self.app.log_message(self.log_display, f"Work Key set to: {work_key}")
        self.app.log_message(self.log_display, f"Using selected Work Category: {work_category}")

        # 3. Prepare inputs dictionary
        inputs = {
            'panchayat_name': panchayat_name,
            'work_category': work_category,
            'work_list_raw': work_key,
            'work_keys': [work_key] # Allocation logic expects a list
        }

        # 4. Save and Start
        self._save_inputs(inputs)
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic, args=(inputs,))

    def start_automation(self):
        for item in self.results_tree.get_children(): self.results_tree.delete(item)
        self.app.clear_log(self.log_display)

        inputs = {
            'panchayat_name': self.panchayat_entry.get().strip(),
            'work_category': self.work_category_var.get(),
            'work_list_raw': self.work_list_text.get("1.0", tkinter.END).strip()
        }

        if not inputs['work_category'] or not inputs['work_list_raw']:
            messagebox.showwarning("Input Error", "Work Category and Work Key List are required.")
            return

        work_keys = [line.strip() for line in inputs['work_list_raw'].splitlines() if line.strip()]
        if not work_keys:
            messagebox.showwarning("Input Error", "No valid items found in the Work Key List.")
            return

        inputs['work_keys'] = work_keys
        if inputs['panchayat_name']:
            self.app.update_history("panchayat_name", inputs['panchayat_name'])
        self._save_inputs(inputs)
        
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic, args=(inputs,))

    def _wait_for_settle(self, driver, long_wait, action_name=""):
        """
        Waits for the 'Please Wait...' overlay to disappear.
        Handles cases where the overlay is very fast or doesn't appear at all.
        """
        self.app.log_message(self.log_display, f"   - Waiting for page to settle after '{action_name}'...")
        try:
            # 1. Check if overlay is visible (with a very short timeout)
            short_wait = WebDriverWait(driver, 0.5) # 0.5 second check
            overlay_visible = short_wait.until(EC.visibility_of_element_located((By.ID, self.wait_overlay_id)))
            
            # 2. If it was visible, wait for it to disappear (with the long timeout)
            if overlay_visible:
                self.app.log_message(self.log_display, "   - Overlay detected, waiting for it to disappear...")
                long_wait.until(EC.invisibility_of_element_located((By.ID, self.wait_overlay_id)))
                self.app.log_message(self.log_display, "   - Page settled.")
            
        except TimeoutException:
            # This is the normal, fast path. The overlay was not visible (or gone in < 0.5s).
            self.app.log_message(self.log_display, "   - (No overlay) Page is settled.", "info")
        
        # Add a small fixed delay for extra safety after any postback
        time.sleep(0.5)

    # --- FUNCTION MODIFIED ---
    def run_automation_logic(self, inputs):
        self.app.after(0, self.set_ui_state, True)
        self.app.after(0, self.app.set_status, "Starting Work Allocation...")
        self.app.log_message(self.log_display, "Starting Work Allocation automation...")
        self.has_failures = False # Reset failure flag
        
        try:
            driver = self.app.get_driver()
            if not driver:
                self.app.after(0, self.set_ui_state, False)
                return
                
            wait = WebDriverWait(driver, 20) # This is the 'long_wait'
            
            self.app.log_message(self.log_display, f"Navigating to Work Allocation page...")
            driver.get(config.WORK_ALLOCATION_CONFIG["url"])

            # --- START: Optional Panchayat Selection (GP Login Fix) ---
            self.app.log_message(self.log_display, "Checking for Panchayat dropdown (for PO/Block Login)...")
            try:
                # 1. Use a SHORT wait (3 sec) to find the dropdown
                short_wait = WebDriverWait(driver, 3)
                panchayat_select_element = short_wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ddlpanchayat_code")))
                
                # 2. If found, it's a PO/Block login. Selection is required.
                self.app.log_message(self.log_display, "Panchayat dropdown found. Selecting...")
                self.app.after(0, self.app.set_status, "Setting Panchayat...")
                
                if not inputs['panchayat_name']:
                    # If dropdown is present, panchayat name IS required
                    raise ValueError("Panchayat Name is required for this login level (PO/Block).")

                panchayat_select = Select(panchayat_select_element)
                if panchayat_select.first_selected_option.text.strip() != inputs['panchayat_name'].strip():
                    panchayat_select.select_by_visible_text(inputs['panchayat_name'])
                    self._wait_for_settle(driver, wait, "Panchayat Selection")
                
                self.app.log_message(self.log_display, "Panchayat selected.")

            except (TimeoutException, NoSuchElementException):
                # 3. If not found, it's a GP login. Log it and continue.
                self.app.log_message(self.log_display, "Panchayat dropdown not found. Assuming GP Login.", "info")
            except ValueError as e:
                # This catches our "Panchayat Name is required" error
                self.app.log_message(self.log_display, str(e), "error")
                messagebox.showerror("Input Error", str(e))
                self.app.after(0, self.set_ui_state, False)
                return
            # --- END: Optional Panchayat Selection ---
            
            # --- Step 2: Set Work Category ---
            self.app.after(0, self.app.set_status, "Setting Work Category...")
            self.app.log_message(self.log_display, f"Selecting Work Category: {inputs['work_category']}")
            
            category_select_element = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ddlworkcategory")))
            category_select = Select(category_select_element)
            
            if category_select.first_selected_option.text.strip() != inputs['work_category'].strip():
                category_select.select_by_visible_text(inputs['work_category'])
                self._wait_for_settle(driver, wait, "Category Selection")

            self.app.log_message(self.log_display, "Setup complete. Starting item processing...", "success")
            
            # --- Process each item ---
            total_items = len(inputs['work_keys'])
            for i, work_key in enumerate(inputs['work_keys']):
                if self.app.stop_events[self.automation_key].is_set():
                    self.app.log_message(self.log_display, "Stop signal received.", "warning")
                    break
                
                status_msg = f"Processing {i+1}/{total_items}: Key={work_key}"
                self.app.after(0, self.app.set_status, status_msg)
                self.app.after(0, self.update_status, status_msg, (i+1)/total_items)
                
                self._process_single_work_key(driver, wait, work_key) # 'wait' is 'long_wait'

        except Exception as e:
            error_msg = f"A critical error occurred: {e}"
            self.app.log_message(self.log_display, error_msg, "error")
            messagebox.showerror("Critical Error", error_msg)
            self.app.after(0, self.app.set_status, "Error")
        finally:
            self.app.after(0, self.set_ui_state, False)
            
            # --- MODIFIED: Final Status and Popup Logic ---
            final_status = "Automation Finished"
            final_message_type = "info" # 'info', 'warning', or 'error'

            if self.app.stop_events[self.automation_key].is_set():
                final_status = "Automation Stopped"
                final_message_type = "warning"
            elif self.has_failures:
                final_status = "Finished with Errors"
                final_message_type = "warning"
            
            self.app.after(0, self.app.set_status, final_status)
            self.app.after(0, self.update_status, final_status, 1.0)

            popup_title = "Complete"
            popup_message = f"{final_status}. Check results."
            
            if final_message_type == "info":
                self.app.after(100, lambda: messagebox.showinfo(popup_title, popup_message))
            elif final_message_type == "warning":
                self.app.after(100, lambda: messagebox.showwarning(popup_title, popup_message))
            # --- END MODIFICATION ---

    # --- FUNCTION MODIFIED (from last time) ---
    def _process_single_work_key(self, driver, wait, work_key): # 'wait' is 'long_wait'
        selected_work_code_text = "N/A"
        try:
            self.app.log_message(self.log_display, f"   - Processing Key: {work_key}")
            
            # --- Step 3: Enter Work Key ---
            search_box = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_txtwrksearchkey")))
            search_box.clear()
            search_box.send_keys(work_key)
            
            # Trigger postback
            driver.find_element(By.TAG_NAME, 'body').click()
            self._wait_for_settle(driver, wait, f"Work Key Search ({work_key})")
            
            # --- Step 4: Select Matching Work Code ---
            work_code_select_element = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ddlWork_code")))
            work_code_select = Select(work_code_select_element)
            
            # Find the option that contains the work key
            matching_option = None
            for option in work_code_select.options:
                if work_key in option.text:
                    matching_option = option
                    break
            
            # --- START: MODIFICATION (User Request) ---
            if not matching_option:
                # This is the user's desired error for a common, known issue
                error_msg = "Workcode not found. Please try with complete workcode."
                self.app.log_message(self.log_display, f"   - FAILED: {error_msg} (Key: {work_key})", "error")
                self._log_result(work_key, "N/A", "Failed", error_msg)
                # Safely exit this function and move to the next key.
                # DO NOT try to refresh the page for this error.
                return 
            # --- END: MODIFICATION ---
            
            selected_work_code_text = matching_option.text
            work_code_select.select_by_visible_text(selected_work_code_text)
            self.app.log_message(self.log_display, f"   - Selected work code: {selected_work_code_text}")
            
            self._wait_for_settle(driver, wait, "Work Code Selection")

            # --- Step 5: Click "Allocate All" ---
            self.app.log_message(self.log_display, "   - Clicking 'Allocate All'...")
            alloc_checkbox = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_GridView1_ctl01_chkHAllocate")))
            
            if not alloc_checkbox.is_selected():
                alloc_checkbox.click()
                self._wait_for_settle(driver, wait, "Allocate All")
            else:
                self.app.log_message(self.log_display, "   - 'Allocate All' was already checked.")

            # --- Step 6: Click Save ---
            self.app.log_message(self.log_display, "   - Clicking 'Save'...")
            save_button = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_cmdSave")))
            save_button.click()
            
            # --- Step 7: Handle Alert ---
            self.app.log_message(self.log_display, "   - Waiting for confirmation alert...")
            alert = wait.until(EC.alert_is_present())
            alert_text = alert.text.strip()
            alert.accept()
            
            self.app.log_message(self.log_display, f"   - Success: {alert_text}", "success")
            self._log_result(work_key, selected_work_code_text, "Success", alert_text)
            
            # Wait for page to reset after save
            self._wait_for_settle(driver, wait, "Save")

        except (TimeoutException, NoAlertPresentException, StaleElementReferenceException) as e:
            # Note: NoSuchElementException is removed because we handle it above
            error_msg = f"An unexpected page error occurred: {str(e).splitlines()[0]}"
            self.app.log_message(self.log_display, f"   - FAILED: {error_msg}", "error")
            self._log_result(work_key, selected_work_code_text, "Failed", error_msg)
            
            # Try to refresh the page to get it back to a stable state for the next item
            try:
                self.app.log_message(self.log_display, "   - Attempting to refresh and reset page state...")
                driver.get(config.WORK_ALLOCATION_CONFIG["url"])
                # Re-select Panchayat and Category
                
                # --- FIX: Handle GP/PO login during refresh ---
                try:
                    # Check for PO login dropdown
                    short_wait = WebDriverWait(driver, 3)
                    panchayat_select_element = short_wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ddlpanchayat_code")))
                    
                    # If PO login, select panchayat
                    if self.panchayat_entry.get():
                        Select(panchayat_select_element).select_by_visible_text(self.panchayat_entry.get())
                        self._wait_for_settle(driver, wait, "Page Reset (Panchayat)")
                    else:
                        self.app.log_message(self.log_display, "   - ERROR: PO login but no Panchayat name to use for reset.", "error")
                        return # Can't continue
                except TimeoutException:
                    # GP login, no panchayat selection needed
                    self.app.log_message(self.log_display, "   - (GP login) No panchayat selection needed for reset.", "info")
                # --- END FIX ---

                category_select_element = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ddlworkcategory")))
                Select(category_select_element).select_by_visible_text(self.work_category_var.get())
                self._wait_for_settle(driver, wait, "Page Reset (Category)")
                self.app.log_message(self.log_display, "   - Page reset successfully.")
            
            except Exception as refresh_e:
                self.app.log_message(self.log_display, f"   - FAILED to refresh page: {refresh_e}", "error")
                # --- START: MODIFICATION (Stability) ---
                # Do not stop the entire automation. Just return and try the next key.
                self.app.log_message(self.log_display, "   - Skipping to next item due to refresh failure.", "warning")
                return # Was: raise Exception("Failed to reset page after error, stopping.")
                # --- END: MODIFICATION ---
        
        except Exception as e:
            error_msg = f"A critical unexpected error occurred: {e}"
            self.app.log_message(self.log_display, f"   - FAILED: {error_msg}", "error")
            self._log_result(work_key, selected_work_code_text, "Failed", error_msg)

    # --- FUNCTION MODIFIED ---
    def _log_result(self, work_key, work_code, status, details):
        timestamp = datetime.now().strftime("%H:%M:%S")
        values = (work_key, work_code, status, details, timestamp)
        
        # --- NEW: Set failure flag ---
        if 'success' not in status.lower():
            self.has_failures = True
            tags = ('failed',)
        else:
            tags = ()
        # --- END NEW ---
        
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
            default_filename = f"Work_Allocation_Report_{safe_name}_{timestamp}.csv"
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
        filename = f"Work_Allocation_Report_{safe_name}_{timestamp}{details['ext']}"

        file_path = filedialog.asksaveasfilename(defaultextension=details['ext'], filetypes=details['types'], initialdir=self.app.get_user_downloads_path(), initialfile=filename, title=details['title'])
        return (data_to_export, file_path) if file_path else (None, None)
    
    def _handle_pdf_export(self, data, file_path):
        try:
            headers = self.results_tree['columns']
            col_widths = [40, 70, 40, 70, 40] # Adjusted widths
            title = f"Work Allocation Report: {self.panchayat_entry.get().strip()}"
            report_date = datetime.now().strftime('%d %b %Y')
            
            success = self.generate_report_pdf(data, headers, col_widths, title, report_date, file_path)
            
            if success:
                if messagebox.askyesno("Success", f"PDF Report exported to:\n{file_path}\n\nDo you want to open the file?"):
                    if sys.platform == "win32":
                        os.startfile(file_path)
                    else:
                        subprocess.call(['open', file_path])
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to create PDF file.\n\SError: {e}")

    def _save_inputs(self, inputs):
        """Saves the panchayat name and work category."""
        save_data = {
            'panchayat_name': inputs.get('panchayat_name'),
            'work_category': inputs.get('work_category')
        }
        try:
            config_file = self.app.get_data_path("work_alloc_inputs.json")
            with open(config_file, 'w') as f:
                json.dump(save_data, f, indent=4)
        except Exception as e:
            print(f"Error saving Work Allocation inputs: {e}")

    def load_inputs(self):
        """Loads the saved panchayat name and work category."""
        try:
            config_file = self.app.get_data_path("work_alloc_inputs.json")
            if not os.path.exists(config_file):
                return
            
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            self.panchayat_entry.delete(0, tkinter.END)
            self.panchayat_entry.insert(0, data.get('panchayat_name', ''))
            
            saved_category = data.get('work_category')
            if saved_category:
                if saved_category in self.work_category_menu.cget("values"):
                    self.work_category_var.set(saved_category)
        except Exception as e:
            print(f"Error loading Work Allocation inputs: {e}")