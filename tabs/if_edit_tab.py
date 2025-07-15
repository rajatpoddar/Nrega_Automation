# tabs/if_edit_tab.py
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
    controls = ttk.LabelFrame(parent_frame, text="IF Editor Controls")
    controls.grid(row=0, column=0, sticky="ew", pady=(0,10))
    controls.columnconfigure(1, weight=1)
    
    ttk.Label(controls, text="CSV Data File:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    file_frame = ttk.Frame(controls)
    file_frame.grid(row=0, column=1, sticky='ew', pady=5, padx=5)
    
    def on_select_csv_click():
        select_csv_file(app_instance)
    
    widgets['select_button'] = ttk.Button(file_frame, text="Select if_edit_data.csv", command=on_select_csv_click)
    widgets['select_button'].pack(side=tk.LEFT, padx=(0, 10))
    widgets['file_label'] = ttk.Label(file_frame, text="No file selected")
    widgets['file_label'].pack(side=tk.LEFT)
    
    action_frame = ttk.Frame(controls)
    action_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(15,5))
    action_frame.columnconfigure((0, 1, 2), weight=1)
    
    def on_start_click(): start_automation(app_instance)
    def on_stop_click(): app_instance.stop_events["if_edit"].set()
    def on_reset_click(): reset_ui(app_instance)

    widgets['start_button'] = ttk.Button(action_frame, text="▶ Start Automation", style="Accent.TButton", command=on_start_click)
    widgets['start_button'].grid(row=0, column=0, sticky="ew", padx=(0,5), ipady=5)
    widgets['stop_button'] = ttk.Button(action_frame, text="Stop", command=on_stop_click, state="disabled")
    widgets['stop_button'].grid(row=0, column=1, sticky="ew", padx=(5,5), ipady=5)
    widgets['reset_button'] = ttk.Button(action_frame, text="Reset", style="Outline.TButton", command=on_reset_click)
    widgets['reset_button'].grid(row=0, column=2, sticky='ew', padx=(5,0), ipady=5)

    log_notebook = ttk.Notebook(parent_frame, style="Modern.TNotebook")
    log_notebook.grid(row=1, column=0, sticky="nsew")
    log_frame = ttk.Frame(log_notebook, padding=15)
    log_notebook.add(log_frame, text="Log")
    
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    widgets['log_area'] = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state="disabled", height=15)
    widgets['log_area'].grid(row=0, column=0, sticky="nsew")

    def copy_log_to_clipboard():
        try:
            log_content = widgets['log_area'].get("1.0", tk.END)
            pyperclip.copy(log_content)
            messagebox.showinfo("Copied", "Log content has been copied to the clipboard.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not copy log: {e}")

    copy_button_frame = ttk.Frame(log_frame)
    copy_button_frame.grid(row=1, column=0, sticky='e', pady=(5,0))
    ttk.Button(copy_button_frame, text="Copy Log", command=copy_log_to_clipboard, style="Outline.TButton").pack()

def reset_ui(app):
    if messagebox.askokcancel("Reset Form?", "Are you sure you want to clear the selected file and log for this tab?"):
        widgets['file_label'].config(text="No file selected")
        if "if_edit" in app.csv_paths:
            app.csv_paths["if_edit"] = None
        app.clear_log(widgets['log_area'])
        app.log_message(widgets['log_area'], "Form has been reset.")

def set_ui_state(running):
    state = "disabled" if running else "normal"
    widgets['start_button'].config(state=state)
    widgets['stop_button'].config(state="normal" if running else "disabled")
    widgets['select_button'].config(state=state)
    widgets['reset_button'].config(state=state)

def select_csv_file(app):
    path = filedialog.askopenfilename(title="Select your CSV data file", filetypes=[("CSV files", "*.csv")])
    if path:
        app.csv_paths["if_edit"] = path
        filename = os.path.basename(path)
        widgets['file_label'].config(text=filename)
        app.log_message(widgets['log_area'], f"Selected file: {path}")

def start_automation(app):
    if "if_edit" not in app.csv_paths or not app.csv_paths["if_edit"]:
        messagebox.showwarning("Input Missing", "Please select a CSV file first."); return
    app.start_automation_thread("if_edit", run_automation_logic)

