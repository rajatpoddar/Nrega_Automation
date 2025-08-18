# tabs/add_activity_tab.py
import tkinter
from tkinter import ttk, messagebox
import customtkinter as ctk
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, UnexpectedAlertPresentException, StaleElementReferenceException

import config
from .base_tab import BaseAutomationTab

class AddActivityTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="add_activity")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._create_widgets()

    def _create_widgets(self):
        # Frame for controls and action buttons
        top_frame = ctk.CTkFrame(self)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        top_frame.grid_columnconfigure(0, weight=1)

        # --- UPDATED: Input fields for Price and Quantity ---
        input_frame = ctk.CTkFrame(top_frame)
        input_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        input_frame.grid_columnconfigure((1, 3), weight=1)
        
        defaults = config.ADD_ACTIVITY_CONFIG['defaults']
        ctk.CTkLabel(input_frame, text=f"Default Activity Code: {defaults['activity_code']}", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=15, pady=(0, 10))

        ctk.CTkLabel(input_frame, text="Unit Price (₹):").grid(row=1, column=0, sticky="w", padx=15)
        self.unit_price_entry = ctk.CTkEntry(input_frame)
        self.unit_price_entry.grid(row=1, column=1, sticky="ew", padx=(0, 15))
        self.unit_price_entry.insert(0, defaults['unit_price'])

        ctk.CTkLabel(input_frame, text="Quantity:").grid(row=1, column=2, sticky="w", padx=15)
        self.quantity_entry = ctk.CTkEntry(input_frame)
        self.quantity_entry.grid(row=1, column=3, sticky="ew", padx=(0, 15))
        self.quantity_entry.insert(0, defaults['quantity'])

        # Action buttons
        action_frame = self._create_action_buttons(parent_frame=top_frame)
        action_frame.grid(row=1, column=0, sticky='ew', pady=(10, 15), padx=15)

        # Notebook for inputs and results
        notebook = ctk.CTkTabview(self)
        notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        work_codes_frame = notebook.add("Work Keys")
        results_frame = notebook.add("Results")
        self._create_log_and_status_area(parent_notebook=notebook)

        # Work Keys Tab
        work_codes_frame.grid_columnconfigure(0, weight=1)
        work_codes_frame.grid_rowconfigure(0, weight=1)
        self.work_keys_text = ctk.CTkTextbox(work_codes_frame, wrap=tkinter.WORD)
        self.work_keys_text.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)

        # Results Tab
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(1, weight=1) # Make space for the button

        results_action_frame = ctk.CTkFrame(results_frame, fg_color="transparent")
        results_action_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(5, 10), padx=5)
        self.export_csv_button = ctk.CTkButton(results_action_frame, text="Export to CSV", command=lambda: self.export_treeview_to_csv(self.results_tree, "add_activity_results.csv"))
        self.export_csv_button.pack(side="left")

        cols = ("Work Key", "Status", "Details", "Timestamp")
        self.results_tree = ttk.Treeview(results_frame, columns=cols, show='headings')
        for col in cols:
            self.results_tree.heading(col, text=col)
        self.results_tree.column("Work Key", width=150)
        self.results_tree.column("Status", width=100, anchor='center')
        self.results_tree.column("Details", width=400)
        self.results_tree.column("Timestamp", width=100, anchor='center')
        self.results_tree.grid(row=1, column=0, sticky='nsew')
        scrollbar = ctk.CTkScrollbar(results_frame, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky='ns')
        self.style_treeview(self.results_tree)

    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running)
        state = "disabled" if running else "normal"
        self.work_keys_text.configure(state=state)
        self.unit_price_entry.configure(state=state)
        self.quantity_entry.configure(state=state)

    def start_automation(self):
        work_keys = [line.strip() for line in self.work_keys_text.get("1.0", tkinter.END).strip().splitlines() if line.strip()]
        if not work_keys:
            messagebox.showwarning("Input Required", "Please provide at least one work key.")
            return
            
        # Get and validate the new inputs
        unit_price = self.unit_price_entry.get().strip()
        quantity = self.quantity_entry.get().strip()

        if not unit_price or not quantity:
            messagebox.showwarning("Input Required", "Please enter a Unit Price and Quantity.")
            return
        
        # Pass the inputs to the automation logic
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic, args=(work_keys, unit_price, quantity))

    def reset_ui(self):
        if messagebox.askokcancel("Reset Form?", "Clear all inputs and logs?"):
            self.work_keys_text.configure(state="normal")
            self.work_keys_text.delete("1.0", tkinter.END)
            # Reset price and quantity to defaults
            defaults = config.ADD_ACTIVITY_CONFIG['defaults']
            self.unit_price_entry.delete(0, tkinter.END)
            self.unit_price_entry.insert(0, defaults['unit_price'])
            self.quantity_entry.delete(0, tkinter.END)
            self.quantity_entry.insert(0, defaults['quantity'])
            
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            self.app.clear_log(self.log_display)
            self.update_status("Ready", 0.0)
            self.app.log_message(self.log_display, "Form has been reset.")
            self.app.after(0, self.app.set_status, "Ready")

    def run_automation_logic(self, work_keys, unit_price, quantity):
        self.app.after(0, self.set_ui_state, True)
        self.app.clear_log(self.log_display)
        self.app.after(0, lambda: [self.results_tree.delete(item) for item in self.results_tree.get_children()])
        self.app.log_message(self.log_display, "Starting 'Add Activity' automation...")
        self.app.after(0, self.app.set_status, "Running Add Activity...")

        try:
            # Replace connect_to_chrome with get_driver
            driver = self.app.get_driver()
            if not driver:
                return

            total = len(work_keys)
            for i, work_key in enumerate(work_keys):
                if self.app.stop_events[self.automation_key].is_set():
                    self.app.log_message(self.log_display, "Automation stopped.", "warning")
                    break
                self.app.after(0, self.update_status, f"Processing {i+1}/{total}: {work_key}", (i+1) / total)
                self._process_single_work_key(driver, work_key, unit_price, quantity)

            final_msg = "Automation finished." if not self.app.stop_events[self.automation_key].is_set() else "Stopped."
            self.app.after(0, self.update_status, final_msg, 1.0)
            if not self.app.stop_events[self.automation_key].is_set():
                messagebox.showinfo("Complete", "'Add Activity' process has finished.")
        except Exception as e:
            self.app.log_message(self.log_display, f"A critical error occurred: {e}", "error")
            messagebox.showerror("Automation Error", f"An error occurred:\n\n{e}")
        finally:
            self.app.after(0, self.set_ui_state, False)
            self.app.after(0, self.app.set_status, "Automation Finished")

    def _log_result(self, work_key, status, details):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.app.after(0, lambda: self.results_tree.insert("", "end", values=(work_key, status, details, timestamp)))

    def _process_single_work_key(self, driver, work_key, unit_price, quantity):
        """
        Automates the process of adding a new activity to a single work key on the NREGA portal.
        
        This function navigates to the activity page, enters all the required data,
        and intelligently waits for the server to respond after saving.
        
        Args:
            driver: The Selenium WebDriver instance.
            work_key (str): The work key to process.
            unit_price (str): The unit price for the activity.
            quantity (str): The quantity for the activity.
        """
        wait = WebDriverWait(driver, 20)
        activity_code = config.ADD_ACTIVITY_CONFIG['defaults']['activity_code']
        progress_element_id = 'ctl00_ContentPlaceHolder1_UpdateProgress2'

        def wait_for_postback_to_finish():
            """A helper function to intelligently wait for the page to finish loading."""
            try:
                loader = WebDriverWait(driver, 3).until(
                    EC.visibility_of_element_located((By.ID, progress_element_id))
                )
                wait.until(EC.invisibility_of_element_located(loader))
            except TimeoutException:
                self.app.log_message(self.log_display, "Page loaded quickly.")

        try:
            # Always navigate fresh to avoid stale elements
            driver.get(config.ADD_ACTIVITY_CONFIG["url"])

            # 1. Enter work key and trigger reload
            self.app.log_message(self.log_display, f"Searching for work key: {work_key}")
            work_key_input = wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_txtwrksearchkey')))
            work_key_input.clear()
            work_key_input.send_keys(work_key)
            driver.execute_script("javascript:setTimeout('__doPostBack(\\'ctl00$ContentPlaceHolder1$txtwrksearchkey\\',\\'\\')', 0)")

            # 2. Select work from dropdown
            work_name_dd_id = 'ctl00_ContentPlaceHolder1_ddlworkName'
            wait.until(EC.presence_of_element_located((By.ID, work_name_dd_id)))
            wait.until(lambda d: len(Select(d.find_element(By.ID, work_name_dd_id)).options) > 1)
            Select(driver.find_element(By.ID, work_name_dd_id)).select_by_index(1)
            self.app.log_message(self.log_display, "Work selected. Loading details...")

            # 3. Select Activity
            activity_dd_id = 'ctl00_ContentPlaceHolder1_ddlAct'
            wait.until(EC.element_to_be_clickable((By.ID, activity_dd_id)))
            Select(driver.find_element(By.ID, activity_dd_id)).select_by_value(activity_code)
            wait_for_postback_to_finish()

            # 4. Fill Unit Price (no clearing)
            unit_price_input = wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_txtAct_UnitPrice')))
            unit_price_input.send_keys(unit_price)
            driver.execute_script("javascript:setTimeout('__doPostBack(\\'ctl00$ContentPlaceHolder1$txtAct_UnitPrice\\',\\'\\')', 0)")
            wait_for_postback_to_finish()

            # 5. Fill Quantity (no clearing)
            quantity_input = wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_txtAct_Qty')))
            quantity_input.send_keys(quantity)
            driver.execute_script("javascript:setTimeout('__doPostBack(\\'ctl00$ContentPlaceHolder1$txtAct_Qty\\',\\'\\')', 0)")
            wait_for_postback_to_finish()

            time.sleep(0.5)

            # 6. Click Save
            self.app.log_message(self.log_display, "Saving activity...")
            driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_btsave').click()

            # Check for success/error message
            try:
                WebDriverWait(driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//*[@id='ctl00_ContentPlaceHolder1_lblmsg' and normalize-space()]")),
                        EC.presence_of_element_located((By.XPATH, "//*[@id='ctl00_ContentPlaceHolder1_lblError' and normalize-space()]"))
                    )
                )
            except TimeoutException:
                self._log_result(work_key, "Success", "Saved (No confirmation message found).")
                return
                
            try:
                success_msg_element = driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_lblmsg')
                if success_msg_element.text.strip():
                    self._log_result(work_key, "Success", success_msg_element.text.strip())
                    return
            except NoSuchElementException:
                pass

            try:
                error_msg_element = driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_lblError')
                if error_msg_element.text.strip():
                    raise ValueError(error_msg_element.text.strip())
            except NoSuchElementException:
                pass

        except UnexpectedAlertPresentException as e:
            self._log_result(work_key, "Failed", f"Unexpected Alert: {e.alert_text}")
            try:
                driver.switch_to.alert.accept()
            except:
                pass
        except StaleElementReferenceException:
            self._log_result(work_key, "Failed", "Page refresh error. The script will retry on the next cycle.")
        except (TimeoutException, NoSuchElementException, ValueError) as e:
            error_message = str(e).splitlines()[0]
            self._log_result(work_key, "Failed", f"Error: {error_message}")
        except Exception as e:
            self._log_result(work_key, "Failed", f"A critical error occurred: {e}")