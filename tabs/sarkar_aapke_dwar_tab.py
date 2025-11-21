# tabs/sarkar_aapke_dwar_tab.py
import tkinter
from tkinter import messagebox, filedialog
import customtkinter as ctk
import json
import os, time, csv
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException
from .base_tab import BaseAutomationTab

class SarkarAapkeDwarTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="sad_auto")
        self.config_file = self.app.get_data_path("sad_inputs.json")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._create_widgets()
        self.load_inputs()

    def _create_widgets(self):
        # --- Configuration Frame ---
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        controls_frame.grid_columnconfigure(1, weight=1)

        # Header
        ctk.CTkLabel(controls_frame, text="Sarkar Aapke Dwar Automation", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=15, pady=(10, 5))

        # --- MODE 1: CSV Bulk Upload (Optional) ---
        bulk_frame = ctk.CTkFrame(controls_frame, fg_color=("gray90", "gray20"))
        bulk_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=10)
        bulk_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(bulk_frame, text="Mode 1: Bulk Entry (via CSV)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=5)
        
        self.csv_path_entry = ctk.CTkEntry(bulk_frame, placeholder_text="Select CSV file for bulk entry...")
        self.csv_path_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        
        btn_frame = ctk.CTkFrame(bulk_frame, fg_color="transparent")
        btn_frame.grid(row=1, column=2, padx=5)
        
        ctk.CTkButton(btn_frame, text="Browse", width=80, command=self.browse_csv).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="Get Demo CSV", width=100, fg_color="green", command=self.generate_demo_csv).pack(side="left", padx=2)
        
        ctk.CTkLabel(bulk_frame, text="* If CSV is selected, app will auto-fill ALL fields and submit applications one by one.", text_color="gray60", font=ctk.CTkFont(size=11)).grid(row=2, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 5))

        # --- MODE 2: Monitor & Auto-Fill (Manual Helper) ---
        monitor_frame = ctk.CTkFrame(controls_frame)
        monitor_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10))
        monitor_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(monitor_frame, text="Mode 2: Manual Helper (Auto-fill Scheme only)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        ctk.CTkLabel(monitor_frame, text="* Used only if CSV is empty. Fills scheme details when you open a new form.", text_color="gray60", font=ctk.CTkFont(size=11)).grid(row=0, column=2, sticky="e", padx=10)

        # 1. Applicant Remarks
        ctk.CTkLabel(monitor_frame, text="Applicant Remarks:").grid(row=1, column=0, sticky="w", padx=10, pady=2)
        self.app_remarks_entry = ctk.CTkEntry(monitor_frame, placeholder_text="Enter Applicant Remarks")
        self.app_remarks_entry.grid(row=1, column=1, columnspan=2, sticky="ew", padx=10, pady=2)

        # 2. Scheme Type Dropdown
        ctk.CTkLabel(monitor_frame, text="Scheme Type:").grid(row=2, column=0, sticky="w", padx=10, pady=2)
        scheme_types = ["Service Focus Area"] 
        self.scheme_type_combobox = ctk.CTkComboBox(monitor_frame, values=scheme_types, width=300)
        self.scheme_type_combobox.set("Service Focus Area")
        self.scheme_type_combobox.grid(row=2, column=1, columnspan=2, sticky="ew", padx=10, pady=2)

        # 3. Scheme/Service Dropdown
        ctk.CTkLabel(monitor_frame, text="Scheme/Service:").grid(row=3, column=0, sticky="w", padx=10, pady=2)
        service_options = [
            "जाति प्रमाण पत्र (Caste Certificate)",
            "आय प्रमाण पत्र (Income Certificate)",
            "जन्म प्रमाण पत्र (Birth Certificate)",
            "मृत्यु प्रमाण पत्र (Death Certificate)",
            "दाखिल खारिज वादों का निष्पादन (Mutation/Disposal of Land Cases)",
            "भूमि की मापी (Measurement of Land)",
            "भूमि धारण प्रमाण पत्र (Land Holding Certificate)",
            "नया राशन कार्ड (New Ration Card)",
            "स्थानीय निवासी प्रमाण पत्र (Local Resident Certificate)",
            "वृद्धा पेंशन (Old Age Pension)",
            "विधवा पेंशन (Widow Pension)",
            "विकलांग पेंशन (Disability Pension)",
            "झारखंड राज्य सेवा देने की गारंटी अधिनियम 2011 से जुड़ी अन्य सेवाएं (Other Services under Jharkhand Right to Guarantee of Services Act 2011)"
        ]
        self.service_combobox = ctk.CTkComboBox(monitor_frame, values=service_options, width=300)
        self.service_combobox.grid(row=3, column=1, columnspan=2, sticky="ew", padx=10, pady=2)

        # 4. Scheme Remarks
        ctk.CTkLabel(monitor_frame, text="Scheme Remarks:").grid(row=4, column=0, sticky="w", padx=10, pady=2)
        self.scheme_remarks_entry = ctk.CTkEntry(monitor_frame, placeholder_text="Enter Scheme Remarks")
        self.scheme_remarks_entry.grid(row=4, column=1, columnspan=2, sticky="ew", padx=10, pady=2)

        # Action Buttons
        action_frame = self._create_action_buttons(parent_frame=controls_frame)
        action_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=15)

        # --- Logs & Status Area ---
        data_notebook = ctk.CTkTabview(self)
        data_notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self._create_log_and_status_area(parent_notebook=data_notebook)

    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running)
        state = "disabled" if running else "normal"
        self.app_remarks_entry.configure(state=state)
        self.scheme_type_combobox.configure(state=state)
        self.service_combobox.configure(state=state)
        self.scheme_remarks_entry.configure(state=state)
        self.csv_path_entry.configure(state=state)

    def browse_csv(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if file_path:
            self.csv_path_entry.delete(0, tkinter.END)
            self.csv_path_entry.insert(0, file_path)

    def generate_demo_csv(self):
        headers = [
            "Applicant Name", "Father/Husband Name", "Age", "Mobile No", 
            "Is WhatsApp (Y/N)", "Village", "Address", "Applicant Remarks", 
            "Scheme Type", "Service", "Scheme Remarks"
        ]
        demo_data = [
            "Ramesh Kumar", "Suresh Kumar", "45", "9876543210", "Y", "Ratu", "House No 12, Main Road", "Camp Application", "Service Focus Area", "जाति प्रमाण पत्र (Caste Certificate)", "Urgent"
        ]
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv", 
            filetypes=[("CSV Files", "*.csv")],
            initialfile="SAD_Bulk_Entry_Demo.csv",
            title="Save Demo CSV"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    writer.writerow(demo_data)
                messagebox.showinfo("Success", "Demo CSV saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {e}")

    def start_automation(self):
        inputs = {
            'csv_file': self.csv_path_entry.get().strip(),
            'app_remarks': self.app_remarks_entry.get().strip(),
            'scheme_type': self.scheme_type_combobox.get().strip(),
            'service': self.service_combobox.get().strip(),
            'scheme_remarks': self.scheme_remarks_entry.get().strip()
        }

        # Validation
        if inputs['csv_file']:
            if not os.path.exists(inputs['csv_file']):
                messagebox.showerror("File Error", "CSV File does not exist.")
                return
        else:
            if not inputs['scheme_type'] or not inputs['service']:
                messagebox.showwarning("Input Error", "For Manual Helper Mode, Scheme Type and Service are required.")
                return

        self.save_inputs(inputs)
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic, args=(inputs,))

    def run_automation_logic(self, inputs):
        self.app.after(0, self.set_ui_state, True)
        self.app.clear_log(self.log_display)
        
        try:
            driver = self.app.get_driver()
            if not driver:
                self.app.after(0, self.set_ui_state, False)
                return
            wait = WebDriverWait(driver, 10)

            # DECIDE MODE
            if inputs['csv_file']:
                self.app.log_message(self.log_display, "Starting BULK ENTRY Mode from CSV...")
                self._run_bulk_mode(driver, wait, inputs['csv_file'])
            else:
                self.app.log_message(self.log_display, "Starting MONITOR Mode (Manual Helper)...")
                self._run_monitor_mode(driver, wait, inputs)

        except Exception as e:
            self.app.log_message(self.log_display, f"Critical Error: {e}", "error")
        finally:
            self.app.after(0, self.set_ui_state, False)
            self.app.after(0, self.app.set_status, "Automation Stopped")

    def _run_bulk_mode(self, driver, wait, csv_path):
        data = []
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                data = list(reader)
        except Exception as e:
            self.app.log_message(self.log_display, f"Error reading CSV: {e}", "error")
            return

        total = len(data)
        self.app.log_message(self.log_display, f"Loaded {total} records from CSV.")

        for i, row in enumerate(data):
            if self.app.stop_events[self.automation_key].is_set(): break
            
            applicant_name = row.get("Applicant Name", "").strip()
            self.app.log_message(self.log_display, f"Processing ({i+1}/{total}): {applicant_name}")
            self.app.after(0, self.update_status, f"Processing {applicant_name}...", (i+1)/total)

            try:
                # 1. Ensure on Create Page
                if "application/create" not in driver.current_url:
                    driver.get("https://sarkaraapkedwar.jharkhand.gov.in/#/application/create")
                    time.sleep(2)

                # 2. Wait for form
                wait.until(EC.presence_of_element_located((By.NAME, "applicantName")))

                # 3. Fill Basic Details
                self._safe_send_keys(driver, "applicantName", applicant_name)
                self._safe_send_keys(driver, "fatherHusbandName", row.get("Father/Husband Name", ""))
                self._safe_send_keys(driver, "age", row.get("Age", ""))
                self._safe_send_keys(driver, "mobileNo", row.get("Mobile No", ""))
                
                # WhatsApp Checkbox
                is_whatsapp = row.get("Is WhatsApp (Y/N)", "N").upper()
                try:
                    chk = driver.find_element(By.ID, "isWhatsAppMobile")
                    if (is_whatsapp.startswith("Y") and not chk.selected) or (is_whatsapp.startswith("N") and chk.selected):
                        chk.click()
                except: pass

                # 4. Village (React Select Handling)
                village = row.get("Village", "")
                if village:
                    try:
                        # React select input usually has an ID like 'react-select-2-input'
                        # We search for the input inside the village container
                        village_input = driver.find_element(By.XPATH, "//div[contains(text(), 'Select Village')]/following-sibling::div//input")
                        # Alternatively, check for specific ID from screenshot/html if consistent
                        if not village_input:
                            village_input = driver.find_element(By.ID, "react-select-2-input")
                        
                        village_input.send_keys(village)
                        time.sleep(1)
                        village_input.send_keys(Keys.ENTER)
                    except Exception as e:
                        self.app.log_message(self.log_display, f"Warning: Could not select Village '{village}'. Error: {e}", "warning")

                # 5. Address & Remarks
                self._safe_send_keys(driver, "address", row.get("Address", ""))
                self._safe_send_keys(driver, "remarks", row.get("Applicant Remarks", ""))

                # 6. Scheme Details
                # Scroll down to ensure visibility
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                scheme_type = row.get("Scheme Type", "")
                if scheme_type:
                    Select(driver.find_element(By.NAME, "schemeId")).select_by_visible_text(scheme_type)
                    time.sleep(1) # Wait for services to load

                service = row.get("Service", "")
                if service:
                    try:
                        svc_select = Select(wait.until(EC.presence_of_element_located((By.NAME, "schemeService"))))
                        try:
                            svc_select.select_by_visible_text(service)
                        except:
                            # Partial match attempt
                            for opt in svc_select.options:
                                if service.lower() in opt.text.lower():
                                    svc_select.select_by_visible_text(opt.text)
                                    break
                    except Exception:
                        self.app.log_message(self.log_display, f"Error selecting Service: {service}", "error")

                self._safe_send_keys(driver, "schemeRemarks", row.get("Scheme Remarks", ""))

                # 7. Click Add Service
                add_btn = driver.find_element(By.XPATH, "//button[contains(., 'Add Service')]")
                add_btn.click()
                
                # Wait for row to appear in table (Validation that service is added)
                time.sleep(1)
                
                # 8. Click Create Application (Final Submit)
                create_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Create Application')]")))
                create_btn.click()
                
                # 9. Handle Success/Reset
                # Wait for success message or page reload
                time.sleep(2)
                
                # Click Reset to prepare for next
                try:
                    reset_btn = driver.find_element(By.XPATH, "//button[contains(., 'Reset')]")
                    reset_btn.click()
                    time.sleep(1)
                except:
                    driver.refresh() # Fallback
                    time.sleep(2)

                self.app.log_message(self.log_display, f"Success: {applicant_name}", "success")

            except Exception as e:
                self.app.log_message(self.log_display, f"Failed to process {applicant_name}: {e}", "error")
                # Try to refresh to recover for next row
                driver.refresh()
                time.sleep(3)

    def _run_monitor_mode(self, driver, wait, inputs):
        # ... (Keep existing Monitor Logic here) ...
        # Copied from previous version for completeness
        while not self.app.stop_events[self.automation_key].is_set():
            try:
                if "application/create" not in driver.current_url:
                    time.sleep(2); continue

                try:
                    tbody = driver.find_element(By.CSS_SELECTOR, "table tbody")
                    if len(tbody.find_elements(By.TAG_NAME, "tr")) > 0:
                        time.sleep(2); continue
                except NoSuchElementException: pass

                scheme_dd = driver.find_element(By.NAME, "schemeId")
                if Select(scheme_dd).first_selected_option.text.strip() == "Select Scheme Type":
                    self.app.log_message(self.log_display, "New blank form. Auto-filling...")
                    
                    if inputs['app_remarks']: self._safe_send_keys(driver, "remarks", inputs['app_remarks'])
                    
                    Select(scheme_dd).select_by_visible_text(inputs['scheme_type'])
                    time.sleep(1)
                    
                    svc_select = Select(driver.find_element(By.NAME, "schemeService"))
                    # Retry loop for service population
                    for _ in range(5):
                        if len(svc_select.options) > 1: break
                        time.sleep(1)
                    
                    try:
                        svc_select.select_by_visible_text(inputs['service'])
                    except:
                        for opt in svc_select.options:
                            if inputs['service'] in opt.text: svc_select.select_by_visible_text(opt.text); break
                    
                    if inputs['scheme_remarks']: self._safe_send_keys(driver, "schemeRemarks", inputs['scheme_remarks'])
                    
                    driver.find_element(By.XPATH, "//button[contains(., 'Add Service')]").click()
                    self.app.log_message(self.log_display, "Service Added.")
                    time.sleep(3)
                else:
                    time.sleep(1)
            except Exception:
                time.sleep(1)

    def _safe_send_keys(self, driver, element_name, value):
        if not value: return
        try:
            elem = driver.find_element(By.NAME, element_name)
            elem.clear()
            elem.send_keys(value)
        except: pass

    def reset_ui(self):
        self.csv_path_entry.delete(0, tkinter.END)
        self.app_remarks_entry.delete(0, tkinter.END)
        self.scheme_type_combobox.set("Service Focus Area")
        self.service_combobox.set("")
        self.scheme_remarks_entry.delete(0, tkinter.END)
        self.app.clear_log(self.log_display)
        self.app.after(0, self.app.set_status, "Ready")

    def save_inputs(self, inputs):
        try:
            with open(self.config_file, 'w') as f: json.dump(inputs, f, indent=4)
        except Exception as e: print(f"Error saving SAD inputs: {e}")

    def load_inputs(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.csv_path_entry.insert(0, data.get('csv_file', ''))
                    self.app_remarks_entry.insert(0, data.get('app_remarks', ''))
                    self.scheme_type_combobox.set(data.get('scheme_type', 'Service Focus Area'))
                    self.service_combobox.set(data.get('service', ''))
                    self.scheme_remarks_entry.insert(0, data.get('scheme_remarks', ''))
        except Exception as e: print(f"Error loading SAD inputs: {e}")