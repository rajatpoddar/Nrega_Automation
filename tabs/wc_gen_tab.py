# tabs/wc_gen_tab.py (Updated with Copy Log)
import tkinter
from tkinter import messagebox, filedialog
import customtkinter as ctk
import os, csv, time, pyperclip, sys
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import config
from .base_tab import BaseAutomationTab

class WcGenTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="wc_gen")
        self.csv_path = None
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)
        self._create_widgets()

    def _create_widgets(self):
        controls = ctk.CTkFrame(self)
        controls.grid(row=0, column=0, sticky='ew', pady=(10, 10), padx=10)
        controls.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(controls, text="Panchayat Name:").grid(row=0, column=0, sticky="w", pady=10, padx=15)
        self.panchayat_entry = ctk.CTkEntry(controls, width=30)
        self.panchayat_entry.grid(row=0, column=1, sticky="ew", pady=10, padx=15)
        
        ctk.CTkLabel(controls, text="CSV Data File:").grid(row=1, column=0, sticky="w", pady=10, padx=15)
        file_frame = ctk.CTkFrame(controls, fg_color="transparent")
        file_frame.grid(row=1, column=1, sticky='ew', pady=10, padx=15)
        self.select_button = ctk.CTkButton(file_frame, text="Select workcode_data.csv", command=self.select_csv_file)
        self.select_button.pack(side="left", padx=(0, 10))
        self.file_label = ctk.CTkLabel(file_frame, text="No file selected", text_color="gray")
        self.file_label.pack(side="left")
        
        action_frame = self._create_action_buttons(parent_frame=controls)
        action_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=15)

        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=1, column=0, sticky='nsew', padx=10, pady=(0,10))
        log_frame.grid_columnconfigure(0, weight=1); log_frame.grid_rowconfigure(1, weight=1)
        
        log_controls = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_controls.grid(row=0, column=0, sticky='ew')
        self.copy_logs_button = ctk.CTkButton(log_controls, text="Copy Log", width=100, command=self.copy_logs_to_clipboard)
        self.copy_logs_button.pack(side='right')
        
        self.log_display = ctk.CTkTextbox(log_frame, wrap=tkinter.WORD, state="disabled")
        self.log_display.grid(row=1, column=0, sticky='nsew', pady=(5,0))

    def set_ui_state(self, running: bool):
        state = "disabled" if running else "normal"
        self.start_button.configure(state=state)
        self.stop_button.configure(state="normal" if running else "disabled")
        self.reset_button.configure(state=state)
        self.select_button.configure(state=state)
        self.panchayat_entry.configure(state=state)
        if hasattr(self, 'copy_logs_button'): self.copy_logs_button.configure(state=state)

    def copy_logs_to_clipboard(self):
        log_content = self.log_display.get("1.0", tkinter.END)
        self.app.clipboard_clear(); self.app.clipboard_append(log_content)
        messagebox.showinfo("Copied", "Log content copied.")

    # ... All other methods like start_automation, reset_ui, run_automation_logic remain unchanged ...
    def reset_ui(self):
        if messagebox.askokcancel("Reset Form?", "Are you sure?"):
            self.panchayat_entry.delete(0, tkinter.END)
            self.file_label.configure(text="No file selected"); self.csv_path = None
            self.app.clear_log(self.log_display); self.app.log_message(self.log_display, "Form has been reset.")
    def select_csv_file(self):
        path = filedialog.askopenfilename(title="Select your CSV data file", filetypes=[("CSV files", "*.csv")])
        if path:
            self.csv_path = path; self.file_label.configure(text=os.path.basename(path))
            self.app.log_message(self.log_display, f"Selected file: {path}")
    def start_automation(self):
        if not self.csv_path: messagebox.showwarning("Missing File", "Please select a CSV file first."); return
        if not self.panchayat_entry.get(): messagebox.showwarning("Missing Info", "Please enter the Panchayat name."); return
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic)
    def run_automation_logic(self):
        self.app.after(0, self.set_ui_state, True)
        self.app.clear_log(self.log_display)
        self.app.log_message(self.log_display, "--- Starting Workcode Generation ---")
        try:
            driver = self.app.connect_to_chrome()
            if not driver: return
            panchayat_name = self.panchayat_entry.get()
            with open(self.csv_path, mode='r', encoding='utf-8') as csvfile:
                csv_reader = csv.reader(csvfile)
                next(csv_reader) # Skip header
                rows = list(csv_reader)
                total = len(rows)
                for i, row in enumerate(rows):
                    if self.app.stop_events[self.automation_key].is_set(): self.app.log_message(self.log_display, "Automation stopped by user."); break
                    if not any(field.strip() for field in row): continue
                    self.app.log_message(self.log_display, f"--- Processing Row {i+1}/{total} ---")
                    try: self._process_single_row(driver, panchayat_name, row)
                    except Exception as e: self.app.log_message(self.log_display, f"ERROR processing row {i+1}: {e}", "error"); continue
        except FileNotFoundError: self.app.log_message(self.log_display, "ERROR: CSV file not found.", "error")
        except Exception as e: self.app.log_message(self.log_display, f"An unexpected error occurred: {e}", "error")
        finally:
            self.app.after(0, self.set_ui_state, False)
            self.app.log_message(self.log_display, "\n--- Automation Finished ---")
    def _process_single_row(self, driver, panchayat_name, row_data):
        cfg = config.WC_GEN_CONFIG["defaults"]; current_year = datetime.now().year
        priority, work_name, khata_no, plot_no, village_name = row_data
        driver.get(config.WC_GEN_CONFIG["url"])
        self.app.log_message(self.log_display, "Navigated to work entry page...")
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_ddlMastercategory")))
        self.app.log_message(self.log_display, "Filling form data from config...")
        Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlMastercategory")).select_by_value(cfg["master_category"])
        Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlproposed_work_category")).select_by_visible_text(cfg["work_category"])
        Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlbeneficiary_type")).select_by_visible_text(cfg["beneficiary_type"])
        Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlactivity_type")).select_by_visible_text(cfg["activity_type"])
        Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlproposed_work_type")).select_by_visible_text(cfg["work_type"])
        Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlprostatus")).select_by_visible_text(cfg["pro_status"])
        driver.find_element(By.ID, "ContentPlaceHolder1_txtdist").clear(); driver.find_element(By.ID, "ContentPlaceHolder1_txtdist").send_keys(cfg["district_distance"])
        Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlpanch")).select_by_visible_text(panchayat_name); time.sleep(1.5)
        self.app.log_message(self.log_display, f"Selecting Village: {village_name}")
        Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlvillage")).select_by_visible_text(village_name)
        Select(driver.find_element(By.ID, "ContentPlaceHolder1_lblFin_year")).select_by_value(cfg["financial_year"])
        Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlridgetype")).select_by_value(cfg["ridge_type"])
        driver.find_element(By.ID, "ContentPlaceHolder1_txtPropDate").clear(); driver.find_element(By.ID, "ContentPlaceHolder1_txtPropDate").send_keys(cfg["proposal_date"].format(year=current_year))
        driver.find_element(By.ID, "ContentPlaceHolder1_txtstartdate").clear(); driver.find_element(By.ID, "ContentPlaceHolder1_txtstartdate").send_keys(cfg["start_date"].format(year=current_year))
        driver.find_element(By.ID, "ContentPlaceHolder1_TxtEstlb").clear(); driver.find_element(By.ID, "ContentPlaceHolder1_TxtEstlb").send_keys(cfg["est_labour_cost"])
        driver.find_element(By.ID, "ContentPlaceHolder1_txtEstMat").clear(); driver.find_element(By.ID, "ContentPlaceHolder1_txtEstMat").send_keys(cfg["est_material_cost"])
        Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlExeAgency")).select_by_value(cfg["executing_agency"])
        driver.find_element(By.ID, "ContentPlaceHolder1_txtPriority").send_keys(priority)
        driver.find_element(By.ID, "ContentPlaceHolder1_txtkhtano").send_keys(khata_no)
        driver.find_element(By.ID, "ContentPlaceHolder1_txtPlotNo").send_keys(plot_no)
        self.app.log_message(self.log_display, "Pasting 'Work Name'...")
        work_name_field = driver.find_element(By.ID, "ContentPlaceHolder1_txtworkname")
        pyperclip.copy(work_name)
        paste_key = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL
        work_name_field.send_keys(paste_key, 'v'); time.sleep(0.5)
        self.app.log_message(self.log_display, "Submitting...")
        driver.find_element(By.ID, "ContentPlaceHolder1_btSave").click(); time.sleep(3)
        self.app.log_message(self.log_display, f"Row submitted successfully.", "success")