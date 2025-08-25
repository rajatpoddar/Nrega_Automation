@echo off
REM =======================================================
REM  Windows Build Script for NREGA Bot
REM =======================================================

REM --- Configuration ---
REM The APP_VERSION is now set by the GitHub Actions workflow environment variable.
SET APP_NAME="NREGA Bot"
SET INNO_SETUP_COMPILER="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

ECHO ######################################################
ECHO.
ECHO  Building %APP_NAME% v%APP_VERSION% for Windows...
ECHO.
ECHO ######################################################
ECHO.
REM --- Step 1: Run PyInstaller ---
ECHO [STEP 1/2] Building the application with PyInstaller...
ECHO.
pyinstaller --noconfirm --windowed --onefile ^
--name %APP_NAME% ^
--icon="assets/app_icon.ico" ^
--add-data="logo.png;." ^
--add-data="theme.json;." ^
--add-data="changelog.json;." ^
--add-data="assets;assets" ^
--add-data=".env;." ^
--add-data="jobcard.jpeg;." ^
--add-data="tabs;tabs" ^
--collect-data fpdf ^
main_app.py

REM Check if PyInstaller failed
if errorlevel 1 (
    ECHO.
    ECHO !!!!!!! PyInstaller build FAILED. !!!!!!!
    goto End
)

ECHO.
ECHO PyInstaller build successful.
ECHO.

REM --- Step 2: Run Inno Setup Compiler ---
ECHO [STEP 2/2] Creating the installer with Inno Setup...
ECHO.
REM Check if the Inno Setup compiler exists
if not exist %INNO_SETUP_COMPILER% (
    ECHO.
    ECHO !!!!!!! Inno Setup Compiler not found at %INNO_SETUP_COMPILER% !!!!!!!
    ECHO Please update the INNO_SETUP_COMPILER path at the top of this script.
    goto End
)

%INNO_SETUP_COMPILER% "installer.iss"

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