# tabs/fto_generation_tab.py (Updated with Autocomplete)
import tkinter
from tkinter import ttk, messagebox
import customtkinter as ctk
import time, json, os, re
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoAlertPresentException, NoSuchElementException
import config
from .base_tab import BaseAutomationTab
from .autocomplete_widget import AutocompleteEntry # Import the new widget

class FtoGenerationTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="fto_gen")
        self.config_file = self.app.get_data_path('fto_gen_config.json')
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)
        self._create_widgets(); self.load_inputs()
    
    def _capitalize_entry(self, var): var.set(var.get().upper())

    def _create_widgets(self):
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls_frame.grid_columnconfigure((1, 3), weight=1)

        self.district_var = ctk.StringVar()
        self.district_var.trace_add('write', lambda *args: self._capitalize_entry(self.district_var))
        ctk.CTkLabel(controls_frame, text="District:").grid(row=0, column=0, sticky='w', padx=15, pady=5)
        self.district_entry = AutocompleteEntry(controls_frame, textvariable=self.district_var, suggestions_list=self.app.history_manager.get_suggestions("district_name"))
        self.district_entry.grid(row=0, column=1, sticky='ew', padx=15, pady=5)

        ctk.CTkLabel(controls_frame, text="Block:").grid(row=0, column=2, sticky='w', padx=10, pady=5)
        self.block_entry = AutocompleteEntry(controls_frame, suggestions_list=self.app.history_manager.get_suggestions("block_name"))
        self.block_entry.grid(row=0, column=3, sticky='ew', padx=15, pady=5)

        ctk.CTkLabel(controls_frame, text="Panchayat:").grid(row=1, column=0, sticky='w', padx=15, pady=5)
        self.panchayat_entry = AutocompleteEntry(controls_frame, suggestions_list=self.app.history_manager.get_suggestions("panchayat_name"))
        self.panchayat_entry.grid(row=1, column=1, columnspan=3, sticky='ew', padx=15, pady=5)
        
        ctk.CTkLabel(controls_frame, text="User ID:").grid(row=2, column=0, sticky='w', padx=15, pady=5)
        self.user_id_entry = ctk.CTkEntry(controls_frame)
        self.user_id_entry.grid(row=2, column=1, columnspan=3, sticky='ew', padx=15, pady=5)

        note_text = "Note: You can manually log in, then run this automation."
        ctk.CTkLabel(controls_frame, text=note_text, text_color="gray50").grid(row=3, column=0, columnspan=4, sticky='w', padx=15, pady=10)
        action_frame = self._create_action_buttons(parent_frame=controls_frame)
        action_frame.grid(row=4, column=0, columnspan=4, sticky='ew', pady=10)
        
        notebook = ctk.CTkTabview(self)
        notebook.grid(row=1, column=0, sticky="nsew")
        self._create_log_and_status_area(parent_notebook=notebook)
        results_frame = notebook.add("Results (FTO Numbers)")

        results_frame.grid_columnconfigure(0, weight=1); results_frame.grid_rowconfigure(0, weight=1)
        cols = ("Page", "FTO Number", "Timestamp")
        self.results_tree = ttk.Treeview(results_frame, columns=cols, show='headings')
        for col in cols: self.results_tree.heading(col, text=col)
        self.results_tree.column("Page", width=150); self.results_tree.column("FTO Number", width=400); self.results_tree.column("Timestamp", width=100, anchor='center')
        self.results_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar = ctk.CTkScrollbar(results_frame, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set); scrollbar.grid(row=0, column=1, sticky='ns')
        self.style_treeview(self.results_tree)

    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running)
        state = "disabled" if running else "normal"
        self.district_entry.configure(state=state)
        self.block_entry.configure(state=state)
        self.panchayat_entry.configure(state=state)
        self.user_id_entry.configure(state=state)

    def save_inputs(self):
        data = {'district': self.district_entry.get(), 'block': self.block_entry.get(), 'panchayat': self.panchayat_entry.get(), 'user_id': self.user_id_entry.get()}
        try:
            with open(self.config_file, 'w') as f: json.dump(data, f, indent=4)
        except Exception as e: print(f"Error saving FTO config: {e}")

    def load_inputs(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f: data = json.load(f)
                self.district_entry.insert(0, data.get('district', '')); self.block_entry.insert(0, data.get('block', ''))
                self.panchayat_entry.insert(0, data.get('panchayat', '')); self.user_id_entry.insert(0, data.get('user_id', ''))
        except (json.JSONDecodeError, IOError) as e: print(f"Error loading FTO config: {e}")

    def reset_ui(self):
        if messagebox.askokcancel("Reset Form?", "This will clear all inputs, results, and logs."):
            self.district_entry.delete(0, tkinter.END); self.block_entry.delete(0, tkinter.END)
            self.panchayat_entry.delete(0, tkinter.END); self.user_id_entry.delete(0, tkinter.END)
            self.app.clear_log(self.log_display)
            for item in self.results_tree.get_children(): self.results_tree.delete(item)
            self.update_status("Ready", 0)
            self.app.log_message(self.log_display, "Form has been reset.")
            if os.path.exists(self.config_file): os.remove(self.config_file)

    def start_automation(self):
        self.save_inputs()
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic)
        
    def _log_result(self, page_name, fto_number):
        self.app.after(0, lambda: self.results_tree.insert("", "end", values=(page_name, fto_number, datetime.now().strftime("%H:%M:%S"))))

    def _process_verification_page(self, driver, wait, verification_url, page_identifier):
        try:
            self.app.log_message(self.log_display, f"Navigating to {page_identifier}..."); driver.get(verification_url)
            wait.until(EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_wage_list_verify"))); self.app.log_message(self.log_display, "Verification page loaded.")
            if not driver.find_elements(By.XPATH, "//input[contains(@id, '_auth')]"):
                self.app.log_message(self.log_display, "No records found.", "warning"); return "No records"
            self.app.log_message(self.log_display, "Accepting all rows..."); driver.execute_script("document.querySelectorAll('input[id*=\"_auth\"]').forEach(radio => radio.click());")
            self.app.log_message(self.log_display, "Clicking 'Submit'..."); wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ch_verified"))).click()
            self.app.log_message(self.log_display, "Clicking 'Authorise'..."); wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_btn"))).click()
            self.app.log_message(self.log_display, "Waiting for confirmation..."); alert = wait.until(EC.alert_is_present())
            fto_match = re.search(r'FTO No : \((.*?)\)', alert.text); fto_number = fto_match.group(1) if fto_match else "Not Found"
            self.app.log_message(self.log_display, f"Captured FTO: {fto_number}", "success"); self._log_result(page_identifier, fto_number); alert.accept()
        except TimeoutException: self.app.log_message(self.log_display, "Page timed out or no records found.", "warning")
        except Exception as e: self.app.log_message(self.log_display, f"Error during verification: {e}", "error")

    # In tabs/fto_generation_tab.py, inside the FtoGenerationTab class

    def run_automation_logic(self):
        self.app.after(0, self.set_ui_state, True)
        self.app.clear_log(self.log_display)
        self.app.after(0, lambda: [self.results_tree.delete(item) for item in self.results_tree.get_children()])
        self.update_status("Starting...", 0)
        try:
            d = self.district_entry.get().strip()
            b = self.block_entry.get().strip()
            p = self.panchayat_entry.get().strip()
            u = self.user_id_entry.get().strip()
            has_login_details = all([d, b, p, u])

            driver = self.app.connect_to_chrome()
            if not driver: return
            
            wait = WebDriverWait(driver, 20)
            cfg = config.FTO_GEN_CONFIG
            
            if has_login_details:
                self.app.log_message(self.log_display, "Login details provided. Navigating to login page...")
                driver.get(cfg["login_url"])
                try:
                    Select(wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddl_District")))).select_by_visible_text(d)
                    wait.until(lambda drv: len(Select(drv.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_Block")).options) > 1)
                    Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_Block")).select_by_visible_text(b)
                    wait.until(lambda drv: len(Select(drv.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_Panch")).options) > 1)
                    Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_Panch")).select_by_visible_text(p)
                    driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txt_UserID").send_keys(u)
                    
                    self.app.update_history("district_name", d)
                    self.app.update_history("block_name", b)
                    self.app.update_history("panchayat_name", p)

                    self.app.log_message(self.log_display, "Details filled. Please enter Password and CAPTCHA.")
                    self.app.after(0, lambda: messagebox.showinfo("Action Required", "Please enter your Password and CAPTCHA, then click 'Login'."))
                    WebDriverWait(driver, 300).until(EC.url_contains("ftoindexframe.aspx"))
                    self.app.log_message(self.log_display, "Login successful!", "success")
                except NoSuchElementException:
                    raise ValueError("A selection (District, Block, or Panchayat) was not found.")
            else:
                self.app.log_message(self.log_display, "No login details provided. Assuming you are already logged in.", "info")
                if "ftoindexframe.aspx" not in driver.current_url.lower():
                    # --- THIS IS THE FIX ---
                    # If not on the correct page, log an error and stop immediately.
                    error_msg = "Not on the FTO home page. Please log in and navigate there before running with empty fields."
                    self.app.log_message(self.log_display, error_msg, "error")
                    messagebox.showerror("Automation Stopped", error_msg)
                    return # Stop the automation

            # At this point, we assume the user is logged in.
            self.app.log_message(self.log_display, "Starting FTO verification process...")
            self.update_status("Processing Aadhaar FTO...", 0.5)
            self._process_verification_page(driver, wait, cfg["aadhaar_fto_url"], "Aadhaar FTO")
            
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