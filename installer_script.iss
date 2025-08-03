; NREGABot Inno Setup Script
[Setup]
AppName=NREGABot
AppVersion=2.5.3
AppPublisher=Rajat Poddar
DefaultDirName={autopf}\NREGABot
DefaultGroupName=NREGABot
OutputDir=Output
OutputBaseFilename=NREGABot-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\NREGABot\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\NREGABot"; Filename: "{app}\NREGABot.exe"
Name: "{group}\Uninstall NREGABot"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\NREGABot.exe"; Description: "Launch NREGABot"; Flags: nowait postinstall skipifsilent
