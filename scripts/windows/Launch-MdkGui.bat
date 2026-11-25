@echo off
REM Copyright 2026 Iván Moreno Mendoza
REM SPDX-License-Identifier: Apache-2.0
REM Opens the MUN Devkit GUI window via WSL (WSLg on Windows 11).
setlocal EnableExtensions
title MUN Devkit
set "REPO=%~dp0..\.."
for %%I in ("%REPO%") do set "REPO=%%~fI"

echo.
echo  MUN Devkit
echo  Starting the GUI window...
echo.

where wsl >nul 2>&1
if errorlevel 1 (
  echo WSL is not installed.
  echo Run:  powershell -ExecutionPolicy Bypass -File "%~dp0Install-MdkGui.ps1"
  echo.
  pause
  exit /b 1
)

REM Start Ubuntu if it was Stopped, install Tk if needed, then open the GUI.
wsl -e bash -lc "set -e; cd \"$(wslpath -a '%REPO%')\"; if ! python3 -c 'import tkinter' 2>/dev/null; then echo 'Installing Python Tk in WSL (one-time)...'; sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-tk git make; fi; chmod +x mdk-gui mdk 2>/dev/null || true; exec ./mdk-gui"
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo.
  echo The GUI did not stay open (exit %ERR%).
  echo Tips:
  echo   - Use Windows 11 so WSLg can show Linux windows
  echo   - In Ubuntu:  sudo apt install -y python3-tk
  echo   - Prefer keeping the repo under \\wsl$\Ubuntu\home\...
  echo.
  pause
)
endlocal
