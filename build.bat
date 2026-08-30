@echo off
chcp 65001 >nul
title Accounting - Build

echo.
echo  ==================================================
echo   Oil Shop Accounting  -  Builder
echo  ==================================================
echo.

echo  [1/4] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto fail

echo.
echo  [2/4] Drawing the icon ...
python make_icons.py
if errorlevel 1 goto fail

echo.
echo  [3/4] Building OilShopAccounting.exe ...
pyinstaller --noconfirm --onefile --windowed ^
    --name "OilShopAccounting" --icon "shop.ico" golden_shop.py
if errorlevel 1 goto fail

rmdir /s /q build 2>nul
del /q *.spec 2>nul

echo.
echo  [4/4] Building the installer ...
set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not exist "%ISCC%" (
    echo.
    echo  Inno Setup was not found - skipping the installer.
    echo  Install it with:  winget install JRSoftware.InnoSetup
    echo.
    echo  The portable EXE was still built:
    echo     dist\OilShopAccounting.exe
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
echo     dist\OilShopAccounting.exe          (portable)
echo  ==================================================
echo.
pause
exit /b 0

:fail
echo.
echo  BUILD FAILED. Make sure Python 3.10+ is installed
echo  and "Add Python to PATH" was checked during setup.
echo.
pause
exit /b 1
