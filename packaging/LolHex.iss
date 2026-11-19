; DD HEX 海克斯助手安装包。先运行 packaging/build.ps1（它会调用本脚本）。
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{0763032E-8343-4ADC-8A9F-F1625DFA68B7}
AppName=DD HEX 海克斯助手
AppVersion={#AppVersion}
AppPublisher=DD HEX independent project
DefaultDirName={localappdata}\Programs\DD HEX
DefaultGroupName=DD HEX 海克斯助手
; 装到用户目录，不需要管理员权限；始终"只为当前用户安装"（卸载信息写在 HKCU），在线更新才能改「应用」列表里的版本号
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force
OutputDir=..\build\installer
OutputBaseFilename=DDHEX-Setup-{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=DD HEX 海克斯助手
UninstallDisplayIcon={app}\DD HEX.exe
SetupIconFile=lolhex.ico
LicenseFile=..\LICENSE

[Languages]
Name: "chs"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："

[Files]
Source: "..\build\dist\DD HEX\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; 升级时先清掉旧的程序文件（onedir 目录合并安装，否则旧版本多出来的文件会留下）
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{group}\DD HEX 海克斯助手"; Filename: "{app}\DD HEX.exe"
Name: "{group}\卸载DD HEX 海克斯助手"; Filename: "{uninstallexe}"
Name: "{userdesktop}\DD HEX 海克斯助手"; Filename: "{app}\DD HEX.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\DD HEX.exe"; Description: "立即启动"; Flags: nowait postinstall skipifsilent
; 助手里点「立即更新」走的是 /SILENT：装完自动重新打开
Filename: "{app}\DD HEX.exe"; Flags: nowait; Check: WizardSilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/c taskkill /im ""DD HEX.exe"" /f"; Flags: runhidden; RunOnceId: "KillDD HEX"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    { Only a completed full installation can retire an incomplete rollback. }
    DeleteFile(ExpandConstant('{app}\update-rollback-incomplete.txt'));
    DeleteFile(ExpandConstant('{app}\update-failed.txt'));
    DelTree(ExpandConstant('{app}\_update_old'), True, True, True);
    DelTree(ExpandConstant('{app}\_update_new'), True, True, True);
  end;
end;
