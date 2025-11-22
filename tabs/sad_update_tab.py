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

        # Title
        ctk.CTkLabel(main_frame, text="Sarkar Aapke Dwar - Update Status / Disposal", 
                     font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=3, pady=10, sticky="w", padx=10)

        # --- NEW NOTE ADDED HERE (Row 1) ---
        ctk.CTkLabel(main_frame, text="Note: Download Excel filtered Applicant report from ASAD portal and directly upload it here.", 
                     text_color="gray", font=("Arial", 12, "italic")).grid(row=1, column=0, columnspan=3, sticky="w", padx=15, pady=(0, 10))

        # 1. File Selection (Row 2)
        ctk.CTkLabel(main_frame, text="Upload File (Excel/CSV):").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.csv_entry = ctk.CTkEntry(main_frame, placeholder_text="Select .xlsx or .csv file")
        self.csv_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        ctk.CTkButton(main_frame, text="Browse", width=80, command=self.browse_file).grid(row=2, column=2, padx=10, pady=5)

        # 2. Action Selection (Row 3)
        ctk.CTkLabel(main_frame, text="Select Action:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.action_combobox = ctk.CTkComboBox(main_frame, values=["Dispose", "Reject", "In Progress", "Pending"])
        self.action_combobox.set("Dispose") 
        self.action_combobox.grid(row=3, column=1, sticky="ew", padx=5, pady=5)

        # 3. Block Code Prefix (Row 4)
        ctk.CTkLabel(main_frame, text="Block Code to Remove:").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        self.prefix_entry = ctk.CTkEntry(main_frame, placeholder_text="e.g. 3/28/ (Leave empty if not needed)")
        self.prefix_entry.grid(row=4, column=1, sticky="ew", padx=5, pady=5)
        ctk.CTkLabel(main_frame, text="(Prefix will be removed)", 
                     text_color="gray", font=("Arial", 10)).grid(row=4, column=2, sticky="w", padx=5)

        # 4. Control Buttons (Row 5)
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=5, column=0, columnspan=3, pady=15, sticky="ew")
        
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

        # 5. Logs
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
        self.prefix_entry.delete(0, tkinter.END)
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
                    self.prefix_entry.insert(0, data.get('block_prefix', '3/28/')) # Default suggested
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
        prefix_val = self.prefix_entry.get().strip()

        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Error", "Valid file select karein.")
            return

        action_map = {"Pending": "0", "In Progress": "1", "Dispose": "2", "Reject": "3"}
        action_val = action_map.get(action_text, "2")

        self.save_inputs({'csv_file': file_path, 'block_prefix': prefix_val})
        
        self.is_running = True
        self.stop_requested = False
        self.start_btn.configure(state="disabled", text="Running...")
        self.stop_btn.configure(state="normal")
        
        threading.Thread(target=self.run_logic, args=(file_path, action_val, action_text, prefix_val), daemon=True).start()

    def stop_process(self):
        if self.is_running:
            self.stop_requested = True
            self.log("Stopping requested... finishing current step.")
            self.stop_btn.configure(state="disabled")

    def run_logic(self, file_path, action_val, action_text, prefix_val):
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
            if prefix_val:
                self.log(f"Using Block Prefix: '{prefix_val}'")

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

                    # --- DYNAMIC PREFIX REMOVAL ---
                    if prefix_val:
                        # Case insensitive check if needed, but standardizing on exact match usually better
                        if search_term.startswith(prefix_val):
                            search_term = search_term[len(prefix_val):]
                        elif prefix_val in search_term:
                            # Fallback: Agar prefix shuru me nahi par beech me hai (kam chance hai)
                            search_term = search_term.replace(prefix_val, "", 1)
                    
                    self.log(f"[{idx+1}/{total}] Processing: {raw_acc} -> Search: {search_term}")

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
                            self.log(f"--> Update Link Not found (Applicant mismatch?).")
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
                            pass

                    # 6. Click "Update Status"
                    try:
                        update_final_btn = driver.find_element(By.XPATH, "//button[contains(., 'Update Status')]")
                        driver.execute_script("arguments[0].scrollIntoView();", update_final_btn)
                        
                        if update_final_btn.is_enabled():
                            update_final_btn.click()
                            
                            # --- Handle SUCCESS Popup (SweetAlert) ---
                            try:
                                # Find 'OK' button in SweetAlert
                                swal_ok = WebDriverWait(driver, 5).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.swal2-confirm"))
                                )
                                swal_ok.click()
                                self.log("--> Success (Popup Closed)")
                                
                                # Wait for popup to vanish
                                WebDriverWait(driver, 3).until(
                                    EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.swal2-container"))
                                )
                            except TimeoutException:
                                self.log("--> Success (No popup/Auto-closed)")
                            
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