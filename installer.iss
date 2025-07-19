; -- NREGA Automation Dashboard Installer Script --
; Script generated for Inno Setup
; This script assumes you have already run PyInstaller and have your output
; in a 'dist' folder relative to this script.

#define MyAppName "NREGA Automation Dashboard"
#define MyAppVersion "2.4.0"
#define MyAppPublisher "Rajat Poddar"
#define MyAppURL "https://nrega-dashboard.palojori.in/"
#define MyAppExeName "NREGA-Dashboard.exe"

[Setup]
; Unique ID for your application.
; Use the Inno Setup "Generate GUID" tool or an online generator.
AppId={{5D9A5B7A-9F7C-4B6E-9E7D-6A3B2C1D0E9F}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; The name of the final setup file.
OutputBaseFilename=NREGA-Dashboard-v{#MyAppVersion}-Setup
; The directory where the setup file will be created.
OutputDir=.\Installer
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Requires admin privileges to write to Program Files.
PrivilegesRequired=admin
; Specify the application icon for the installer and Add/Remove Programs.
; This file should be in the same directory as this script.
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; These create checkboxes in the installer wizard.
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; This is the most important section.
; Source: The path to your application files after running PyInstaller.
;         "dist\..." is the main executable.
;         "dist\*" includes all other necessary files (DLLs, assets, etc.).
; DestDir: "{app}" is the directory the user chooses during installation.
; Flags: recursesubdirs tells Inno Setup to include all files and folders.
;        createallsubdirs ensures the directory structure is maintained.

Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; NOTE: Ensure your 'logo.png', 'payment_qr.png', and any other assets
; are inside the 'dist' folder alongside your .exe before compiling.

[Icons]
; Start Menu shortcut
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
; Optional Desktop shortcut (linked to the "desktopicon" task)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
; Optional Quick Launch shortcut
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon
; Uninstall shortcut
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"


[Run]
; Offers to run the application after the installation is complete.
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
