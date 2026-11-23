#define AppName "3D Kalkulačka P2S"
#define AppVersion "0.8.1"
#define AppExe "Kalkulacka3DTisku.exe"

[Setup]
AppId={{B7E3E76F-A8B4-4499-B5C0-8659F961CE92}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Projekt Kalkulačka 3D tisku
AppPublisherURL=https://github.com/kolobezkarmichal/Kalkulacka-3D-tisku-
AppSupportURL=https://github.com/kolobezkarmichal/Kalkulacka-3D-tisku-/issues
DefaultDirName={localappdata}\Programs\Kalkulacka 3D tisku
DefaultGroupName=3D Kalkulačka P2S
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\output
OutputBaseFilename=Kalkulacka-3D-tisku-v0.8.1-Windows-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExe}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "czech"; MessagesFile: "compiler:Languages\Czech.isl"

[Tasks]
Name: "desktopicon"; Description: "Vytvořit zástupce na ploše"; GroupDescription: "Další úlohy:"; Flags: unchecked

[Files]
Source: "..\dist\Kalkulacka3DTisku\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\3D Kalkulačka P2S"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\3D Kalkulačka P2S"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Spustit 3D kalkulačku"; Flags: nowait postinstall skipifsilent
