# tabs/fto_generation_tab.py
import tkinter
from tkinter import ttk, messagebox
import customtkinter as ctk
import time, json, os, re
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoAlertPresentException

import config
from .base_tab import BaseAutomationTab

class FtoGenerationTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="fto_gen")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._create_widgets()

    def _create_widgets(self):
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls_frame.grid_columnconfigure(0, weight=1)

        note_text = "Instructions:\n1. Launch Chrome and log in to the NREGA website.\n2. Return here and click 'Start FTO Generation'."
        ctk.CTkLabel(controls_frame, text=note_text, justify="left").grid(row=0, column=0, sticky='w', padx=15, pady=10)
        
        action_frame = self._create_action_buttons(parent_frame=controls_frame)
        action_frame.grid(row=1, column=0, sticky='ew', pady=10, padx=15)
        
        notebook = ctk.CTkTabview(self)
        notebook.grid(row=1, column=0, sticky="nsew")
        self._create_log_and_status_area(parent_notebook=notebook)
        results_frame = notebook.add("Results (FTO Numbers)")

        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(0, weight=1)
        cols = ("Page", "FTO Number", "Timestamp")
        self.results_tree = ttk.Treeview(results_frame, columns=cols, show='headings')
        for col in cols: self.results_tree.heading(col, text=col)
        self.results_tree.column("Page", width=150)
        self.results_tree.column("FTO Number", width=400)
        self.results_tree.column("Timestamp", width=100, anchor='center')
        self.results_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar = ctk.CTkScrollbar(results_frame, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.style_treeview(self.results_tree)

    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running)

    def reset_ui(self):
        if messagebox.askokcancel("Reset?", "This will clear all results and logs."):
            self.app.clear_log(self.log_display)
            for item in self.results_tree.get_children(): self.results_tree.delete(item)
            self.update_status("Ready", 0)
            self.app.log_message(self.log_display, "UI has been reset.")

    def start_automation(self):
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic)
        
    def _log_result(self, page_name, fto_number):
        self.app.after(0, lambda: self.results_tree.insert("", "end", values=(page_name, fto_number, datetime.now().strftime("%H:%M:%S"))))

    def _process_verification_page(self, driver, wait, verification_url, page_identifier):
        try:
            self.app.log_message(self.log_display, f"Navigating to {page_identifier}...")
            driver.get(verification_url)
            
            # This is now the primary check for being logged in.
            wait.until(EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_wage_list_verify")))
            self.app.log_message(self.log_display, "Verification page loaded.")

            if not driver.find_elements(By.XPATH, "//input[contains(@id, '_auth')]"):
                self.app.log_message(self.log_display, "No records found on this page.", "warning")
                return "No records"

            self.app.log_message(self.log_display, "Accepting all rows...")
            driver.execute_script("document.querySelectorAll('input[id*=\"_auth\"]').forEach(radio => radio.click());")
            
            self.app.log_message(self.log_display, "Clicking 'Submit'...")
            wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ch_verified"))).click()
            
            self.app.log_message(self.log_display, "Clicking 'Authorise'...")
            wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_btn"))).click()
            
            self.app.log_message(self.log_display, "Waiting for confirmation...")
            alert = wait.until(EC.alert_is_present())
            
            fto_match = re.search(r'FTO No : \((.*?)\)', alert.text)
            fto_number = fto_match.group(1) if fto_match else "Not Found"
            
            self.app.log_message(self.log_display, f"Captured FTO: {fto_number}", "success")
            self._log_result(page_identifier, fto_number)
            alert.accept()
            return "Success" # Return a success status
        except TimeoutException:
            # This will now trigger if the user is not logged in
            self.app.log_message(self.log_display, "Could not find verification table. Are you logged in?", "error")
            return "Login Required"
        except Exception as e:
            self.app.log_message(self.log_display, f"An error occurred during {page_identifier} verification: {e}", "error")
            return "Error"

    def run_automation_logic(self):
        self.app.after(0, self.set_ui_state, True)
        self.app.clear_log(self.log_display)
        self.app.after(0, lambda: [self.results_tree.delete(item) for item in self.results_tree.get_children()])
        self.update_status("Starting...", 0)
        try:
            driver = self.app.connect_to_chrome()
            if not driver: return
            
            # --- REMOVED: The check for ftoindexframe.aspx is gone ---
            self.app.log_message(self.log_display, "Starting FTO verification process...")
            cfg = config.FTO_GEN_CONFIG
            wait = WebDriverWait(driver, 15) # Slightly shorter wait time
            
            self.update_status("Processing Aadhaar FTO...", 0.25)
            # Process the first page and check its result
            result = self._process_verification_page(driver, wait, cfg["aadhaar_fto_url"], "Aadhaar FTO")
            
            # If the first page failed due to a login issue, stop here.
            if result == "Login Required":
                messagebox.showerror("Login Required", "Could not find the FTO verification page. Please ensure you are logged in to the NREGA website.")
                return

            self.update_status("Processing Top-Up FTO...", 0.75)
            self._process_verification_page(driver, wait, cfg["top_up_fto_url"], "Top-Up FTO")
            
            self.app.log_message(self.log_display, "Workflow complete.")
            self.app.after(0, lambda: messagebox.showinfo("Workflow Complete", "Check the 'Results' tab for captured FTO numbers."))

        except Exception as e:
            error_msg = f"A critical error occurred: {e}"
            self.app.log_message(self.log_display, error_msg, "error")
            messagebox.showerror("Automation Error", error_msg)
        finally:
            self.app.after(0, self.set_ui_state, False)
            self.app.after(0, self.update_status, "Finished.", 1.0)