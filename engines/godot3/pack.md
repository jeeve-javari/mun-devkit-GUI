# Packing a Godot 3.5 / FRT game for MUN (sketch)

Not wired into `mdk pack` yet. Target layout for a later project type:

```text
build/
  frt_aarch64          # card entry (ELF, ≤ 64 MiB), hardening=report
  content/
    game.pck           # exported from Godot 3.5 (GLES2 / ETC as needed)
    …                  # optional raw assets the game loads at runtime
mun-project.toml
```

Example `mun-project.toml` shape (proposed):

```toml
[project]
name = "tails-from-alteria"

[card]
id = "org.example.tails-from-alteria"
title = "Tails From Alteria"
version = "0.1.0"
profile = "linux-arm64-gl-v0"   # or a future FRT-oriented profile
size_mib = 64

[build]
run = "tools/export.sh"       # produces build/content/game.pck
entry = "build/frt_aarch64"
content = "build/content"
hardening = "report"          # entry is an engine binary, not mdk-compiled C
```

## Launch contract (open questions for MUN OS)

Today a session starts the entry with **no arguments**. FRT often wants
`--main-pack …` and `--video-driver GLES2`. Options to agree upstream:

1. **Wrapper entry** (small C program the Devkit compiles) that `exec`s FRT
   with fixed paths under `MUN_CONTENT_DIR`.
2. **FRT build** that defaults to `MUN_CONTENT_DIR/game.pck` when no args.
3. **Profile change** allowing a documented argv — belongs in MUN OS, not
   only this repo.

SIGTERM within the console’s grace period must become a normal Godot quit
(exit 0), same requirement as the Godot 4.7 track.

## What works today without `mdk pack`

1. Develop in Godot **3.5.2** with `addons/mun` autoloaded.
2. Export a `.pck` for your device / FRT as you already do.
3. Use `mdk sim` only after an entry + content layout exists and a UDS peer
   is in the engine — until then, treat Mun saves as `UNAVAILABLE` in the
   editor.
