#define MyAppName "ClassNotice 教师端"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "校园信息化项目组"
#define MyAppURL "http://localhost:5000"
#define MyAppExeName "ClassNoticeTeacher.exe"
#define MyAppCopyright "Copyright (C) 2026 校园信息化项目组"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-ClassNoticeTeacher}
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

DefaultDirName={autopf}\ClassNotice\Teacher
DefaultGroupName=ClassNotice 教师端
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

OutputDir=..\installer_output
OutputBaseFilename=ClassNoticeTeacher_Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
LZMANumBlockThreads=4

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
chinesesimplified.WelcomeLabel2=这将安装 {#MyAppName} {#MyAppVersion} 到您的计算机。%n%n教师端功能：%n  - 发送课堂通知到指定班级%n  - 配置课程表（智能延迟发送）%n  - 查看学生已读状态%n  - 管理课后消息发送时间%n%n首次运行需使用班主任账号登录。

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: unchecked
Name: "autostart"; Description: "开机自动启动"; GroupDescription: "附加选项:"; Flags: unchecked

[Files]
Source: "dist\ClassNoticeTeacher.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{userappdata}\ClassNoticeTeacher"; Permissions: users-full

[Icons]
Name: "{group}\ClassNotice 教师端"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "启动 ClassNotice 教师端通知发送程序"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\ClassNotice 教师端"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "ClassNoticeTeacher"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即启动教师端（首次运行需登录）"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\ClassNoticeTeacher"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if MsgBox('是否删除教师端配置数据？', mbConfirmation, MB_YESNO) = IDYES then
    begin
      DelTree(ExpandConstant('{userappdata}\ClassNoticeTeacher'), True, True, True);
    end;
  end;
end;
