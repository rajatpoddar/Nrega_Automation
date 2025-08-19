# tabs/jobcard_verify_tab.py
import tkinter
from tkinter import messagebox, filedialog
import customtkinter as ctk
import time, os, sys
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import config
from .base_tab import BaseAutomationTab
from .autocomplete_widget import AutocompleteEntry

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class JobcardVerifyTab(BaseAutomationTab):
    def __init__(self, parent, app_instance):
        super().__init__(parent, app_instance, automation_key="jc_verify")
        self.photo_folder_path = ""
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)
        self._create_widgets()

    def _create_widgets(self):
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(controls_frame, text="Panchayat Name:").grid(row=0, column=0, sticky='w', padx=15, pady=10)
        self.panchayat_entry = AutocompleteEntry(controls_frame, suggestions_list=self.app.history_manager.get_suggestions("panchayat_name"))
        self.panchayat_entry.grid(row=0, column=1, sticky='ew', padx=15, pady=10)
        
        ctk.CTkLabel(controls_frame, text="Village Name:").grid(row=1, column=0, sticky='w', padx=15, pady=10)
        self.village_entry = AutocompleteEntry(controls_frame, suggestions_list=self.app.history_manager.get_suggestions("village_name"))
        self.village_entry.grid(row=1, column=1, sticky='ew', padx=15, pady=10)

        self.process_all_villages_var = tkinter.BooleanVar()
        self.process_all_checkbox = ctk.CTkCheckBox(
            controls_frame,
            text="Process all villages in this Panchayat",
            variable=self.process_all_villages_var,
            command=self._toggle_village_entry
        )
        self.process_all_checkbox.grid(row=2, column=1, sticky='w', padx=15, pady=(0, 10))

        photo_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        photo_frame.grid(row=3, column=0, columnspan=2, sticky='ew', padx=15, pady=10)
        photo_frame.grid_columnconfigure(1, weight=1)
        
        self.select_folder_button = ctk.CTkButton(photo_frame, text="Select Photo Folder...", command=self.select_photo_folder)
        self.select_folder_button.grid(row=0, column=0, sticky='w')
        self.photo_path_label = ctk.CTkLabel(photo_frame, text=f"No folder selected (will use default '{config.JOBCARD_VERIFY_CONFIG['default_photo']}')", text_color="gray", anchor='w')
        self.photo_path_label.grid(row=0, column=1, sticky='ew', padx=10)
        
        instruction_text = "Note: Name photos with the last part of the Jobcard No. (e.g., 417.jpg for ...01/417)"
        ctk.CTkLabel(photo_frame, text=instruction_text, text_color="gray50").grid(row=1, column=0, columnspan=2, sticky='w', pady=2)

        action_frame = self._create_action_buttons(parent_frame=controls_frame)
        action_frame.grid(row=4, column=0, columnspan=2, sticky='ew', pady=15)

        notebook = ctk.CTkTabview(self)
        notebook.grid(row=1, column=0, sticky="nsew")
        self._create_log_and_status_area(parent_notebook=notebook)
        self.progress_bar.grid_forget()

    def _toggle_village_entry(self):
        if self.process_all_villages_var.get():
            self.village_entry.configure(state="disabled")
        else:
            self.village_entry.configure(state="normal")

    def set_ui_state(self, running: bool):
        self.set_common_ui_state(running)
        state = "disabled" if running else "normal"
        self.panchayat_entry.configure(state=state)
        self.select_folder_button.configure(state=state)
        self.process_all_checkbox.configure(state=state)
        if running or self.process_all_villages_var.get():
            self.village_entry.configure(state="disabled")
        else:
            self.village_entry.configure(state="normal")

    def select_photo_folder(self):
        path = filedialog.askdirectory(title="Select Folder Containing Photos")
        if path:
            self.photo_folder_path = path
            self.photo_path_label.configure(text=self.photo_folder_path)
            self.app.log_message(self.log_display, f"Selected photo folder: {self.photo_folder_path}")

    def reset_ui(self):
        if messagebox.askokcancel("Reset Form?", "Are you sure?"):
            self.panchayat_entry.delete(0, tkinter.END)
            self.village_entry.delete(0, tkinter.END)
            self.process_all_villages_var.set(False)
            self._toggle_village_entry()
            self.photo_folder_path = ""
            self.photo_path_label.configure(text=f"No folder selected (will use default '{config.JOBCARD_VERIFY_CONFIG['default_photo']}')")
            self.app.clear_log(self.log_display)
            self.update_status("Ready")
            self.app.after(0, self.app.set_status, "Ready")

    def start_automation(self):
        panchayat = self.panchayat_entry.get().strip()
        village = self.village_entry.get().strip()
        process_all = self.process_all_villages_var.get()

        if not panchayat:
            messagebox.showwarning("Input Required", "Panchayat name is required.")
            return
        if not process_all and not village:
            messagebox.showwarning("Input Required", "Please enter a Village name or check 'Process all villages'.")
            return
            
        inputs = {'panchayat': panchayat, 'village': village, 'process_all': process_all}
        self.app.start_automation_thread(self.automation_key, self.run_automation_logic, args=(inputs,))

    def _get_photo_for_jobcard(self, jobcard_no):
        try:
            jobcard_key = jobcard_no.split('/')[-1]
            if self.photo_folder_path:
                for ext in ['.jpg', '.jpeg', '.png']:
                    photo_path = os.path.join(self.photo_folder_path, jobcard_key + ext)
                    if os.path.exists(photo_path):
                        self.app.log_message(self.log_display, f"Found photo: {os.path.basename(photo_path)}"); return photo_path
            
            default_photo_path = resource_path(config.JOBCARD_VERIFY_CONFIG["default_photo"])
            if os.path.exists(default_photo_path):
                self.app.log_message(self.log_display, f"Using default photo '{config.JOBCARD_VERIFY_CONFIG['default_photo']}'.", "warning"); return default_photo_path
            
            self.app.log_message(self.log_display, f"No photo found for {jobcard_key}.", "error"); return None
        except Exception as e:
            self.app.log_message(self.log_display, f"Error finding photo for {jobcard_no}: {e}", "error"); return None

    def run_automation_logic(self, inputs):
        self.app.after(0, self.set_ui_state, True)
        self.app.clear_log(self.log_display)
        self.app.log_message(self.log_display, "🚀 Starting Jobcard Verification...")
        self.app.after(0, self.app.set_status, "Running Jobcard Verification...")
        
        try:
            driver = self.app.get_driver()
            if not driver: return
            wait = WebDriverWait(driver, 20)
            url = config.JOBCARD_VERIFY_CONFIG["url"]
            driver.get(url)
            
            villages_to_process = []
            self.app.log_message(self.log_display, f"Selecting Panchayat: {inputs['panchayat']}")
            html_element = driver.find_element(By.TAG_NAME, "html")
            Select(wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_UC_panch_vill_reg1_ddlpnch")))).select_by_visible_text(inputs['panchayat'])
            wait.until(EC.staleness_of(html_element))

            if inputs['process_all']:
                self.app.log_message(self.log_display, "Finding all villages in Panchayat...")
                village_dropdown = Select(wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_UC_panch_vill_reg1_ddlVillage"))))
                villages_to_process = [opt.text for opt in village_dropdown.options if "--Select" not in opt.text]
                self.app.log_message(self.log_display, f"Found {len(villages_to_process)} villages.")
            else:
                villages_to_process.append(inputs['village'])

            self.app.update_history("panchayat_name", inputs['panchayat'])

            for village_name in villages_to_process:
                if self.app.stop_events[self.automation_key].is_set():
                    self.app.log_message(self.log_display, "🛑 Stop signal received.", "warning"); break
                
                self.app.log_message(self.log_display, f"\n--- Processing Village: {village_name} ---")
                self.app.after(0, self.update_status, f"Processing Village: {village_name}")
                self.app.update_history("village_name", village_name)
                
                html_element = driver.find_element(By.TAG_NAME, "html")
                Select(wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_UC_panch_vill_reg1_ddlVillage")))).select_by_visible_text(village_name)
                wait.until(EC.staleness_of(html_element))
                
                try:
                    msg_element = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_lblmsg")
                    if "no record found" in msg_element.text.lower():
                        self.app.log_message(self.log_display, f"   - Village has no records. Skipping.", "info")
                        continue
                except NoSuchElementException:
                    pass

                self._process_jobcards_for_current_page(driver, wait)

            if not self.app.stop_events[self.automation_key].is_set():
                messagebox.showinfo("Success", "Jobcard verification complete for all selected villages.")
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e).splitlines()[0]}"; self.app.log_message(self.log_display, f"Error: {error_msg}", "error"); messagebox.showerror("Automation Error", f"An error occurred: {error_msg}")
        finally:
            self.app.after(0, self.update_status, "Finished"); self.app.after(0, self.set_ui_state, False)
            self.app.after(0, self.app.set_status, "Automation Finished")
    
    def _process_jobcards_for_current_page(self, driver, wait):
        jobcard_count = 1
        while not self.app.stop_events[self.automation_key].is_set():
            try:
                jobcard_no = wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_grdData_ctl02_hidd_reg"))).get_attribute("value")
                self.app.log_message(self.log_display, f"   - Verifying Jobcard #{jobcard_count}: {jobcard_no}")
            except TimeoutException:
                self.app.log_message(self.log_display, "   - No more jobcards found in this village.", "success"); break
            
            photo_to_upload = self._get_photo_for_jobcard(jobcard_no)
            
            try:
                upload_link = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_grdData_ctl02_link_img_F")
                if photo_to_upload:
                    main_window_handle = driver.current_window_handle
                    upload_link.click()
                    
                    # --- NEW, MORE ROBUST POP-UP HANDLING ---
                    try:
                        wait.until(EC.number_of_windows_to_be(2))
                        popup_handle = [h for h in driver.window_handles if h != main_window_handle][0]
                        
                        time.sleep(1) # Crucial pause before switching
                        driver.switch_to.window(popup_handle)
                        
                        # Wait for the pop-up to finish loading its URL
                        WebDriverWait(driver, 10).until(lambda d: "UploadPhoto_Verified" in d.current_url)
                        self.app.log_message(self.log_display, "     - Pop-up loaded successfully.")
                        
                        # Now find elements using the reliable CSS selectors
                        file_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]')))
                        file_input.send_keys(photo_to_upload)
                        
                        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="submit"]'))).click()
                        
                        wait.until(EC.alert_is_present()).accept()
                        self.app.log_message(self.log_display, "     - Photo uploaded successfully.", "success")

                    finally:
                        # Ensure we always close the pop-up and switch back
                        if len(driver.window_handles) > 1:
                            driver.close()
                        driver.switch_to.window(main_window_handle)

                else: 
                    self.app.log_message(self.log_display, "     - Skipping photo upload, no image found.", "warning")
            except NoSuchElementException: 
                self.app.log_message(self.log_display, "     - Photo already uploaded, skipping.")
            
            wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_grdData_ctl02_rblDmd_0"))).click()
            html_element = driver.find_element(By.TAG_NAME, "html")
            wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_grdData_ctl02_rblJCVer_0"))).click()
            wait.until(EC.staleness_of(html_element))
            wait.until(EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_grdData_ctl02_txt_DtrblJCVer"))).send_keys(datetime.now().strftime("%d/%m/%Y"))
            wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_grdData_ctl02_BtnUpdate"))).click()
            final_alert = wait.until(EC.alert_is_present())
            self.app.log_message(self.log_display, f"     - Saved successfully: {final_alert.text}", "success"); final_alert.accept()
            jobcard_count += 1
            time.sleep(2)
            wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_UC_panch_vill_reg1_ddlpnch")))