#ifndef MyAppVersion
#define MyAppVersion "dev"
#endif

[Setup]
AppName=NREGABot
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\\NREGABot
DefaultGroupName=NREGABot
OutputBaseFilename=NREGABot-v{#MyAppVersion}-Setup
OutputDir=dist
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\\NREGABot\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\\NREGABot"; Filename: "{app}\\NREGABot.exe"
Name: "{commondesktop}\\NREGABot"; Filename: "{app}\\NREGABot.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
