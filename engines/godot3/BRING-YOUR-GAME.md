# Bring your Godot 3.5 game onto the Devkit (fork workflow)

You do **not** need Play-MUN to approve the upstream issue before trying this
on the fork. Upstream agreement is for merging the track into official
`mun-devkit`; your fork can keep moving.

## What “running on the Devkit” means

| Goal | How |
| --- | --- |
| Play / iterate on PC | Godot **3.5.2** editor + copy `engines/godot3/addons/mun` into your game, autoload `Mun` |
| Session under `mdk sim` | Card layout: **frt-boot** entry + `content/game.pck` + `content/frt` (aarch64 FRT 3.5.x) |
| GUI | Project folder → your game’s folder that contains `mun-project.toml` → Build → Simulate |

**Display note:** FRT expects KMS/DRM or a suitable SDL driver. Inside Docker
Desktop on Windows you may only see log lines (or a quick container flash),
not a full handheld-like window. A visible window is most reliable in the
Godot editor on Windows, or on real Linux ARM / device hardware. The Devkit
path still validates pack → session → saves once UDS is in FRT.

## Tails From Alteria (example)

Repo: https://github.com/jeeve-javari/tails-from-alteria

### 1. Mun addon in the Godot project

```text
tails-from-alteria/
  addons/mun/mun.gd    ← copy from mun-devkit-GUI/engines/godot3/addons/mun/
```

In `project.godot`:

```ini
[autoload]
Mun="*res://addons/mun/mun.gd"
```

Develop and run in Godot 3.5.2 as you already do.

### 2. Export a pack

Export your **EmuELEC FRT (pck)** (or equivalent GLES2 pack) to e.g.
`TailsFromAlteria.pck`.

### 3. Get an aarch64 FRT 3.5.x binary

PortMaster **Godot/FRT 3.5.2** aarch64, or an [FRT release](https://github.com/efornara/frt/releases)
for arm64. (An arm32 binary will not run in the Devkit’s `linux/arm64`
environment.)

### 4. Add a `mun-project.toml` next to the Godot project

```toml
[project]
name = "tails-from-alteria"

[card]
id = "org.example.tails-from-alteria"
title = "Tails From Alteria"
version = "0.1.0"
profile = "linux-arm64-gl-v0"
size_mib = 64

[build]
run = "make -f path/to/mun-devkit/samples/hello-mun-godot3/Makefile MUN_DEVKIT=path/to/mun-devkit"
entry = "build/frt-boot"
content = "build/content"
hardening = "report"
```

Or call the assembler from the mun-devkit tree:

```bash
# In WSL, from the game folder after exporting the pck:
DEVKIT=/mnt/c/Users/inver/mun-devkit-GUI
"$DEVKIT/engines/godot3/tools/assemble-layout.sh" \
  --pck ./TailsFromAlteria.pck \
  --frt /path/to/frt_aarch64_3.5.2 \
  --out ./build
```

Then set `mun-project.toml` `build.run` to a no-op `true` if `build/` is
already assembled, or a tiny Makefile that only ensures files exist.

### 5. Devkit GUI / CLI

```bash
cd /mnt/c/Users/inver/mun-devkit-GUI
./mdk build --project "/mnt/c/Users/inver/Documents/.../tails-from-alteria"
./mdk sim --container --project "..." --env MUN_HELLO_SCRIPT=quit
```

Or in the GUI: Browse → that project folder → Build → Simulate.

## Probe sample in this repo

`samples/hello-mun-godot3` has `mun-project.toml` and a Makefile. After
`mdk build` you still must place `build/content/game.pck` and
`build/content/frt` (export the probe from Godot 3.5, or temporarily use
your game’s pck to smoke-test the boot path).
