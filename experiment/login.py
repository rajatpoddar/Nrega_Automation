import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- 1. USER INPUT ---
# !! IMPORTANT !!: All values must be an EXACT match to the text in the dropdowns.
DISTRICT_NAME = "DEOGHAR"
BLOCK_NAME = "PALOJORI"
PANCHAYAT_NAME = "Dhawa"
USER_ID = "3493233109"
PASSWORD = "Dhawa@008"

# --- 2. AUTOMATION SCRIPT ---

# --- THIS IS THE MODIFIED PART ---
# Selenium will automatically download and manage the correct driver.
# No path is needed.
print("Initializing WebDriver (Selenium will manage the driver automatically)...")
driver = webdriver.Chrome()
# --- END OF MODIFIED PART ---


# Open the login page
url = "https://mnregaweb3.nic.in/Netnrega/FTO/Login.aspx?&level=HomeACGP&state_code=34"
driver.get(url)
print("Successfully opened the NREGA login page.")

try:
    # (The rest of your script remains exactly the same)
    wait = WebDriverWait(driver, 20)

    print("Selecting District: {}...".format(DISTRICT_NAME))
    # ... rest of the script
    # ...

# (Paste the rest of your try/except/finally block here)
    # --- Step 1: Select District ---
    district_dropdown_id = "ctl00_ContentPlaceHolder1_ddl_District"
    district_element = wait.until(EC.presence_of_element_located((By.ID, district_dropdown_id)))
    Select(district_element).select_by_visible_text(DISTRICT_NAME)
    print("District selected.")

    # --- Step 2: Wait for Block dropdown to populate and then select a Block ---
    print("Waiting for Block list to populate for {}...".format(DISTRICT_NAME))
    block_dropdown_id = "ctl00_ContentPlaceHolder1_ddl_Block"
    wait.until(lambda d: len(Select(d.find_element(By.ID, block_dropdown_id)).options) > 1)
    
    print("Selecting Block: {}...".format(BLOCK_NAME))
    Select(driver.find_element(By.ID, block_dropdown_id)).select_by_visible_text(BLOCK_NAME)
    print("Block selected.")

    # --- Step 3: Wait for Panchayat dropdown to populate and then select a Panchayat ---
    print("Waiting for Panchayat list to populate for {}...".format(BLOCK_NAME))
    panchayat_dropdown_id = "ctl00_ContentPlaceHolder1_ddl_Panch"
    wait.until(lambda d: len(Select(d.find_element(By.ID, panchayat_dropdown_id)).options) > 1)

    print("Selecting Panchayat: {}...".format(PANCHAYAT_NAME))
    Select(driver.find_element(By.ID, panchayat_dropdown_id)).select_by_visible_text(PANCHAYAT_NAME)
    print("Panchayat selected.")

    # --- Step 4: Enter User ID and Password ---
    print("Entering User ID and Password...")
    driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txt_UserID").send_keys(USER_ID)
    driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txt_Password").send_keys(PASSWORD)
    print("Credentials entered.")

    # --- Step 5: Handle the CAPTCHA (Manual Step) ---
    print("\n" + "="*40)
    print("SCRIPT PAUSED: Please solve the CAPTCHA.")
    print("Look at the browser window opened by the script.")
    print("Type the Security Code from the image into this terminal and press Enter.")
    print("="*40)
    
    captcha_input = input("Enter Security Code: ")
    driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txt_Captcha").send_keys(captcha_input)

    # --- Step 6: Click Login ---
    print("Attempting to log in...")
    driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btn_Login").click()

    print("\nLogin submitted. The browser window will remain open for 60 seconds.")
    time.sleep(60)

except Exception as e:
    print("\nAn error occurred: {}".format(e))
    print("Please check if the input values (District, Block, etc.) are correct and exist on the page.")

finally:
    print("Closing the browser.")
    driver.quit()