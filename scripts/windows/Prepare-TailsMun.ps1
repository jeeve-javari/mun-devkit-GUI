# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
# Run from mun-devkit-GUI: prepares sibling tails-from-alteria for Devkit sim.
# Prefer Prepare-TailsMun.bat (bypasses execution policy).
$ErrorActionPreference = "Stop"
$DevkitRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Sibling = Join-Path (Split-Path $DevkitRoot -Parent) "tails-from-alteria"

$candidates = @(
  $Sibling,
  (Join-Path $env:USERPROFILE "tails-from-alteria"),
  $env:TAILS_FROM_ALTERIA
) | Where-Object { $_ }

$GameRoot = $null
foreach ($c in $candidates) {
  if (-not $c) { continue }
  $script = Join-Path $c "tools\mun\Prepare-MunDevkit.ps1"
  if (Test-Path $script) {
    $GameRoot = (Resolve-Path $c).Path
    break
  }
}

if (-not $GameRoot) {
  Write-Host "tails-from-alteria is not on this PC yet."
  Write-Host "Will clone into: $Sibling"
  Write-Host ""
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git is not on PATH. Install Git for Windows, then re-run."
  }
  New-Item -ItemType Directory -Force -Path (Split-Path $Sibling -Parent) | Out-Null
  git clone https://github.com/jeeve-javari/tails-from-alteria.git $Sibling
  if ($LASTEXITCODE -ne 0) { throw "git clone failed" }
  $GameRoot = (Resolve-Path $Sibling).Path
}

# Always pull so Windows picks up quoting fixes without a manual cd.
if (Get-Command git -ErrorAction SilentlyContinue) {
  Write-Host "Updating game repo..."
  git -C $GameRoot pull --ff-only
}

$Prepare = Join-Path $GameRoot "tools\mun\Prepare-MunDevkit.ps1"
if (-not (Test-Path $Prepare)) {
  throw "Game repo is missing Prepare-MunDevkit.ps1 - pull latest main in tails-from-alteria."
}

Write-Host "Using game repo: $GameRoot"
# Fresh powershell.exe parse (do not dot-source).
$p = Start-Process -FilePath "powershell.exe" -ArgumentList @(
  "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $Prepare
) -Wait -PassThru -NoNewWindow
if ($p.ExitCode -ne 0) {
  exit $p.ExitCode
}
