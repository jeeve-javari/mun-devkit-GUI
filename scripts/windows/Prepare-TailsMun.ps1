# Run from mun-devkit-GUI: prepares sibling tails-from-alteria for Devkit sim.
# The real prepare script lives in the game repo (tools/mun/Prepare-MunDevkit.ps1).
$ErrorActionPreference = "Stop"
$DevkitRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

$candidates = @(
  (Join-Path $DevkitRoot "..\tails-from-alteria"),
  (Join-Path $env:USERPROFILE "tails-from-alteria"),
  $env:TAILS_FROM_ALTERIA
) | Where-Object { $_ }

$GameRoot = $null
foreach ($c in $candidates) {
  $script = Join-Path $c "tools\mun\Prepare-MunDevkit.ps1"
  if (Test-Path $script) {
    $GameRoot = (Resolve-Path $c).Path
    break
  }
}

if (-not $GameRoot) {
  Write-Host @"
Could not find tails-from-alteria next to this Devkit.

Clone or put the game repo here:
  $(Join-Path (Split-Path $DevkitRoot -Parent) 'tails-from-alteria')

Then either:
  cd that folder
  .\tools\mun\Prepare-MunDevkit.ps1

Or set `$env:TAILS_FROM_ALTERIA = 'C:\full\path\to\tails-from-alteria'` and re-run this script.
"@
  exit 1
}

Write-Host "Using game repo: $GameRoot"
& (Join-Path $GameRoot "tools\mun\Prepare-MunDevkit.ps1")
