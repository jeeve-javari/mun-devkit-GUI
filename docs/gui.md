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
| Project | Pick an **engine lane**, create a project, then build / check / pack | `mdk new` / sample copy; `build`, `check`, `pack` |
| Engines | Honest map of every lane (ready / partial / planned) | — |
| Simulate | **Play in MUN OS** (copy packed `.img` → `mun play --card`); or SDK container session | `mun play --card …` / `mdk sim --container …` |

**Play in MUN OS** needs a mun-os checkout (the folder where you run `py mun play`). Set that path once on the Simulate tab; it is remembered with the other GUI settings. **Pack then Play** packs the project card and opens QEMU in one step.

### Engine lanes (for everyone)

A MUN game is always an **AArch64 Linux** program on a Game Card. The GUI
does not pretend every engine exports today — it names the path:

| Lane | Status | Create project |
| --- | --- | --- |
| Native (C / SDL2) | Ready | `mdk new` (hello-mun) |
| Godot 3.5 + FRT | Ready | copies `samples/hello-mun-godot3` |
| Godot 3.6+ | Partial | guide only — use the 3.5 lane and match your build |
| Godot 4.7 | Partial | copies `samples/hello-mun-godot` (console export not ready) |
| Unity | Planned | guide — need arm64 player + profile work |
| Unreal | Planned | guide — likely needs Vulkan profile later |
| Bring your own binary | Ready | scaffolds the native card shell; replace the entry ELF |

Hardware that “supports Unity / Unreal” is necessary but not sufficient:
MUN still needs a runtime profile, card rules (entry ≤ 64 MiB, `content/`
noexec), and Devkit packaging. Until those land, those rows stay **Planned**
and point at [port a game](https://github.com/Play-MUN/mun-os/blob/main/docs/guides/port-a-game.md).

The full package is still this repository: the C client, contracts, samples,
Godot adapters, tests and `mdk` itself. Lane logic lives in
`tools/gui/engines.py` so new engines are data, not a one-off UI fork.

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
follow the same journey as the README. The Project folder (and the “new
project” fields) are remembered in `~/.config/mun-devkit/gui-state.json`
when you close the window.


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
