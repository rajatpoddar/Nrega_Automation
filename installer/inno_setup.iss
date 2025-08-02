[Setup]
AppName=NREGABot
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\NREGABot
DefaultGroupName=NREGABot
OutputBaseFilename=NREGABot-v{#MyAppVersion}-Setup
OutputDir=dist
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\NREGABot-v{#MyAppVersion}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\NREGABot"; Filename: "{app}\NREGABot-v{#MyAppVersion}.exe"
Name: "{commondesktop}\NREGABot"; Filename: "{app}\NREGABot-v{#MyAppVersion}.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
