# tabs/wc_gen_tab.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import os, csv, time, pyperclip
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import config

widgets = {}

def create_tab(parent_frame, app_instance):
    parent_frame.columnconfigure(0, weight=1)
    parent_frame.rowconfigure(1, weight=1)
    controls = ttk.LabelFrame(parent_frame, text="Workcode Generation Controls")
    controls.grid(row=0, column=0, sticky='ew', pady=(0, 10))
    controls.columnconfigure(1, weight=1)
    
    ttk.Label(controls, text="Panchayat Name:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
    widgets['panchayat_entry'] = ttk.Entry(controls, width=30)
    widgets['panchayat_entry'].grid(row=0, column=1, sticky=tk.EW, pady=5, padx=5)
    
    ttk.Label(controls, text="CSV Data File:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
    file_frame = ttk.Frame(controls)
    file_frame.grid(row=1, column=1, sticky='ew', pady=5, padx=5)
    
    def on_select_csv_click():
        select_csv_file(app_instance)
    
    widgets['select_button'] = ttk.Button(file_frame, text="Select workcode_data.csv", command=on_select_csv_click)
    widgets['select_button'].pack(side=tk.LEFT, padx=(0, 10))
    widgets['file_label'] = ttk.Label(file_frame, text="No file selected")
    widgets['file_label'].pack(side=tk.LEFT)
    
    action_frame = ttk.Frame(controls)
    action_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(15,5))
    # Updated: Column configuration for two buttons
    action_frame.columnconfigure((0, 1), weight=1)

    def on_start_click():
        start_automation(app_instance)
    # New: Reset function call
    def on_reset_click():
        reset_ui(app_instance)

    widgets['start_button'] = ttk.Button(action_frame, text="▶ Start Automation", style="Accent.TButton", command=on_start_click)
    widgets['start_button'].grid(row=0, column=0, sticky='ew', padx=(0, 5), ipady=5)
    # New: Reset button added
    widgets['reset_button'] = ttk.Button(action_frame, text="Reset", style="Outline.TButton", command=on_reset_click)
    widgets['reset_button'].grid(row=0, column=1, sticky='ew', padx=(5, 0), ipady=5)

    log_frame = ttk.LabelFrame(parent_frame, text="Log")
    log_frame.grid(row=1, column=0, sticky='nsew')
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    widgets['log_area'] = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state=tk.DISABLED, height=10)
    widgets['log_area'].grid(row=0, column=0, sticky='nsew')

# New: Function to reset the UI for this tab
def reset_ui(app):
    if messagebox.askokcancel("Reset Form?", "Are you sure you want to clear all inputs and logs for this tab?"):
        widgets['panchayat_entry'].delete(0, tk.END)
        widgets['file_label'].config(text="No file selected")
        if "wc_gen" in app.csv_paths:
            app.csv_paths["wc_gen"] = None
        app.clear_log(widgets['log_area'])
        app.log_message(widgets['log_area'], "Form has been reset.")

def set_ui_state(running):
    state = "disabled" if running else "normal"
    widgets['start_button'].config(state=state)
    widgets['select_button'].config(state=state)
    widgets['panchayat_entry'].config(state=state)
    widgets['reset_button'].config(state=state)

def select_csv_file(app):
    path = filedialog.askopenfilename(title="Select your CSV data file", filetypes=[("CSV files", "*.csv")])
    if path:
        app.csv_paths["wc_gen"] = path
        filename = os.path.basename(path)
        widgets['file_label'].config(text=filename)
        app.log_message(widgets['log_area'], f"Selected file: {path}")

def start_automation(app):
    if "wc_gen" not in app.csv_paths or not app.csv_paths["wc_gen"]:
        messagebox.showwarning("Missing File", "Please select a CSV file first."); return
    if not widgets['panchayat_entry'].get():
        messagebox.showwarning("Missing Info", "Please enter the Panchayat name."); return
    app.start_automation_thread("wc_gen", run_automation_logic)

