#!/bin/bash

# --- Read version directly from config.py for local builds ---
APP_VERSION=$(grep "APP_VERSION =" config.py | awk -F'"' '{print $2}')
if [ -z "$APP_VERSION" ]; then
    echo "Error: Could not determine APP_VERSION from config.py"
    exit 1
fi

APP_NAME="NREGA Bot"
OUTPUT_DMG_NAME="dist/${APP_NAME}-v${APP_VERSION}-macOS.dmg"

echo "Building ${APP_NAME} v${APP_VERSION} for Universal (Intel & Apple Silicon)..."

# --- Set ARCHFLAGS for universal build and export it ---
export ARCHFLAGS="-arch arm64 -arch x86_64"

# --- Re-install dependencies from source to ensure they are universal ---
echo "Installing/re-installing dependencies to ensure they are universal..."
pip install --no-cache-dir --no-binary :all: -r requirements.txt

# Check if pip install failed
if [ $? -ne 0 ]; then
    echo "Dependency installation FAILED."
    exit 1
fi

# --- Step 1: Run PyInstaller ---
echo "Building the application with PyInstaller..."
pyinstaller --noconfirm --windowed --name "${APP_NAME}" \
--icon="assets/app_icon.icns" \
--target-arch universal2 \
--add-data="logo.png:." \
--add-data="theme.json:." \
--add-data="changelog.json:." \
--add-data="assets:assets" \
--add-data=".env:." \
--add-data="jobcard.jpeg:." \
--collect-data fpdf \
main_app.py

# Check if PyInstaller failed
if [ $? -ne 0 ]; then
    echo "PyInstaller build FAILED."
    exit 1
fi

# --- Step 2: Create the DMG ---
echo "Creating DMG package..."
create-dmg \
  --volname "${APP_NAME} Installer" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 128 \
  --app-drop-link 440 180 \
  --icon "${APP_NAME}.app" 160 180 \
  "${OUTPUT_DMG_NAME}" \
  "dist/${APP_NAME}.app"

echo "Build complete! Find your installer at: ${OUTPUT_DMG_NAME}"
