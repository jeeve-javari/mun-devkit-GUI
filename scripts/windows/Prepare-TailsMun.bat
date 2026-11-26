@echo off
REM Copyright 2026 Iván Moreno Mendoza
REM SPDX-License-Identifier: Apache-2.0
REM Bypass PowerShell execution policy and prepare sibling tails-from-alteria.
setlocal EnableExtensions
set "REPO=%~dp0..\.."
for %%I in ("%REPO%") do set "REPO=%%~fI"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%REPO%\scripts\windows\Prepare-TailsMun.ps1" %*
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo.
  pause
  exit /b %ERR%
)
endlocal
