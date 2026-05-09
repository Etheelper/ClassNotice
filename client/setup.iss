#define MyAppName "ClassNotice 学生端"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "校园信息化项目组"
#define MyAppURL "http://localhost:5000"
#define MyAppExeName "ClassNoticeClient.exe"
#define MyAppCopyright "Copyright (C) 2026 校园信息化项目组"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-ClassNoticeCli}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppCopyright={#MyAppCopyright}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

DefaultDirName={autopf}\ClassNotice\Client
DefaultGroupName=ClassNotice 学生端
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

OutputDir=..\installer_output
OutputBaseFilename=ClassNoticeClient_Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes

WizardStyle=modern

PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

MinVersion=10.0
CloseApplications=force

DisableProgramGroupPage=yes
DisableWelcomePage=no

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Default.isl"

[Messages]
chinesesimplified.WelcomeLabel2=这将安装 {#MyAppName} {#MyAppVersion} 到您的计算机。%n%n首次运行将弹出配置向导，只需两步：%n  1. 输入服务器地址（如：192.168.1.100:5000）%n  2. 选择所在班级（1~26班）%n%n保存后自动后台运行，无需再次配置！

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: unchecked
Name: "autostart"; Description: "开机自动启动"; GroupDescription: "附加选项:"; Flags: checkedonce

[Files]
Source: "dist\ClassNoticeClient.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{userappdata}\ClassNotice"; Permissions: users-full

[Icons]
Name: "{group}\ClassNotice 学生端"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "启动 ClassNotice 学生端通知接收程序"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\ClassNotice 学生端"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "ClassNoticeClient"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即启动学生端（首次运行需配置）"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\ClassNotice"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if MsgBox('是否删除学生端配置数据？', mbConfirmation, MB_YESNO) = IDYES then
    begin
      DelTree(ExpandConstant('{userappdata}\ClassNotice'), True, True, True);
    end;
  end;
end;