def run_automation_logic(app):
    app.after(0, set_ui_state, True)
    app.clear_log(widgets['log_area'])
    app.log_message(widgets['log_area'], "--- Starting Workcode Generation ---")
    try:
        driver = app.connect_to_chrome()
        panchayat_name = widgets['panchayat_entry'].get()
        with open(app.csv_paths["wc_gen"], mode='r', encoding='utf-8') as csvfile:
            csv_reader = csv.reader(csvfile)
            next(csv_reader)
            rows = list(csv_reader)
            total = len(rows)
            for i, row in enumerate(rows):
                if app.stop_events["wc_gen"].is_set():
                    app.log_message(widgets['log_area'], "Automation stopped.", "warning"); break
                if not any(field.strip() for field in row): continue
                app.log_message(widgets['log_area'], f"--- Processing Row {i+1}/{total} ---")
                try:
                    priority, work_name, khata_no, plot_no, village_name = row
                    driver.get(config.WC_GEN_CONFIG["url"])
                    app.log_message(widgets['log_area'], "Navigated to work entry page...")
                    wait = WebDriverWait(driver, 20)
                    wait.until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_ddlMastercategory")))
                    app.log_message(widgets['log_area'], "Filling form data...")
                    Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlMastercategory")).select_by_value("B")
                    Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlproposed_work_category")).select_by_value("Construction of house")
                    Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlbeneficiary_type")).select_by_value("Individual")
                    Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlactivity_type")).select_by_value("Construction/Plantation/Development/Reclamation")
                    Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlproposed_work_type")).select_by_value("Construction of PMAY /State House")
                    Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlprostatus")).select_by_value("Constr of State scheme House for Individuals")
                    driver.find_element(By.ID, "ContentPlaceHolder1_txtdist").clear(); driver.find_element(By.ID, "ContentPlaceHolder1_txtdist").send_keys("36")
                    Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlpanch")).select_by_visible_text(panchayat_name)
                    time.sleep(1.5)
                    app.log_message(widgets['log_area'], f"Selecting Village: {village_name}")
                    Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlvillage")).select_by_visible_text(village_name)
                    Select(driver.find_element(By.ID, "ContentPlaceHolder1_lblFin_year")).select_by_value("2025-2026")
                    Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlridgetype")).select_by_value("L")
                    driver.find_element(By.ID, "ContentPlaceHolder1_txtPropDate").clear(); driver.find_element(By.ID, "ContentPlaceHolder1_txtPropDate").send_keys("15/06/2025")
                    driver.find_element(By.ID, "ContentPlaceHolder1_txtstartdate").clear(); driver.find_element(By.ID, "ContentPlaceHolder1_txtstartdate").send_keys("15/06/2025")
                    driver.find_element(By.ID, "ContentPlaceHolder1_TxtEstlb").clear(); driver.find_element(By.ID, "ContentPlaceHolder1_TxtEstlb").send_keys("0.25380")
                    driver.find_element(By.ID, "ContentPlaceHolder1_txtEstMat").clear(); driver.find_element(By.ID, "ContentPlaceHolder1_txtEstMat").send_keys("0.0")
                    Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlExeAgency")).select_by_value("3")
                    driver.find_element(By.ID, "ContentPlaceHolder1_txtPriority").send_keys(priority)
                    driver.find_element(By.ID, "ContentPlaceHolder1_txtkhtano").send_keys(khata_no)
                    driver.find_element(By.ID, "ContentPlaceHolder1_txtPlotNo").send_keys(plot_no)
                    app.log_message(widgets['log_area'], "Pasting 'Work Name'...")
                    work_name_field = driver.find_element(By.ID, "ContentPlaceHolder1_txtworkname")
                    pyperclip.copy(work_name)
                    paste_key = Keys.COMMAND if config.OS_SYSTEM == "Darwin" else Keys.CONTROL
                    work_name_field.send_keys(paste_key, 'v')
                    time.sleep(0.5)
                    app.log_message(widgets['log_area'], "Submitting...")
                    driver.find_element(By.ID, "ContentPlaceHolder1_btSave").click()
                    time.sleep(3)
                    app.log_message(widgets['log_area'], f"Row {i+1} submitted successfully.", "success")
                except Exception as e:
                    app.log_message(widgets['log_area'], f"ERROR processing row {i+1}: {e}", "error"); continue
    except FileNotFoundError:
        app.log_message(widgets['log_area'], f"ERROR: CSV file not found.", "error")
    except Exception as e:
        app.log_message(widgets['log_area'], f"An unexpected error occurred: {e}", "error")
    finally:
        app.after(0, set_ui_state, False)
        app.log_message(widgets['log_area'], "\n--- Automation Finished ---")