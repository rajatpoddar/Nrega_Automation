# tabs/wagelist_gen_tab.py
import tkinter
from tkinter import ttk, messagebox
import customtkinter as ctk
import time
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import config
from .base_tab import BaseAutomationTab
from .autocomplete_widget import AutocompleteEntry

class WagelistGenTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="gen")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._create_widgets()

    def _create_widgets(self):
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(controls_frame, text=f"Agency Name ({config.AGENCY_PREFIX}...):").grid(row=0, column=0, sticky='w', padx=15, pady=(15,0))
        # --- FIX: Changed CTkEntry to AutocompleteEntry ---
        self.agency_entry = AutocompleteEntry(controls_frame, suggestions_list=self.app.history_manager.get_suggestions("panchayat_name"))
        self.agency_entry.grid(row=0, column=1, sticky='ew', padx=15, pady=(15,0))
        ctk.CTkLabel(controls_frame, text="Enter only the Panchayat name (e.g., Palojori).", text_color="gray50").grid(row=1, column=1, sticky='w', padx=15)

        action_frame = self._create_action_buttons(parent_frame=controls_frame)
        action_frame.grid(row=6, column=0, columnspan=4, sticky='ew', pady=(15, 15))

        notebook = ctk.CTkTabview(self)
        notebook.grid(row=1, column=0, sticky="nsew")

        results_frame = notebook.add("Results")
        self._create_log_and_status_area(parent_notebook=notebook)

        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(1, weight=1)

        results_action_frame = ctk.CTkFrame(results_frame, fg_color="transparent")
        results_action_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(5, 10), padx=5)
        self.export_csv_button = ctk.CTkButton(results_action_frame, text="Export to CSV", command=lambda: self.export_treeview_to_csv(self.results_tree, "wagelist_gen_results.csv"))
        self.export_csv_button.pack(side="left")
        
        # --- ENHANCEMENT: Added 'Wagelist No.' column ---
        cols = ("Timestamp", "Work Code", "Status", "Wagelist No.", "Job Card No.", "Applicant Name")
        self.results_tree = ttk.Treeview(results_frame, columns=cols, show='headings')
        for col in cols: self.results_tree.heading(col, text=col)
        self.results_tree.column("Timestamp", width=80, anchor='center')
        self.results_tree.column("Work Code", width=200)
        self.results_tree.column("Status", width=150)
        self.results_tree.column("Wagelist No.", width=180)
        self.results_tree.column("Job Card No.", width=200)
        self.results_tree.column("Applicant Name", width=150)
        self.results_tree.grid(row=1, column=0, sticky='nsew')
        scrollbar = ctk.CTkScrollbar(results_frame, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set); scrollbar.grid(row=1, column=1, sticky='ns')
        self.style_treeview(self.results_tree)

    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running)
        state = "disabled" if running else "normal"
        self.agency_entry.configure(state=state)

    def reset_ui(self):
        if messagebox.askokcancel("Reset Form?", "Are you sure?"):
            self.agency_entry.delete(0, tkinter.END)
            for item in self.results_tree.get_children(): self.results_tree.delete(item)
            self.app.clear_log(self.log_display)
            self.update_status("Ready", 0.0)
            self.app.log_message(self.log_display, "Form has been reset.")
            self.app.after(0, self.app.set_status, "Ready")

    def start_automation(self):
        agency_name_part = self.agency_entry.get().strip()
        if not agency_name_part:
            messagebox.showwarning("Input Error", "Please enter an Agency name."); return
        # --- FIX: Save Panchayat name to history ---
        self.app.update_history("panchayat_name", agency_name_part)
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic, args=(agency_name_part,))

    def run_automation_logic(self, agency_name_part):
        self.app.after(0, self.set_ui_state, True)
        self.app.clear_log(self.log_display)
        self.app.after(0, lambda: [self.results_tree.delete(item) for item in self.results_tree.get_children()])
        self.app.log_message(self.log_display, f"Starting wagelist generation for: {agency_name_part}")
        self.app.after(0, self.app.set_status, "Running Wagelist Generation...")
        try:
            driver = self.app.get_driver()
            if not driver: return
            wait = WebDriverWait(driver, 20)
            total_errors_to_skip = 0
            while not self.app.stop_events[self.automation_key].is_set():
                self.app.after(0, self.update_status, "Navigating and selecting agency...")
                driver.get(config.WAGELIST_GEN_CONFIG["base_url"])
                agency_select_element = wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_exe_agency')))
                select = Select(agency_select_element)
                full_agency_name = config.AGENCY_PREFIX + agency_name_part
                match_text = next((opt.text for opt in select.options if opt.text.strip() == full_agency_name), None)
                if not match_text:
                    error_msg = f"Agency '{full_agency_name}' not found."; self.app.log_message(self.log_display, error_msg, "error"); messagebox.showerror("Agency Not Found", error_msg); break
                select.select_by_visible_text(match_text)
                self.app.log_message(self.log_display, f"Selected agency: {match_text}", "success"); time.sleep(1)
                proceed_button = wait.until(EC.element_to_be_clickable((By.ID, 'ctl00_ContentPlaceHolder1_go')))
                driver.execute_script("arguments[0].scrollIntoView(true);", proceed_button); proceed_button.click()
                try:
                    wagelist_table = wait.until(EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_wagelist_msr")))
                    rows = wagelist_table.find_elements(By.XPATH, ".//tr[td]")
                    if not rows or total_errors_to_skip >= len(rows):
                        self.app.log_message(self.log_display, "No more wagelists to process.", "info"); break
                    row_to_process = rows[total_errors_to_skip]
                    try: checkbox = row_to_process.find_element(By.XPATH, ".//input[@type='checkbox']")
                    except NoSuchElementException: self.app.log_message(self.log_display, "Row without checkbox found, assuming end.", "info"); break
                    work_code = row_to_process.find_elements(By.TAG_NAME, "td")[2].text.strip()
                    self.app.after(0, self.update_status, f"Processing work code {work_code}...")
                    self.app.log_message(self.log_display, f"Processing row {total_errors_to_skip + 1} (Work Code: {work_code})")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
                    if not checkbox.is_selected(): checkbox.click()
                    wait.until(EC.element_to_be_clickable((By.ID, 'ctl00_ContentPlaceHolder1_btn_go'))).click()
                    wait.until(EC.any_of(EC.url_changes(config.WAGELIST_GEN_CONFIG["base_url"]), EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_lblmsg"))))
                    if "view_wagelist.aspx" in driver.current_url:
                        # --- ENHANCEMENT: Parse URL to get wagelist number ---
                        parsed_url = urlparse(driver.current_url)
                        query_params = parse_qs(parsed_url.query)
                        wagelist_no = query_params.get('Wage_Listno', ['N/A'])[0]
                        self.app.log_message(self.log_display, f"SUCCESS: Wagelist {wagelist_no} generated for {work_code}.", "success")
                        self._log_result(work_code, "Success", wagelist_no, "", "")
                    else:
                        error_text = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_lblmsg").text.strip()
                        self.app.log_message(self.log_display, f"ERROR on {work_code}: {error_text}", "error")
                        try:
                            job_cards, applicant_names = [], []
                            unfrozen_table = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_GridView1")
                            for u_row in unfrozen_table.find_elements(By.XPATH, ".//tr[td]"):
                                u_cells = u_row.find_elements(By.TAG_NAME, "td")
                                job_cards.append(u_cells[1].text.strip()); applicant_names.append(u_cells[3].text.strip())
                            self._log_result(work_code, "Unfrozen Account", "N/A", ", ".join(job_cards), ", ".join(applicant_names))
                        except NoSuchElementException: self._log_result(work_code, "Failed (Unknown Error)", "N/A", "", "")
                        total_errors_to_skip += 1
                except TimeoutException: self.app.log_message(self.log_display, "No wagelist table found. Assuming process complete.", "info"); break
                if self.app.stop_events[self.automation_key].is_set(): self.app.log_message(self.log_display, "Stop signal received."); break
            if not self.app.stop_events[self.automation_key].is_set(): self.app.after(0, lambda: messagebox.showinfo("Automation Complete", "The wagelist generation process has finished."))
        except Exception as e: self.app.log_message(self.log_display, f"A critical error occurred: {e}", level="error")
        finally:
            self.app.after(0, self.set_ui_state, False)
            self.app.after(0, self.update_status, "Automation Finished.")
            self.app.after(0, self.app.set_status, "Automation Finished")

    def _log_result(self, work_code, status, wagelist_no, job_card, applicant_name):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.app.after(0, lambda: self.results_tree.insert("", "end", values=(timestamp, work_code, status, wagelist_no, job_card, applicant_name)))