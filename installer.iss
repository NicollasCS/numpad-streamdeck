; Inno Setup Script
; Compile com o Inno Setup Compiler

[Setup]
AppName=Numpad Stream Deck
AppVersion=2.2.0
DefaultDirName={autopf}\NumpadStreamDeck
DefaultGroupName=Numpad Stream Deck
OutputDir=installer
OutputBaseFilename=NumpadStreamDeck_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
UninstallDisplayName=Numpad Stream Deck
UninstallDisplayIcon={app}\NumpadStreamDeck.exe
AppPublisher=Numpad Stream Deck
AppPublisherURL=https://github.com/NicollasCS/numpad-streamdeck
AppSupportURL=https://github.com/NicollasCS/numpad-streamdeck/issues
AppUpdatesURL=https://github.com/NicollasCS/numpad-streamdeck/releases
WizardStyle=modern
ShowLanguageDialog=no
CreateAppDir=true
SetupIconFile=icon.ico

[CustomMessages]
ptbr.Startup=Iniciar com o Windows
ptbr.DesktopShortcut=Atalho na area de trabalho
english.Startup=Start with Windows
english.DesktopShortcut=Create a desktop shortcut

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\NumpadStreamDeck.exe"; DestDir: "{app}"
Source: "dist\raw_input_filter.exe"; DestDir: "{app}\cpp"
Source: "icon.ico"; DestDir: "{app}"
Source: "VC_redist.x64.exe"; DestDir: "{tmp}"

[Icons]
Name: "{userdesktop}\Numpad Stream Deck"; Filename: "{app}\NumpadStreamDeck.exe"; Tasks: desktopicon
Name: "{group}\Numpad Stream Deck"; Filename: "{app}\NumpadStreamDeck.exe"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Opcoes adicionais:";
Name: "startup"; Description: "Iniciar com o Windows"; GroupDescription: "Opcoes adicionais:";

[Run]
Filename: "{tmp}\VC_redist.x64.exe"; Description: "Instalando Microsoft Visual C++ Redistributable"; Parameters: "/quiet /norestart"; Flags: waituntilterminated; Check: IsWin64
Filename: "{app}\NumpadStreamDeck.exe"; Description: "Executar Numpad Stream Deck"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "NumpadStreamDeck"; ValueData: "{app}\NumpadStreamDeck.exe"; Tasks: startup

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\NumpadStreamDeck"

[Code]
function InitializeSetup(): Boolean;
begin
  if not IsWin64 then
    MsgBox('You are using a 32-bit system, which may cause compatibility issues. We recommend using a 64-bit system.', mbInformation, MB_OK);
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    Log('Instalacao do Numpad Stream Deck concluida.');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    DelTree(ExpandConstant('{userappdata}\NumpadStreamDeck'), True, True, True);
end;
