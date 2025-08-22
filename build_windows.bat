@echo off
REM =================================================================
REM  Professional Windows Build Script for NREGA Bot
REM =================================================================

ECHO [STEP 0] Cleaning up previous build artifacts...
IF EXIST "dist" ( rmdir /s /q "dist" )
IF EXIST "build" ( rmdir /s /q "build" )
ECHO Cleanup complete.

REM --- Configuration ---
SET "APP_NAME=NREGA Bot"
SET "INNO_SETUP_COMPILER=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

REM --- Step 1: Dynamically get version from config.py ---
ECHO [STEP 1] Reading application version from config.py...
FOR /F "tokens=2 delims=='\" " %%V IN ('findstr /R /C:"^APP_VERSION = " config.py') DO (SET "APP_VERSION=%%V")

IF NOT DEFINED APP_VERSION (
    ECHO !!!!!!! ERROR: FAILED to read version from config.py !!!!!!!
    goto End
)

ECHO Found version: %APP_VERSION%

REM --- Step 2: Run PyInstaller ---
ECHO [STEP 2] Building the application executable with PyInstaller...
pyinstaller --noconfirm --windowed --onefile --name "%APP_NAME%" --icon="assets/app_icon.ico" --add-data="logo.png;." --add-data="theme.json;." --add-data="changelog.json;." --add-data="assets;assets" --add-data=".env;." --add-data="jobcard.jpeg;." --add-data="tabs;tabs" --add-data="bin;bin" --collect-data fpdf main_app.py

if errorlevel 1 (
    ECHO !!!!!!! PyInstaller build FAILED. !!!!!!!
    goto End
)
ECHO PyInstaller build successful.

REM --- Step 3: Run Inno Setup Compiler ---
ECHO [STEP 3] Creating the installer with Inno Setup...
if not exist "%INNO_SETUP_COMPILER%" (
    ECHO !!!!!!! ERROR: Inno Setup Compiler not found! !!!!!!!
    goto End
)

"%INNO_SETUP_COMPILER%" /DAppVersion="%APP_VERSION%" "installer.iss"

if errorlevel 1 (
    ECHO !!!!!!! Inno Setup build FAILED. !!!!!!!
    goto End
)
ECHO Installer created successfully.

:End
ECHO.
pause