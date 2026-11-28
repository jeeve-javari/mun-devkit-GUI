@echo off
REM Copyright 2026 Iván Moreno Mendoza
REM SPDX-License-Identifier: Apache-2.0
REM Opens the MUN Devkit GUI window via WSL (WSLg on Windows 11).
setlocal EnableExtensions
title MUN Devkit
set "REPO=%~dp0..\.."
for %%I in ("%REPO%") do set "REPO=%%~fI"
set "LOG=%TEMP%\mun-devkit-launch.log"

echo.
echo  MUN Devkit
echo  Starting the GUI window...
echo  If this closes instantly, re-open from a PowerShell window so you can read the error:
echo    cd /d "%REPO%"
echo    .\scripts\windows\Launch-MdkGui.bat
echo.

where wsl >nul 2>&1
if errorlevel 1 (
  echo WSL is not installed.
  echo Run:  powershell -ExecutionPolicy Bypass -File "%~dp0Install-MdkGui.ps1"
  echo.
  pause
  exit /b 1
)

if not exist "%REPO%\mdk-gui" (
  echo Could not find mdk-gui in:
  echo   %REPO%
  echo Pull the latest repo, or run Install-MdkGui.ps1 from the mun-devkit-GUI folder.
  echo.
  pause
  exit /b 1
)

if not exist "%REPO%\scripts\windows\launch-mdk-gui-wsl.sh" (
  echo Missing launch-mdk-gui-wsl.sh. Run: git pull
  echo.
  pause
  exit /b 1
)

REM Resolve the Windows path once; avoid a fragile one-line bash -lc string.
set "REPO_WSL="
for /f "usebackq delims=" %%i in (`wsl wslpath -a "%REPO%" 2^>nul`) do set "REPO_WSL=%%i"
if not defined REPO_WSL (
  echo Could not map this folder into WSL:
  echo   %REPO%
  echo Open Ubuntu and check that WSL starts, then try again.
  echo.
  pause
  exit /b 1
)

echo  WSL path: %REPO_WSL%
echo  Log file: %LOG%
echo.

wsl -e bash "%REPO_WSL%/scripts/windows/launch-mdk-gui-wsl.sh"
set "ERR=%ERRORLEVEL%"

if not "%ERR%"=="0" (
  echo.
  echo The GUI did not stay open ^(exit %ERR%^).
  echo.
  echo Full log:
  if exist "%LOG%" (
    type "%LOG%"
  ) else (
    echo   ^(no log written yet — WSL may have failed before the script started^)
  )
  echo.
  echo Tips:
  echo   1. Open Ubuntu and run:  sudo apt update ^&^& sudo apt install -y python3 python3-tk
  echo   2. In PowerShell:  wsl --update
  echo   3. Then run this launcher again from PowerShell ^(so the window stays open^).
  echo.
  pause
  exit /b %ERR%
)
endlocal
