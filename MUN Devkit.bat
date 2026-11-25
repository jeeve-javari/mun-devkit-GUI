@echo off
REM Copyright 2026 Iván Moreno Mendoza
REM SPDX-License-Identifier: Apache-2.0
REM Double-click this file to open the MUN Devkit GUI on Windows.
setlocal EnableExtensions
set "LAUNCHER=%~dp0scripts\windows\Launch-MdkGui.bat"
if not exist "%LAUNCHER%" (
  echo Could not find:
  echo   %LAUNCHER%
  echo Make sure you are in the mun-devkit-GUI folder and run: git pull
  echo.
  pause
  exit /b 1
)
call "%LAUNCHER%"
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo.
  pause
)
exit /b %ERR%
