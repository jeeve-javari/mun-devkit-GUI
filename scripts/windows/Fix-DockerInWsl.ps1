# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
# Finds Docker Desktop (Program Files OR per-user LocalAppData install),
# reminds you to enable Ubuntu WSL integration, restarts WSL, and checks
# that docker works inside Ubuntu.
#
# Run from PowerShell (NOT from the Ubuntu terminal):
#   powershell -ExecutionPolicy Bypass -File .\scripts\windows\Fix-DockerInWsl.ps1

$ErrorActionPreference = "Continue"

Write-Host "MUN Devkit - find Docker and connect it to WSL" -ForegroundColor Cyan
Write-Host ""

$candidates = @(
    "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe",
    "$env:LOCALAPPDATA\Programs\Docker\Docker\Docker Desktop.exe",
    "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
    "${env:ProgramFiles(x86)}\Docker\Docker\Docker Desktop.exe"
)

$dockerExe = $null
foreach ($path in $candidates) {
    if ($path -and (Test-Path -LiteralPath $path)) {
        $dockerExe = $path
        break
    }
}

if (-not $dockerExe) {
    $searchRoots = @(
        "$env:LOCALAPPDATA\Programs",
        "$env:ProgramFiles",
        "${env:ProgramFiles(x86)}"
    ) | Where-Object { $_ -and (Test-Path $_) }
    foreach ($root in $searchRoots) {
        $hit = Get-ChildItem -LiteralPath $root -Filter "Docker Desktop.exe" -Recurse -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($hit) {
            $dockerExe = $hit.FullName
            break
        }
    }
}

if ($dockerExe) {
    Write-Host "Found Docker Desktop at:" -ForegroundColor Green
    Write-Host "  $dockerExe"
    Write-Host "Starting it..."
    Start-Process -FilePath $dockerExe
} else {
    Write-Host "Docker Desktop.exe was NOT found on this PC." -ForegroundColor Yellow
    Write-Host "Searched Program Files and %LOCALAPPDATA%\Programs (per-user install)."
    Write-Host ""
    Write-Host "On Snapdragon / Windows ARM, install the ARM build:"
    Write-Host "  https://docs.docker.com/desktop/setup/install/windows-install/"
    Write-Host "  (use Docker Desktop for Windows - Arm / Early Access)"
    Write-Host ""
    Write-Host "If you already installed something else named Docker, it may not be Docker Desktop."
}

$binDirs = @(
    "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin",
    "$env:LOCALAPPDATA\Programs\Docker\Docker\resources\bin",
    "$env:ProgramFiles\Docker\Docker\resources\bin"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

Write-Host ""
Write-Host "Docker CLI folders found:"
if ($binDirs.Count -eq 0) {
    Write-Host "  (none)"
} else {
    $binDirs | ForEach-Object { Write-Host "  $_" }
}

Write-Host ""
Write-Host "In Docker Desktop:"
Write-Host "  Settings -> Resources -> WSL integration"
Write-Host "  - Enable integration with my default WSL distro: ON"
Write-Host "  - Scroll down and enable the switch next to Ubuntu (by name): ON"
Write-Host "  - Apply and Restart, wait for Engine running"
Write-Host ""
Write-Host "Press Enter when Engine is running (or to continue anyway)..."
[void][System.Console]::ReadLine()

Write-Host "Shutting down WSL so it reloads Docker integration..."
wsl --shutdown
Start-Sleep -Seconds 3

$pathParts = New-Object System.Collections.Generic.List[string]
foreach ($dir in $binDirs) {
    if ($dir -match '^[A-Za-z]:\\') {
        $drive = $dir.Substring(0, 1).ToLower()
        $rest = $dir.Substring(3).Replace('\', '/')
        [void]$pathParts.Add("/mnt/$drive/$rest")
    }
}
[void]$pathParts.Add("/mnt/c/Program Files/Docker/Docker/resources/bin")
[void]$pathParts.Add("/mnt/c/Users/$env:USERNAME/AppData/Local/Programs/DockerDesktop/resources/bin")
$wslPath = ($pathParts | Select-Object -Unique) -join ':'

Write-Host "Checking docker inside Ubuntu..."
Write-Host "(This must be run from PowerShell. Inside Ubuntu type only: docker version)"
Write-Host ""

$bash = @"
export PATH='$wslPath':"`$PATH"
echo "Looking for docker:"
command -v docker || true
command -v docker.exe || true
echo "Per-user DockerDesktop folder:"
ls -la "/mnt/c/Users/$env:USERNAME/AppData/Local/Programs/DockerDesktop" 2>/dev/null | head -n 20 || echo "(missing)"
echo "Program Files Docker folder:"
ls -la "/mnt/c/Program Files/Docker/Docker" 2>/dev/null | head -n 20 || echo "(missing)"
echo ""
echo "docker version:"
docker version 2>&1 | head -n 50 || docker.exe version 2>&1 | head -n 50 || echo "docker still not found inside WSL"
"@

wsl -e bash -lc $bash

Write-Host ""
Write-Host "Next:"
Write-Host "  - If you saw Client/Server versions: reopen MUN Devkit and press Check again."
Write-Host "  - If Docker Desktop.exe was missing: install the ARM Docker Desktop build, then re-run this script."
Write-Host "  - Inside Ubuntu test with:  docker version"
Write-Host "    Do NOT type wsl -e ... inside Ubuntu."
