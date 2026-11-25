# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
# Helps Docker Desktop become visible inside WSL for MUN Devkit.
# Run in PowerShell (Admin optional):
#   powershell -ExecutionPolicy Bypass -File .\scripts\windows\Fix-DockerInWsl.ps1
#
# UTF-8 with BOM for Windows PowerShell 5.1.

$ErrorActionPreference = "Continue"

Write-Host "MUN Devkit - fix Docker visibility in WSL" -ForegroundColor Cyan
Write-Host ""

$dockerExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (Test-Path $dockerExe) {
    Write-Host "Found Docker Desktop. Starting it..."
    Start-Process $dockerExe
} else {
    Write-Host "Docker Desktop.exe not found at:"
    Write-Host "  $dockerExe"
    Write-Host "Install Docker Desktop first, then re-run this script."
}

Write-Host ""
Write-Host "In Docker Desktop:"
Write-Host "  Settings -> Resources -> WSL integration"
Write-Host "  - Enable integration with my default WSL distro: ON"
Write-Host "  - Scroll down and enable the switch for Ubuntu (by name): ON"
Write-Host "  - Apply and Restart"
Write-Host ""
Write-Host "Press Enter after Docker says Engine running..."
[void][System.Console]::ReadLine()

Write-Host "Shutting down WSL so it reloads Docker integration..."
wsl --shutdown
Start-Sleep -Seconds 2

Write-Host "Checking docker inside WSL:"
wsl -e bash -lc "export PATH=\"/mnt/c/Program Files/Docker/Docker/resources/bin:\$PATH\"; command -v docker; docker version 2>&1 | head -n 40"
Write-Host ""
Write-Host "If that printed a Client/Server version, reopen MUN Devkit and press Check again."
Write-Host "If it failed, the Ubuntu toggle in WSL integration is usually still off."