def run_automation_logic(app):
    app.after(0, set_ui_state, True)
    app.clear_log(widgets['log_area'])
    app.log_message(widgets['log_area'], "--- Starting IF Editor Automation ---")
    try:
        driver = app.connect_to_chrome()
        wait = WebDriverWait(driver, 10)
        with open(app.csv_paths["if_edit"], mode='r', encoding='utf-8-sig') as csvfile:
            csv_reader = csv.reader(csvfile)
            next(csv_reader)
            rows = list(csv_reader)
            total = len(rows)
            for i, row in enumerate(rows):
                if app.stop_events["if_edit"].is_set():
                    app.log_message(widgets['log_area'], "Automation stopped.", "warning"); break
                if not row or len(row) < 3:
                    app.log_message(widgets['log_area'], f"Skipping empty row {i+1}.", "warning"); continue
                work_code, beneficiary_type, job_card = row[0].strip(), row[1].strip(), row[2].strip()
                app.log_message(widgets['log_area'], f"--- Processing {i+1}/{total}: WC={work_code} ---")
                _process_single_if_edit(app, driver, wait, work_code, beneficiary_type, job_card)
    except FileNotFoundError:
        app.log_message(widgets['log_area'], "FATAL ERROR: File not found.", "error")
    except Exception as e:
        app.log_message(widgets['log_area'], f"A critical error occurred: {e}", "error")
    finally:
        app.log_message(widgets['log_area'], "--- Automation Finished ---")
        app.after(0, set_ui_state, False)

def _process_single_if_edit(app, driver, wait, work_code, beneficiary_type, job_card):
    try:
        # Page 1
        driver.get(config.IF_EDIT_CONFIG["url"])
        app.log_message(widgets['log_area'], "Page 1: Entering work details...")
        wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_txtwrksearchkey"))).clear()
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtwrksearchkey").send_keys(work_code)
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtwrksearchkey").send_keys(Keys.TAB); time.sleep(1)
        
        Select(wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_ddlworkName")))).select_by_index(1); time.sleep(3)
        
        wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_TxtEstpd"))).clear()
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_TxtEstpd").send_keys("0.090")
        
        beneficiaries_input = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txt_nofobenificary")
        beneficiaries_input.clear(); beneficiaries_input.send_keys("1"); beneficiaries_input.send_keys(Keys.TAB); time.sleep(2)
        
        Select(wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_grdData_ctl02_ddljobcard")))).select_by_value(job_card); time.sleep(1)
        
        Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlTypeBenif")).select_by_visible_text(beneficiary_type)
        Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlpresentstatus")).select_by_visible_text("Not Exist")
        
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_UCconverg_rblConverg_0").click(); time.sleep(1)
        
        Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_UCconverg_ddlSchemeType1")).select_by_visible_text("State"); time.sleep(1) 
        Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_UCconverg_ddlScheme1")).select_by_visible_text("ABUA AWAS YOJNA")
        
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btupdate").click()
        app.log_message(widgets['log_area'], "Page 1 'Update' clicked.", "success")
        
        # Page 2
        app.log_message(widgets['log_area'], "Page 2: Entering sanction details...")
        wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_txtsanctionno")))
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtsanctionno").send_keys("1-06/2025")
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtsanctionDate").send_keys("20/06/2025")
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtEstTimecompWork").send_keys("1")
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtAvglabourperday").send_keys("10")
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtExcpectedmanday").clear(); driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtExcpectedmanday").send_keys("0.090")
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtTechsancAmt").clear(); driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtTechsancAmt").send_keys("0.25380")
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_Sanc_Tech_Labr_Unskilled").clear(); driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_Sanc_Tech_Labr_Unskilled").send_keys("0.25380")
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtFinsan_no").send_keys("01-06/2025")
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_sanc_fin_date").send_keys("20/06/2025")
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_sanc_fin_Amt").clear(); driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_sanc_fin_Amt").send_keys("0.25380")
        
        # UPDATED: Added a Keys.TAB press after the final input
        fin_scheme_input = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_fin_scheme1")
        fin_scheme_input.clear()
        fin_scheme_input.send_keys("0")
        fin_scheme_input.send_keys(Keys.TAB)
        time.sleep(0.5) # A brief pause after tabbing
        
        save_button = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btSave")
        driver.execute_script("arguments[0].click();", save_button)
        
        app.log_message(widgets['log_area'], "Page 2 'Save' clicked.", "success")
        
        # Page 3
        app.log_message(widgets['log_area'], "Page 3: Entering activity details...")
        wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddlAct")))
        Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddlAct")).select_by_value("ACT105"); time.sleep(2)
        
        unit_price_input = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_txtAct_UnitPrice")))
        unit_price_input.clear(); unit_price_input.send_keys("282"); unit_price_input.send_keys(Keys.TAB); time.sleep(2)
        
        qty_input = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_txtAct_Qty")))
        qty_input.clear(); qty_input.send_keys("90"); qty_input.send_keys(Keys.TAB); time.sleep(1)
        
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btsave").click()
        app.log_message(widgets['log_area'], f"SUCCESS: Final 'Save' clicked for {job_card}.", "success"); time.sleep(3)
    except Exception as e:
        app.log_message(widgets['log_area'], f"An error occurred for WC {work_code}: {e}", "error")