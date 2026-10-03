; Inno Setup Script for College Timetable Manager (standalone Windows desktop app)
; Requires Inno Setup 6.x
; PHASE 4 guarantees baked into this script:
; - Installer contains ONLY the app + runtime (CollegeTimetable.exe + README).
;   No timetable.db, no learned profile, no pretrained model.joblib is bundled.
; - Each PC keeps its own data under %APPDATA%\CollegeTimetableManager\:
;     timetable.db, timetable_learning_profile.json,
;     timetable_agent_model\model.joblib|metadata.json|training_rows.jsonl
; - Program Files install dir is read-only at runtime; user data never lives there.
; - No Python, no Ollama, no internet required. Ollama stays an optional
;   localhost planner only. Version (MyAppVersion) is stamped by build.py from
;   the single source of truth app/__init__.py::__version__.

#define MyAppName "College Timetable Manager"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "College Timetable"
#define MyAppURL "https://github.com/Siddharth2278/Time-Table-Management"
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
LicenseFile=..\LICENSE
OutputDir=..\dist
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
; Do NOT delete user data in AppData automatically - preserve timetable.db,
; learned profile and trained model for future reinstalls.
; Type: filesandordirs; Name: "{localappdata}\CollegeTimetableManager"  ; intentionally not deleted
; Only delete if user explicitly chooses Yes in the post-uninstall prompt.

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
    // User data is preserved by default; only an explicit Yes deletes it.
    DataDir := ExpandConstant('{userappdata}\CollegeTimetableManager');
    if MsgBox('Do you want to delete all timetable data? (timetable.db, learned profile, trained model and backups will be permanently removed)' + #13#10 +
              'Location: ' + DataDir + #13#10 + #13#10 +
              'Click Yes to delete all data, No to keep your data for future reinstalls (recommended).',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      DelTree(DataDir, True, True, True);
    end;
  end;
end;
