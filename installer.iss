; NREGA Dashboard Inno Setup Script
; Version 2.4.1

#define AppName "NREGA-Dashboard"
#define AppVersion "2.4.1"
#define AppPublisher "PoddarSolutions"
#define AppURL "https://github.com/rajatpoddar"
#define AppExeName "NREGA-Dashboard.exe"
#define OutputName "NREGA-Dashboard-v" + AppVersion + "-Setup"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value for other applications.
AppId={{E6A5B0D1-2C3D-4E5F-8A9B-1C2D3E4F5A6B}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={autopf64}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; The setup file will be created in an 'installer' sub-folder.
OutputDir=installer
OutputBaseFilename={#OutputName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#AppExeName}
SetupIconFile=app_icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}";

[Files]
; This command packages everything from your PyInstaller output directory.
Source: "dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent