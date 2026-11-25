# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
# Sets up WSL 2, installs GUI deps in Ubuntu when possible, and puts a
# "MUN Devkit" shortcut on your Desktop so you can open the app by double-click.
# Run from the repo root in elevated PowerShell:
#   powershell -ExecutionPolicy Bypass -File .\scripts\windows\Install-MdkGui.ps1
#
# Saved as UTF-8 with BOM so Windows PowerShell 5.1 parses non-ASCII text.

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Launcher = Join-Path $RepoRoot "MUN Devkit.bat"

Write-Host "MUN Devkit - Windows setup" -ForegroundColor Cyan
Write-Host "This installs a Desktop shortcut that opens the GUI app."
Write-Host "Builds still use WSL 2 + Docker under the hood (linux/arm64)."
Write-Host ""

$arch = (Get-CimInstance Win32_ComputerSystem).SystemType
Write-Host "This PC reports: $arch"
if ($arch -match "ARM") {
    Write-Host "ARM device detected (for example Snapdragon X Elite)."
    Write-Host "WSL 2 will be ARM64 - linux/arm64 containers run natively. Good."
} else {
    Write-Host "x86-64 device detected."
    Write-Host "Docker will emulate linux/arm64 (slower builds; same cards)."
}
Write-Host ""

$wsl = Get-Command wsl -ErrorAction SilentlyContinue
if (-not $wsl) {
    Write-Host "Installing WSL 2 (may reboot)..." -ForegroundColor Yellow
    wsl --install
    Write-Host "After reboot, re-run this script."
    exit 0
}

Write-Host "WSL is present. Distros:"
wsl --list --verbose
Write-Host ""

# Best-effort: install Python + Tk inside the default distro so the window can open.
Write-Host "Installing Python + Tk inside WSL (may ask for your Linux password)..." -ForegroundColor Yellow
try {
    wsl -e bash -lc "sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-tk git make"
} catch {
    Write-Host "Could not install packages automatically. You can run this later in Ubuntu:"
    Write-Host "  sudo apt update && sudo apt install -y python3 python3-tk git make"
}

# Desktop shortcut that double-clicks like a normal app.
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "MUN Devkit.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($ShortcutPath)
$shortcut.TargetPath = $Launcher
$shortcut.WorkingDirectory = $RepoRoot
$shortcut.WindowStyle = 1
$shortcut.Description = "Open the MUN Devkit GUI"
$shortcut.Save()
Write-Host ""
Write-Host "Created Desktop shortcut: $ShortcutPath" -ForegroundColor Green
Write-Host "Also double-clickable in the repo: $Launcher" -ForegroundColor Green
Write-Host ""
Write-Host "Still needed for building games (not just opening the window):"
Write-Host "  - Docker Desktop for Windows, with WSL integration enabled for Ubuntu"
Write-Host ""
Write-Host "Opening the GUI now..."
Start-Process -FilePath $Launcher
Write-Host ""
Write-Host "Docs: docs/gui.md"
