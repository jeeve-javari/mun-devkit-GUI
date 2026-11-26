# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
# Run from mun-devkit-GUI: prepares the Tails Godot project for Devkit sim.
# Prefer Prepare-TailsMun.bat (bypasses execution policy).
$ErrorActionPreference = "Stop"
$DevkitRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Sibling = Join-Path (Split-Path $DevkitRoot -Parent) "tails-from-alteria"
$GodotProject = "C:\Godot Game Development\Projects\Tails From Alteria GD 3.5"

function Find-WiringSource {
  foreach ($c in @($Sibling, (Join-Path $env:USERPROFILE "tails-from-alteria"))) {
    if ($c -and (Test-Path (Join-Path $c "tools\mun\Sync-MunWiring.ps1"))) {
      return (Resolve-Path $c).Path
    }
  }
  return $null
}

# Prefer the real Godot project (full game assets), then github clone.
$GameRoot = $null
foreach ($c in @($env:TAILS_FROM_ALTERIA, $GodotProject, $Sibling, (Join-Path $env:USERPROFILE "tails-from-alteria"))) {
  if (-not $c) { continue }
  if (Test-Path (Join-Path $c "project.godot")) {
    $GameRoot = (Resolve-Path $c).Path
    break
  }
}

if (-not $GameRoot) {
  Write-Host "No project.godot found. Cloning github repo to $Sibling ..."
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git is not on PATH"
  }
  git clone https://github.com/jeeve-javari/tails-from-alteria.git $Sibling
  $GameRoot = (Resolve-Path $Sibling).Path
}

$Prepare = Join-Path $GameRoot "tools\mun\Prepare-MunDevkit.ps1"
if (-not (Test-Path $Prepare)) {
  $WiringSource = Find-WiringSource
  if (-not $WiringSource) {
    Write-Host "Cloning tails-from-alteria for MUN wiring files..."
    if (-not (Test-Path $Sibling)) {
      git clone https://github.com/jeeve-javari/tails-from-alteria.git $Sibling
    } else {
      git -C $Sibling fetch origin
      git -C $Sibling checkout main
      git -C $Sibling pull --ff-only origin main
    }
    $WiringSource = (Resolve-Path $Sibling).Path
  }
  Write-Host "Syncing MUN wiring into: $GameRoot"
  $sync = Join-Path $WiringSource "tools\mun\Sync-MunWiring.ps1"
  # Call operator keeps paths-with-spaces as one argument (Start-Process does not).
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $sync -Target $GameRoot
  if ($LASTEXITCODE -ne 0) { throw "Sync-MunWiring failed" }
}

$Prepare = Join-Path $GameRoot "tools\mun\Prepare-MunDevkit.ps1"
if (-not (Test-Path $Prepare)) {
  throw "Still missing Prepare-MunDevkit.ps1 under $GameRoot"
}

# Always tell the game prepare script where THIS Devkit checkout is
# (game project is often not a sibling of mun-devkit-GUI).
$env:MUN_DEVKIT = $DevkitRoot

# Refresh prepare script from github clone when available
$WiringSource = Find-WiringSource
if ($WiringSource) {
  $fresh = Join-Path $WiringSource "tools\mun\Prepare-MunDevkit.ps1"
  if (Test-Path $fresh) {
    Copy-Item -Force $fresh $Prepare
  }
}

Write-Host "Using game project: $GameRoot"
Write-Host "MUN_DEVKIT:         $env:MUN_DEVKIT"
Write-Host "Running: $Prepare"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Prepare
exit $LASTEXITCODE
