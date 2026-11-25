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

REM Include all-users and per-user Docker Desktop CLI paths inside WSL.
wsl -e bash -lc "set -e; cd \"$(wslpath -a '%REPO%')\"; WINUSER=\"$(cmd.exe /c echo %USERNAME% 2>/dev/null | tr -d '\r')\"; export PATH=\"/mnt/c/Program Files/Docker/Docker/resources/bin:/mnt/c/Users/${WINUSER}/AppData/Local/Programs/DockerDesktop/resources/bin:/mnt/c/Users/${WINUSER}/AppData/Local/Programs/Docker/Docker/resources/bin:$PATH\"; if ! python3 -c 'import tkinter' 2>/dev/null; then echo 'Installing Python Tk in WSL (one-time)...'; sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-tk git make; fi; chmod +x mdk-gui mdk 2>/dev/null || true; exec ./mdk-gui"
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo.
  echo The GUI did not stay open (exit %ERR%).
  echo Tips:
  echo   - Run scripts\windows\Fix-DockerInWsl.ps1 from PowerShell
  echo   - Docker Desktop for ARM: docs.docker.com desktop windows-install
  echo   - Inside Ubuntu test with: docker version   (not wsl -e ...)
  echo.
  pause
)
endlocal
