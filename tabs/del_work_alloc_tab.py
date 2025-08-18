# tabs/del_work_alloc_tab.py
import tkinter
from tkinter import ttk, messagebox
import customtkinter as ctk
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

import config
from .base_tab import BaseAutomationTab
from .autocomplete_widget import AutocompleteEntry

class DelWorkAllocTab(BaseAutomationTab):
    """
    A tab for automating the deletion of work allocations on the NREGA website.
    """
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="del_work_alloc")
        
        self.grid_columnconfigure(0, weight=1)
        # --- MODIFIED: Configure rows for new layout ---
        self.grid_rowconfigure(0, weight=0) # Settings row
        self.grid_rowconfigure(1, weight=0) # Action buttons row
        self.grid_rowconfigure(2, weight=1) # Results/Logs row (will expand)
        
        self._create_widgets()

    def _create_widgets(self):
        """Creates the UI elements for the tab."""
        # --- NEW: Main container for all settings, made scrollable ---
        settings_container = ctk.CTkScrollableFrame(self, label_text="Settings")
        settings_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        settings_container.grid_columnconfigure(0, weight=1)

        # Frame for input controls
        controls_frame = ctk.CTkFrame(settings_container)
        controls_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        controls_frame.grid_columnconfigure(1, weight=1)

        # Panchayat Name Input
        ctk.CTkLabel(controls_frame, text="Panchayat Name:").grid(row=0, column=0, sticky='w', padx=15, pady=10)
        self.panchayat_entry = AutocompleteEntry(controls_frame, suggestions_list=self.app.history_manager.get_suggestions("panchayat_name"))
        self.panchayat_entry.grid(row=0, column=1, sticky='ew', padx=15, pady=10)

        # --- Jobcards Input Frame (MOVED from notebook) ---
        jobcards_frame = ctk.CTkFrame(settings_container)
        jobcards_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        jobcards_frame.grid_columnconfigure(0, weight=1)
        jobcards_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(jobcards_frame, text="Jobcard / Registration IDs (one per line)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky='w', padx=15, pady=(10,0))
        ctk.CTkLabel(jobcards_frame, text="If left empty, the bot will process all Registration IDs for the selected Panchayat.", wraplength=600, justify="left").grid(row=1, column=0, sticky='w', padx=15, pady=5)
        
        self.jobcards_text = ctk.CTkTextbox(jobcards_frame, height=150)
        self.jobcards_text.grid(row=2, column=0, sticky='nsew', padx=15, pady=(5,15))

        # --- Action buttons (MOVED) ---
        action_frame = self._create_action_buttons(parent_frame=self)
        action_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0,10))

        # --- Tab view for Results and Logs (MOVED) ---
        data_notebook = ctk.CTkTabview(self)
        data_notebook.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0,10))
        
        results_tab = data_notebook.add("Results")
        self._create_log_and_status_area(parent_notebook=data_notebook)

        # Results Tab Content
        results_tab.grid_columnconfigure(0, weight=1)
        results_tab.grid_rowconfigure(1, weight=1)

        results_action_frame = ctk.CTkFrame(results_tab, fg_color="transparent")
        results_action_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(5, 10), padx=5)
        self.export_csv_button = ctk.CTkButton(results_action_frame, text="Export to CSV", command=lambda: self.export_treeview_to_csv(self.results_tree, "delete_work_alloc_results.csv"))
        self.export_csv_button.pack(side="left")

        cols = ("Timestamp", "Panchayat", "Jobcard/RegID", "Status", "Details")
        self.results_tree = ttk.Treeview(results_tab, columns=cols, show='headings')
        for col in cols:
            self.results_tree.heading(col, text=col)
        
        self.results_tree.column("Timestamp", width=80, anchor='center')
        self.results_tree.column("Panchayat", width=150)
        self.results_tree.column("Jobcard/RegID", width=200)
        self.results_tree.column("Status", width=100, anchor='center')
        self.results_tree.column("Details", width=350)
        
        self.results_tree.grid(row=1, column=0, sticky='nsew')
        scrollbar = ctk.CTkScrollbar(results_tab, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky='ns')
        
        self.style_treeview(self.results_tree)

    def set_ui_state(self, running: bool):
        """Enable or disable UI elements based on automation state."""
        self.set_common_ui_state(running)
        state = "disabled" if running else "normal"
        self.panchayat_entry.configure(state=state)
        self.jobcards_text.configure(state=state)

    def start_automation(self):
        """Gathers inputs and starts the automation thread."""
        panchayat = self.panchayat_entry.get().strip()
        if not panchayat:
            messagebox.showwarning("Input Error", "Panchayat Name is required.")
            return

        # Clear previous results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        jobcard_list = [line.strip() for line in self.jobcards_text.get("1.0", tkinter.END).strip().splitlines() if line.strip()]
        
        self.app.update_history("panchayat_name", panchayat)
        
        # Start the automation logic in a separate thread
        self.app.start_automation_thread(
            self.automation_key, 
            self.run_automation_logic, 
            args=(panchayat, jobcard_list)
        )

    def reset_ui(self):
        """Resets the UI to its initial state."""
        if messagebox.askokcancel("Reset Form?", "Clear all inputs and logs?"):
            self.panchayat_entry.delete(0, tkinter.END)
            self.jobcards_text.delete('1.0', tkinter.END)
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            self.app.clear_log(self.log_display)
            self.update_status("Ready", 0.0)
            self.app.log_message(self.log_display, "Form has been reset.")
            self.app.after(0, self.app.set_status, "Ready")

    def run_automation_logic(self, panchayat, jobcard_list):
        """The core logic for the web automation task."""
        self.app.after(0, self.set_ui_state, True)
        self.app.clear_log(self.log_display)
        self.app.log_message(self.log_display, f"Starting Delete Work Allocation for Panchayat: {panchayat}")
        self.app.after(0, self.app.set_status, "Running Delete Work Allocation...")

        try:
            driver = self.app.get_driver()
            if not driver:
                return

            # Determine the mode of operation
            auto_mode = not bool(jobcard_list)
            items_to_process = []

            # Navigate and select Panchayat
            driver.get(config.DEL_WORK_ALLOC_CONFIG["url"])
            wait = WebDriverWait(driver, 20)
            
            self.app.log_message(self.log_display, "Selecting Panchayat...")
            panchayat_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddlpanchayat_code"))))
            panchayat_dropdown.select_by_visible_text(panchayat)
            
            # Wait for the registration dropdown to be populated, which indicates the page has reloaded.
            wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ddlRegistration")))
            time.sleep(1) # Add a small buffer for safety
            self.app.log_message(self.log_display, "Panchayat selected successfully.", "success")

            if auto_mode:
                self.app.log_message(self.log_display, "Auto Mode: Fetching all Registration IDs.")
                reg_id_dropdown_element = wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddlRegistration")))
                reg_id_dropdown = Select(reg_id_dropdown_element)
                items_to_process = [opt.get_attribute("value") for opt in reg_id_dropdown.options if opt.get_attribute("value")]
                if not items_to_process:
                    self.app.log_message(self.log_display, "No Registration IDs found for this Panchayat.", "warning")
            else:
                self.app.log_message(self.log_display, f"Manual Mode: Processing {len(jobcard_list)} provided IDs.")
                items_to_process = jobcard_list

            total_items = len(items_to_process)
            for i, item_id in enumerate(items_to_process):
                if self.app.stop_events[self.automation_key].is_set():
                    self.app.log_message(self.log_display, "Automation stopped by user.", "warning")
                    break
                
                self.app.after(0, self.update_status, f"Processing {i+1}/{total_items}: {item_id}", (i+1) / total_items)
                self._process_single_id(driver, wait, panchayat, item_id, auto_mode)

            final_msg = "Automation finished." if not self.app.stop_events[self.automation_key].is_set() else "Stopped."
            self.app.after(0, self.update_status, final_msg, 1.0)
            if not self.app.stop_events[self.automation_key].is_set():
                messagebox.showinfo("Complete", "Delete Work Allocation process has finished.")

        except Exception as e:
            self.app.log_message(self.log_display, f"A critical error occurred: {e}", "error")
            messagebox.showerror("Automation Error", f"An error occurred:\n\n{e}")
        finally:
            self.app.after(0, self.set_ui_state, False)
            self.app.after(0, self.app.set_status, "Automation Finished")

    def _process_single_id(self, driver, wait, panchayat, item_id, is_auto_mode):
        """Processes a single Jobcard or Registration ID."""
        try:
            # If not in auto mode, search for the jobcard first
            if not is_auto_mode:
                self.app.log_message(self.log_display, f"Searching for Jobcard/RegID: {item_id}")
                search_box = wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_txtRegSearch")))
                search_box.clear()
                search_box.send_keys(item_id)
                search_box.send_keys(Keys.TAB)
                # Wait for the postback to complete by checking if the dropdown is populated
                wait.until(lambda d: len(Select(d.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlRegistration")).options) > 1)
                time.sleep(1) # Extra buffer

            # Now, select the Registration ID from the dropdown
            reg_id_dropdown_element = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ddlRegistration")))
            reg_id_dropdown = Select(reg_id_dropdown_element)

            if is_auto_mode:
                reg_id_dropdown.select_by_value(item_id)
            else: 
                # After searching, the correct ID should be the first selectable option
                if len(reg_id_dropdown.options) > 1:
                    reg_id_dropdown.select_by_index(1)
                else:
                    raise ValueError("Jobcard search returned no results.")

            # Wait for the grid to appear/reload after selecting the registration ID
            grid_view = wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_GridView1")))
            self.app.log_message(self.log_display, f"Details loaded for {item_id}.")
            
            # Check if there's anything to delete
            try:
                select_all_checkbox = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_GridView1_ctl01_chkHAllocate")
            except NoSuchElementException:
                self._log_result(panchayat, item_id, "Skipped", "No work allocations found to delete.")
                return

            # Proceed with deletion
            select_all_checkbox.click()
            time.sleep(0.5) # Small delay for safety
            
            proceed_button = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_cmdUpdate")
            proceed_button.click()
            
            # --- REVISED SUCCESS/FAILURE LOGIC ---
            try:
                # A successful deletion reloads the page, making the old grid element stale.
                wait.until(EC.staleness_of(grid_view))
                self._log_result(panchayat, item_id, "Success", "Work allocation deleted.")
            except TimeoutException:
                # If the page doesn't reload, check for an explicit error message.
                try:
                    error_element = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_lblMsg")
                    error_text = error_element.text.strip()
                    self._log_result(panchayat, item_id, "Failed", error_text if error_text else "Unknown error after clicking proceed.")
                except NoSuchElementException:
                    self._log_result(panchayat, item_id, "Failed", "Page did not reload and no error message found.")


        except (TimeoutException, NoSuchElementException, StaleElementReferenceException, ValueError) as e:
            error_msg = str(e).split('\n')[0]
            self.app.log_message(self.log_display, f"Failed to process {item_id}: {error_msg}", "error")
            self._log_result(panchayat, item_id, "Failed", error_msg)
            # Attempt to recover by going back to the page for the next item
            try:
                driver.get(config.DEL_WORK_ALLOC_CONFIG["url"])
                Select(wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddlpanchayat_code")))).select_by_visible_text(panchayat)
                wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ddlRegistration")))
            except Exception as recovery_e:
                self.app.log_message(self.log_display, f"Recovery failed: {recovery_e}", "error")


    def _log_result(self, panchayat, item_id, status, details):
        """Logs the outcome of an operation to the results Treeview."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        values = (timestamp, panchayat, item_id, status, details)
        self.app.after(0, lambda: self.results_tree.insert("", "end", values=values))
