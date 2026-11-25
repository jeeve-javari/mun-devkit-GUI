# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
# Sets up WSL 2 + hints for Docker so the full MUN Devkit GUI can run on
# Windows (Snapdragon X Elite / ARM64, or x86-64). Run in an elevated
# PowerShell from the repo root:
#   powershell -ExecutionPolicy Bypass -File .\scripts\windows\Install-MdkGui.ps1
#
# Saved as UTF-8 with BOM so Windows PowerShell 5.1 parses non-ASCII text.

$ErrorActionPreference = "Stop"

Write-Host "MUN Devkit - Windows setup" -ForegroundColor Cyan
Write-Host "The console build targets linux/arm64. On Windows the supported path is WSL 2 + Docker."
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
    Write-Host "After reboot, re-run this script, then install Docker Desktop and enable WSL integration."
    exit 0
}

Write-Host "WSL is present. Distros:"
wsl --list --verbose
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Install Docker Desktop for Windows and turn on WSL integration for your distro."
Write-Host "  2. In WSL: sudo apt update && sudo apt install -y python3 python3-tk git make"
Write-Host "  3. Clone or open this repository inside WSL (under your Linux home, not only /mnt/c)."
Write-Host "  4. Run:  ./mdk-gui     or double-click scripts/windows/Launch-MdkGui.bat"
Write-Host "  5. In the GUI: Setup -> Check this computer -> Fetch MUN OS tools -> Build SDK environment"
Write-Host ""
Write-Host "Docs: docs/gui.md"
