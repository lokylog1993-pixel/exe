
#define AppName "BitD GM AI"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define SourceDir "dist\BitD_GM_AI"
#define OutputDir "dist\installer"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={pf}\{#AppName}
DefaultGroupName={#AppName}
DisableDirPage=no
DisableProgramGroupPage=no
OutputDir={#OutputDir}
OutputBaseFilename=BitD_GM_AI_Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=packaging\bitd_gm_ai.ico

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\BitD GM AI.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\BitD GM AI.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
