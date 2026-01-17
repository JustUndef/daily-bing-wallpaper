; Bing Wallpaper Downloader - Inno Setup Installer Script
; Requires Inno Setup 6.0 or later (https://jrsoftware.org/isinfo.php)

#define MyAppName "Bing Wallpaper Downloader"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Your Company Name"
#define MyAppURL "https://github.com/yourusername/daily-bing-wallpaper"
#define MyAppExeName "BingWallpaperDownloader.exe"
#define MyTrayExeName "BingWallpaperTray.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE.txt
OutputDir=installer_output
OutputBaseFilename=BingWallpaperDownloader_Setup
; SetupIconFile=installer_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Run daily and at login (downloads wallpaper automatically)"; GroupDescription: "Startup Options:"
Name: "starttray"; Description: "Start system tray app at login (for manual control and navigation)"; GroupDescription: "Startup Options:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\{#MyTrayExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} Manager"; Filename: "{app}\{#MyTrayExeName}"
Name: "{group}\Configure {#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--help"
Name: "{group}\Download Folder"; Filename: "{code:GetDownloadFolder}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Download wallpaper now"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#MyTrayExeName}"; Description: "Start system tray manager"; Flags: nowait postinstall skipifsilent
Filename: "{code:GetDownloadFolder}"; Description: "Open download folder"; Flags: nowait postinstall skipifsilent shellexec

[UninstallDelete]
; Note: We handle wallpaper deletion in code with user prompt
; Type: filesandordirs; Name: "{code:GetDownloadFolder}"

[Code]
var
  ConfigPage: TWizardPage;
  ImageCountEdit: TNewEdit;
  ImageCountLabel: TNewStaticText;
  SetWallpaperCheckbox: TNewCheckBox;
  DownloadFolderPage: TInputDirWizardPage;
  MarketPage: TInputOptionWizardPage;
  ResolutionPage: TInputOptionWizardPage;
  DownloadFolderVar: String;
  MarketVar: String;
  ResolutionVar: String;
  ImageCountVar: Integer;
  SetLatestVar: Boolean;

{ Helper function to convert boolean to JSON string }
function GetJsonBool(value: Boolean): String;
begin
  if value then
    Result := 'true'
  else
    Result := 'false';
end;

{ Helper function to escape backslashes for JSON }
function EscapeJsonString(value: String): String;
var
  i: Integer;
begin
  Result := '';
  for i := 1 to Length(value) do
  begin
    if value[i] = '\' then
      Result := Result + '\\'
    else
      Result := Result + value[i];
  end;
end;

{ Get the configured download folder }
function GetDownloadFolder(Param: String): String;
begin
  if DownloadFolderVar <> '' then
    Result := DownloadFolderVar
  else
    Result := ExpandConstant('{userdocs}\Pictures\BingWallpapers');
end;

{ Create custom wizard pages }
procedure InitializeWizard;
var
  PicturesPath: String;
begin
  { Download Folder Page }
  DownloadFolderPage := CreateInputDirPage(wpSelectDir,
    'Select Download Folder', 'Where should wallpapers be saved?',
    'Select the folder where Bing wallpapers will be downloaded, then click Next.',
    False, '');
  
  PicturesPath := ExpandConstant('{userdocs}\Pictures\BingWallpapers');
  DownloadFolderPage.Add('');
  DownloadFolderPage.Values[0] := PicturesPath;
  
  { Market Selection Page }
  MarketPage := CreateInputOptionPage(DownloadFolderPage.ID,
    'Market Selection', 'Select your preferred Bing market',
    'Choose the region for wallpaper images. This affects available images and descriptions.',
    False, False);
  
  MarketPage.Add('Germany (de-DE)');
  MarketPage.Add('United States (en-US)');
  MarketPage.Add('United Kingdom (en-GB)');
  MarketPage.Add('France (fr-FR)');
  MarketPage.Add('Spain (es-ES)');
  MarketPage.Add('Italy (it-IT)');
  MarketPage.Add('Japan (ja-JP)');
  MarketPage.Add('China (zh-CN)');
  MarketPage.SelectedValueIndex := 0;
  
  { Resolution Selection Page }
  ResolutionPage := CreateInputOptionPage(MarketPage.ID,
    'Resolution Preferences', 'Select your preferred resolution',
    'The downloader will try your selected resolution first, then automatically fall back to lower resolutions if needed.',
    True, False);
  
  ResolutionPage.Add('4K Ultra HD (3840x2160) - Recommended');
  ResolutionPage.Add('2K QHD (2560x1440)');
  ResolutionPage.Add('Full HD (1920x1080)');
  ResolutionPage.Add('HD Plus (1920x1200)');
  ResolutionPage.SelectedValueIndex := 0;
  
  { Configuration Page - Custom page with edit box and checkbox }
  ConfigPage := CreateCustomPage(ResolutionPage.ID,
    'Download Settings', 'Configure download behavior');
  
  { Label for image count }
  ImageCountLabel := TNewStaticText.Create(ConfigPage);
  ImageCountLabel.Parent := ConfigPage.Surface;
  ImageCountLabel.Caption := 'Number of wallpapers to download (1-8):';
  ImageCountLabel.Left := 0;
  ImageCountLabel.Top := 0;
  ImageCountLabel.Width := ConfigPage.SurfaceWidth;
  
  { Edit box for image count }
  ImageCountEdit := TNewEdit.Create(ConfigPage);
  ImageCountEdit.Parent := ConfigPage.Surface;
  ImageCountEdit.Left := 0;
  ImageCountEdit.Top := ImageCountLabel.Top + ImageCountLabel.Height + 4;
  ImageCountEdit.Width := 100;
  ImageCountEdit.Text := '8';
  
  { Checkbox for wallpaper setting }
  SetWallpaperCheckbox := TNewCheckBox.Create(ConfigPage);
  SetWallpaperCheckbox.Parent := ConfigPage.Surface;
  SetWallpaperCheckbox.Caption := 'Set latest wallpaper as desktop background';
  SetWallpaperCheckbox.Left := 0;
  SetWallpaperCheckbox.Top := ImageCountEdit.Top + ImageCountEdit.Height + 16;
  SetWallpaperCheckbox.Width := ConfigPage.SurfaceWidth;
  SetWallpaperCheckbox.Checked := True;
end;

{ Validate user input }
function NextButtonClick(CurPageID: Integer): Boolean;
var
  Count: Integer;
begin
  Result := True;
  
  if CurPageID = ConfigPage.ID then
  begin
    { Validate image count }
    try
      Count := StrToInt(ImageCountEdit.Text);
      if (Count < 1) or (Count > 8) then
      begin
        MsgBox('Please enter a number between 1 and 8 for wallpaper count.', mbError, MB_OK);
        Result := False;
      end;
    except
      MsgBox('Please enter a valid number between 1 and 8 for wallpaper count.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

{ Store configuration when installation finishes }
procedure CurStepChanged(CurStep: TSetupStep);
var
  TaskXml: String;
  TaskName: String;
  ExePath: String;
  Params: String;
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    { Store user selections }
    DownloadFolderVar := DownloadFolderPage.Values[0];
    
    { Store market selection }
    case MarketPage.SelectedValueIndex of
      0: MarketVar := 'de-DE';
      1: MarketVar := 'en-US';
      2: MarketVar := 'en-GB';
      3: MarketVar := 'fr-FR';
      4: MarketVar := 'es-ES';
      5: MarketVar := 'it-IT';
      6: MarketVar := 'ja-JP';
      7: MarketVar := 'zh-CN';
    else
      MarketVar := 'en-US';
    end;
    
    { Store resolution selection }
    case ResolutionPage.SelectedValueIndex of
      0: ResolutionVar := 'UHD,3840x2160,2560x1440,1920x1200,1920x1080';
      1: ResolutionVar := '2560x1440,1920x1200,1920x1080,3840x2160';
      2: ResolutionVar := '1920x1080,1920x1200,2560x1440,3840x2160';
      3: ResolutionVar := '1920x1200,1920x1080,2560x1440,3840x2160';
    else
      ResolutionVar := 'UHD,3840x2160,2560x1440,1920x1200,1920x1080';
    end;
    
    { Store image count }
    ImageCountVar := StrToIntDef(ImageCountEdit.Text, 8);
    
    { Store wallpaper setting preference }
    SetLatestVar := SetWallpaperCheckbox.Checked;
    
    { Create download folder }
    ForceDirectories(DownloadFolderVar);
    
    { Save configuration to JSON file }
    SaveStringToFile(ExpandConstant('{userappdata}\BingWallpaperDownloader\config.json'),
      '{' + #13#10 +
      '  "download_folder": "' + EscapeJsonString(DownloadFolderVar) + '",' + #13#10 +
      '  "market": "' + MarketVar + '",' + #13#10 +
      '  "fallback_markets": "en-US",' + #13#10 +
      '  "resolution": "' + ResolutionVar + '",' + #13#10 +
      '  "image_count": ' + IntToStr(ImageCountVar) + ',' + #13#10 +
      '  "set_latest": ' + GetJsonBool(SetLatestVar) + ',' + #13#10 +
      '  "file_mode": "skip",' + #13#10 +
      '  "name_mode": "slug"' + #13#10 +
      '}', False);
    
    ExePath := ExpandConstant('{app}\{#MyAppExeName}');
    TaskName := 'BingWallpaperDownloader';
    
    { Create scheduled task for daily autostart if selected }
    if WizardIsTaskSelected('autostart') then
    begin
      { Delete existing task if it exists }
      Exec('schtasks.exe', '/Delete /TN "' + TaskName + '" /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      
      { Create new scheduled task (runs daily at 9 AM) }
      TaskXml := ExpandConstant('{tmp}\task.xml');
      SaveStringToFile(TaskXml, 
        '<?xml version="1.0" encoding="UTF-16"?>' + #13#10 +
        '<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">' + #13#10 +
        '  <RegistrationInfo>' + #13#10 +
        '    <Description>Downloads daily Bing wallpaper</Description>' + #13#10 +
        '  </RegistrationInfo>' + #13#10 +
        '  <Triggers>' + #13#10 +
        '    <CalendarTrigger>' + #13#10 +
        '      <StartBoundary>2025-01-01T09:00:00</StartBoundary>' + #13#10 +
        '      <Enabled>true</Enabled>' + #13#10 +
        '      <ScheduleByDay>' + #13#10 +
        '        <DaysInterval>1</DaysInterval>' + #13#10 +
        '      </ScheduleByDay>' + #13#10 +
        '    </CalendarTrigger>' + #13#10 +
        '    <LogonTrigger>' + #13#10 +
        '      <Enabled>true</Enabled>' + #13#10 +
        '      <Delay>PT1M</Delay>' + #13#10 +
        '    </LogonTrigger>' + #13#10 +
        '  </Triggers>' + #13#10 +
        '  <Principals>' + #13#10 +
        '    <Principal>' + #13#10 +
        '      <LogonType>InteractiveToken</LogonType>' + #13#10 +
        '      <RunLevel>HighestAvailable</RunLevel>' + #13#10 +
        '    </Principal>' + #13#10 +
        '  </Principals>' + #13#10 +
        '  <Settings>' + #13#10 +
        '    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>' + #13#10 +
        '    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>' + #13#10 +
        '    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>' + #13#10 +
        '    <AllowHardTerminate>true</AllowHardTerminate>' + #13#10 +
        '    <StartWhenAvailable>true</StartWhenAvailable>' + #13#10 +
        '    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>' + #13#10 +
        '    <IdleSettings>' + #13#10 +
        '      <StopOnIdleEnd>false</StopOnIdleEnd>' + #13#10 +
        '      <RestartOnIdle>false</RestartOnIdle>' + #13#10 +
        '    </IdleSettings>' + #13#10 +
        '    <AllowStartOnDemand>true</AllowStartOnDemand>' + #13#10 +
        '    <Enabled>true</Enabled>' + #13#10 +
        '    <Hidden>false</Hidden>' + #13#10 +
        '    <RunOnlyIfIdle>false</RunOnlyIfIdle>' + #13#10 +
        '    <WakeToRun>false</WakeToRun>' + #13#10 +
        '    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>' + #13#10 +
        '    <Priority>7</Priority>' + #13#10 +
        '  </Settings>' + #13#10 +
        '  <Actions Context="Author">' + #13#10 +
        '    <Exec>' + #13#10 +
        '      <Command>"' + ExePath + '"</Command>' + #13#10 +
        '    </Exec>' + #13#10 +
        '  </Actions>' + #13#10 +
        '</Task>', False);
      
      Exec('schtasks.exe', '/Create /TN "' + TaskName + '" /XML "' + TaskXml + '" /F', 
        '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      
      DeleteFile(TaskXml);
    end;
    
    { Create tray app startup shortcut if selected }
    if WizardIsTaskSelected('starttray') then
    begin
      CreateShellLink(
        ExpandConstant('{userstartup}\{#MyAppName} Manager.lnk'),
        'Bing Wallpaper Manager',
        ExpandConstant('{app}\{#MyTrayExeName}'),
        '',
        '',
        ExpandConstant('{app}\{#MyTrayExeName}'),
        0,
        SW_SHOWNORMAL);
    end;
  end;
end;

{ Helper function to kill a process by name }
function KillProcess(const ProcessName: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('taskkill.exe', '/F /IM "' + ProcessName + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  { ResultCode 128 means process not found, which is also success for our purposes }
  if ResultCode = 128 then
    Result := True;
end;

{ Helper function to read download folder from config }
function GetDownloadFolderFromConfig(): String;
var
  ConfigPath: String;
  ConfigContent: AnsiString;
  StartPos, EndPos: Integer;
begin
  Result := ExpandConstant('{userdocs}\Pictures\BingWallpapers'); { Default }
  ConfigPath := ExpandConstant('{userappdata}\BingWallpaperDownloader\config.json');
  
  if FileExists(ConfigPath) then
  begin
    if LoadStringFromFile(ConfigPath, ConfigContent) then
    begin
      { Simple JSON parsing to find download_folder value }
      StartPos := Pos('"download_folder":', ConfigContent);
      if StartPos > 0 then
      begin
        StartPos := StartPos + Length('"download_folder":');
        { Skip whitespace and opening quote }
        while (StartPos <= Length(ConfigContent)) and 
              ((ConfigContent[StartPos] = ' ') or (ConfigContent[StartPos] = #9) or 
               (ConfigContent[StartPos] = #13) or (ConfigContent[StartPos] = #10)) do
          StartPos := StartPos + 1;
        
        if (StartPos <= Length(ConfigContent)) and (ConfigContent[StartPos] = '"') then
        begin
          StartPos := StartPos + 1; { Skip opening quote }
          EndPos := StartPos;
          { Find closing quote, handle escaped backslashes }
          while (EndPos <= Length(ConfigContent)) and (ConfigContent[EndPos] <> '"') do
          begin
            if ConfigContent[EndPos] = '\' then
              EndPos := EndPos + 1; { Skip next char if backslash }
            EndPos := EndPos + 1;
          end;
          
          if EndPos > StartPos then
          begin
            Result := Copy(ConfigContent, StartPos, EndPos - StartPos);
            { Unescape backslashes }
            StringChangeEx(Result, '\\', '\', True);
          end;
        end;
      end;
    end;
  end;
end;

{ Cleanup on uninstall }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
  WallpaperFolder: String;
  DeleteConfig: Boolean;
  DeleteWallpapers: Boolean;
  KeptItems: String;
begin
  { Kill running processes BEFORE trying to delete files }
  if CurUninstallStep = usUninstall then
  begin
    { Stop the tray app }
    KillProcess('BingWallpaperTray.exe');
    { Stop the main app if running }
    KillProcess('BingWallpaperDownloader.exe');
    { Give processes time to fully terminate }
    Sleep(500);
  end;
  
  if CurUninstallStep = usPostUninstall then
  begin
    { Remove scheduled task }
    Exec('schtasks.exe', '/Delete /TN "BingWallpaperDownloader" /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    
    { Remove startup shortcuts }
    DeleteFile(ExpandConstant('{userstartup}\{#MyAppName}.lnk'));
    DeleteFile(ExpandConstant('{userstartup}\{#MyAppName} Manager.lnk'));
    
    { Read download folder from config BEFORE potentially deleting it }
    WallpaperFolder := GetDownloadFolderFromConfig();
    
    { Ask user about deleting configuration file }
    DeleteConfig := MsgBox('Do you want to delete your configuration file?' + #13#10 + #13#10 +
                           'This contains your settings (download folder, market, resolution, etc.)' + #13#10 + #13#10 +
                           'Location: ' + ExpandConstant('{userappdata}\BingWallpaperDownloader'), 
                           mbConfirmation, MB_YESNO) = IDYES;
    
    { Ask user about deleting downloaded wallpapers }
    DeleteWallpapers := MsgBox('Do you want to delete all downloaded wallpapers?' + #13#10 + #13#10 +
                               'Location: ' + WallpaperFolder, 
                               mbConfirmation, MB_YESNO) = IDYES;
    
    { Delete config if requested }
    if DeleteConfig then
    begin
      DelTree(ExpandConstant('{userappdata}\BingWallpaperDownloader'), True, True, True);
    end;
    
    { Delete wallpapers if requested }
    if DeleteWallpapers then
    begin
      if DirExists(WallpaperFolder) then
      begin
        DelTree(WallpaperFolder, True, True, True);
      end;
    end;
    
    { Show info about kept data if any }
    if (not DeleteConfig) or (not DeleteWallpapers) then
    begin
      KeptItems := 'The following items have been kept:' + #13#10 + #13#10;
      
      if not DeleteConfig then
        KeptItems := KeptItems + '• Configuration: ' + ExpandConstant('{userappdata}\BingWallpaperDownloader') + #13#10;
      
      if not DeleteWallpapers then
        KeptItems := KeptItems + '• Wallpapers: ' + WallpaperFolder + #13#10;
      
      MsgBox(KeptItems, mbInformation, MB_OK);
    end;
  end;
end;
