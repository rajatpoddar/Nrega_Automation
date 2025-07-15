import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

# --- 1. USER INPUT ---
DISTRICT_NAME = "DEOGHAR"
BLOCK_NAME = "PALOJORI"
PANCHAYAT_NAME = "Dhawa"
USER_ID = "3493233109"
PASSWORD = "Dhawa@008"

# --- 2. AUTOMATION SCRIPT ---
print("Initializing WebDriver (Selenium will manage the driver automatically)...")
driver = webdriver.Chrome()
driver.implicitly_wait(5) # Set a default wait time

url = "https://mnregaweb3.nic.in/Netnrega/FTO/Login.aspx?&level=HomeACGP&state_code=34"
driver.get(url)
print("Successfully opened the NREGA login page.")

try:
    wait = WebDriverWait(driver, 20)

    # Steps 1, 2, and 3 remain the same
    print(f"Selecting District: {DISTRICT_NAME}...")
    Select(wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddl_District")))).select_by_visible_text(DISTRICT_NAME)
    print("District selected.")

    print(f"Waiting for Block list to populate for {DISTRICT_NAME}...")
    block_dropdown_id = "ctl00_ContentPlaceHolder1_ddl_Block"
    wait.until(lambda d: len(Select(d.find_element(By.ID, block_dropdown_id)).options) > 1)
    Select(driver.find_element(By.ID, block_dropdown_id)).select_by_visible_text(BLOCK_NAME)
    print("Block selected.")

    print(f"Waiting for Panchayat list to populate for {BLOCK_NAME}...")
    panchayat_dropdown_id = "ctl00_ContentPlaceHolder1_ddl_Panch"
    wait.until(lambda d: len(Select(d.find_element(By.ID, panchayat_dropdown_id)).options) > 1)
    Select(driver.find_element(By.ID, panchayat_dropdown_id)).select_by_visible_text(PANCHAYAT_NAME)
    print("Panchayat selected.")

    # Step 4: Enter User ID
    print("Entering User ID...")
    user_id_field_id = "ctl00_ContentPlaceHolder1_txt_UserID"
    wait.until(EC.element_to_be_clickable((By.ID, user_id_field_id))).send_keys(USER_ID)
    print("User ID entered.")

    # --- FINAL, MORE ROBUST FIX ---
    # Step 5: Enter Password using a retry loop
    print("Entering Password...")
    password_field_id = "ctl00_ContentPlaceHolder1_txt_Password"
    end_time = time.time() + 10  # Try for 10 seconds
    while True:
        try:
            # Find the password field and type in it. This will be retried if it fails.
            wait.until(EC.element_to_be_clickable((By.ID, password_field_id))).send_keys(PASSWORD)
            print("Password entered successfully.")
            break  # Exit the loop on success
        except StaleElementReferenceException:
            # If the element is stale, the loop will simply try again.
            if time.time() > end_time:
                raise Exception("Failed to enter password due to persistent page refreshes.")
            pass
    # --- END OF FINAL FIX ---


    # Step 6: Handle the CAPTCHA (Manual Step)
    print("\n" + "="*40)
    print("SCRIPT PAUSED: Please solve the CAPTCHA.")
    print("Look at the browser window and type the Security Code into this terminal.")
    print("="*40)
    
    captcha_input = input("Enter Security Code: ")
    driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txt_Captcha").send_keys(captcha_input)

    # Step 7: Click Login
    print("Attempting to log in...")
    driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btn_Login").click()

    print("\nLogin submitted. The browser window will remain open for 60 seconds.")
    time.sleep(60)

except Exception as e:
    print(f"\nAn error occurred: {e}")
    print("Please check if the input values are correct and exist on the page.")

finally:
    print("Closing the browser.")
    driver.quit()