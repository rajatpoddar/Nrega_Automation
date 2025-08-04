@echo off
REM =================================================================
REM  Professional Windows Build Script for NREGA Bot (v3 - Bulletproof)
REM
REM  This script now includes:
REM  1. Cleaning of old build directories.
REM  2. Pre-flight checks to ensure wizard images exist before building.
REM =================================================================

ECHO.
ECHO [STEP 0] Cleaning up previous build artifacts...
IF EXIST "dist" ( rmdir /s /q "dist" )
IF EXIST "build" ( rmdir /s /q "build" )
ECHO Cleanup complete.
ECHO.

REM --- Pre-flight Check for Wizard Images ---
ECHO [STEP 1] Verifying required files...
IF NOT EXIST "wizard_image.bmp" (
    ECHO.
    ECHO !!!!!!! ERROR: "wizard_image.bmp" not found! !!!!!!!
    ECHO Please run the 'generate_wizard_images.py' script first.
    goto End
)
IF NOT EXIST "wizard_small_image.bmp" (
    ECHO.
    ECHO !!!!!!! ERROR: "wizard_small_image.bmp" not found! !!!!!!!
    ECHO Please run the 'generate_wizard_images.py' script first.
    goto End
)
ECHO Required files found.
ECHO.


REM --- Configuration ---
SET "APP_NAME=NREGA Bot"
SET "INNO_SETUP_COMPILER=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

REM --- Step 2: Dynamically get version from config.py ---
ECHO [STEP 2] Reading application version from config.py...
for /f "tokens=*" %%i in ('python -c "import config; print(config.APP_VERSION)"') do (SET "APP_VERSION=%%i")

if not defined APP_VERSION (
    ECHO.
    ECHO !!!!!!! ERROR: FAILED to read version from config.py !!!!!!!
    goto End
)

ECHO.
ECHO ######################################################
ECHO.
ECHO  Building "%APP_NAME%" v%APP_VERSION% for Windows...
ECHO.
ECHO ######################################################
ECHO.

REM --- Step 3: Run PyInstaller ---
ECHO [BUILD 1/2] Building the application executable with PyInstaller...
ECHO.
pyinstaller --noconfirm --windowed --onefile --name "%APP_NAME%" --icon="assets/app_icon.ico" --add-data="logo.png;." --add-data="theme.json;." --add-data="changelog.json;." --add-data="assets;assets" --add-data=".env;." --add-data="jobcard.jpeg;." --add-data="tabs;tabs" --collect-data fpdf main_app.py

if errorlevel 1 (
    ECHO.
    ECHO !!!!!!! PyInstaller build FAILED. !!!!!!!
    goto End
)

ECHO.
ECHO PyInstaller build successful.
ECHO.

REM --- Step 4: Run Inno Setup Compiler ---
ECHO [BUILD 2/2] Creating the installer with Inno Setup...
ECHO.
if not exist "%INNO_SETUP_COMPILER%" (
    ECHO.
    ECHO !!!!!!! ERROR: Inno Setup Compiler not found! !!!!!!!
    goto End
)

"%INNO_SETUP_COMPILER%" /DAppVersion="%APP_VERSION%" "installer.iss"

if errorlevel 1 (
    ECHO.
    ECHO !!!!!!! Inno Setup compilation FAILED. !!!!!!!
    goto End
)

ECHO.
ECHO =======================================================
ECHO.
ECHO  Build successful!
ECHO  Find your installer in the 'installer' sub-folder.
ECHO.
ECHO =======================================================

:End
pause
