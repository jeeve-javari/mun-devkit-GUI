@echo off
REM Copyright 2026 Iván Moreno Mendoza
REM SPDX-License-Identifier: Apache-2.0
REM Launch the MUN Devkit GUI inside the default WSL distro (WSLg on Windows 11).
setlocal
set "REPO=%~dp0..\.."
for %%I in ("%REPO%") do set "REPO=%%~fI"
where wsl >nul 2>&1
if errorlevel 1 (
  echo WSL is not installed. Run scripts\windows\Install-MdkGui.ps1 first.
  pause
  exit /b 1
)
REM Convert the Windows path to a WSL path and start the GUI.
wsl -e bash -lc "cd \"$(wslpath '%REPO%')\" && chmod +x mdk-gui mdk 2>/dev/null; ./mdk-gui"
if errorlevel 1 (
  echo.
  echo If the window did not open: install python3-tk in WSL, and use Windows 11 WSLg or an X server.
  pause
)
endlocal
