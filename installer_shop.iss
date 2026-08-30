; دامەزرێنەری سیستەمی دووکانی جوملە
; بە Inno Setup درووست دەکرێت — بڕوانە build.bat

#define AppName    "Oil Shop Accounting"
#define AppNameKu  "سیستەمی دووکانی جوملە"
#define AppVersion "1.0"
#define AppExe     "OilShopAccounting.exe"

[Setup]
AppId={{8F3A1C24-6B71-4E85-9D2A-51C0E7A4B310}
AppName={#AppNameKu}
AppVersion={#AppVersion}
AppVerName={#AppNameKu} {#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppNameKu}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=OilShopAccounting-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=shop.ico
UninstallDisplayName={#AppNameKu}
UninstallDisplayIcon={app}\{#AppExe}

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"

[Messages]
en.WelcomeLabel1=بەخێربێیت بۆ دامەزراندنی [name]
en.WelcomeLabel2=ئەم بەرنامەیە سیستەمی حیساباتی دووکانی جوملەیە.%n%nپێش بەردەوامبوون باشترە هەموو بەرنامەکانی تر دابخەیت.
en.SelectDirLabel3=بەرنامەکە لەم فۆڵدەرەدا دادەمەزرێت.
en.ReadyLabel1=ئێستا ئامادەیە بۆ دامەزراندن.
en.FinishedHeadingLabel=دامەزراندن تەواو بوو
en.FinishedLabelNoIcons=[name] بە سەرکەوتوویی دامەزرا.
en.FinishedLabel=[name] بە سەرکەوتوویی دامەزرا.
en.RunEntryExec=کردنەوەی [name]

[Tasks]
Name: "desktopicon"; Description: "شۆرتکەت لەسەر دێسکتۆپ درووست بکە"; GroupDescription: "شۆرتکەتەکان:"

[Files]
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppNameKu}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppNameKu}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "کردنەوەی بەرنامەکە"; Flags: nowait postinstall skipifsilent
