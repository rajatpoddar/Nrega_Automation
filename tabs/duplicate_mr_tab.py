# tabs/duplicate_mr_tab.py
import tkinter
from tkinter import ttk, messagebox
import customtkinter as ctk
import os
import base64
import json
import time
import threading
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

import config
from .base_tab import BaseAutomationTab
from .autocomplete_widget import AutocompleteEntry

class DuplicateMrTab(BaseAutomationTab):
    """
    A tab for automating the process of re-printing Muster Rolls (MRs) for multiple work codes.
    """
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="duplicate_mr")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self._create_widgets()
        self._load_history()
        self.current_panchayat = "" # To store panchayat name for saving files

    def _create_widgets(self):
        # --- Main container ---
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(1, weight=1)

        # --- Input Frame ---
        input_frame = ctk.CTkFrame(main_container)
        input_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        input_frame.grid_columnconfigure(1, weight=1)

        # Panchayat Entry
        ctk.CTkLabel(input_frame, text="Panchayat Name:").grid(row=0, column=0, padx=15, pady=10, sticky="w")
        self.panchayat_entry = AutocompleteEntry(input_frame, placeholder_text="Start typing Panchayat name...")
        self.panchayat_entry.grid(row=0, column=1, padx=15, pady=10, sticky="ew")

        # Output Action
        ctk.CTkLabel(input_frame, text="Output Action:").grid(row=1, column=0, padx=15, pady=10, sticky="w")
        self.output_action_var = ctk.StringVar(value="Save as PDF Only")
        self.output_action_menu = ctk.CTkOptionMenu(input_frame, variable=self.output_action_var, values=["Save as PDF Only", "Print and Save PDF"])
        self.output_action_menu.grid(row=1, column=1, padx=15, pady=10, sticky="w")

        # --- PDF Options ---
        ctk.CTkLabel(input_frame, text="Orientation:").grid(row=2, column=0, padx=15, pady=10, sticky="w")
        self.orientation_var = ctk.StringVar(value="Landscape")
        self.orientation_segmented_button = ctk.CTkSegmentedButton(input_frame, variable=self.orientation_var, values=["Landscape", "Portrait"])
        self.orientation_segmented_button.grid(row=2, column=1, padx=15, pady=10, sticky="w")

        ctk.CTkLabel(input_frame, text="PDF Scale:").grid(row=3, column=0, padx=15, pady=10, sticky="w")
        scale_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        scale_frame.grid(row=3, column=1, padx=15, pady=10, sticky="ew")
        scale_frame.grid_columnconfigure(0, weight=1)

        self.scale_slider = ctk.CTkSlider(scale_frame, from_=50, to=100, number_of_steps=50, command=self._update_scale_label)
        self.scale_slider.set(75) # Default to 75%
        self.scale_slider.grid(row=0, column=0, sticky="ew")

        self.scale_label = ctk.CTkLabel(scale_frame, text="75%", width=40)
        self.scale_label.grid(row=0, column=1, padx=(10, 0))
        
        # Action Buttons
        action_frame = self._create_action_buttons(input_frame)
        action_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=15, pady=(10, 15))

        # --- Data Notebook (Work Codes, Results, Logs) ---
        notebook = ctk.CTkTabview(main_container)
        notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        work_codes_tab = notebook.add("Work Codes")
        results_tab = notebook.add("Results")
        self._create_log_and_status_area(notebook)
        
        # --- Work Codes Tab ---
        work_codes_tab.grid_columnconfigure(0, weight=1)
        work_codes_tab.grid_rowconfigure(0, weight=1)
        self.work_codes_textbox = ctk.CTkTextbox(work_codes_tab, height=150)
        self.work_codes_textbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # --- Results Tab ---
        results_tab.grid_columnconfigure(0, weight=1)
        results_tab.grid_rowconfigure(1, weight=1)
        results_action_frame = ctk.CTkFrame(results_tab, fg_color="transparent")
        results_action_frame.grid(row=0, column=0, sticky="ew", pady=(5, 10), padx=5)
        self.export_csv_button = ctk.CTkButton(results_action_frame, text="Export to CSV", command=lambda: self.export_treeview_to_csv(self.results_tree, "duplicate_mr_results.csv"))
        self.export_csv_button.pack(side="left")

        cols = ("Timestamp", "Work Code", "MSR No", "Status")
        self.results_tree = ttk.Treeview(results_tab, columns=cols, show='headings')
        for col in cols: self.results_tree.heading(col, text=col)
        self.results_tree.column("Timestamp", width=100, anchor="center")
        self.results_tree.column("MSR No", width=100, anchor="center")
        self.style_treeview(self.results_tree)

        self.results_tree.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        scrollbar = ctk.CTkScrollbar(results_tab, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky='ns')
        
    def _update_scale_label(self, value):
        self.scale_label.configure(text=f"{int(value)}%")

    def _load_history(self):
        panchayat_history = self.app.history_manager.get_suggestions("panchayat_name")
        self.panchayat_entry.suggestions = panchayat_history

    def _log_result(self, work_code, msr_no, status):
        timestamp = time.strftime("%H:%M:%S")
        self.app.after(0, lambda: self.results_tree.insert("", "end", values=(timestamp, work_code, msr_no, status)))

    def start_automation(self):
        panchayat = self.panchayat_entry.get().strip()
        work_codes_raw = self.work_codes_textbox.get("1.0", "end").strip()
        action = self.output_action_var.get()
        orientation = self.orientation_var.get()
        scale = self.scale_slider.get()

        if not panchayat or not work_codes_raw:
            messagebox.showwarning("Input Required", "Panchayat Name and Work Codes are required.")
            return
            
        work_codes = [line.strip() for line in work_codes_raw.splitlines() if line.strip()]
        self.app.history_manager.save_entry("panchayat_name", panchayat)
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic, args=(panchayat, work_codes, action, orientation, scale))

    def run_automation_logic(self, panchayat, work_codes, action, orientation, scale):
        self.app.after(0, self.set_ui_state, True)
        self.app.clear_log(self.log_display)
        for item in self.results_tree.get_children(): self.results_tree.delete(item)

        self.app.log_message(self.log_display, "--- Starting Duplicate MR Printing ---")
        self.current_panchayat = panchayat
        
        driver = self.app.get_driver()
        if not driver:
            self.app.log_message(self.log_display, "Browser not available.", "error")
            self.app.after(0, self.set_ui_state, False)
            return

        try:
            total_codes = len(work_codes)
            for i, work_code in enumerate(work_codes):
                if self.app.stop_events[self.automation_key].is_set():
                    self.app.log_message(self.log_display, "Automation stopped by user.", "warning")
                    break
                
                self.update_status(f"Processing WC {i+1}/{total_codes}: {work_code}", (i + 1) / total_codes)
                self.app.log_message(self.log_display, f"--- Processing Work Code: {work_code} ---")
                self._process_single_work_code(driver, work_code, action, panchayat, orientation, scale)

        except Exception as e:
            error_msg = str(e).splitlines()[0]
            self.app.log_message(self.log_display, f"A critical error occurred: {error_msg}", "error")
        
        finally:
            self.app.after(0, self.set_ui_state, False)
            self.update_status("Automation Finished", 1.0)
            self.app.log_message(self.log_display, "\n--- Automation Finished ---")
            # CRASH FIX: Call the completion dialog safely on the main thread.
            self.app.after(100, self._show_completion_dialog)

    def _show_completion_dialog(self):
        """Safely shows the completion message box on the main UI thread."""
        final_message = "Duplicate MR process has finished."
        output_dir = os.path.join(self.app.get_user_downloads_path(), "Duplicate MR", datetime.now().strftime('%Y-%m-%d'), self.current_panchayat)
        
        if os.path.exists(output_dir) and any(os.scandir(output_dir)):
            if messagebox.askyesno("Complete", f"{final_message}\n\nDo you want to open the output folder?"):
                self.app.open_folder(output_dir)
        else:
            messagebox.showinfo("Complete", final_message)

    def _process_single_work_code(self, driver, work_code, action, panchayat, orientation, scale):
        wait = WebDriverWait(driver, 20)
        url = config.DUPLICATE_MR_CONFIG["url"]
        try:
            msr_options = self._get_msr_list(driver, wait, work_code, panchayat, url)
            if not msr_options: return

            for i, msr_no in enumerate(msr_options):
                if self.app.stop_events[self.automation_key].is_set(): break
                
                self.app.log_message(self.log_display, f"--- Processing MSR {i+1}/{len(msr_options)}: {msr_no} ---")
                
                self.app.log_message(self.log_display, "Navigating to page to select MSR...")
                driver.get(url)
                # TIMING FIX: Add a delay to ensure the page is fully loaded before interacting.
                time.sleep(2)
                
                panchayat_dd_element = wait.until(EC.element_to_be_clickable((By.ID, "ddlPanchayat")))
                Select(panchayat_dd_element).select_by_visible_text(panchayat)
                wait.until(EC.staleness_of(panchayat_dd_element))

                wc_input = wait.until(EC.element_to_be_clickable((By.ID, "txtWork")))
                wc_input.clear()
                wc_input.send_keys(work_code)
                driver.find_element(By.ID, "imgButtonSearch").click()
                time.sleep(2)

                wait.until(lambda d: len(Select(d.find_element(By.ID, "ddlworkcode")).options) > 1)
                Select(driver.find_element(By.ID, "ddlworkcode")).select_by_index(1)
                wait.until(EC.staleness_of(wc_input))
                
                current_msr_dd = Select(wait.until(EC.element_to_be_clickable((By.ID, "ddlmsrno"))))
                current_msr_dd.select_by_value(msr_no)
                
                driver.find_element(By.ID, "btnproceed").click()
                
                # TIMING FIX: Add a delay to allow the print preview page to fully render.
                self.app.log_message(self.log_display, "Waiting 2 seconds for print page to stabilize...")
                time.sleep(2)
                
                wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Print")))
                
                pdf_path = self._save_mr_as_pdf(driver, work_code, msr_no, orientation, scale)
                if pdf_path: self._log_result(work_code, msr_no, "Saved as PDF")
                else: self._log_result(work_code, msr_no, "PDF Save Failed")

                if "Print" in action and pdf_path:
                    self.app.log_message(self.log_display, "Opening system print dialog...")
                    driver.execute_script("window.print();")
                    time.sleep(5)
        
        except TimeoutException:
            self.app.log_message(self.log_display, "Operation timed out. Work code may be invalid or MSRs not available.", "error")
            self._log_result(work_code, "N/A", "Timeout or no MSRs found")
        except Exception as e:
            error_msg = str(e).splitlines()[0]
            self.app.log_message(self.log_display, f"Error processing {work_code}: {error_msg}", "error")
            self._log_result(work_code, "N/A", f"Error: {error_msg}")

    def _get_msr_list(self, driver, wait, work_code, panchayat, url):
        self.app.log_message(self.log_display, f"Getting MSR list for Work Code: {work_code}")
        driver.get(url)
        time.sleep(2)
        
        panchayat_dd_element = wait.until(EC.element_to_be_clickable((By.ID, "ddlPanchayat")))
        Select(panchayat_dd_element).select_by_visible_text(panchayat)
        wait.until(EC.staleness_of(panchayat_dd_element))

        wc_input = wait.until(EC.element_to_be_clickable((By.ID, "txtWork")))
        wc_input.clear(); wc_input.send_keys(work_code)
        driver.find_element(By.ID, "imgButtonSearch").click()
        time.sleep(2)
        
        wait.until(lambda d: len(Select(d.find_element(By.ID, "ddlworkcode")).options) > 1)
        Select(driver.find_element(By.ID, "ddlworkcode")).select_by_index(1)
        wait.until(EC.staleness_of(wc_input))
        
        wait.until(lambda d: len(Select(d.find_element(By.ID, "ddlmsrno")).options) > 1)
        msr_dd_element = driver.find_element(By.ID, "ddlmsrno")
        msr_options = [opt.get_attribute('value') for opt in Select(msr_dd_element).options if '--' not in opt.text]
        
        if not msr_options:
            self.app.log_message(self.log_display, "No MSR numbers found for this work code.", "warning")
            self._log_result(work_code, "N/A", "No MSRs found")
            return []
        
        self.app.log_message(self.log_display, f"Found {len(msr_options)} MSRs: {', '.join(msr_options)}")
        return msr_options

    def _save_mr_as_pdf(self, driver, work_code, msr_no, orientation, scale):
        try:
            today_str = datetime.now().strftime('%Y-%m-%d')
            output_dir = os.path.join(self.app.get_user_downloads_path(), "Duplicate MR", today_str, self.current_panchayat)
            os.makedirs(output_dir, exist_ok=True)
            
            safe_work_code = work_code.replace('/', '_')
            filename = f"MR_{safe_work_code}_{msr_no}.pdf"
            filepath = os.path.join(output_dir, filename)

            # --- LANDSCAPE FIX: Inject CSS to force landscape mode ---
            is_landscape = (orientation == "Landscape")
            if is_landscape:
                self.app.log_message(self.log_display, "Injecting CSS to force landscape orientation...")
                driver.execute_script(
                    "var css = '@page { size: landscape; }';"
                    "var head = document.head || document.getElementsByTagName('head')[0];"
                    "var style = document.createElement('style');"
                    "style.type = 'text/css';"
                    "style.media = 'print';"
                    "if (style.styleSheet){ style.styleSheet.cssText = css; }"
                    "else { style.appendChild(document.createTextNode(css)); }"
                    "head.appendChild(style);"
                )

            pdf_scale = scale / 100.0
            print_options = {
                "landscape": is_landscape,
                "displayHeaderFooter": False,
                "printBackground": False,
                "scale": pdf_scale,
                "marginTop": 0.4, "marginBottom": 0.4,
                "marginLeft": 0.4, "marginRight": 0.4
            }
            
            result = driver.execute_cdp_cmd('Page.printToPDF', print_options)
            pdf_data = base64.b64decode(result['data'])
            
            with open(filepath, 'wb') as f:
                f.write(pdf_data)
            return filepath
        except Exception as e:
            self.app.log_message(self.log_display, f"Error saving PDF: {e}", "error")
            return None

    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running)
        state = "disabled" if running else "normal"
        self.panchayat_entry.configure(state=state)
        self.work_codes_textbox.configure(state=state)
        self.output_action_menu.configure(state=state)
        self.orientation_segmented_button.configure(state=state)
        self.scale_slider.configure(state=state)

    def reset_ui(self):
        if messagebox.askokcancel("Reset Form?", "Are you sure?"):
            self.panchayat_entry.delete(0, "end")
            self.work_codes_textbox.delete("1.0", "end")
            self.app.clear_log(self.log_display)
            self.update_status("Ready", 0)
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            self.orientation_var.set("Landscape")
            self.scale_slider.set(75)
            self.scale_label.configure(text="75%")
