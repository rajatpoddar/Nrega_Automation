# tabs/mb_entry_tab.py
import tkinter
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import time, os, json, sys, subprocess, random
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
        """Initializes the eMB Entry tab."""
        super().__init__(parent, app_instance, automation_key="mb_entry")
        
        # Path to save/load form inputs
        self.config_file = self.app.get_data_path("mb_entry_inputs.json")
        
        # Dictionary to hold form field variables
        self.config_vars = {}
        
        # Variable for the "Auto MB No." checkbox
        self.auto_mb_no_var = ctk.BooleanVar(value=True)
        
        # --- Panchayat-dependent mate name logic ---
        self.panchayat_after_id = None # ID for debouncing panchayat key release
        self.notebook = None # To store the tab view instance
        # ---

        # Configure grid layout
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)
        
        # Create and load UI elements
        self._create_widgets(); self._load_inputs()
        self._toggle_mb_no_entry() # Set initial state of MB No. entry

    def _create_widgets(self):
        """Creates and places all UI elements for this tab."""
        
        # --- Top Frame for Configuration ---
        top_frame = ctk.CTkFrame(self)
        top_frame.grid(row=0, column=0, sticky='ew', padx=10, pady=(10,0))
        
        config_frame = ctk.CTkFrame(top_frame)
        config_frame.pack(pady=(0, 10), fill='x')
        
        # --- FIX: Corrected 'grid_column' to 'grid_columnconfigure' ---
        config_frame.grid_columnconfigure((1, 3), weight=1)
        
        # --- Form Fields ---
        self.panchayat_entry = self._create_autocomplete_field(config_frame, "panchayat_name", "Panchayat Name", 0, 0)
        # Bind key release to update mate names dynamically
        self.panchayat_entry.bind("<KeyRelease>", self._on_panchayat_change_debounced)
        
        # --- MB No. with Auto Checkbox ---
        ctk.CTkLabel(config_frame, text="MB No.").grid(row=1, column=0, sticky='w', padx=15, pady=5)
        mb_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        mb_frame.grid(row=1, column=1, sticky='ew', padx=15, pady=5)
        mb_frame.grid_columnconfigure(0, weight=1)
        
        mb_var = ctk.StringVar()
        self.config_vars["measurement_book_no"] = mb_var
        self.mb_no_entry = ctk.CTkEntry(mb_frame, textvariable=mb_var)
        self.mb_no_entry.grid(row=0, column=0, sticky='ew')

        self.auto_mb_no_checkbox = ctk.CTkCheckBox(
            mb_frame, text="Auto", variable=self.auto_mb_no_var,
            command=self._toggle_mb_no_entry
        )
        self.auto_mb_no_checkbox.grid(row=0, column=1, padx=(10, 0))
        # --- End MB No. Section ---

        self.page_no_entry = self._create_field(config_frame, "page_no", "Page No.", 1, 2)
        self.unit_cost_entry = self._create_field(config_frame, "unit_cost", "Unit Cost (₹)", 2, 0)
        self.pit_count_entry = self._create_field(config_frame, "default_pit_count", "Pit Count", 2, 2)
        
        # Create mate name entry (key will be updated dynamically)
        self.mate_name_entry = self._create_autocomplete_field(config_frame, "mate_name", "Mate Names (comma-separated)", 3, 0)
        # Set the correct dynamic key based on loaded panchayat
        self._on_panchayat_change()

        # Note for user
        note = ctk.CTkLabel(config_frame, text="ℹ️ Note: Use this emb automation only for single activity works.", text_color="#E53E3E", wraplength=450)
        note.grid(row=4, column=0, columnspan=4, sticky='w', padx=15, pady=(10, 15))

        # --- Action Buttons (Start, Stop, Reset) ---
        action_frame_container = ctk.CTkFrame(top_frame)
        action_frame_container.pack(pady=10, fill='x')
        action_frame = self._create_action_buttons(parent_frame=action_frame_container)
        action_frame.pack(expand=True, fill='x')
        
        # --- Tab View for Work Codes, Results, Logs ---
        self.notebook = ctk.CTkTabview(self)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10))
        work_codes_frame = self.notebook.add("Work Codes")
        results_frame = self.notebook.add("Results")
        self._create_log_and_status_area(parent_notebook=self.notebook) # Adds "Logs & Status" tab

        # --- Work Codes Tab ---
        work_codes_frame.grid_columnconfigure(0, weight=1); work_codes_frame.grid_rowconfigure(1, weight=1)
        wc_controls_frame = ctk.CTkFrame(work_codes_frame, fg_color="transparent")
        wc_controls_frame.grid(row=0, column=0, sticky='ew')
        
        clear_button = ctk.CTkButton(wc_controls_frame, text="Clear", width=80, command=lambda: self.work_codes_text.delete("1.0", tkinter.END))
        clear_button.pack(side='right', pady=(5,0), padx=(0,5))
        
        # Button to extract workcodes/wagelists from pasted text
        extract_button = ctk.CTkButton(wc_controls_frame, text="Extract from Text", width=120,
                                       command=lambda: self._extract_and_update_workcodes(self.work_codes_text))
        extract_button.pack(side='right', pady=(5,0), padx=(0, 5))
        
        self.work_codes_text = ctk.CTkTextbox(work_codes_frame, wrap=tkinter.WORD)
        self.work_codes_text.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        
        # --- Results Tab ---
        results_frame.grid_columnconfigure(0, weight=1); results_frame.grid_rowconfigure(1, weight=1)
        results_action_frame = ctk.CTkFrame(results_frame, fg_color="transparent")
        results_action_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(5, 10), padx=5)
        
        export_controls_frame = ctk.CTkFrame(results_action_frame, fg_color="transparent")
        export_controls_frame.pack(side='right', padx=(10, 0))
        self.export_button = ctk.CTkButton(export_controls_frame, text="Export Report", command=self.export_report)
        self.export_button.pack(side='left')
        self.export_format_menu = ctk.CTkOptionMenu(export_controls_frame, width=130, values=["PDF (.pdf)", "CSV (.csv)"], command=self._on_format_change)
        self.export_format_menu.pack(side='left', padx=5)
        self.export_filter_menu = ctk.CTkOptionMenu(export_controls_frame, width=150, values=["Export All", "Success Only", "Failed Only"])
        self.export_filter_menu.pack(side='left', padx=(0, 5))

        # --- Results Treeview ---
        cols = ("Work Code", "Status", "Details", "Timestamp")
        self.results_tree = ttk.Treeview(results_frame, columns=cols, show='headings')
        for col in cols: self.results_tree.heading(col, text=col)
        self.results_tree.column("Work Code", width=200); self.results_tree.column("Status", width=100, anchor='center'); self.results_tree.column("Details", width=350); self.results_tree.column("Timestamp", width=100, anchor='center')
        self.results_tree.grid(row=1, column=0, sticky='nsew')
        scrollbar = ctk.CTkScrollbar(results_frame, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set); scrollbar.grid(row=1, column=1, sticky='ns')
        self.style_treeview(self.results_tree); self._setup_treeview_sorting(self.results_tree)

    def _toggle_mb_no_entry(self):
        """Enables or disables the MB No. entry based on the 'Auto' checkbox."""
        if self.auto_mb_no_var.get():
            # Auto is checked: Disable entry and set placeholder text
            self.mb_no_entry.configure(state="disabled")
            self.config_vars["measurement_book_no"].set("Auto from Workcode")
        else:
            # Auto is unchecked: Enable entry and load saved value
            self.mb_no_entry.configure(state="normal")
            saved_data = {}
            if os.path.exists(self.config_file):
                try:
                    with open(self.config_file, 'r') as f: saved_data = json.load(f)
                except (json.JSONDecodeError, IOError): pass
            self.config_vars["measurement_book_no"].set(saved_data.get("measurement_book_no", ""))

    def _on_format_change(self, selected_format):
        """Disables the 'Success/Failed' filter when CSV is selected."""
        if "CSV" in selected_format: self.export_filter_menu.configure(state="disabled")
        else: self.export_filter_menu.configure(state="normal")

    def _create_field(self, parent, key, text, r, c):
        """Helper to create a standard text entry field."""
        ctk.CTkLabel(parent, text=text).grid(row=r, column=c, sticky='w', padx=15, pady=5)
        var = ctk.StringVar(); self.config_vars[key] = var
        entry = ctk.CTkEntry(parent, textvariable=var)
        entry.grid(row=r, column=c+1, sticky='ew', padx=15, pady=5)
        return entry

    def _create_autocomplete_field(self, parent, key, text, r, c):
        """Helper to create an autocomplete entry field."""
        ctk.CTkLabel(parent, text=text).grid(row=r, column=c, sticky='w', padx=15, pady=5)
        var = ctk.StringVar(); self.config_vars[key] = var
        
        # Get initial suggestions from history
        initial_suggestions = self.app.history_manager.get_suggestions(key)
        
        # Create the widget, passing app instance and history key for deletion
        entry = AutocompleteEntry(parent, 
                                  textvariable=var, 
                                  suggestions_list=initial_suggestions,
                                  app_instance=self.app, # Pass app
                                  history_key=key)       # Pass key

        entry.grid(row=r, column=c+1, columnspan=3, sticky='ew', padx=15, pady=5)
        return entry

    # --- Panchayat-dependent mate name logic ---

    def _get_current_mate_key(self):
        """Generates a dynamic history key for mates based on the panchayat name."""
        panchayat_name = self.panchayat_entry.get().strip().lower()
        # Create a safe key (e.g., "palojori")
        panchayat_safe_name = "".join(c for c in panchayat_name if c.isalnum() or c == '_').rstrip()
        
        if not panchayat_safe_name:
            return "mate_name_default" # Default key if no panchayat is entered
        
        return f"mate_name_{panchayat_safe_name}"

    def _on_panchayat_change_debounced(self, event=None):
        """
        Debounces the panchayat entry's KeyRelease event.
        Waits 300ms after user stops typing to update mate names.
        """
        # Cancel any pending update
        if self.panchayat_after_id:
            self.after_cancel(self.panchayat_after_id)
        
        # Don't update on navigation keys
        if event and event.keysym in ("Up", "Down", "Return", "Enter", "Tab"):
            return
            
        # Schedule a new update
        self.panchayat_after_id = self.after(300, self._on_panchayat_change)

    def _on_panchayat_change(self):
        """
        Updates the mate name suggestions based on the current panchayat.
        Called by the debouncer or directly when loading data.
        """
        # Cancel any pending job, just in case
        if self.panchayat_after_id:
            self.after_cancel(self.panchayat_after_id)
            self.panchayat_after_id = None

        # Get the new dynamic key (e.g., "mate_name_palojori")
        mate_key = self._get_current_mate_key()
        
        # Get the list of mates for this specific panchayat
        new_suggestions = self.app.history_manager.get_suggestions(mate_key)
        
        if self.mate_name_entry:
            # Update the autocomplete widget with the new key and suggestion list
            self.mate_name_entry.history_key = mate_key
            self.mate_name_entry.suggestions = new_suggestions
            self.mate_name_entry.delete(0, "end") # Clear old mate name
    
    # --- End of Panchayat-dependent logic ---

    def set_ui_state(self, running: bool):
        """Enables or disables UI elements based on automation state."""
        self.set_common_ui_state(running) # Handles Start, Stop, Reset buttons
        state = "disabled" if running else "normal"
        
        # Toggle all form elements
        self.work_codes_text.configure(state=state)
        self.panchayat_entry.configure(state=state)
        self.page_no_entry.configure(state=state)
        self.unit_cost_entry.configure(state=state)
        self.mate_name_entry.configure(state=state)
        self.pit_count_entry.configure(state=state)
        self.export_button.configure(state=state)
        self.export_format_menu.configure(state=state)
        self.export_filter_menu.configure(state=state)
        self.auto_mb_no_checkbox.configure(state=state)

        if state == "normal":
            # If enabling UI, set correct dependent states
            self._on_format_change(self.export_format_menu.get())
            self._toggle_mb_no_entry()
        else:
            # If disabling, ensure MB entry is also disabled
            self.mb_no_entry.configure(state="disabled")

    def reset_ui(self):
        """Resets the form to default values."""
        if messagebox.askokcancel("Reset Form?", "Clear all inputs and logs?"):
            self._load_inputs() # Load saved defaults
            self.config_vars['panchayat_name'].set("") # Clear panchayat
            self.work_codes_text.configure(state="normal")
            self.work_codes_text.delete("1.0", tkinter.END)
            self.work_codes_text.configure(state="disabled")
            for item in self.results_tree.get_children(): self.results_tree.delete(item)
            self.app.clear_log(self.log_display)
            self.update_status("Ready", 0.0)
            self.app.log_message(self.log_display, "Form has been reset.")
            self.app.after(0, self.app.set_status, "Ready")

    def start_automation(self):
        """Validates inputs and starts the automation thread."""
        # Get all config values
        cfg = {key: var.get().strip() for key, var in self.config_vars.items()}
        
        # Validate MB No.
        if not self.auto_mb_no_var.get() and not cfg.get("measurement_book_no"):
            messagebox.showwarning("Input Error", "MB No. field is required when 'Auto' is unchecked.")
            return
            
        # Validate other required fields
        required_fields = ["panchayat_name", "page_no", "unit_cost", "default_pit_count", "mate_name"]
        if any(not cfg.get(key) for key in required_fields):
            messagebox.showwarning("Input Error", "All configuration fields must be filled out.")
            return

        # Get and validate work codes
        work_codes_raw = [line.strip() for line in self.work_codes_text.get("1.0", tkinter.END).strip().splitlines() if line.strip()]
        if not work_codes_raw:
            messagebox.showwarning("Input Required", "Please paste at least one work code.")
            return
            
        # Save inputs for next session
        self._save_inputs(cfg)
        
        # Start the automation in a new thread
        self.app.start_automation_thread(
            self.automation_key, 
            self.run_automation_logic, 
            args=(cfg, work_codes_raw)
        )
    
    def _save_inputs(self, cfg):
        """Saves configuration to a JSON file."""
        try:
            with open(self.config_file, 'w') as f: json.dump(cfg, f, indent=4)
        except Exception as e: 
            self.app.log_message(self.log_display, f"Could not save inputs: {e}", "warning")

    def _load_inputs(self):
        """Loads configuration from a JSON file."""
        saved_data = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f: saved_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e: 
                self.app.log_message(self.log_display, f"Could not load inputs: {e}", "warning")
        
        # Set values, falling back to defaults if not found
        for key, var in self.config_vars.items():
            default_value = config.MB_ENTRY_CONFIG["defaults"].get(key, "")
            var.set(saved_data.get(key, default_value))
        
        # Update mate suggestions based on the loaded panchayat
        self.after(100, self._on_panchayat_change)

    def run_automation_logic(self, cfg, work_codes_raw):
        """The main logic for the eMB Entry automation thread."""
        
        # --- UI Setup ---
        self.app.after(0, self.set_ui_state, True) # Disable UI
        self.app.clear_log(self.log_display) # Clear log
        self.app.after(0, lambda: [self.results_tree.delete(item) for item in self.results_tree.get_children()]) # Clear tree
        self.app.log_message(self.log_display, "Starting eMB Entry automation...")
        self.app.after(0, self.app.set_status, "Running eMB Entry...") # App-level status
        
        try:
            driver = self.app.get_driver()
            if not driver: 
                return # Exit if browser not found

            # Validate and prepare mate names
            mate_names_list = [name.strip() for name in cfg["mate_name"].split(',') if name.strip()]
            if not mate_names_list:
                messagebox.showerror("Input Error", "Please provide at least one Mate Name.")
                return

            # --- Save to History ---
            if not self.app.stop_events[self.automation_key].is_set():
                self.app.update_history("panchayat_name", cfg['panchayat_name'])
                # Save mates under the dynamic, panchayat-specific key
                mate_key = self._get_current_mate_key()
                for mate in mate_names_list:
                    self.app.update_history(mate_key, mate)
            
            processed_codes = set() # To avoid processing duplicates
            total = len(work_codes_raw)
            self.app.after(0, self.app.set_status, f"Starting eMB Entry for {total} workcodes...")

            # --- Main Loop ---
            for i, work_code in enumerate(work_codes_raw):
                if self.app.stop_events[self.automation_key].is_set():
                    self.app.log_message(self.log_display, "Automation stopped.", "warning"); break
                
                # Update per-workcode status
                self.app.after(0, self.update_status, f"Processing {i+1}/{total}: {work_code}", (i+1) / total)
                
                if work_code in processed_codes:
                    self._log_result(work_code, "Skipped", "Duplicate entry."); continue
                
                # Process the work code
                self._process_single_work_code(driver, work_code, cfg, mate_names_list)
                processed_codes.add(work_code) # Mark as processed

            # --- Completion ---
            final_msg = "Automation finished." if not self.app.stop_events[self.automation_key].is_set() else "Stopped."
            self.app.after(0, self.update_status, final_msg, 1.0)
            if not self.app.stop_events[self.automation_key].is_set(): 
                messagebox.showinfo("Complete", "e-MB Entry process has finished.")
        
        except Exception as e:
            # --- Error Handling ---
            self.app.log_message(self.log_display, f"A critical error occurred: {e}", "error")
            messagebox.showerror("Automation Error", f"An error occurred:\n\n{e}")
        
        finally:
            # --- Cleanup ---
            self.app.after(0, self.set_ui_state, False) # Re-enable UI
            self.app.after(0, self.app.set_status, "Automation Finished")

    def _log_result(self, work_code, status, details):
        """Helper to add a row to the results treeview on the main thread."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        tags = ('failed',) if 'success' not in status.lower() else ()
        self.app.after(0, lambda: self.results_tree.insert("", "end", values=(work_code, status, details, timestamp), tags=tags))

    def _process_single_work_code(self, driver, work_code, cfg, mate_names_list):
        """Performs the browser automation for a single work code."""
        wait = WebDriverWait(driver, 20)
        try:
            self.app.after(0, self.app.set_status, f"Navigating for {work_code}...")
            driver.get(config.MB_ENTRY_CONFIG["url"])
            
            # --- 1. Select Panchayat (if not GP login) ---
            try:
                panchayat_dropdown = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_ddl_panch')))
                page_body = driver.find_element(By.TAG_NAME, 'body')
                self.app.log_message(self.log_display, f"Selecting Panchayat '{cfg['panchayat_name']}'...")
                self.app.after(0, self.app.set_status, f"Selecting Panchayat for {work_code}...")
                Select(panchayat_dropdown).select_by_visible_text(cfg['panchayat_name'])
                wait.until(EC.staleness_of(page_body)) # Wait for page reload
            except (TimeoutException, NoSuchElementException):
                self.app.log_message(self.log_display, "Panchayat dropdown not needed (GP Login).", "info")
            
            # --- 2. Determine MB No ---
            mb_no_to_use = cfg["measurement_book_no"]
            if self.auto_mb_no_var.get():
                if len(work_code) >= 4:
                    mb_no_to_use = work_code[-4:] # Use last 4 digits
                    self.app.log_message(self.log_display, f"Using auto MB No: {mb_no_to_use} from workcode.", "info")
                else:
                    self.app.log_message(self.log_display, "Workcode too short for auto MB No. Using manual value.", "warning")

            # --- 3. Fill Initial Form ---
            self.app.after(0, self.app.set_status, f"Searching {work_code}...")
            wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_txtMBNo'))).send_keys(mb_no_to_use)
            driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtpageno').send_keys(cfg["page_no"])
            driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtWrkCode').send_keys(work_code)
            driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_imgButtonSearch').click()
            
            # --- 4. Select Work and Period ---
            self.app.after(0, self.app.set_status, f"Selecting work details for {work_code}...")
            wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_ddlSelWrk'))); time.sleep(1) # Wait for JS
            select_work = Select(driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_ddlSelWrk'))
            if len(select_work.options) <= 1: raise ValueError("Work code not found/processed.")
            select_work.select_by_index(1) # Select first work in list
            
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_rddist_0").click() # Click 'Distinct' radio
            time.sleep(2) # Wait for period to load
            
            period_dropdown = Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlSelMPeriod"))
            if len(period_dropdown.options) <= 1: raise ValueError("No measurement period found.")
            period_dropdown.select_by_index(1) # Select first period
            
            # --- 5. Validate Person Days ---
            total_persondays_str = driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_lbl_person_days').get_attribute('value').strip()
            total_persondays = int(total_persondays_str) if total_persondays_str else 0
            if total_persondays == 0: raise ValueError("eMB already Booked or 0 persondays")

            # --- 6. Fill Activity Details ---
            self.app.after(0, self.app.set_status, f"Finding activity for {work_code}...")
            prefix = self._find_activity_prefix(driver) # Find 'Earth work' row
            driver.find_element(By.NAME, f'{prefix}$qty').send_keys(str(total_persondays))
            driver.find_element(By.NAME, f'{prefix}$unitcost').send_keys(cfg["unit_cost"])
            driver.find_element(By.NAME, f'{prefix}$labcomp').send_keys(str(total_persondays * int(cfg["unit_cost"])))
            
            # Fill pit count (if field exists)
            try: driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtpit").send_keys(cfg["default_pit_count"])
            except NoSuchElementException: pass # Field doesn't exist, skip

            # --- 7. Fill Mate Name and Save ---
            random_mate = random.choice(mate_names_list)
            self.app.log_message(self.log_display, f"Randomly selected Mate: {random_mate}")
            mate_name_field = driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_txt_mat_name')
            mate_name_field.clear()
            mate_name_field.send_keys(random_mate)

            self.app.after(0, self.app.set_status, f"Saving eMB for {work_code}...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);"); time.sleep(0.5)
            driver.find_element(By.XPATH, '//input[@value="Save"]').click()
            
            # --- 8. Handle Confirmation Alert ---
            try:
                alert = WebDriverWait(driver, 5).until(EC.alert_is_present())
                self._log_result(work_code, "Success", alert.text); alert.accept()
            except TimeoutException:
                self._log_result(work_code, "Success", "Saved (No confirmation alert).") # Assume success if no alert
        
        # --- Specific Error Handling ---
        except UnexpectedAlertPresentException:
            try:
                alert = driver.switch_to.alert
                self._log_result(work_code, "Failed", f"Unexpected Alert: {alert.text}")
                alert.accept()
            except: pass # Ignore errors trying to handle alert
        except ValueError as e:
            error_message = str(e)
            if "No measurement period found" in error_message: self._log_result(work_code, "Failed", "MR Not Filled Yet")
            elif "eMB already Booked" in error_message: self._log_result(work_code, "Failed", "eMB already Booked.")
            else: self._log_result(work_code, "Failed", f"{type(e).__name__}: {error_message.splitlines()[0]}")
        except NoSuchElementException: 
            self._log_result(work_code, "Failed", "Add Activity for PMAYG/ IAY Houses") # Common error
        except Exception as e: 
            self._log_result(work_code, "Failed", f"{type(e).__name__}: {str(e).splitlines()[0]}") # Generic error
            
    def _find_activity_prefix(self, driver):
        """Finds the 'Earth work' activity row to fill data."""
        self.app.log_message(self.log_display, "Searching for 'Earth work' activity...")
        for i in range(1, 61): # Check up to 60 activities
            try:
                activity_id = f"ctl00_ContentPlaceHolder1_activity_ctl{str(i).zfill(2)}_act_name"
                if "earth work" in driver.find_element(By.ID, activity_id).text.lower():
                    self.app.log_message(self.log_display, f"✅ Found 'Earth work' in row #{i}.", "success")
                    # Return the prefix needed for input fields (e.g., ctl00$ContentPlaceHolder1$activity$ctl01)
                    return f"ctl00$ContentPlaceHolder1$activity$ctl{str(i).zfill(2)}"
            except NoSuchElementException: 
                continue # Row doesn't exist, check next
        self.app.log_message(self.log_display, "⚠️ 'Earth work' not found, defaulting to first row (ctl01).", "warning")
        return "ctl00$ContentPlaceHolder1$activity$ctl01"
    
    def export_report(self):
        """Handles the logic for exporting data to PDF or CSV."""
        export_format = self.export_format_menu.get()
        if "CSV" in export_format:
            self.export_treeview_to_csv(self.results_tree, "mb_entry_results.csv"); return
            
        data, file_path = self._get_filtered_data_and_filepath(export_format)
        if not data: return
        
        if "PDF" in export_format: 
            self._handle_pdf_export(data, file_path)

    def _get_filtered_data_and_filepath(self, export_format):
        """Filters treeview data and gets a save file path from the user."""
        all_items = self.results_tree.get_children()
        if not all_items: 
            messagebox.showinfo("No Data", "There are no results to export."); return None, None
            
        panchayat_name = self.panchayat_entry.get().strip()
        if not panchayat_name: 
            messagebox.showwarning("Input Needed", "Please enter a Panchayat Name for the report title."); return None, None
            
        # Filter data based on dropdown
        filter_option = self.export_filter_menu.get()
        data_to_export = []
        for item_id in all_items:
            row_values = self.results_tree.item(item_id)['values']
            status = row_values[1].upper() # Status is the second column
            if filter_option == "Export All": data_to_export.append(row_values)
            elif filter_option == "Success Only" and "SUCCESS" in status: data_to_export.append(row_values)
            elif filter_option == "Failed Only" and "SUCCESS" not in status: data_to_export.append(row_values)
            
        if not data_to_export: 
            messagebox.showinfo("No Data", f"No records found for filter '{filter_option}'."); return None, None

        # --- Get Save Path ---
        safe_name = "".join(c for c in panchayat_name if c.isalnum() or c in (' ', '_')).rstrip()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_details = {"Image (.jpg)": { "ext": ".jpg", "types": [("JPEG Image", "*.jpg")]}, "PDF (.pdf)": { "ext": ".pdf", "types": [("PDF Document", "*.pdf")]}}
        details = file_details[export_format]
        filename = f"eMB_Entry_Report_{safe_name}_{timestamp}{details['ext']}"
        file_path = filedialog.asksaveasfilename(defaultextension=details['ext'], filetypes=details['types'], initialdir=self.app.get_user_downloads_path(), initialfile=filename, title="Save Report")
        
        return (data_to_export, file_path) if file_path else (None, None)
    
    def _handle_pdf_export(self, data, file_path):
        """Generates and saves a PDF report."""
        headers = self.results_tree['columns'] # ("Work Code", "Status", "Details", "Timestamp")
        col_widths = [70, 45, 130, 25] # Relative widths
        title = f"eMB Entry Report: {self.panchayat_entry.get().strip()}"
        report_date = datetime.now().strftime('%d %b %Y')
        
        success = self.generate_report_pdf(data, headers, col_widths, title, report_date, file_path)
        
        if success:
            if messagebox.askyesno("Success", f"PDF Report saved to:\n{file_path}\n\nDo you want to open it?"):
                if sys.platform == "win32": os.startfile(file_path)
                else: subprocess.call(['open', file_path])
    
    def load_data_from_mr_tracking(self, workcodes: str, panchayat_name: str):
        """
        Receives data from the MR Tracking tab and populates the form.
        Called by main_app.py.
        """
        # Set Panchayat
        self.panchayat_entry.delete(0, tkinter.END)
        self.panchayat_entry.insert(0, panchayat_name)
        
        # Manually trigger the update for mate suggestions
        self._on_panchayat_change()
        
        # Set Workcodes
        self.work_codes_text.configure(state="normal")
        self.work_codes_text.delete("1.0", tkinter.END)
        self.work_codes_text.insert("1.0", workcodes)
        self.work_codes_text.configure(state="disabled")
        
        # Switch to the Work Codes tab so the user sees the data
        if self.notebook:
            self.notebook.set("Work Codes")
