# tabs/sad_update_tab.py
import tkinter
from tkinter import messagebox, filedialog
import customtkinter as ctk
import json
import os, time, csv
import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from .base_tab import BaseAutomationTab

class SADUpdateStatusTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="sad_update_status")
        self.config_file = self.app.get_data_path("sad_update_inputs.json")
        
        # Flags
        self.is_running = False
        self.stop_requested = False
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1) 
        
        self.main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.main_scroll.grid_columnconfigure(0, weight=1)

        self._create_widgets()
        self.load_inputs()

    def _create_widgets(self):
        # Frame
        main_frame = ctk.CTkFrame(self.main_scroll)
        main_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        main_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(main_frame, text="Sarkar Aapke Dwar - Update Status / Disposal", 
                     font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=3, pady=10, sticky="w", padx=10)

        # 1. File Selection
        ctk.CTkLabel(main_frame, text="Upload File (Excel/CSV):").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.csv_entry = ctk.CTkEntry(main_frame, placeholder_text="Select .xlsx or .csv file")
        self.csv_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        ctk.CTkButton(main_frame, text="Browse", width=80, command=self.browse_file).grid(row=1, column=2, padx=10, pady=5)

        # 2. Action Selection Dropdown
        ctk.CTkLabel(main_frame, text="Select Action:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.action_combobox = ctk.CTkComboBox(main_frame, values=["Dispose", "Reject", "In Progress", "Pending"])
        self.action_combobox.set("Dispose") 
        self.action_combobox.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        # 3. Control Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=3, column=0, columnspan=3, pady=15, sticky="ew")
        
        self.start_btn = ctk.CTkButton(btn_frame, text="Start Process", command=self.start_process, 
                                       fg_color="#28a745", hover_color="#218838", width=100)
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(btn_frame, text="Stop", command=self.stop_process, 
                                      fg_color="#dc3545", hover_color="#c82333", width=80, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        self.reset_btn = ctk.CTkButton(btn_frame, text="Reset", command=self.reset_ui, 
                                       fg_color="#6c757d", hover_color="#5a6268", width=80)
        self.reset_btn.pack(side="left", padx=5)

        self.copy_log_btn = ctk.CTkButton(btn_frame, text="Copy Log", command=self.copy_logs, 
                                          fg_color="#17a2b8", hover_color="#138496", width=80)
        self.copy_log_btn.pack(side="left", padx=5)

        # 4. Logs
        log_frame = ctk.CTkFrame(self.main_scroll)
        log_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        log_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(log_frame, text="Process Logs").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.log_display = ctk.CTkTextbox(log_frame, height=200, state="disabled")
        self.log_display.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel/CSV Files", "*.xlsx *.csv")])
        if file_path:
            self.csv_entry.delete(0, tkinter.END)
            self.csv_entry.insert(0, file_path)

    def log(self, message):
        self.app.log_message(self.log_display, message)

    def copy_logs(self):
        try:
            log_content = self.log_display.get("1.0", "end")
            self.app.clipboard_clear()
            self.app.clipboard_append(log_content)
            self.app.update()
            messagebox.showinfo("Copied", "Logs copied to clipboard!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy: {e}")

    def reset_ui(self):
        self.csv_entry.delete(0, tkinter.END)
        self.app.clear_log(self.log_display)
        self.log("UI Reset.")

    def save_inputs(self, inputs):
        try:
            with open(self.config_file, 'w') as f: json.dump(inputs, f, indent=4)
        except: pass

    def load_inputs(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.csv_entry.insert(0, data.get('csv_file', ''))
        except: pass

    # --- File Reading Helper ---
    def read_file_data(self, file_path):
        rows = []
        file_ext = os.path.splitext(file_path)[1].lower()
        try:
            if file_ext == '.xlsx':
                try:
                    import openpyxl
                    wb = openpyxl.load_workbook(file_path, data_only=True)
                    sheet = wb.active
                    headers = [str(cell.value).strip() for cell in sheet[1] if cell.value]
                    for row in sheet.iter_rows(min_row=2, values_only=True):
                        if any(row):
                            row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
                            rows.append(row_dict)
                    return rows, None
                except ImportError:
                    return [], "Error: 'openpyxl' module missing."
                except Exception as e:
                    return [], f"Excel Read Error: {str(e)}"
            else:
                encodings_to_try = ['utf-8-sig', 'cp1252', 'latin1']
                for enc in encodings_to_try:
                    try:
                        with open(file_path, 'r', encoding=enc) as f:
                            reader = csv.DictReader(f)
                            rows = list(reader)
                        return rows, None
                    except UnicodeDecodeError: continue
                    except Exception as e: return [], f"CSV Error: {str(e)}"
                return [], "Failed to read CSV with standard encodings."
        except Exception as e:
            return [], f"File Read Error: {str(e)}"

    def start_process(self):
        file_path = self.csv_entry.get().strip()
        action_text = self.action_combobox.get().strip()

        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Error", "Valid file select karein.")
            return

        action_map = {"Pending": "0", "In Progress": "1", "Dispose": "2", "Reject": "3"}
        action_val = action_map.get(action_text, "2")

        self.save_inputs({'csv_file': file_path})
        
        self.is_running = True
        self.stop_requested = False
        self.start_btn.configure(state="disabled", text="Running...")
        self.stop_btn.configure(state="normal")
        
        threading.Thread(target=self.run_logic, args=(file_path, action_val, action_text), daemon=True).start()

    def stop_process(self):
        if self.is_running:
            self.stop_requested = True
            self.log("Stopping requested... finishing current step.")
            self.stop_btn.configure(state="disabled")

    def run_logic(self, file_path, action_val, action_text):
        try:
            driver = self.app.get_driver()
            if not driver: return

            self.log(f"Reading file: {os.path.basename(file_path)}")
            rows, error_msg = self.read_file_data(file_path)
            if error_msg:
                self.log(error_msg)
                self.finish_run()
                return

            total = len(rows)
            self.log(f"Total Rows: {total}. Action: {action_text}")

            processed_success = 0
            
            for idx, row in enumerate(rows):
                if self.stop_requested:
                    self.log("!!! Process Stopped by User !!!")
                    break

                try:
                    # --- Get accNo ---
                    raw_acc = None
                    for key in row.keys():
                        if key.lower() in ['accno', 'ack no', 'acknowledgement no', 'ackno']:
                            raw_acc = row[key]
                            break
                    
                    if not raw_acc: continue
                    
                    raw_acc = str(raw_acc).strip()
                    search_term = raw_acc
                    if "3/28/" in raw_acc:
                        parts = raw_acc.split("3/28/")
                        if len(parts) > 1:
                            search_term = parts[1]
                    
                    self.log(f"[{idx+1}/{total}] Processing: {raw_acc}")

                    # 1. Search Page
                    driver.get("https://sarkaraapkedwar.jharkhand.gov.in/#/application/search")
                    wait = WebDriverWait(driver, 5)

                    # 2. Enter Number
                    try:
                        inp = wait.until(EC.presence_of_element_located((By.NAME, "accNo")))
                        inp.clear()
                        inp.send_keys(search_term)
                    except TimeoutException:
                        self.log(f"--> Error: Input field 'accNo' not found.")
                        continue

                    # 3. Click Search
                    try:
                        search_btn = driver.find_element(By.XPATH, "//button[contains(., 'Search Applicant')]")
                        search_btn.click()
                    except NoSuchElementException:
                        self.log("--> Search button not found.")
                        continue

                    # 4. Click Update Icon
                    try:
                        edit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'update-status')]")))
                        edit_btn.click()
                    except TimeoutException:
                        try:
                            edit_btn = driver.find_element(By.XPATH, "//a[contains(., 'Update')]")
                            edit_btn.click()
                        except:
                            self.log(f"--> Update Link Not found.")
                            continue
                    
                    # 5. Select Action
                    try:
                        select_elem = wait.until(EC.presence_of_element_located((By.TAG_NAME, "select")))
                        select = Select(select_elem)
                        select.select_by_value(action_val)
                    except:
                        self.log("--> Select dropdown not found.")
                        continue
                    
                    time.sleep(0.5)

                    # --- Handle "Set Documents" Modal for Dispose ---
                    if action_val == "2":
                        try:
                            set_docs_btn = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Set Documents')]"))
                            )
                            set_docs_btn.click()
                            time.sleep(1)
                        except TimeoutException:
                            pass # Modal not found, proceeding

                    # 6. Click "Update Status"
                    try:
                        update_final_btn = driver.find_element(By.XPATH, "//button[contains(., 'Update Status')]")
                        driver.execute_script("arguments[0].scrollIntoView();", update_final_btn)
                        
                        if update_final_btn.is_enabled():
                            update_final_btn.click()
                            
                            # --- NEW: Handle SUCCESS Popup (SweetAlert) ---
                            try:
                                # Look for the 'OK' button in SweetAlert and click it
                                # Class usually 'swal2-confirm' or button text 'OK'
                                swal_ok = WebDriverWait(driver, 5).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.swal2-confirm"))
                                )
                                swal_ok.click()
                                self.log("--> Success (Popup Closed)")
                                
                                # Wait for popup to disappear so it doesn't block next loop
                                WebDriverWait(driver, 3).until(
                                    EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.swal2-container"))
                                )
                            except TimeoutException:
                                self.log("--> Success (Popup auto-closed or not found)")
                            
                            processed_success += 1
                            time.sleep(1) 
                        else:
                            self.log("--> Update button disabled.")
                    except Exception as e:
                         self.log(f"--> Update click failed: {e}")

                except Exception as e:
                    self.log(f"Error on row {idx+1}: {str(e)}")

            self.log("Automation Batch Ended.")
            if not self.stop_requested:
                messagebox.showinfo("Completed", f"Process Finished.\nSuccess: {processed_success}/{total}")

        except Exception as e:
            self.log(f"Critical Error: {e}")
            messagebox.showerror("Error", str(e))
        finally:
            self.finish_run()

    def finish_run(self):
        self.is_running = False
        self.stop_requested = False
        self.app.after(0, lambda: self.start_btn.configure(state="normal", text="Start Process"))
        self.app.after(0, lambda: self.stop_btn.configure(state="disabled"))