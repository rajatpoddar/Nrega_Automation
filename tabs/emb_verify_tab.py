# tabs/emb_verify_tab.py
import tkinter
from tkinter import ttk, messagebox
import customtkinter as ctk
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, UnexpectedAlertPresentException
import config
from .base_tab import BaseAutomationTab
from .autocomplete_widget import AutocompleteEntry

class EmbVerifyTab(BaseAutomationTab):
    """
    A tab for automating the e-Measurement Book (eMB) verification process.
    """
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="emb_verify")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Add row for work codes text box
        self._create_widgets()

    def _create_widgets(self):
        """Creates the user interface elements for the tab."""
        # --- Top Frame for Configuration ---
        top_frame = ctk.CTkFrame(self)
        top_frame.grid(row=0, column=0, sticky='ew', padx=10, pady=(10, 0))

        config_frame = ctk.CTkFrame(top_frame)
        config_frame.pack(pady=(0, 10), fill='x')
        config_frame.grid_columnconfigure((1, 3), weight=1)

        # Panchayat input field
        ctk.CTkLabel(config_frame, text="Panchayat Name:").grid(row=0, column=0, sticky='w', padx=15, pady=5)
        self.panchayat_entry = AutocompleteEntry(config_frame, suggestions_list=self.app.history_manager.get_suggestions("panchayat_name"))
        self.panchayat_entry.grid(row=0, column=1, columnspan=3, sticky='ew', padx=15, pady=5)
        
        # Verify Amount input field
        ctk.CTkLabel(config_frame, text="Verify Amount (₹):").grid(row=1, column=0, sticky='w', padx=15, pady=5)
        self.verify_amount_entry = ctk.CTkEntry(config_frame)
        self.verify_amount_entry.insert(0, "282")
        self.verify_amount_entry.grid(row=1, column=1, sticky='ew', padx=15, pady=5)

        # Action buttons
        action_frame_container = ctk.CTkFrame(top_frame)
        action_frame_container.pack(pady=10, fill='x')
        action_frame = self._create_action_buttons(parent_frame=action_frame_container)
        action_frame.pack(expand=True, fill='x')

        # --- Middle Frame for Work Code Input ---
        work_code_frame = ctk.CTkFrame(self)
        work_code_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=10)
        work_code_frame.grid_columnconfigure(0, weight=1)
        work_code_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(work_code_frame, text="Enter Work Codes (one per line). Leave blank to process all.").pack(anchor='w', padx=10, pady=(5,0))
        self.work_codes_text = ctk.CTkTextbox(work_code_frame, height=150)
        self.work_codes_text.pack(expand=True, fill="both", padx=10, pady=10)


        # --- Bottom Frame for Results and Logs ---
        notebook = ctk.CTkTabview(self)
        notebook.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        results_frame = notebook.add("Results")
        self._create_log_and_status_area(parent_notebook=notebook)

        # Results Tab UI
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(1, weight=1)
        
        results_action_frame = ctk.CTkFrame(results_frame, fg_color="transparent")
        results_action_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(5, 10), padx=5)
        self.export_csv_button = ctk.CTkButton(results_action_frame, text="Export to CSV", command=lambda: self.export_treeview_to_csv(self.results_tree, "emb_verify_results.csv"))
        self.export_csv_button.pack(side="left")

        cols = ("Work Code", "Status", "Details", "Timestamp")
        self.results_tree = ttk.Treeview(results_frame, columns=cols, show='headings')
        for col in cols:
            self.results_tree.heading(col, text=col)
        self.results_tree.column("Work Code", width=250)
        self.results_tree.column("Status", width=100, anchor='center')
        self.results_tree.column("Details", width=350)
        self.results_tree.column("Timestamp", width=120, anchor='center')
        self.results_tree.grid(row=1, column=0, sticky='nsew')
        
        scrollbar = ctk.CTkScrollbar(results_frame, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky='ns')
        self.style_treeview(self.results_tree)

    def set_ui_state(self, running: bool):
        """Enable or disable UI elements based on automation state."""
        self.set_common_ui_state(running)
        state = "disabled" if running else "normal"
        self.panchayat_entry.configure(state=state)
        self.verify_amount_entry.configure(state=state)
        self.work_codes_text.configure(state=state)

    def reset_ui(self):
        """Resets the UI to its initial state."""
        if messagebox.askokcancel("Reset Form?", "This will clear all inputs and results. Continue?"):
            self.panchayat_entry.delete(0, tkinter.END)
            self.verify_amount_entry.delete(0, tkinter.END)
            self.verify_amount_entry.insert(0, "282")
            self.work_codes_text.delete("1.0", tkinter.END)
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            self.app.clear_log(self.log_display)
            self.update_status("Ready", 0.0)
            self.app.log_message(self.log_display, "Form has been reset.")

    def start_automation(self):
        """Validates inputs and starts the automation thread."""
        panchayat = self.panchayat_entry.get().strip()
        verify_amount = self.verify_amount_entry.get().strip()
        
        if not panchayat or not verify_amount:
            messagebox.showwarning("Input Error", "Panchayat Name and Verify Amount are required.")
            return

        work_codes = [line.strip() for line in self.work_codes_text.get("1.0", "end-1c").splitlines() if line.strip()]
        
        self.app.update_history("panchayat_name", panchayat)
        for wc in work_codes:
            self.app.update_history("work_code", wc)

        self.app.start_automation_thread(self.automation_key, self.run_automation_logic, args=(panchayat, verify_amount, work_codes))

    def _log_result(self, work_code, status, details):
        """Logs a result to the treeview."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.app.after(0, lambda: self.results_tree.insert("", "end", values=(work_code, status, details, timestamp)))

    def run_automation_logic(self, panchayat, verify_amount, work_codes_from_ui):
        """The main logic for the eMB verification automation."""
        self.app.after(0, self.set_ui_state, True)
        self.app.clear_log(self.log_display)
        self.app.after(0, lambda: [self.results_tree.delete(item) for item in self.results_tree.get_children()])
        self.app.log_message(self.log_display, f"Starting eMB Verification for Panchayat: {panchayat}")

        try:
            driver = self.app.get_driver()
            if not driver: return

            driver.get(config.EMB_VERIFY_CONFIG["url"])
            wait = WebDriverWait(driver, 20) 

            # Select Panchayat
            self.app.log_message(self.log_display, f"Selecting Panchayat: {panchayat}")
            panchayat_select = Select(wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddl_panch"))))
            panchayat_select.select_by_visible_text(panchayat)
            
            self.app.log_message(self.log_display, "Waiting for page to reload...")
            wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddl_work")))
            time.sleep(1) 
            self.app.log_message(self.log_display, "Page reloaded successfully.")
            
            work_codes_to_process = []
            use_search = bool(work_codes_from_ui)

            if use_search:
                work_codes_to_process = work_codes_from_ui
                self.app.log_message(self.log_display, f"Processing {len(work_codes_to_process)} work codes from input.")
            else:
                self.app.log_message(self.log_display, "No work codes provided. Fetching all from dropdown...")
                work_code_select_element = Select(wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddl_work"))))
                work_codes_to_process = [opt.text for opt in work_code_select_element.options if opt.get_attribute('value')]
                if not work_codes_to_process:
                    self.app.log_message(self.log_display, "No work codes found for this Panchayat.", "warning")
                    self._log_result("N/A", "Skipped", "No work codes found.")
            
            total = len(work_codes_to_process)
            for i, current_wc in enumerate(work_codes_to_process):
                if self.app.stop_events[self.automation_key].is_set():
                    self.app.log_message(self.log_display, "Automation stopped by user.", "warning")
                    break
                
                self.app.after(0, self.update_status, f"Processing {i+1}/{total}: {current_wc}", (i+1)/total)
                self._process_single_work_code(driver, wait, current_wc, use_search, verify_amount)

                if not use_search and i < total - 1:
                    self.app.log_message(self.log_display, "Navigating back for next work code...")
                    driver.get(config.EMB_VERIFY_CONFIG["url"])
                    panchayat_select = Select(wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddl_panch"))))
                    panchayat_select.select_by_visible_text(panchayat)
                    wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddl_work")))
                    time.sleep(1)

            final_msg = "Automation finished." if not self.app.stop_events[self.automation_key].is_set() else "Stopped."
            self.app.after(0, self.update_status, final_msg, 1.0)
            if not self.app.stop_events[self.automation_key].is_set():
                messagebox.showinfo("Complete", "e-MB Verification process has finished.")

        except Exception as e:
            self.app.log_message(self.log_display, f"A critical error occurred: {e}", "error")
            messagebox.showerror("Automation Error", f"An unexpected error occurred:\n\n{e}")
        finally:
            self.app.after(0, self.set_ui_state, False)

    def _process_single_work_code(self, driver, wait, work_code, use_search, verify_amount):
        """Handles the logic for a single work code verification."""
        try:
            if use_search:
                self.app.log_message(self.log_display, f"Searching for work code: {work_code}")
                search_box = wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_txt_search")))
                search_box.clear()
                search_box.send_keys(work_code)
                driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_imgButtonSearch").click()
                time.sleep(2) 
                work_select = Select(wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddl_work"))))
                if len(work_select.options) <= 1:
                    raise NoSuchElementException(f"Work code '{work_code}' not found after search.")
                work_select.select_by_index(1)
            else:
                self.app.log_message(self.log_display, f"Selecting work code from dropdown: {work_code}")
                work_select = Select(wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddl_work"))))
                work_select.select_by_visible_text(work_code)
            
            self.app.log_message(self.log_display, "Work selected. Pausing for page to update...")
            time.sleep(2) 

            self.app.log_message(self.log_display, "Selecting 'Musterroll Period Wise'.")
            period_radio_btn = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_rbl_mustrolltype_0")))
            driver.execute_script("arguments[0].click();", period_radio_btn)
            
            self.app.log_message(self.log_display, "Waiting for measurement periods to load...")
            period_dropdown_element = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ddl_mperiod")))
            time.sleep(2) 

            period_select = Select(period_dropdown_element)
            if len(period_select.options) <= 1:
                self._log_result(work_code, "Skipped", "No measurement period available.")
                return
            period_select.select_by_index(1)
            
            self.app.log_message(self.log_display, "Waiting for activity table to load...")
            wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_grd_activitycomponent_ctl02_lbl_act_unitcost")))
            
            unit_cost = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_grd_activitycomponent_ctl02_lbl_act_unitcost").text.strip()
            wage_per_day = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_grd_activitycomponent_ctl02_lbl_wageperday").text.strip()

            self.app.log_message(self.log_display, f"Found Unit Cost: {unit_cost}, Wage Per Day: {wage_per_day} for {work_code}")

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)

            if unit_cost == verify_amount and wage_per_day == verify_amount:
                driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btn_verify").click()
                self._log_result(work_code, "Verified", f"Unit Cost & Wage were correct ({verify_amount}).")
            else:
                rejection_reason = "unit cost is not correct"
                self.app.log_message(self.log_display, f"Rejecting. Unit Cost: {unit_cost}, Wage: {wage_per_day}", "warning")
                driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txt_rejection_reason").send_keys(rejection_reason)
                driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btn_reject").click()
                self._log_result(work_code, "Rejected", f"Unit Cost: {unit_cost}, Wage: {wage_per_day}. Reason sent.")

            try:
                final_alert = WebDriverWait(driver, 5).until(EC.alert_is_present())
                self.app.log_message(self.log_display, f"Confirmation: {final_alert.text}")
                final_alert.accept()
            except TimeoutException:
                self.app.log_message(self.log_display, "No final confirmation alert appeared.", "info")

        except UnexpectedAlertPresentException as e:
            try:
                alert = driver.switch_to.alert
                self._log_result(work_code, "Failed", f"Unexpected Alert: {alert.text}")
                alert.accept()
            except: pass
        except (TimeoutException, NoSuchElementException) as e:
            self._log_result(work_code, "Failed", f"Could not find a required element or work code not found.")
            self.app.log_message(self.log_display, f"Error details: {e}", "error")
        except Exception as e:
            self._log_result(work_code, "Error", f"An unexpected error occurred: {e}")
