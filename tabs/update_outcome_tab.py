# tabs/update_outcome_tab.py
import tkinter
from tkinter import ttk, messagebox
import customtkinter as ctk
import time
import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException, NoAlertPresentException

import config
from .base_tab import BaseAutomationTab

class UpdateOutcomeTab(BaseAutomationTab):
    """
    A tab for automating the process of updating the 'Estimated Outcome' for a list of work codes.
    """
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="update_outcome")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self._create_widgets()

    def _create_widgets(self):
        # --- Main container ---
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(1, weight=1) # Let the notebook expand

        # --- Input Frame ---
        input_frame = ctk.CTkFrame(main_container)
        input_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        input_frame.grid_columnconfigure(1, weight=1)

        # Estimated Outcome Entry
        ctk.CTkLabel(input_frame, text="Estimated Outcome:").grid(row=0, column=0, padx=15, pady=10, sticky="w")
        self.outcome_entry = ctk.CTkEntry(input_frame, placeholder_text="e.g., 0.20")
        self.outcome_entry.grid(row=0, column=1, padx=15, pady=10, sticky="ew")

        # Work Codes Textbox
        ctk.CTkLabel(input_frame, text="Work Codes (one per line):").grid(row=1, column=0, columnspan=2, padx=15, pady=(10, 0), sticky="w")
        self.work_codes_textbox = ctk.CTkTextbox(input_frame, height=150)
        self.work_codes_textbox.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=15, pady=(5, 15))

        # Action Buttons moved inside the input frame
        action_frame = self._create_action_buttons(input_frame)
        action_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 15))

        # --- Results and Logs Notebook ---
        notebook = ctk.CTkTabview(main_container)
        notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        results_tab = notebook.add("Results")
        self._create_log_and_status_area(notebook)
        
        # --- Results Treeview ---
        results_tab.grid_columnconfigure(0, weight=1)
        results_tab.grid_rowconfigure(1, weight=1)

        results_action_frame = ctk.CTkFrame(results_tab, fg_color="transparent")
        results_action_frame.grid(row=0, column=0, sticky="ew", pady=(5, 10), padx=5)
        self.export_csv_button = ctk.CTkButton(results_action_frame, text="Export to CSV", command=lambda: self.export_treeview_to_csv(self.results_tree, "update_outcome_results.csv"))
        self.export_csv_button.pack(side="left")

        cols = ("Timestamp", "Work Code", "Status")
        self.results_tree = ttk.Treeview(results_tab, columns=cols, show='headings')
        self.results_tree.heading("Timestamp", text="Timestamp")
        self.results_tree.heading("Work Code", text="Work Code")
        self.results_tree.heading("Status", text="Status")
        self.results_tree.column("Timestamp", width=100, anchor="center")
        self.results_tree.column("Work Code", width=250)
        self.style_treeview(self.results_tree)

        self.results_tree.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        scrollbar = ctk.CTkScrollbar(results_tab, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky='ns')

    def _log_result(self, work_code, status):
        timestamp = time.strftime("%H:%M:%S")
        self.app.after(0, lambda: self.results_tree.insert("", "end", values=(timestamp, work_code, status)))

    def start_automation(self):
        estimated_outcome = self.outcome_entry.get().strip()
        work_codes_raw = self.work_codes_textbox.get("1.0", "end").strip()
        
        if not estimated_outcome:
            messagebox.showwarning("Input Required", "Please enter a value for 'Estimated Outcome'.")
            return
            
        if not work_codes_raw:
            messagebox.showwarning("Input Required", "Please enter at least one work code.")
            return

        work_codes = [line.strip() for line in work_codes_raw.splitlines() if line.strip()]
        
        self.app.start_automation_thread(
            self.automation_key,
            self.run_automation_logic,
            args=(work_codes, estimated_outcome)
        )

    def run_automation_logic(self, work_codes, estimated_outcome):
        self.app.after(0, self.set_ui_state, True)
        self.app.clear_log(self.log_display)
        for item in self.results_tree.get_children(): self.results_tree.delete(item)

        self.app.log_message(self.log_display, "--- Starting Estimated Outcome Update ---")
        self.app.after(0, self.app.set_status, "Running Update Outcome...")
        
        driver = self.app.get_driver()
        if not driver:
            self.app.log_message(self.log_display, "Browser not available. Please launch a browser first.", "error")
            self.app.after(0, self.set_ui_state, False)
            return

        total_codes = len(work_codes)
        for i, work_code in enumerate(work_codes):
            if self.app.stop_events[self.automation_key].is_set():
                self.app.log_message(self.log_display, "Automation stopped by user.", "warning")
                break
            
            self.update_status(f"Processing {i+1}/{total_codes}: {work_code}", (i + 1) / total_codes)
            self.app.log_message(self.log_display, f"--- Processing work code: {work_code} ---")
            
            try:
                status = self._process_single_work_code(driver, work_code, estimated_outcome)
                self._log_result(work_code, status)
                self.app.log_message(self.log_display, f"Result for {work_code}: {status}", "success" if "Success" in status else "error")
            except Exception as e:
                error_msg = str(e).splitlines()[0]
                self._log_result(work_code, f"Error: {error_msg}")
                self.app.log_message(self.log_display, f"An unexpected error occurred for {work_code}: {error_msg}", "error")

        self.app.after(0, self.set_ui_state, False)
        self.update_status("Automation Finished", 1.0)
        self.app.log_message(self.log_display, "\n--- Automation Finished ---")
        messagebox.showinfo("Complete", "Outcome update process has finished.")
        self.app.after(0, self.app.set_status, "Automation Finished")

    def _process_single_work_code(self, driver, work_code, estimated_outcome):
        wait = WebDriverWait(driver, 20)
        url = config.UPDATE_OUTCOME_CONFIG["url"]
        
        try:
            self.app.log_message(self.log_display, "Navigating to the Update Outcome page...")
            driver.get(url)
            
            # --- ADDED: A fixed delay to allow the page to fully initialize ---
            self.app.log_message(self.log_display, "Page navigation initiated. Waiting 2 seconds for page to settle...")
            time.sleep(2)
            # --- END ADDITION ---
            
            self.app.log_message(self.log_display, "Page settled. Waiting for the work code search box to be clickable...")
            search_box = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_txtwrksearchkey")))
            
            self.app.log_message(self.log_display, f"Search box found. Entering work code: {work_code}")
            search_box.clear()
            search_box.send_keys(work_code)
            search_box.send_keys(Keys.TAB)
            
            self.app.log_message(self.log_display, "Waiting for work dropdown to populate...")
            wait.until(lambda d: len(Select(d.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlworkName")).options) > 1)
            
            self.app.log_message(self.log_display, "Work dropdown populated. Selecting work...")
            work_dropdown = Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlworkName"))
            work_dropdown.select_by_index(1)
            
            self.app.log_message(self.log_display, "Waiting for page to reload after selection...")
            wait.until(EC.staleness_of(search_box))

            self.app.log_message(self.log_display, "Page reloaded. Entering estimated outcome...")
            outcome_input = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_Txtest_outcome")))
            outcome_input.clear()
            outcome_input.send_keys(estimated_outcome)
            
            self.app.log_message(self.log_display, "Clicking Save...")
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_Btnsubmit").click()
            
            self.app.log_message(self.log_display, "Waiting for success message...")
            success_message_xpath = "//*[contains(text(), 'Update successfully')]"
            wait.until(EC.visibility_of_element_located((By.XPATH, success_message_xpath)))
            return "Success: Update successfully"
                
        except UnexpectedAlertPresentException as e:
            try:
                alert_text = driver.switch_to.alert.text
                driver.switch_to.alert.accept()
                return f"Error: Unexpected alert - {alert_text}"
            except NoAlertPresentException:
                return f"Error: Unexpected alert present, but could not read it. Details: {e.text}"
        except TimeoutException:
            return "Error: Timed out waiting for a page element. The work code might be invalid or the page is slow."
        except Exception as e:
            return f"Error: {str(e).splitlines()[0]}"

    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running)
        state = "disabled" if running else "normal"
        self.outcome_entry.configure(state=state)
        self.work_codes_textbox.configure(state=state)

    def reset_ui(self):
        if messagebox.askokcancel("Reset Form?", "Are you sure you want to clear all inputs and results?"):
            self.outcome_entry.delete(0, "end")
            self.work_codes_textbox.delete("1.0", "end")
            self.app.clear_log(self.log_display)
            self.update_status("Ready", 0)
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            self.app.after(0, self.app.set_status, "Ready")
