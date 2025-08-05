#!/bin/bash

# --- Define app details here ---
APP_NAME="NREGABot"
APP_VERSION="2.5.5" #<-- I've updated this to your latest version
OUTPUT_DMG_NAME="dist/${APP_NAME}-v${APP_VERSION}-macOS.dmg"

# --- Step 1: Run PyInstaller ---
echo "Building the application with PyInstaller..."
pyinstaller --noconfirm --windowed --name "${APP_NAME}" \
--icon="assets/app_icon.icns" \
--add-data="logo.png:." \
--add-data="payment_qr.png:." \
--add-data="theme.json:." \
--add-data="changelog.json:." \
--add-data="assets:assets" \
--add-data=".env:." \
--add-data="jobcard.jpeg:." \
--collect-data fpdf \
main_app.py

# --- Step 2: Create the DMG ---
echo "Creating DMG package..."
# This part of your script is already excellent and needs no changes
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