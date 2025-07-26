# tabs/wagelist_send_tab.py (Refactored to use BaseAutomationTab)
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
        self.grid_rowconfigure(2, weight=1)
        
        self._create_widgets()

    def _create_widgets(self):
        note_frame = ctk.CTkFrame(self)
        note_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        instruction_text = "IMPORTANT: Before starting, please manually:\n" \
                           "1. Go to the 'Send Wagelist For Payment' page.\n" \
                           "2. Select the correct 'Financial Year'.\n" \
                           "3. Wait for the 'Wagelist No.' list to populate, then click 'Start Sending'."
        ctk.CTkLabel(note_frame, text=instruction_text, justify="left", wraplength=850).pack(fill='x', pady=10, padx=15)
        
        controls = ctk.CTkFrame(self)
        controls.grid(row=1, column=0, sticky='ew')
        
        row_frame = ctk.CTkFrame(controls, fg_color="transparent")
        row_frame.pack(fill='x', pady=5, padx=15)
        ctk.CTkLabel(row_frame, text="Start Row:").pack(side="left")
        self.row_start_entry = ctk.CTkEntry(row_frame, width=60)
        self.row_start_entry.insert(0, config.WAGELIST_SEND_CONFIG["defaults"]["start_row"])
        self.row_start_entry.pack(side="left", padx=5)
        ctk.CTkLabel(row_frame, text="End Row:").pack(side="left", padx=(10,0))
        self.row_end_entry = ctk.CTkEntry(row_frame, width=60)
        self.row_end_entry.insert(0, config.WAGELIST_SEND_CONFIG["defaults"]["end_row"])
        self.row_end_entry.pack(side="left", padx=5)
        
        action_frame = self._create_action_buttons(parent_frame=controls)
        action_frame.pack(pady=10, padx=15, fill='x')
        
        data_notebook = ctk.CTkTabview(self)
        data_notebook.grid(row=2, column=0, sticky="nsew", pady=(10,0))
        results_frame = data_notebook.add("Results")
        self._create_log_and_status_area(parent_notebook=data_notebook)

        results_frame.grid_columnconfigure(0, weight=1); results_frame.grid_rowconfigure(0, weight=1)
        cols = ("Wagelist No.", "Status", "Timestamp")
        self.results_tree = ttk.Treeview(results_frame, columns=cols, show='headings')
        for col in cols: self.results_tree.heading(col, text=col)
        self.results_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar = ctk.CTkScrollbar(results_frame, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set); scrollbar.grid(row=0, column=1, sticky='ns')
        self.style_treeview(self.results_tree)

    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running)
        state = "disabled" if running else "normal"
        self.row_start_entry.configure(state=state)
        self.row_end_entry.configure(state=state)

    def reset_ui(self):
        if messagebox.askokcancel("Reset Form?", "Are you sure?"):
            self.row_start_entry.delete(0, tkinter.END)
            self.row_start_entry.insert(0, config.WAGELIST_SEND_CONFIG["defaults"]["start_row"])
            self.row_end_entry.delete(0, tkinter.END)
            self.row_end_entry.insert(0, config.WAGELIST_SEND_CONFIG["defaults"]["end_row"])
            for item in self.results_tree.get_children(): self.results_tree.delete(item)
            self.app.clear_log(self.log_display)
            self.update_status("Ready", 0.0)
            self.app.log_message(self.log_display, "Form has been reset.")

    def start_automation(self):
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic)

    def run_automation_logic(self):
        self.app.after(0, self.set_ui_state, True)
        self.app.after(0, lambda: [self.results_tree.delete(item) for item in self.results_tree.get_children()])
        self.app.clear_log(self.log_display)
        self.app.log_message(self.log_display, "Starting automation...")
        try:
            start_row = int(self.row_start_entry.get()); end_row = int(self.row_end_entry.get())
        except ValueError:
            messagebox.showerror("Input Error", "Row numbers must be integers."); self.app.after(0, self.set_ui_state, False); return
        try:
            driver = self.app.connect_to_chrome()
            if not driver: return
            wait = WebDriverWait(driver, 10)
            self.app.log_message(self.log_display, "Fetching wagelists from the current page...")
            wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddl_sel")))
            all_wagelists = [o.get_attribute("value") for o in Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_sel")).options if o.get_attribute("value") != "select"]
            if not all_wagelists:
                self.app.log_message(self.log_display, "No wagelists found.", "error"); self.app.after(0, self.set_ui_state, False); return
            self.app.log_message(self.log_display, f"Found {len(all_wagelists)} wagelists.")
            total = len(all_wagelists)
            for idx, wagelist in enumerate(all_wagelists, 1):
                if self.app.stop_events[self.automation_key].is_set(): break
                self.app.after(0, self.update_status, f"Processing {idx}/{total}: {wagelist}", idx / total)
                success = self._process_single_wagelist(driver, wait, wagelist, start_row, end_row)
                self.app.after(0, lambda w=wagelist, s="Success" if success else "Failed", t=datetime.now().strftime("%H:%M:%S"): self.results_tree.insert("", tkinter.END, values=(w, s, t)))
                time.sleep(1)
        except Exception as e:
            self.app.log_message(self.log_display, f"A critical error occurred: {e}", "error"); messagebox.showerror("Automation Error", f"An error occurred: {e}")
        finally:
            stopped = self.app.stop_events[self.automation_key].is_set()
            final_msg = "Process stopped by user." if stopped else "✅ All wagelists processed."
            self.app.after(0, self.update_status, final_msg, 1.0)
            self.app.after(0, self.set_ui_state, False)
            if not stopped:
                self.app.after(0, lambda: messagebox.showinfo("Automation Complete", "Wagelist sending process finished."))

    def _process_single_wagelist(self, driver, wait, wagelist, start_row, end_row):
        for attempt in range(2):
            if self.app.stop_events[self.automation_key].is_set(): return False
            try:
                old_html = driver.page_source
                Select(wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ddl_sel")))).select_by_value(wagelist)
                wait.until(lambda d: d.page_source != old_html)
                start_row_radio_id = f"ctl00_ContentPlaceHolder1_GridView1_ctl{str(start_row).zfill(2)}_rdbPayment_2"
                wait.until(EC.element_to_be_clickable((By.ID, start_row_radio_id)))
                for i in range(start_row, end_row + 1):
                    if self.app.stop_events[self.automation_key].is_set(): return False
                    try:
                        driver.find_element(By.ID, f"ctl00_ContentPlaceHolder1_GridView1_ctl{str(i).zfill(2)}_rdbPayment_2").click()
                        time.sleep(0.2)
                    except NoSuchElementException: break
                if self.app.stop_events[self.automation_key].is_set(): return False
                driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btnsubmit").click()
                WebDriverWait(driver, 5).until(EC.alert_is_present()).accept()
                self.app.log_message(self.log_display, f"✅ {wagelist} submitted successfully.", "success")
                return True
            except Exception as e:
                self.app.log_message(self.log_display, f"[WARN] Attempt {attempt+1} failed for {wagelist}: {type(e).__name__}", "warning"); time.sleep(2)
        return False