# Friendly GUI

**English** · [Español](gui.es.md)

A desktop front-end for the same host tool the README describes. Every button
runs `mdk` with the same arguments you would type; the log pane shows the
same output. Nothing here replaces the CLI — it wraps it.

```sh
./mdk-gui
# or
./mdk gui
```

Needs a display (a normal desktop session, or Windows 11 WSLg). Python 3.9+
with Tk (`python3-tk` on Debian/Ubuntu).

## What it can do

| Tab | Actions | Same as |
| --- | --- | --- |
| Setup | Check this computer, fetch MUN OS tools, build the SDK environment | `mdk doctor`, `mdk os fetch`, `mdk env build` |
| Project | New project from the sample; build, check, pack | `mdk new`, `build`, `check`, `pack` |
| Simulate | Session with container / fresh card / hello-mun script | `mdk sim --container …` |

The full package is still this repository: the C client, contracts, samples,
Godot adapter, tests and `mdk` itself. The GUI does not ship a smaller SDK.

## Windows (Snapdragon X Elite / ARM, and x86)

Native Windows is not a MUN build host yet: a console game is an AArch64
Linux program, and `mdk build` / `mdk sim --container` need a container
runtime that runs `linux/arm64`. On Windows that path is **WSL 2 + Docker
Desktop**.

| Your PC | What happens |
| --- | --- |
| Windows on ARM (Snapdragon X Elite and similar) | WSL 2 is ARM64; `linux/arm64` containers run natively — the same happy path as Linux ARM64 / Apple Silicon |
| Windows x86-64 | Docker emulates `linux/arm64` (slower); cards and checks are the same |

1. In elevated PowerShell, from the repo folder:
   `powershell -ExecutionPolicy Bypass -File .\scripts\windows\Install-MdkGui.ps1`
   That installs Tk in WSL when it can, puts **MUN Devkit** on your Desktop,
   and tries to open the window.
2. Or double-click **`MUN Devkit.bat`** in the repo root (same launcher).
3. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and
   enable WSL integration when you want to build / pack / simulate for the console.

Then in the window use **Setup** until doctor is green, open **Project**, and
follow the same journey as the README.

If the black console flashes and closes: run the launcher from PowerShell so the
error stays on screen (`.\scripts\windows\Launch-MdkGui.bat`). A copy of the
log is also written to `%TEMP%\mun-devkit-launch.log`. Most often Tk is missing
(`sudo apt install -y python3-tk` in Ubuntu) or WSLg needs `wsl --update`.

## Downloadable release

A GitHub Release can attach a zip of this tree (source + GUI entry points +
Windows helpers). Unzip, run the Windows script or `./mdk-gui` on macOS /
Linux, and complete Setup once. Building still needs Docker (and on Windows,
WSL), as above — the GUI cannot invent a console toolchain the host lacks.

## macOS and Linux

Same binary journey as the CLI. On Apple Silicon and Linux ARM64, containers
are native. On Linux x86-64, Docker uses emulation for `linux/arm64` (see the
README status table).
