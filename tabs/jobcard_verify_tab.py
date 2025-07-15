# tabs/jobcard_verify_tab.py
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import time, os, sys
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException

import config

widgets = {}
photo_folder_path = "" # Will now store the path to the folder

# Helper function to find resources, making it work in the bundled app
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def create_tab(parent_frame, app_instance):
    """Creates the Jobcard Verification & Photo Upload tab UI."""
    parent_frame.columnconfigure(0, weight=1)
    parent_frame.rowconfigure(1, weight=1)

    # --- Controls Frame ---
    controls_frame = ttk.LabelFrame(parent_frame, text="Jobcard Verification Controls")
    controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    controls_frame.columnconfigure(1, weight=1)
    
    ttk.Label(controls_frame, text="Panchayat Name:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
    widgets['panchayat_entry'] = ttk.Entry(controls_frame)
    widgets['panchayat_entry'].grid(row=0, column=1, sticky='ew', padx=5, pady=5)
    
    ttk.Label(controls_frame, text="Village Name:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
    widgets['village_entry'] = ttk.Entry(controls_frame)
    widgets['village_entry'].grid(row=1, column=1, sticky='ew', padx=5, pady=5)

    # Photo selection
    photo_frame = ttk.Frame(controls_frame)
    photo_frame.grid(row=2, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
    photo_frame.columnconfigure(1, weight=1)
    
    def select_photo_folder():
        global photo_folder_path
        path = filedialog.askdirectory(title="Select Folder Containing Photos")
        if path:
            photo_folder_path = path
            widgets['photo_path_label'].config(text=photo_folder_path)
            app_instance.log_message(widgets['log_display'], f"Selected photo folder: {photo_folder_path}")

    ttk.Button(photo_frame, text="Select Photo Folder...", command=select_photo_folder).grid(row=0, column=0, sticky='w')
    widgets['photo_path_label'] = ttk.Label(photo_frame, text="No folder selected (will use default 'jobcard.jpeg')", style="Secondary.TLabel", anchor='w')
    widgets['photo_path_label'].grid(row=0, column=1, sticky='ew', padx=10)
    
    instruction_text = "Note: Name photos with the last part of the Jobcard No. (e.g., 417.jpg for ...01/417)"
    ttk.Label(photo_frame, text=instruction_text, style="Instruction.TLabel").grid(row=1, column=0, columnspan=2, sticky='w', padx=5, pady=2)


    # Action buttons
    action_frame = ttk.Frame(controls_frame)
    action_frame.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(15, 5))
    action_frame.columnconfigure((0, 1, 2), weight=1)

    def on_start_click(): start_automation(app_instance)
    def on_stop_click(): app_instance.stop_events["jc_verify"].set()
    def on_reset_click(): reset_ui(app_instance)

    widgets['start_button'] = ttk.Button(action_frame, text="▶ Start Verification", style="Accent.TButton", command=on_start_click)
    widgets['start_button'].grid(row=0, column=0, sticky="ew", padx=(0,5), ipady=5)
    widgets['stop_button'] = ttk.Button(action_frame, text="Stop", command=on_stop_click, state="disabled")
    widgets['stop_button'].grid(row=0, column=1, sticky="ew", padx=(5,5), ipady=5)
    widgets['reset_button'] = ttk.Button(action_frame, text="Reset", style="Outline.TButton", command=on_reset_click)
    widgets['reset_button'].grid(row=0, column=2, sticky='ew', padx=(5,0), ipady=5)

    notebook = ttk.Notebook(parent_frame, style="Modern.TNotebook")
    notebook.grid(row=1, column=0, sticky="nsew")
    logs_frame = ttk.Frame(notebook, padding=15)
    notebook.add(logs_frame, text="Logs & Status")

    logs_frame.columnconfigure(0, weight=1); logs_frame.rowconfigure(2, weight=1)
    def on_copy_log_click():
        log_content = widgets['log_display'].get("1.0", tk.END)
        parent_frame.clipboard_clear()
        parent_frame.clipboard_append(log_content)
        messagebox.showinfo("Copied", "Log content has been copied to the clipboard.")
    widgets['copy_log_button'] = ttk.Button(logs_frame, text="Copy Log", command=on_copy_log_click)
    widgets['copy_log_button'].grid(row=0, column=0, sticky='w')
    widgets['status_label'] = ttk.Label(logs_frame, text="Status: Ready", style="Status.TLabel")
    widgets['status_label'].grid(row=1, column=0, sticky='ew', pady=(5,0))
    widgets['log_display'] = scrolledtext.ScrolledText(logs_frame, wrap=tk.WORD, state="disabled")
    widgets['log_display'].grid(row=2, column=0, sticky='nsew', pady=(10, 0))

def reset_ui(app):
    global photo_folder_path
    if messagebox.askokcancel("Reset Form?", "Are you sure you want to clear all inputs and logs?"):
        widgets['panchayat_entry'].delete(0, tk.END)
        widgets['village_entry'].delete(0, tk.END)
        photo_folder_path = ""
        widgets['photo_path_label'].config(text="No folder selected (will use default blank photo 'jobcard.jpeg')")
        app.clear_log(widgets['log_display'])
        widgets['status_label'].config(text="Status: Ready")

def set_ui_state(running):
    state = "disabled" if running else "normal"
    widgets['start_button'].config(state=state)
    widgets['stop_button'].config(state="normal" if running else "disabled")
    widgets['reset_button'].config(state=state)
    for w in ['panchayat_entry', 'village_entry']:
        widgets[w].config(state=state)

def start_automation(app):
    global photo_folder_path
    if not widgets['panchayat_entry'].get() or not widgets['village_entry'].get():
        messagebox.showwarning("Input Required", "Panchayat and Village names are required.")
        return
    # FIXED: The 'app' instance is automatically passed by the thread starter,
    # so it should not be included in the 'args' tuple.
    app.start_automation_thread("jc_verify", run_automation_logic, args=(widgets['panchayat_entry'].get(), widgets['village_entry'].get(), photo_folder_path))

def _get_photo_for_jobcard(app, jobcard_no, folder_path):
    """Finds the correct photo for a jobcard, with a default fallback."""
    try:
        jobcard_key = jobcard_no.split('/')[-1]

        if folder_path:
            for ext in ['.jpg', '.jpeg', '.png']:
                photo_path = os.path.join(folder_path, jobcard_key + ext)
                if os.path.exists(photo_path):
                    app.log_message(widgets['log_display'], f"Found matching photo: {os.path.basename(photo_path)}")
                    return photo_path

        default_photo_path = resource_path("jobcard.jpeg")
        if os.path.exists(default_photo_path):
            app.log_message(widgets['log_display'], "Using default photo 'jobcard.jpeg'.", "warning")
            return default_photo_path
            
        app.log_message(widgets['log_display'], f"No specific or default photo found for {jobcard_key}.", "error")
        return None

    except Exception as e:
        app.log_message(widgets['log_display'], f"Error finding photo for {jobcard_no}: {e}", "error")
        return None

def run_automation_logic(app, panchayat_name, village_name, photo_folder):
    app.after(0, set_ui_state, True)
    app.clear_log(widgets['log_display'])
    app.log_message(widgets['log_display'], "Starting Jobcard Verification process...")

    try:
        driver = app.connect_to_chrome()
        wait = WebDriverWait(driver, 20)
        url = "https://nregade4.nic.in/Netnrega/VerificationJCatPO.aspx"
        
        jobcard_count = 1
        while not app.stop_events["jc_verify"].is_set():
            app.after(0, lambda: widgets['status_label'].config(text=f"Status: Processing Jobcard #{jobcard_count}..."))
            
            driver.get(url)
            main_window_handle = driver.current_window_handle

            html_element = driver.find_element(By.TAG_NAME, "html")
            Select(wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_UC_panch_vill_reg1_ddlpnch")))).select_by_visible_text(panchayat_name)
            wait.until(EC.staleness_of(html_element))

            html_element = driver.find_element(By.TAG_NAME, "html")
            Select(wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_UC_panch_vill_reg1_ddlVillage")))).select_by_visible_text(village_name)
            wait.until(EC.staleness_of(html_element))
            app.log_message(widgets['log_display'], f"Selected Panchayat: {panchayat_name}, Village: {village_name}")

            try:
                jobcard_no = wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_grdData_ctl02_hidd_reg"))).get_attribute("value")
                app.log_message(widgets['log_display'], f"--- Found Jobcard #{jobcard_count}: {jobcard_no} ---")
            except TimeoutException:
                app.log_message(widgets['log_display'], "No more jobcards found in the list. Process complete.", "success")
                break
            
            photo_to_upload = _get_photo_for_jobcard(app, jobcard_no, photo_folder)

            try:
                upload_link = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_grdData_ctl02_link_img_F")
                if photo_to_upload:
                    upload_link.click()
                    
                    wait.until(EC.number_of_windows_to_be(2))
                    popup_handle = [handle for handle in driver.window_handles if handle != main_window_handle][0]
                    driver.switch_to.window(popup_handle)
                    
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))).send_keys(photo_to_upload)
                    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="submit"]'))).click()
                    
                    upload_alert = wait.until(EC.alert_is_present())
                    upload_alert.accept()
                    
                    driver.close()
                    driver.switch_to.window(main_window_handle)
                    app.log_message(widgets['log_display'], "Photo uploaded successfully.", "success")
                else:
                    app.log_message(widgets['log_display'], "Skipping photo upload as no image was found.", "warning")

            except NoSuchElementException:
                app.log_message(widgets['log_display'], "Photo already uploaded for this jobcard, skipping photo step.")

            wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_grdData_ctl02_rblDmd_0"))).click()
            
            html_element = driver.find_element(By.TAG_NAME, "html")
            wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_grdData_ctl02_rblJCVer_0"))).click()
            wait.until(EC.staleness_of(html_element))
            
            current_date = datetime.now().strftime("%d/%m/%Y")
            wait.until(EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_grdData_ctl02_txt_DtrblJCVer"))).send_keys(current_date)
            
            wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_grdData_ctl02_BtnUpdate"))).click()
            
            final_alert = wait.until(EC.alert_is_present())
            alert_text = final_alert.text
            app.log_message(widgets['log_display'], f"Saved successfully for {jobcard_no}: {alert_text}", "success")
            final_alert.accept()
            jobcard_count += 1
            time.sleep(2)

        if not app.stop_events["jc_verify"].is_set():
            app.after(0, lambda: messagebox.showinfo("Success", "Jobcard verification process completed for all items."))

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e).splitlines()[0]}"
        app.log_message(widgets['log_display'], f"Error during automation: {error_msg}", "error")
        messagebox.showerror("Automation Error", f"An error occurred: {error_msg}")
    finally:
        app.after(0, lambda: widgets['status_label'].config(text="Status: Finished"))
        app.after(0, set_ui_state, False)