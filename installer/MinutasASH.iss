#define MyAppName "Minutas ASH"
#define MyAppVersion "2.3.5"
#define MyAppPublisher "ASH Ingeniería y Proyectos"
#define MyAppExeName "MinutasASH.exe"

[Setup]
AppId={{C6DB4E51-BD1D-4E44-9E38-1AF77AF18BB8}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Instalador de {#MyAppName}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\ASH\MinutasASH
DefaultGroupName=ASH
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist_installer
OutputBaseFilename=MinutasASH_Setup_2.3.5_Online
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\ash.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19045
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
UsePreviousTasks=yes
AllowNoIcons=yes
DisableWelcomePage=no
AppContact=ASH Ingeniería y Proyectos
AppComments=Gestión local de minutas de reunión
SetupLogging=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce
Name: "whisper"; Description: "Transcripción local de audio y video (Whisper CPU + modelo base, 235 MB)"; GroupDescription: "Componentes opcionales:"; Flags: unchecked

[Files]
Source: "..\dist\MinutasASH\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dist_whisper\WhisperWorker.exe"; DestDir: "{localappdata}\MinutasASH\components\whisper"; Flags: ignoreversion; Tasks: whisper
Source: "..\.runtime\whisper-package\MinutasASH\models\whisper\*"; DestDir: "{localappdata}\MinutasASH\models\whisper"; Flags: ignoreversion recursesubdirs createallsubdirs; Tasks: whisper

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Manual maestro"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--help-topic maestro"; WorkingDir: "{app}"
Name: "{group}\Manual de usuario"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--help-topic usuario"; WorkingDir: "{app}"
Name: "{group}\Manual de configuración"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--help-topic configuracion"; WorkingDir: "{app}"
Name: "{group}\Reuniones extensas y recuperación"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--help-topic procesamiento"; WorkingDir: "{app}"
Name: "{group}\Guía del programador"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--help-topic programador"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.vtt\shell\MinutasASH"; ValueType: string; ValueName: ""; ValueData: "Abrir con Minutas ASH"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.vtt\shell\MinutasASH"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.vtt\shell\MinutasASH\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\MinutasASH"; ValueType: string; ValueName: ""; ValueData: "Abrir como fuente en Minutas ASH"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\MinutasASH"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.txt\shell\MinutasASH\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\MinutasASH"; ValueType: string; ValueName: ""; ValueData: "Abrir como fuente en Minutas ASH"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\MinutasASH"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.docx\shell\MinutasASH\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\MinutasASH"; ValueType: string; ValueName: ""; ValueData: "Transcribir con Minutas ASH"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\MinutasASH"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp3\shell\MinutasASH\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\MinutasASH"; ValueType: string; ValueName: ""; ValueData: "Transcribir con Minutas ASH"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\MinutasASH"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wav\shell\MinutasASH\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\MinutasASH"; ValueType: string; ValueName: ""; ValueData: "Transcribir con Minutas ASH"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\MinutasASH"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.m4a\shell\MinutasASH\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\MinutasASH"; ValueType: string; ValueName: ""; ValueData: "Transcribir con Minutas ASH"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\MinutasASH"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flac\shell\MinutasASH\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\MinutasASH"; ValueType: string; ValueName: ""; ValueData: "Transcribir con Minutas ASH"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\MinutasASH"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ogg\shell\MinutasASH\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\MinutasASH"; ValueType: string; ValueName: ""; ValueData: "Transcribir con Minutas ASH"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\MinutasASH"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\MinutasASH\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\MinutasASH"; ValueType: string; ValueName: ""; ValueData: "Transcribir con Minutas ASH"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\MinutasASH"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\MinutasASH\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\MinutasASH"; ValueType: string; ValueName: ""; ValueData: "Transcribir con Minutas ASH"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\MinutasASH"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webm\shell\MinutasASH\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--provision-auto"; Description: "Preparar componentes de la aplicación"; StatusMsg: "Preparando Minutas ASH..."; Flags: waituntilterminated skipifsilent
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function InitializeSetup(): Boolean;
var
  Version: TWindowsVersion;
begin
  GetWindowsVersionEx(Version);
  Result := True;
  if not IsWin64 then
  begin
    MsgBox('Minutas ASH requiere Windows de 64 bits.', mbError, MB_OK);
    Result := False;
    exit;
  end;
end;
