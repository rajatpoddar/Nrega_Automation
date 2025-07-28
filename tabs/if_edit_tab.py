# tabs/if_edit_tab.py (Refactored to use BaseAutomationTab)
import tkinter
from tkinter import messagebox, filedialog
import customtkinter as ctk
import os, csv, time, pyperclip
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import config
from .base_tab import BaseAutomationTab

class IfEditTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="if_edit")
        self.csv_path = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self._create_widgets()

    def _create_widgets(self):
        controls = ctk.CTkFrame(self)
        controls.grid(row=0, column=0, sticky="ew", pady=(0,10))
        controls.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(controls, text="CSV Data File:").grid(row=0, column=0, sticky="w", padx=15, pady=10)
        file_frame = ctk.CTkFrame(controls, fg_color="transparent")
        file_frame.grid(row=0, column=1, sticky='ew', pady=10, padx=15)
        
        self.select_button = ctk.CTkButton(file_frame, text="Select if_edit_data.csv", command=self.select_csv_file)
        self.select_button.pack(side="left", padx=(0, 10))
        self.file_label = ctk.CTkLabel(file_frame, text="No file selected", text_color="gray")
        self.file_label.pack(side="left")
        
        # Use the method from the base class to create the action buttons
        action_frame = self._create_action_buttons(parent_frame=controls)
        action_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=15)

        # This tab has a simple logger, so we create it here
        log_notebook = ctk.CTkTabview(self)
        log_notebook.grid(row=1, column=0, sticky="nsew")
        log_frame = log_notebook.add("Log")
        
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)
        self.log_area = ctk.CTkTextbox(log_frame, wrap=tkinter.WORD, state="disabled")
        self.log_area.grid(row=0, column=0, sticky="nsew")
        
        copy_button = ctk.CTkButton(log_frame, text="Copy Log", width=100, command=self.copy_log_to_clipboard)
        copy_button.grid(row=1, column=0, sticky='e', pady=(5,0))

    def copy_log_to_clipboard(self):
        try:
            pyperclip.copy(self.log_area.get("1.0", tkinter.END))
            messagebox.showinfo("Copied", "Log content copied to clipboard.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not copy log: {e}")

    def reset_ui(self):
        if messagebox.askokcancel("Reset Form?", "Are you sure?"):
            self.file_label.configure(text="No file selected")
            self.csv_path = None
            self.app.clear_log(self.log_area)
            self.app.log_message(self.log_area, "Form has been reset.")

    def set_ui_state(self, running: bool):
        # Use the common method for start/stop/reset buttons
        # Note: Base class progress bar doesn't apply here, but that's okay
        self.start_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")
        self.reset_button.configure(state="disabled" if running else "normal")
        
        # Handle tab-specific widgets
        self.select_button.configure(state="disabled" if running else "normal")

    def select_csv_file(self):
        path = filedialog.askopenfilename(title="Select CSV", filetypes=[("CSV files", "*.csv")])
        if path:
            self.csv_path = path
            self.file_label.configure(text=os.path.basename(path))
            self.app.log_message(self.log_area, f"Selected file: {path}")

    def start_automation(self):
        if not self.csv_path:
            messagebox.showwarning("Input Missing", "Please select a CSV file first.")
            return
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic)

    def run_automation_logic(self):
        self.app.after(0, self.set_ui_state, True)
        self.app.clear_log(self.log_area)
        self.app.log_message(self.log_area, "--- Starting IF Editor Automation ---")
        try:
            driver = self.app.get_driver()
            if not driver: return
            
            with open(self.csv_path, mode='r', encoding='utf-8-sig') as csvfile:
                rows = list(csv.reader(csvfile))[1:]
                total = len(rows)
                for i, row in enumerate(rows):
                    if self.app.stop_events[self.automation_key].is_set():
                        self.app.log_message(self.log_area, "Automation stopped.", "warning"); break
                    if not row or len(row) < 3:
                        self.app.log_message(self.log_area, f"Skipping empty row {i+1}.", "warning"); continue
                        
                    work_code, beneficiary_type, job_card = row[0].strip(), row[1].strip(), row[2].strip()
                    self.app.log_message(self.log_area, f"--- Processing {i+1}/{total}: WC={work_code} ---")
                    self._process_single_if_edit(driver, work_code, beneficiary_type, job_card)
        
        except FileNotFoundError:
            self.app.log_message(self.log_area, f"FATAL: File not found at {self.csv_path}", "error")
        except Exception as e:
            self.app.log_message(self.log_area, f"A critical error occurred: {e}", "error")
        finally:
            self.app.log_message(self.log_area, "--- Automation Finished ---")
            self.app.after(0, self.set_ui_state, False)

    def _process_single_if_edit(self, driver, work_code, beneficiary_type, job_card):
        # This method's logic is specific and remains unchanged
        try:
            cfg1 = config.IF_EDIT_CONFIG["page1"]; cfg2 = config.IF_EDIT_CONFIG["page2"]; cfg3 = config.IF_EDIT_CONFIG["page3"]
            current_year = datetime.now().year; wait = WebDriverWait(driver, 10)
            driver.get(config.IF_EDIT_CONFIG["url"]); self.app.log_message(self.log_area, "Page 1: Entering work details...")
            wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_txtwrksearchkey"))).clear()
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtwrksearchkey").send_keys(work_code)
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtwrksearchkey").send_keys(Keys.TAB); time.sleep(1)
            Select(wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ddlworkName")))).select_by_index(1); time.sleep(3)
            wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_TxtEstpd"))).clear()
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_TxtEstpd").send_keys(cfg1["estimated_pd"])
            beneficiaries_input = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txt_nofobenificary")
            beneficiaries_input.clear(); beneficiaries_input.send_keys(cfg1["beneficiaries_count"])
            beneficiaries_input.send_keys(Keys.TAB); time.sleep(2)
            Select(wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_grdData_ctl02_ddljobcard")))).select_by_value(job_card); time.sleep(1)
            Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlTypeBenif")).select_by_visible_text(beneficiary_type)
            Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlpresentstatus")).select_by_visible_text(cfg1["present_status"])
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_UCconverg_rblConverg_0").click(); time.sleep(1)
            Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_UCconverg_ddlSchemeType1")).select_by_visible_text(cfg1["convergence_scheme_type"]); time.sleep(1) 
            Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_UCconverg_ddlScheme1")).select_by_visible_text(cfg1["convergence_scheme_name"])
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btupdate").click(); self.app.log_message(self.log_area, "Page 1 'Update' clicked.", "success")
            self.app.log_message(self.log_area, "Page 2: Entering sanction details..."); wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_txtsanctionno")))
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtsanctionno").send_keys(cfg2["sanction_no"].format(year=current_year))
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtsanctionDate").send_keys(cfg2["sanction_date"].format(year=current_year))
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtEstTimecompWork").send_keys(cfg2["est_time_completion"])
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtAvglabourperday").send_keys(cfg2["avg_labour_per_day"])
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtExcpectedmanday").clear(); driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtExcpectedmanday").send_keys(cfg2["expected_mandays"])
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtTechsancAmt").clear(); driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtTechsancAmt").send_keys(cfg2["tech_sanction_amount"])
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_Sanc_Tech_Labr_Unskilled").clear(); driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_Sanc_Tech_Labr_Unskilled").send_keys(cfg2["unskilled_labour_cost"])
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtFinsan_no").send_keys(cfg2["fin_sanction_no"].format(year=current_year))
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_sanc_fin_date").send_keys(cfg2["fin_sanction_date"].format(year=current_year))
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_sanc_fin_Amt").clear(); driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_sanc_fin_Amt").send_keys(cfg2["fin_sanction_amount"])
            fin_scheme_input = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_fin_scheme1"); fin_scheme_input.clear()
            fin_scheme_input.send_keys(cfg2["fin_scheme_input"]); fin_scheme_input.send_keys(Keys.TAB); time.sleep(0.5)
            save_button = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btSave"); driver.execute_script("arguments[0].click();", save_button); self.app.log_message(self.log_area, "Page 2 'Save' clicked.", "success")
            self.app.log_message(self.log_area, "Page 3: Entering activity details..."); wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddlAct")))
            Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlAct")).select_by_value(cfg3["activity_code"]); time.sleep(2)
            unit_price_input = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_txtAct_UnitPrice")))
            unit_price_input.clear(); unit_price_input.send_keys(cfg3["unit_price"]); unit_price_input.send_keys(Keys.TAB); time.sleep(2)
            qty_input = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_txtAct_Qty")))
            qty_input.clear(); qty_input.send_keys(cfg3["quantity"]); qty_input.send_keys(Keys.TAB); time.sleep(1)
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btsave").click(); self.app.log_message(self.log_area, f"SUCCESS: Final 'Save' clicked for {job_card}.", "success"); time.sleep(3)
        except Exception as e:
            self.app.log_message(self.log_area, f"An error occurred for WC {work_code}: {e}", "error")