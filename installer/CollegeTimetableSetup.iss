; Inno Setup Script for College Timetable Manager
; Requires Inno Setup 6.x

#define MyAppName "College Timetable Manager"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "College Timetable"
#define MyAppURL ""
#define MyAppExeName "CollegeTimetable.exe"

[Setup]
AppId={{8C1F5E2A-3B4D-4A6E-9F8A-2B3C4D5E6F7A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\CollegeTimetableManager
DisableDirPage=no
DefaultGroupName=College Timetable Manager
AllowNoIcons=yes
LicenseFile=
OutputDir=..
OutputBaseFilename=CollegeTimetableSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\CollegeTimetable.exe"; DestDir: "{app}"; Flags: ignoreversion
; If using onedir build, use: Source: "..\dist\CollegeTimetable\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Do NOT delete user data in AppData - preserve timetable.db
; Type: filesandordirs; Name: "{localappdata}\CollegeTimetableManager"  ; intentionally not deleted
; Only delete if user explicitly chooses - handled via code

[Code]
var
  DeleteDataCheckBox: TNewCheckBox;

procedure InitializeWizard;
begin
  // Optional: add checkbox on uninstall to delete data
end;

function InitializeUninstall(): Boolean;
begin
  // Preserve user data by default
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\CollegeTimetableManager');
    if MsgBox('Do you want to delete all timetable data? (Database and backups will be permanently removed)' + #13#10 + 
              'Location: ' + DataDir + #13#10 + #13#10 +
              'Click Yes to delete all data, No to keep your data for future reinstalls.', 
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      DelTree(DataDir, True, True, True);
    end;
  end;
end;
