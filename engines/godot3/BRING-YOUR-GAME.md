# Bring your Godot 3.5 game onto the Devkit (MUN console)

This is for running the **full game on a MUN console** (and Devkit sim), not
a handheld EmuELEC / PortMaster port.

You do **not** need Play-MUN to approve [upstream #20](https://github.com/Play-MUN/mun-devkit/issues/20)
before trying this on the fork.

## Tails From Alteria (wired)

The full-game MUN path lives **in the game repo**:

- https://github.com/jeeve-javari/tails-from-alteria — see **`README_MUN.md`**
- `addons/mun`, `mun-project.toml`, and `Makefile` are already there
- Handheld EmuELEC remains **`README_HANDHELD.md`** (separate deploy)

Point the Devkit GUI **Project folder** at the tails-from-alteria checkout
(the directory that contains `mun-project.toml`), then Build → Simulate after
you assemble `build/content/game.pck` + aarch64 `frt`.

**Fast path:** export preset **MUN Console (pck)** in the game repo, then
from **either** folder:

```powershell
# from the game repo
cd C:\Users\YOU\tails-from-alteria
.\tools\mun\Prepare-MunDevkit.ps1

# or from mun-devkit-GUI (sibling checkout)
cd C:\Users\YOU\mun-devkit-GUI
.\scripts\windows\Prepare-TailsMun.ps1
```

WSL: `tails-from-alteria/tools/mun/prepare-devkit.sh`.

## What “running on the Devkit” means

| Goal | How |
| --- | --- |
| Play the full game on PC | Godot **3.5.2** editor (Mun autoload is safe when not in a MUN session) |
| MUN console card session | **frt-boot** entry + `content/game.pck` + `content/frt` (aarch64 FRT 3.5.x) |
| GUI | Browse → game folder with `mun-project.toml` → Build → Simulate |

**Display:** FRT wants KMS/DRM. Docker Desktop on Windows may only log or
flash. Use the Godot editor to *see* the full game; use Devkit sim to exercise
the MUN card/session layout.

## Other Godot 3.5 games

1. Copy `engines/godot3/addons/mun` into the project; autoload `Mun`.
2. Add `mun-project.toml` + a Makefile like `samples/hello-mun-godot3` or
   Tails’ `Makefile`.
3. Export a GLES2 `.pck`, obtain **aarch64** FRT 3.5.x, run
   `engines/godot3/tools/assemble-layout.sh`.
4. `mdk build` / `mdk sim --container` (or the GUI).

Probe sample in this repo: `samples/hello-mun-godot3`.
