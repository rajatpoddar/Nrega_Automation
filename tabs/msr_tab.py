# tabs/msr_tab.py (Updated with Autocomplete)
import tkinter
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import os, random, time, sys, subprocess
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException, NoAlertPresentException
from fpdf import FPDF
import config
from .base_tab import BaseAutomationTab
from .autocomplete_widget import AutocompleteEntry # Import the new widget

class MsrTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="msr")
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)
        self._create_widgets()

    def _create_widgets(self):
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(controls_frame, text="Panchayat Name", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky='w', pady=(10, 5), padx=15)
        # UPDATED: Use AutocompleteEntry
        self.panchayat_entry = AutocompleteEntry(controls_frame, suggestions_list=self.app.history_manager.get_suggestions("panchayat_name"))
        self.panchayat_entry.grid(row=1, column=0, sticky='ew', pady=(0, 5), padx=15)
        ctk.CTkLabel(controls_frame, text="e.g., Palojori (must exactly match the name on the website)", text_color="gray50").grid(row=2, column=0, sticky='w', padx=15)

        action_frame = self._create_action_buttons(parent_frame=controls_frame)
        action_frame.grid(row=6, column=0, columnspan=4, sticky='ew', pady=(15, 15))

        data_notebook = ctk.CTkTabview(self)
        data_notebook.grid(row=1, column=0, sticky="nsew")

        work_codes_frame = data_notebook.add("Work Codes")
        results_frame = data_notebook.add("Results")
        self._create_log_and_status_area(parent_notebook=data_notebook)

        # Work Codes Tab with Clear button...
        work_codes_frame.grid_columnconfigure(0, weight=1); work_codes_frame.grid_rowconfigure(1, weight=1)
        wc_controls_frame = ctk.CTkFrame(work_codes_frame, fg_color="transparent")
        wc_controls_frame.grid(row=0, column=0, sticky='ew')
        clear_button = ctk.CTkButton(wc_controls_frame, text="Clear", width=80, command=lambda: self.work_key_text.delete("1.0", tkinter.END))
        clear_button.pack(side='right', pady=(5,0), padx=(0,5))
        self.work_key_text = ctk.CTkTextbox(work_codes_frame, wrap=tkinter.WORD)
        self.work_key_text.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)

        # Results Tab
        results_frame.grid_columnconfigure(0, weight=1); results_frame.grid_rowconfigure(1, weight=1)
        results_action_frame = ctk.CTkFrame(results_frame, fg_color="transparent")
        results_action_frame.grid(row=0, column=0, sticky='ew', pady=(5, 10)) # Added some padding
        
        self.export_pdf_button = ctk.CTkButton(results_action_frame, text="Export to PDF", command=self.export_to_pdf)
        self.export_pdf_button.pack(side='left', padx=(0, 10))

        # --- NEW: Add Export to CSV button ---
        self.export_csv_button = ctk.CTkButton(
            results_action_frame,
            text="Export to CSV",
            command=lambda: self.export_treeview_to_csv(self.results_tree, "msr_payment_results.csv")
        )
        self.export_csv_button.pack(side='left')
        # --- END NEW ---

        cols = ("Workcode", "Status", "Details", "Timestamp")
        self.results_tree = ttk.Treeview(results_frame, columns=cols, show='headings')
        for col in cols: self.results_tree.heading(col, text=col)
        self.results_tree.column("Status", anchor='center', width=150); self.results_tree.column("Details", width=350)
        self.results_tree.grid(row=1, column=0, sticky='nsew')
        scrollbar = ctk.CTkScrollbar(results_frame, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set); scrollbar.grid(row=1, column=1, sticky='ns')
        self.style_treeview(self.results_tree)

    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running)
        state = "disabled" if running else "normal"
        self.panchayat_entry.configure(state=state)
        self.work_key_text.configure(state=state)
        self.export_pdf_button.configure(state=state)

    # ... All other methods like start_automation, reset_ui, run_automation_logic remain unchanged ...
    def start_automation(self):
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic)
    def reset_ui(self):
        if messagebox.askokcancel("Reset Form?", "Clear all inputs, results, and logs?"):
            self.panchayat_entry.delete(0, tkinter.END)
            self.work_key_text.configure(state="normal"); self.work_key_text.delete("1.0", tkinter.END)
            for item in self.results_tree.get_children(): self.results_tree.delete(item)
            self.app.clear_log(self.log_display)
            self.update_status("Ready", 0)
            self.app.log_message(self.log_display, "Form has been reset.")
            self.app.after(0, self.app.set_status, "Ready")
    def run_automation_logic(self):
        self.app.after(0, self.set_ui_state, True)
        self.app.after(0, lambda: [self.results_tree.delete(item) for item in self.results_tree.get_children()])
        self.app.clear_log(self.log_display)
        self.app.log_message(self.log_display, "Starting MSR processing...")
        self.app.after(0, self.app.set_status, "Running MSR Payment...")
        panchayat_name = self.panchayat_entry.get().strip()
        if not panchayat_name: messagebox.showerror("Input Error", "Please enter a Panchayat name."); self.app.after(0, self.set_ui_state, False); return
        work_keys = [line.strip() for line in self.work_key_text.get("1.0", tkinter.END).strip().splitlines() if line.strip()]
        if not work_keys: messagebox.showerror("Input Error", "No work keys provided."); self.app.after(0, self.set_ui_state, False); return
        try:
            driver = self.app.get_driver()
            if not driver: return
            wait = WebDriverWait(driver, 15)
            if driver.current_url != config.MSR_CONFIG["url"]: driver.get(config.MSR_CONFIG["url"])
            panchayat_select = Select(wait.until(EC.presence_of_element_located((By.NAME, "ddlPanchayat"))))
            # Corrected line
            match = next((opt.text for opt in panchayat_select.options if panchayat_name.strip().lower() in opt.text.lower()), None)
            if not match: raise ValueError(f"Panchayat '{panchayat_name}' not found.")
            panchayat_select.select_by_visible_text(match)
            
            # Save successful input to history
            self.app.update_history("panchayat_name", panchayat_name)

            self.app.log_message(self.log_display, f"Successfully selected Panchayat: {match}", "success"); time.sleep(2)
            total = len(work_keys)
            for i, work_key in enumerate(work_keys, 1):
                if self.app.stop_events[self.automation_key].is_set(): self.app.log_message(self.log_display, "Automation stopped by user.", "warning"); break
                self.app.after(0, self.update_status, f"Processing {i}/{total}: {work_key}", (i/total))
                self._process_single_work_code(driver, wait, work_key)
            if not self.app.stop_events[self.automation_key].is_set(): messagebox.showinfo("Completed", "Automation finished! Check the 'Results' tab for details.")
        except Exception as e:
            self.app.log_message(self.log_display, f"A critical error occurred: {e}", "error")
            messagebox.showerror("MSR Error", f"An error occurred: {e}")
        finally:
            self.app.after(0, self.set_ui_state, False)
            self.app.after(0, self.update_status, "Automation Finished.", 1.0)
            self.app.after(0, self.app.set_status, "Automation Finished")
            
    def export_to_pdf(self):
        data = [self.results_tree.item(item_id)['values'] for item_id in self.results_tree.get_children()]
        if not data: messagebox.showinfo("No Data", "There are no results to export."); return
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Documents", "*.pdf")], initialdir=self.app.get_user_downloads_path(), title="Save Results As PDF")
        if not file_path: return
        try:
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            pdf.add_page(); pdf.set_font("Arial", size=12); pdf.cell(0, 10, 'MSR Processing Results', 0, 1, 'C')
            pdf.set_font("Arial", 'B', 9)
            col_widths, headers = [55, 35, 155, 25], ["Workcode", "Status", "Details", "Timestamp"]
            for i, header in enumerate(headers): pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
            pdf.ln(); pdf.set_font("Arial", '', 8)
            for row in data:
                for i, item in enumerate(row): pdf.cell(col_widths[i], 6, str(item).encode('latin-1', 'replace').decode('latin-1'), 1, 0)
                pdf.ln()
            pdf.output(file_path)
            if messagebox.askyesno("Success", f"Results exported to:\n{file_path}\n\nDo you want to open the file?"):
                if sys.platform == "win32": os.startfile(file_path)
                else: subprocess.call(['open', file_path])
        except Exception as e: messagebox.showerror("Export Error", f"Failed to create PDF file.\n\nError: {e}")
    def _process_single_work_code(self, driver, wait, work_key):
        try:
            try: driver.switch_to.alert.accept()
            except NoAlertPresentException: pass
            wait.until(EC.presence_of_element_located((By.ID, "txtSearch"))).clear()
            driver.find_element(By.ID, "txtSearch").send_keys(work_key)
            wait.until(EC.element_to_be_clickable((By.ID, "ImgbtnSearch"))).click(); time.sleep(1)
            error_span = driver.find_element(By.ID, "lblError")
            if error_span and error_span.text.strip(): raise ValueError(f"Site error: '{error_span.text.strip()}'")
            work_code_select = Select(wait.until(EC.presence_of_element_located((By.ID, "ddlWorkCode"))))
            if len(work_code_select.options) <= config.MSR_CONFIG["work_code_index"]: raise IndexError("Work code not found.")
            work_code_select.select_by_index(config.MSR_CONFIG["work_code_index"]); time.sleep(1.5)
            msr_select = Select(wait.until(EC.presence_of_element_located((By.ID, "ddlMsrNo"))))
            if len(msr_select.options) <= config.MSR_CONFIG["muster_roll_index"]: raise IndexError("Muster Roll (MSR) not found.")
            msr_select.select_by_index(config.MSR_CONFIG["muster_roll_index"]); time.sleep(1.5)
            wait.until(EC.element_to_be_clickable((By.ID, "btnSave"))).click()
            WebDriverWait(driver, 10).until(EC.alert_is_present()).accept()
            outcome_found = False
            for _ in range(3):
                try:
                    final_alert = driver.switch_to.alert; final_alert_text = final_alert.text.strip(); final_alert.accept()
                    if "Muster Roll Payment has been saved" in final_alert_text: self._log_result("Success", work_key, final_alert_text)
                    elif "and hence it is not saved" in final_alert_text: self._log_result("Success", work_key, "Saved (ignorable attendance error)")
                    else: self._log_result("Failed", work_key, f"Unknown Alert: {final_alert_text}")
                    outcome_found = True; break
                except NoAlertPresentException:
                    if "Expenditure on unskilled labours exceeds sanction amount" in driver.page_source: self._log_result("Failed", work_key, "Exceeds Labour Payment"); outcome_found = True; break
                    time.sleep(1)
            if not outcome_found: self._log_result("Failed", work_key, "No final confirmation found (Timeout).")
            delay = random.uniform(config.MSR_CONFIG["min_delay"], config.MSR_CONFIG["max_delay"])
            self.app.after(0, self.update_status, f"Waiting {delay:.1f}s...")
            time.sleep(delay)
        except (ValueError, IndexError, NoSuchElementException, TimeoutException) as e:
            display_msg = "MR not Filled yet." if isinstance(e, IndexError) else "Page timed out or element not found." if isinstance(e, TimeoutException) else str(e)
            self._log_result("Failed", work_key, display_msg)
        except Exception as e: self._log_result("Failed", work_key, f"CRITICAL ERROR: {type(e).__name__}")
    def _log_result(self, status, work_key, msg):
        level = "success" if status.lower() == "success" else "error"
        timestamp = datetime.now().strftime("%H:%M:%S")
        details = msg.replace("\n", " ").replace("\r", " ")
        if "No final confirmation found" in msg: details = "Pending for JE & AE Approval"
        elif "Muster Roll (MSR) not found" in msg: details = "MR not Filled yet."
        elif "Work code not found" in msg: details = "Work Code not found."
        self.app.log_message(self.log_display, f"'{work_key}' - {status.upper()}: {details}", level=level)
        self.app.after(0, lambda: self.results_tree.insert("", "end", values=(work_key, status.upper(), details, timestamp)))