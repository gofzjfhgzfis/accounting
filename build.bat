@echo off
chcp 65001 >nul
title Accounting - Build

echo.
echo  ==================================================
echo   Oil Shop Accounting  -  Builder (Flutter)
echo  ==================================================
echo.

set "FLUTTER=flutter"
where flutter >nul 2>nul || set "FLUTTER=%USERPROFILE%\flutter\bin\flutter.bat"

echo  [1/3] Getting packages...
call "%FLUTTER%" pub get
if errorlevel 1 goto fail

echo.
echo  [2/3] Building OilShopAccounting.exe ...
call "%FLUTTER%" build windows --release
if errorlevel 1 goto fail

echo.
echo  [3/3] Building the installer ...
set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not exist "%ISCC%" (
    echo.
    echo  Inno Setup was not found - skipping the installer.
    echo  Install it with:  winget install JRSoftware.InnoSetup
    echo.
    echo  The app was still built in:
    echo     build\windows\x64\runner\Release\
    echo.
    pause
    exit /b 0
)

"%ISCC%" installer_shop.iss
if errorlevel 1 goto fail

echo.
echo  ==================================================
echo   DONE.
echo     dist\OilShopAccounting-Setup.exe    (installer)
echo  ==================================================
echo.
pause
exit /b 0

:fail
echo.
echo  BUILD FAILED. Make sure Flutter is installed (flutter doctor),
echo  Visual Studio has "Desktop development with C++",
echo  and Windows Developer Mode is on.
echo.
pause
exit /b 1
