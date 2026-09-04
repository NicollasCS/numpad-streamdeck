[Setup]
AppName=Numpad Stream Deck 2
AppVersion=2.0.0
DefaultDirName={autopf}\NumpadStreamDeck2
DefaultGroupName=Numpad Stream Deck 2
OutputDir=installer
OutputBaseFilename=NumpadStreamDeck2_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
UninstallDisplayName=Numpad Stream Deck 2
UninstallDisplayIcon={app}\NumpadStreamDeck.exe
WizardStyle=modern
ShowLanguageDialog=no
CreateAppDir=true
SetupIconFile=icon.ico

[Files]
Source: "dist-v2\NumpadStreamDeck.exe"; DestDir: "{app}"
Source: "dist-v2\*.dll"; DestDir: "{app}"; Flags: skipifsourcedoesntexist
Source: "dist-v2\platforms\*"; DestDir: "{app}\platforms"; Flags: recursesubdirs skipifsourcedoesntexist
Source: "dist-v2\styles\*"; DestDir: "{app}\styles"; Flags: recursesubdirs skipifsourcedoesntexist
Source: "dist-v2\imageformats\*"; DestDir: "{app}\imageformats"; Flags: recursesubdirs skipifsourcedoesntexist
Source: "resources\themes\default.qss"; DestDir: "{app}\resources\themes"
Source: "config\default_profile.json"; DestDir: "{app}\config"
Source: "icon.ico"; DestDir: "{app}"

[Icons]
Name: "{group}\Numpad Stream Deck 2"; Filename: "{app}\NumpadStreamDeck.exe"
Name: "{userdesktop}\Numpad Stream Deck 2"; Filename: "{app}\NumpadStreamDeck.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Opcoes adicionais:"
Name: "startup"; Description: "Iniciar com o Windows"; GroupDescription: "Opcoes adicionais:"

[Run]
Filename: "{app}\NumpadStreamDeck.exe"; Description: "Executar Numpad Stream Deck 2"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "NumpadStreamDeck2"; ValueData: "{app}\NumpadStreamDeck.exe"; Tasks: startup