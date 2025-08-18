# tabs/wagelist_send_tab.py
import tkinter
from tkinter import ttk, messagebox
import customtkinter as ctk
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import config
from .base_tab import BaseAutomationTab

class WagelistSendTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="send")
        
        self.grid_columnconfigure(0, weight=1)
        # --- MODIFIED: Configure rows for new layout ---
        self.grid_rowconfigure(0, weight=0) # Settings row
        self.grid_rowconfigure(1, weight=0) # Action buttons row
        self.grid_rowconfigure(2, weight=1) # Results/Logs row (will expand)
        
        self._create_widgets()

    def _create_widgets(self):
        # --- NEW: Main container for all settings, made scrollable ---
        settings_container = ctk.CTkScrollableFrame(self, label_text="Settings")
        settings_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        settings_container.grid_columnconfigure(0, weight=1)

        # --- Controls Frame (inside scrollable frame) ---
        controls_frame = ctk.CTkFrame(settings_container)
        controls_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        controls_frame.grid_columnconfigure(1, weight=1)

        # --- Financial Year Selection ---
        ctk.CTkLabel(controls_frame, text="Financial Year:").grid(row=0, column=0, padx=(15, 5), pady=10, sticky="w")
        
        current_year = datetime.now().year
        year_options = [f"{year}-{year+1}" for year in range(current_year + 1, current_year - 10, -1)]
        
        self.fin_year_combobox = ctk.CTkComboBox(controls_frame, values=year_options)
        default_year = f"{current_year}-{current_year+1}" if datetime.now().month >= 4 else f"{current_year-1}-{current_year}"
        self.fin_year_combobox.set(default_year)
        self.fin_year_combobox.grid(row=0, column=1, columnspan=3, padx=(0, 15), pady=10, sticky="ew")

        # --- Row Selection ---
        ctk.CTkLabel(controls_frame, text="Start Row:").grid(row=1, column=0, padx=(15, 5), pady=(0, 15), sticky="w")
        self.row_start_entry = ctk.CTkEntry(controls_frame)
        self.row_start_entry.insert(0, config.WAGELIST_SEND_CONFIG["defaults"]["start_row"])
        self.row_start_entry.grid(row=1, column=1, pady=(0, 15), sticky="w")

        ctk.CTkLabel(controls_frame, text="End Row:").grid(row=1, column=2, padx=(10, 5), pady=(0, 15), sticky="w")
        self.row_end_entry = ctk.CTkEntry(controls_frame)
        self.row_end_entry.insert(0, config.WAGELIST_SEND_CONFIG["defaults"]["end_row"])
        self.row_end_entry.grid(row=1, column=3, padx=0, pady=(0, 15), sticky="w")

        # --- Action Buttons (MOVED) ---
        action_frame = self._create_action_buttons(parent_frame=self)
        action_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # --- Results and Logs (MOVED) ---
        data_notebook = ctk.CTkTabview(self)
        data_notebook.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0,10))
        results_frame = data_notebook.add("Results")
        self._create_log_and_status_area(parent_notebook=data_notebook)

        results_frame.grid_columnconfigure(0, weight=1); results_frame.grid_rowconfigure(1, weight=1)

        results_action_frame = ctk.CTkFrame(results_frame, fg_color="transparent")
        results_action_frame.grid(row=0, column=0, sticky='ew', pady=(5, 10), padx=5)

        self.export_csv_button = ctk.CTkButton(
            results_action_frame, 
            text="Export to CSV", 
            command=lambda: self.export_treeview_to_csv(self.results_tree, "wagelist_send_results.csv")
        )
        self.export_csv_button.pack(side="left")

        cols = ("Wagelist No.", "Status", "Timestamp")
        self.results_tree = ttk.Treeview(results_frame, columns=cols, show='headings')
        for col in cols: self.results_tree.heading(col, text=col)
        self.results_tree.grid(row=1, column=0, sticky='nsew')
        scrollbar = ctk.CTkScrollbar(results_frame, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set); scrollbar.grid(row=1, column=1, sticky='ns')
        self.style_treeview(self.results_tree)

    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running)
        state = "disabled" if running else "normal"
        self.fin_year_combobox.configure(state=state)
        self.row_start_entry.configure(state=state)
        self.row_end_entry.configure(state=state)

    def reset_ui(self):
        if messagebox.askokcancel("Reset Form?", "Are you sure?"):
            self.row_start_entry.delete(0, tkinter.END)
            self.row_start_entry.insert(0, config.WAGELIST_SEND_CONFIG["defaults"]["start_row"])
            self.row_end_entry.delete(0, tkinter.END)
            self.row_end_entry.insert(0, config.WAGELIST_SEND_CONFIG["defaults"]["end_row"])
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            self.app.clear_log(self.log_display)
            self.update_status("Ready", 0.0)
            self.app.log_message(self.log_display, "Form has been reset.")
            self.app.after(0, self.app.set_status, "Ready")

    def start_automation(self):
        try:
            start_row = int(self.row_start_entry.get())
            end_row = int(self.row_end_entry.get())
            fin_year = self.fin_year_combobox.get()
        except ValueError:
            messagebox.showerror("Input Error", "Row numbers must be integers.")
            return
        
        if not fin_year:
            messagebox.showerror("Input Error", "Please select a Financial Year.")
            return

        self.app.start_automation_thread(self.automation_key, self.run_automation_logic, args=(fin_year, start_row, end_row))

    def run_automation_logic(self, fin_year, start_row, end_row):
        self.app.after(0, self.set_ui_state, True)
        self.app.after(0, lambda: [self.results_tree.delete(item) for item in self.results_tree.get_children()])
        self.app.clear_log(self.log_display)
        self.app.log_message(self.log_display, "Starting automation...")
        self.app.after(0, self.app.set_status, "Running Wagelist Send...")
        
        try:
            driver = self.app.get_driver()
            if not driver: return
            wait = WebDriverWait(driver, 15)

            self.app.log_message(self.log_display, f"Navigating to Send Wagelist page...")
            driver.get(config.WAGELIST_SEND_CONFIG["url"])
            
            self.app.log_message(self.log_display, f"Selecting Financial Year: {fin_year}")
            fin_year_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddlfin"))))
            fin_year_dropdown.select_by_value(fin_year)
            
            self.app.log_message(self.log_display, "Waiting for wagelists to load...")
            wait.until(EC.element_to_be_clickable((By.XPATH, "//select[@id='ctl00_ContentPlaceHolder1_ddl_sel']/option[position()>1]")))
            time.sleep(1)

            all_wagelists = [o.get_attribute("value") for o in Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_sel")).options if o.get_attribute("value") != "select"]
            if not all_wagelists:
                self.app.log_message(self.log_display, "No wagelists found for the selected year.", "warning")
                messagebox.showwarning("No Wagelists", f"No wagelists were found for the financial year {fin_year}.")
                self.app.after(0, self.set_ui_state, False)
                return
                
            self.app.log_message(self.log_display, f"Found {len(all_wagelists)} wagelists.")
            total = len(all_wagelists)
            for idx, wagelist in enumerate(all_wagelists, 1):
                if self.app.stop_events[self.automation_key].is_set():
                    break
                self.app.after(0, self.update_status, f"Processing {idx}/{total}: {wagelist}", idx / total)
                success = self._process_single_wagelist(driver, wait, wagelist, start_row, end_row)
                self.app.after(0, lambda w=wagelist, s="Success" if success else "Failed", t=datetime.now().strftime("%H:%M:%S"): self.results_tree.insert("", tkinter.END, values=(w, s, t)))
                time.sleep(1)

        except Exception as e:
            self.app.log_message(self.log_display, f"A critical error occurred: {e}", "error")
            messagebox.showerror("Automation Error", f"An error occurred: {e}")
        finally:
            stopped = self.app.stop_events[self.automation_key].is_set()
            final_msg = "Process stopped by user." if stopped else "✅ All wagelists processed."
            self.app.after(0, self.update_status, final_msg, 1.0)
            self.app.after(0, self.set_ui_state, False)
            if not stopped:
                self.app.after(0, lambda: messagebox.showinfo("Automation Complete", "Wagelist sending process finished."))
                self.app.after(0, self.app.set_status, "Automation Finished")

    def _process_single_wagelist(self, driver, wait, wagelist, start_row, end_row):
        for attempt in range(2):
            if self.app.stop_events[self.automation_key].is_set():
                return False
            try:
                Select(wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ddl_sel")))).select_by_value(wagelist)
                
                start_row_radio_id = f"ctl00_ContentPlaceHolder1_GridView1_ctl{str(start_row).zfill(2)}_rdbPayment_2"
                wait.until(EC.presence_of_element_located((By.ID, start_row_radio_id)))
                
                for i in range(start_row, end_row + 1):
                    if self.app.stop_events[self.automation_key].is_set():
                        return False
                    try:
                        driver.find_element(By.ID, f"ctl00_ContentPlaceHolder1_GridView1_ctl{str(i).zfill(2)}_rdbPayment_2").click()
                        time.sleep(0.1)
                    except NoSuchElementException:
                        break
                
                if self.app.stop_events[self.automation_key].is_set():
                    return False
                
                driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btnsubmit").click()
                WebDriverWait(driver, 5).until(EC.alert_is_present()).accept()
                
                self.app.log_message(self.log_display, f"✅ {wagelist} submitted successfully.", "success")
                return True
            except Exception as e:
                self.app.log_message(self.log_display, f"[WARN] Attempt {attempt+1} failed for {wagelist}: {type(e).__name__}", "warning")
                time.sleep(2)
                driver.refresh()
                wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ddl_sel")))
        return False
