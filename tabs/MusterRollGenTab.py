# tabs/musterroll_gen_tab.py
import tkinter
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import os, csv, time, base64
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from .base_tab import BaseAutomationTab

class MusterRollGenTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, "musterroll_gen")
        self.csv_path = None
        self.save_dir = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._create_widgets()

    def _create_widgets(self):
        main_container = ctk.CTkFrame(self)
        main_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_container.grid_columnconfigure(0, weight=1)

        # --- File/Folder Selection Frame ---
        file_folder_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        file_folder_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        file_folder_frame.grid_columnconfigure(1, weight=1)

        # CSV File Selection
        ctk.CTkLabel(file_folder_frame, text="CSV File:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.csv_path_entry = ctk.CTkEntry(file_folder_frame, placeholder_text="Select a CSV file containing work codes")
        self.csv_path_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.browse_csv_button = ctk.CTkButton(file_folder_frame, text="Browse...", width=100, command=self._browse_csv)
        self.browse_csv_button.grid(row=0, column=2, sticky="e", padx=5, pady=5)

        # Save Directory Selection
        ctk.CTkLabel(file_folder_frame, text="Save To:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.save_dir_entry = ctk.CTkEntry(file_folder_frame, placeholder_text="Select a folder to save PDFs")
        self.save_dir_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        self.browse_dir_button = ctk.CTkButton(file_folder_frame, text="Browse...", width=100, command=self._browse_dir)
        self.browse_dir_button.grid(row=1, column=2, sticky="e", padx=5, pady=5)
        
        # --- Automation Control & Login Frame ---
        self.controls_frame = self._create_controls_frame(main_container, row=1, column=0, columnspan=2)

        # --- Results Display ---
        self.results_frame = self._create_results_frame(self, row=2, column=0)
        self.results_tree.configure(columns=("Work Code", "Status", "Details"))
        self.results_tree.heading("Work Code", text="Work Code")
        self.results_tree.heading("Status", text="Status")
        self.results_tree.heading("Details", text="Details")
        self.results_tree.column("Work Code", width=150)

    def _browse_csv(self):
        path = filedialog.askopenfilename(
            title="Select Muster Roll CSV",
            filetypes=(("CSV Files", "*.csv"), ("All files", "*.*")),
            initialdir=self.app.get_user_downloads_path()
        )
        if path:
            self.csv_path = path
            self.csv_path_entry.delete(0, "end")
            self.csv_path_entry.insert(0, path)
            self.app.log_message(self.log_display, f"Selected CSV: {os.path.basename(path)}", "info")
            self._validate_inputs()

    def _browse_dir(self):
        path = filedialog.askdirectory(
            title="Select Folder to Save PDFs",
            initialdir=self.app.get_user_downloads_path()
        )
        if path:
            self.save_dir = path
            self.save_dir_entry.delete(0, "end")
            self.save_dir_entry.insert(0, path)
            self.app.log_message(self.log_display, f"Save directory set to: {path}", "info")
            self._validate_inputs()

    def _validate_inputs(self):
        if self.csv_path and self.save_dir:
            self.start_button.configure(state="normal")
        else:
            self.start_button.configure(state="disabled")

    def _run_automation_logic(self, driver, username, password, fin_year):
        if not self.csv_path or not self.save_dir:
            messagebox.showerror("Input Missing", "Please select both a CSV file and a save directory.")
            return

        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)
                if 'work_code' not in header:
                    raise ValueError("CSV must contain a 'work_code' column.")
                work_codes = [row[header.index('work_code')] for row in reader if row]
        except Exception as e:
            messagebox.showerror("CSV Error", f"Failed to read work codes from CSV.\nError: {e}")
            return

        total_codes = len(work_codes)
        self.app.log_message(self.log_display, f"Found {total_codes} work codes to process.")
        wait = WebDriverWait(driver, 20)

        for i, work_code in enumerate(work_codes):
            if self.stop_event.is_set():
                self.app.log_message(self.log_display, "Automation stopped by user.", "warning")
                break
            
            work_code = work_code.strip()
            self.update_status(f"Processing {i+1}/{total_codes}: {work_code}", (i + 1) / total_codes)
            self.app.log_message(self.log_display, f"--- Processing Work Code: {work_code} ---")
            
            try:
                driver.get(self.app.cfg['MR_GEN']['url'])
                main_window_handle = driver.current_window_handle

                # Fill the form
                wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddlfin_year")))
                self.app.log_message(self.log_display, "   - Selecting financial year and entering work code.")
                
                # ... (Date selection logic can be added here if needed) ...

                wc_input = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtworkcode")
                wc_input.clear()
                wc_input.send_keys(work_code)
                
                driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btnShow").click()

                # Wait for muster roll table and then click print
                wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_grdMuster")))
                self.app.log_message(self.log_display, "   - Muster roll found. Opening print view...")
                driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btnPrint").click()

                # Switch to the new print window
                wait.until(EC.number_of_windows_to_be(2))
                for handle in driver.window_handles:
                    if handle != main_window_handle:
                        driver.switch_to.window(handle)
                        break
                
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                self.app.log_message(self.log_display, "   - Switched to print view.")

                # --- NEW: Save PDF in Landscape using Chrome DevTools Protocol ---
                pdf_path = os.path.join(self.save_dir, f"MR_{work_code}.pdf")
                self.app.log_message(self.log_display, f"   - Saving PDF in landscape mode to: {os.path.basename(pdf_path)}")

                print_options = {
                    'landscape': True,
                    'printBackground': True,
                    'preferCSSPageSize': True,
                }

                result = driver.execute_cdp_cmd("Page.printToPDF", print_options)
                
                with open(pdf_path, 'wb') as file:
                    file.write(base64.b64decode(result['data']))
                
                self._log_result(work_code, "Success", f"PDF saved to {os.path.basename(pdf_path)}")

            except (TimeoutException, NoSuchElementException) as e:
                error_msg = str(getattr(e, 'msg', "Element not found or page timed out."))
                self._log_result(work_code, "Failed", error_msg.splitlines()[0])
            except Exception as e:
                self._log_result(work_code, "Failed", str(e).splitlines()[0])
            finally:
                # Close the print tab and switch back to the main window
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(main_window_handle)
                
                time.sleep(1) # Small delay before next iteration

        self.app.log_message(self.log_display, "Muster Roll generation finished.", "info")