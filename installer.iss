; NREGA Bot Inno Setup Script
; Version 2.5.3 (Updated)
; Created by NREGA Bot Team

#define AppName "NREGA Bot"
#define AppVersion "2.5.3"
#define AppPublisher "PoddarSolutions"
#define AppURL "https://nregabot.com"
#define AppExeName "NREGA Bot.exe"
#define OutputName "NREGABot-v" + AppVersion + "-Setup"

[Setup]
; IMPORTANT: This ID must be the SAME for all versions.
AppId={{E6A5B0D1-2C3D-4E5F-8A9B-1C2D3E4F5A6B}
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

; --- CORRECTED DIRECTIVES ---
; The SignTool line has been removed to allow building on GitHub Actions.
; This directive will automatically close the running application before installing.
CloseApplications=yes
; This specifies which application to look for and close.
CloseApplicationsFilter=NREGA Bot.exe

[Languages]
Name: "english"; [cite_start]MessagesFile: "compiler:Default.isl" [cite: 3]

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}";

[Files]
Source: "dist\{#AppExeName}"; DestDir: "{app}"; [cite_start]Flags: ignoreversion [cite: 4]

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; [cite_start]Flags: nowait postinstall skipifsilent [cite: 5]