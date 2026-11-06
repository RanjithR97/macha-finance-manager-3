#define MyAppName "Macha Finance Manager"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "Macha Finance Manager"
#define MyAppExeName "MachaFinanceManager.exe"

[Setup]
AppId={{8D13C4A2-EE41-4C43-91B9-4F2C7B0F18A1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Macha Finance Manager
DefaultGroupName={#MyAppName}
OutputDir=..\installer-output
OutputBaseFilename=MachaFinanceManager-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "..\dist\MachaFinanceManager.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Macha Finance Manager"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Macha Finance Manager"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Macha Finance Manager"; Flags: postinstall nowait skipifsilent
