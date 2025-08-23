#!/bin/bash

# --- Define app details here ---
APP_NAME="NREGABot"
ICON_FILE="assets/app_icon.icns"

# --- NEW: Automatically detect version from config.py ---
echo "Reading application version from config.py..."
# This command extracts the version string from the config file
APP_VERSION=$(grep "APP_VERSION =" config.py | sed 's/.*"\(.*\)".*/\1/')

if [ -z "$APP_VERSION" ]; then
    echo "!!!!!! ERROR: FAILED to read version from config.py !!!!!!"
    exit 1
fi
echo "Found version: $APP_VERSION"

OUTPUT_DMG_NAME="dist/${APP_NAME}-v${APP_VERSION}-macOS.dmg"

# --- Step 1: Run PyInstaller ---
echo "Building the application with PyInstaller..."
pyinstaller --noconfirm --windowed --name "${APP_NAME}" \
--icon="$ICON_FILE" \
--add-data="logo.png:." \
--add-data="theme.json:." \
--add-data="changelog.json:." \
--add-data="assets:assets" \
--add-data=".env:." \
--add-data="jobcard.jpeg:." \
--add-data="tabs:tabs" \
--add-data="bin/mac:bin/mac" \
--collect-data fpdf \
main_app.py

# --- Step 2: Create the DMG ---
echo "Creating DMG package..."
create-dmg \
  --volname "${APP_NAME} Installer" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "${APP_NAME}.app" 175 180 \
  --hide-extension "${APP_NAME}.app" \
  --app-drop-link 425 180 \
  "$OUTPUT_DMG_NAME" \
  "dist/${APP_NAME}.app"

echo "Build complete! DMG is located at: ${OUTPUT_DMG_NAME}"