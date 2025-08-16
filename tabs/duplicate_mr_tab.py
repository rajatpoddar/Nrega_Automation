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
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException

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
        self.current_panchayat = ""

    def _create_widgets(self):
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(1, weight=1)

        input_frame = ctk.CTkFrame(main_container)
        input_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        input_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(input_frame, text="Panchayat Name:").grid(row=0, column=0, padx=15, pady=10, sticky="w")
        self.panchayat_entry = AutocompleteEntry(input_frame, placeholder_text="Start typing Panchayat name...")
        self.panchayat_entry.grid(row=0, column=1, padx=15, pady=10, sticky="ew")

        ctk.CTkLabel(input_frame, text="Output Action:").grid(row=1, column=0, padx=15, pady=10, sticky="w")
        self.output_action_var = ctk.StringVar(value="Save as PDF Only")
        self.output_action_menu = ctk.CTkOptionMenu(input_frame, variable=self.output_action_var, values=["Save as PDF Only", "Print and Save PDF"])
        self.output_action_menu.grid(row=1, column=1, padx=15, pady=10, sticky="w")

        ctk.CTkLabel(input_frame, text="Orientation:").grid(row=2, column=0, padx=15, pady=10, sticky="w")
        self.orientation_var = ctk.StringVar(value="Landscape")
        self.orientation_segmented_button = ctk.CTkSegmentedButton(input_frame, variable=self.orientation_var, values=["Landscape", "Portrait"])
        self.orientation_segmented_button.grid(row=2, column=1, padx=15, pady=10, sticky="w")

        ctk.CTkLabel(input_frame, text="PDF Scale:").grid(row=3, column=0, padx=15, pady=10, sticky="w")
        scale_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        scale_frame.grid(row=3, column=1, padx=15, pady=10, sticky="ew")
        scale_frame.grid_columnconfigure(0, weight=1)

        self.scale_slider = ctk.CTkSlider(scale_frame, from_=50, to=100, number_of_steps=50, command=self._update_scale_label)
        self.scale_slider.set(75)
        self.scale_slider.grid(row=0, column=0, sticky="ew")

        self.scale_label = ctk.CTkLabel(scale_frame, text="75%", width=40)
        self.scale_label.grid(row=0, column=1, padx=(10, 0))
        
        action_frame = self._create_action_buttons(input_frame)
        action_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=15, pady=(10, 15))

        notebook = ctk.CTkTabview(main_container)
        notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        work_codes_tab = notebook.add("Work Codes")
        results_tab = notebook.add("Results")
        self._create_log_and_status_area(notebook)
        
        work_codes_tab.grid_columnconfigure(0, weight=1)
        work_codes_tab.grid_rowconfigure(1, weight=1) # Allow textbox to expand
        
        # --- ADDED: Frame with a Clear button for the textbox ---
        wc_controls = ctk.CTkFrame(work_codes_tab, fg_color="transparent")
        wc_controls.grid(row=0, column=0, sticky='ew', padx=5, pady=(5,0))
        clear_button = ctk.CTkButton(wc_controls, text="Clear", width=80, command=lambda: self.work_codes_textbox.delete("1.0", tkinter.END))
        clear_button.pack(side='right')
        # --- END ADDED ---

        self.work_codes_textbox = ctk.CTkTextbox(work_codes_tab, height=150)
        self.work_codes_textbox.grid(row=1, column=0, sticky="nsew", padx=5, pady=5) # Changed row from 0 to 1

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
        self.results_tree.column("Work Code", width=250)
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
            messagebox.showerror(
                "Browser Not Found",
                "No active browser session was found.\n\nPlease use the 'Launch Chrome' or 'Launch Firefox' buttons at the top-right to start a browser before running the automation."
            )
            self.app.after(0, self.set_ui_state, False)
            return

        try:
            for work_code in work_codes:
                if self.app.stop_events[self.automation_key].is_set():
                    break
                self.app.log_message(self.log_display, f"\n--- Processing Work Code: {work_code} ---")
                self._process_single_work_code(driver, work_code, action, panchayat, orientation, scale)
        except Exception as e:
            self.app.log_message(self.log_display, f"A critical error occurred: {str(e).splitlines()[0]}", "error")
        finally:
            self.app.after(0, self.set_ui_state, False)
            self.app.log_message(self.log_display, "\n--- Automation Finished ---")
            self.app.after(100, self._show_completion_dialog)

    def _show_completion_dialog(self):
        final_message = "Duplicate MR process has finished."
        output_dir = os.path.join(self.app.get_user_downloads_path(), "NREGABot_Duplicate_MR_Output", datetime.now().strftime('%Y-%m-%d'), self.current_panchayat)
        
        if os.path.exists(output_dir) and any(os.scandir(output_dir)):
            if messagebox.askyesno("Complete", f"{final_message}\n\nDo you want to open the output folder?"):
                self.app.open_folder(output_dir)
        else:
            messagebox.showinfo("Complete", final_message)

    def _process_single_work_code(self, driver, work_code, action, panchayat, orientation, scale):
        wait = WebDriverWait(driver, 40)
        url = config.DUPLICATE_MR_CONFIG["url"]
        try:
            msr_options = self._get_msr_list(driver, wait, work_code, panchayat, url)
            if not msr_options: return

            for i, msr_no in enumerate(msr_options):
                if self.app.stop_events[self.automation_key].is_set(): break
                
                self.app.log_message(self.log_display, f"--- Processing MSR {i+1}/{len(msr_options)}: {msr_no} ---")
                
                driver.get(url)
                
                panchayat_dd_element = wait.until(EC.element_to_be_clickable((By.ID, "ddlPanchayat")))
                Select(panchayat_dd_element).select_by_visible_text(panchayat)
                
                wc_input = wait.until(EC.element_to_be_clickable((By.ID, "txtWork")))
                
                wc_input.clear()
                wc_input.send_keys(work_code)
                driver.find_element(By.ID, "imgButtonSearch").click()
                time.sleep(2)

                wait.until(lambda d: len(Select(d.find_element(By.ID, "ddlworkcode")).options) > 1)
                Select(driver.find_element(By.ID, "ddlworkcode")).select_by_index(1)
                
                wait.until(lambda d: len(Select(d.find_element(By.ID, "ddlmsrno")).options) > 1)

                current_msr_dd = Select(driver.find_element(By.ID, "ddlmsrno"))
                current_msr_dd.select_by_value(msr_no)
                
                driver.find_element(By.ID, "btnproceed").click()
                
                self.app.log_message(self.log_display, "   - Loading print page content...")
                
                try:
                    iframe_wait = WebDriverWait(driver, 5)
                    iframe_wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, 'iframe')))
                    self.app.log_message(self.log_display, "   - Switched to content iframe.")
                except TimeoutException:
                    self.app.log_message(self.log_display, "   - No iframe detected, proceeding in main document.")

                self.app.log_message(self.log_display, "   - Waiting for 'Print' link to become available...")
                wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Print")))
                self.app.log_message(self.log_display, "   - Print page is ready.")
                
                pdf_path = self._save_mr_as_pdf(driver, work_code, msr_no, orientation, scale)
                
                if pdf_path: self._log_result(work_code, msr_no, "Saved as PDF")
                else: self._log_result(work_code, msr_no, "PDF Save Failed")

                if "Print and Save" in action and pdf_path:
                    driver.execute_script("window.print();")
                    time.sleep(5)
                
                driver.switch_to.default_content()
        
        except TimeoutException:
            self._log_result(work_code, "N/A", "Timeout")
        except NoSuchElementException:
            self._log_result(work_code, "N/A", "Element not found")
        except Exception as e:
            self._log_result(work_code, "N/A", "Unexpected Error")

    def _get_msr_list(self, driver, wait, work_code, panchayat, url):
        self.app.log_message(self.log_display, f"Getting MSR list for Work Code: {work_code}")
        driver.get(url)
        
        panchayat_dd_element = wait.until(EC.element_to_be_clickable((By.ID, "ddlPanchayat")))
        Select(panchayat_dd_element).select_by_visible_text(panchayat)
        
        wc_input = wait.until(EC.element_to_be_clickable((By.ID, "txtWork")))
        wc_input.clear(); wc_input.send_keys(work_code)
        driver.find_element(By.ID, "imgButtonSearch").click()
        time.sleep(2)
        
        wait.until(lambda d: len(Select(d.find_element(By.ID, "ddlworkcode")).options) > 1)
        Select(driver.find_element(By.ID, "ddlworkcode")).select_by_index(1)
        
        wait.until(lambda d: len(Select(d.find_element(By.ID, "ddlmsrno")).options) > 1)
        msr_dd_element = driver.find_element(By.ID, "ddlmsrno")
        msr_options = [opt.get_attribute('value') for opt in Select(msr_dd_element).options if '--' not in opt.text]
        
        if not msr_options:
            self.app.log_message(self.log_display, "No MSR numbers found.", "warning")
            self._log_result(work_code, "N/A", "No MSRs found")
            return []
        
        self.app.log_message(self.log_display, f"Found {len(msr_options)} MSRs: {', '.join(msr_options)}")
        return msr_options

    # --- RE-INSERTED MISSING FUNCTION ---
    def _save_mr_as_pdf(self, driver, work_code, msr_no, orientation, scale):
        try:
            today_str = datetime.now().strftime('%Y-%m-%d')
            output_dir = os.path.join(self.app.get_user_downloads_path(), "NREGABot_Duplicate_MR_Output", today_str, self.current_panchayat)
            os.makedirs(output_dir, exist_ok=True)
            
            safe_work_code = work_code.split('/')[-1][-6:]
            filename = f"MR_{safe_work_code}_{msr_no}.pdf"
            filepath = os.path.join(output_dir, filename)

            is_landscape = (orientation == "Landscape")
            pdf_scale = scale / 100.0
            pdf_data_base64 = None

            if is_landscape:
                driver.execute_script(
                    "var css = '@page { size: landscape; }';"
                    "var head = document.head || document.getElementsByTagName('head')[0];"
                    "var style = document.createElement('style');"
                    "style.type = 'text/css'; style.media = 'print';"
                    "if (style.styleSheet){ style.styleSheet.cssText = css; }"
                    "else { style.appendChild(document.createTextNode(css)); }"
                    "head.appendChild(style);"
                )
            
            if self.app.active_browser == 'firefox':
                self.app.log_message(self.log_display, "   - Note: PDF Scale setting is not supported for Firefox and will be ignored.", "warning")
                pdf_data_base64 = driver.print_page()
            
            elif self.app.active_browser == 'chrome':
                print_options = {
                    "landscape": is_landscape,
                    "displayHeaderFooter": False,
                    "printBackground": False,
                    "scale": pdf_scale,
                    "marginTop": 0.4, "marginBottom": 0.4,
                    "marginLeft": 0.4, "marginRight": 0.4
                }
                result = driver.execute_cdp_cmd('Page.printToPDF', print_options)
                pdf_data_base64 = result['data']

            if pdf_data_base64:
                pdf_data = base64.b64decode(pdf_data_base64)
                with open(filepath, 'wb') as f:
                    f.write(pdf_data)
                return filepath
            else:
                return None
        except Exception as e:
            self.app.log_message(self.log_display, f"Error saving PDF: {e}", "error")
            return None
    # --- END RE-INSERTED FUNCTION ---

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