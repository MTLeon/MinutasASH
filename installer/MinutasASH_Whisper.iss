#define AppVersion "2.3.4"

[Setup]
AppId={{5D907A8F-558D-4D2C-A90C-6308FF76C2D9}
AppName=Minutas ASH - Complemento Whisper
AppVersion={#AppVersion}
AppPublisher=ASH Ingeniería y Proyectos
DefaultDirName={localappdata}\MinutasASH\components\whisper
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist_installer
OutputBaseFilename=MinutasASH_Whisper_CPU_2.3.4
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=Minutas ASH - Complemento Whisper CPU

[Files]
Source: "..\dist_whisper\WhisperWorker.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Minutas ASH\Desinstalar complemento Whisper"; Filename: "{uninstallexe}"
