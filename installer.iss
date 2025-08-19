; NREGA Bot Inno Setup Script
; Version 2.6.3 (Bitmap Fix)

#define AppVersion "2.6.3"  ; Add this line
#define AppName "NREGA Bot"
#define AppPublisher "PoddarSolutions"
#define AppURL "https://nregabot.com"
#define AppExeName "NREGA Bot.exe"
#define OutputName "NREGABot-v" + AppVersion + "-Setup"

[Setup]
; This ID must be the SAME for all versions to ensure proper updates.
AppId={{E6A5B0D1-2C3D-4E5F-8A9B-1C2D3E4F5A6B}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={autopf64}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=installer
OutputBaseFilename={#OutputName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#AppExeName}
SetupIconFile=assets\app_icon.ico

; --- Professional UI & UX Enhancements ---
; Use a dedicated .bmp file for maximum compatibility with the wizard.
; The large image on the left of the wizard.
WizardImageFile=wizard_image.bmp
; The small image in the top-right of the wizard.
WizardSmallImageFile=wizard_small_image.bmp
LicenseFile=license.txt
InfoBeforeFile=infobefore.txt

; --- Update & Relaunch Logic ---
CloseApplications=yes
CloseApplicationsFilter=NREGA Bot.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}";

[Files]
; The main executable built by PyInstaller.
; The license, info, and wizard image files are only needed at compile time
; and do not need to be included in the [Files] section.
Source: "dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; This section ensures a clean uninstall.
Type: filesandordirs; Name: "{localappdata}\PoddarSolutions\NREGABot"
