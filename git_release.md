# Changelog

## Version 2.3.0

### 🆕 FTO Generation
- Added new **'FTO Generation'** automation tab.
- Automates login, processes two verification URLs, accepts all rows, and captures FTO numbers.
- Added a **'Results'** tab to display captured FTO numbers.
- Login process now automatically skips if the user is already logged in.
- Removed password field from UI for better security; user now enters it in the browser.

### 🔧 eMB Entry
- Fixed bug where **'Earth work'** activity was not being detected due to case-sensitivity.
- Added a **'Results'** tab and **'Copy Log'** button for better feedback and debugging.
- Optimized workflow to prevent errors and skip duplicate work codes.

---

## Version 2.2.1

### 🛠 Stability & Bug Fixes
- Fixed critical stability issues in **'MR Fill & Absent'** and **'Jobcard Verify'** tabs.
- Resolved multiple `StaleElementReferenceException` and `TimeoutException` errors.
- Greatly improved the reliability of the **smart wait** feature for manual user actions.
- Corrected element IDs to ensure **'Jobcard Verify'** automation runs without timing out.

### 💡 Usability Enhancements
- Added a user-friendly error message for mistyped **Panchayat** or **Village** names.
- Added instructional note for the **photo naming convention** in the **'Jobcard Verify'** tab.

---

## Version 2.2.0

### ➕ New Features
- Added new **'MR Fill & Absent'** automation tab with manual edit pause.
- Added new **'Jobcard Verify & Photo'** automation tab.

### 🔁 Enhancements
- Enhanced **'Jobcard Verify'** to loop through all job cards and use folder-based or default photo matching.
- Enhanced **'MSR Processor'** and **'Wagelist Gen'** with improved, more resilient error handling and clearer results.

### 🐞 Bug Fixes & UI Improvements
- Fixed various bugs including `StaleElementReferenceException` and `UnexpectedAlertPresentException`.
- Added **'Copy Log'** button and **'Results'** tabs to several modules for better user feedback.

---

## Version 2.1.0

- Added **license expiry notifications**.
- Improved **'About'** tab layout.
- Added **donation** and **pricing** information.

---

## Version 2.0.0

### 🎨 UI Overhaul
- Shortened and reordered tab names for better visibility.
- Enhanced header buttons for launching Chrome with a clearer design.
- Added a direct link to the **Nrega Palojori** website in the footer.
- Added **'Copy Log'** button to more tabs for easier debugging.
