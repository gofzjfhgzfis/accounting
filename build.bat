@echo off
chcp 65001 >nul
title Accounting - Build

echo.
echo  ==================================================
echo   EXE Builder  (Shop + Factory)
echo  ==================================================
echo.

echo  [1/3] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto fail

echo.
echo  [2/5] Drawing the icons ...
python make_icons.py
if errorlevel 1 goto fail

echo.
echo  [3/5] Building OilShopAccounting.exe ...
pyinstaller --noconfirm --onefile --windowed ^
    --name "OilShopAccounting" --icon "shop.ico" golden_shop.py
if errorlevel 1 goto fail

echo.
echo  [4/5] Building FactoryAccounting.exe ...
pyinstaller --noconfirm --onefile --windowed ^
    --name "FactoryAccounting" --icon "factory.ico" golden_factory.py
if errorlevel 1 goto fail

rmdir /s /q build 2>nul
del /q *.spec 2>nul

echo.
echo  [5/5] Building the installers ...
set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not exist "%ISCC%" (
    echo.
    echo  Inno Setup was not found - skipping the installers.
    echo  Install it with:  winget install JRSoftware.InnoSetup
    echo.
    echo  The portable EXEs were still built:
    echo     dist\OilShopAccounting.exe
    echo     dist\FactoryAccounting.exe
    echo.
    pause
    exit /b 0
)

"%ISCC%" installer_shop.iss
if errorlevel 1 goto fail
"%ISCC%" installer_factory.iss
if errorlevel 1 goto fail

echo.
echo  ==================================================
echo   DONE.
echo     dist\OilShopAccounting-Setup.exe    (installer)
echo     dist\FactoryAccounting-Setup.exe    (installer)
echo     dist\OilShopAccounting.exe          (portable)
echo     dist\FactoryAccounting.exe          (portable)
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
