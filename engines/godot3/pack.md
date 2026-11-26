# Packing a Godot 3.5 / FRT game for MUN

## Card layout (implemented by frt-boot)

```text
build/
  frt-boot                 # card entry (small C wrapper; mdk build produces this)
  content/
    game.pck               # exported from Godot 3.5
    frt                    # aarch64 FRT 3.5.x (executable)
```

`mun-project.toml`:

```toml
[build]
run = "make"
entry = "build/frt-boot"
content = "build/content"
hardening = "report"
```

MUN starts `frt-boot` with **no arguments**. The wrapper reads
`MUN_CONTENT_DIR`, finds `game.pck` + `frt`, and `exec`s:

```text
frt --main-pack $MUN_CONTENT_DIR/game.pck --video-driver GLES2
```

See [frt-boot/](frt-boot/) and [tools/assemble-layout.sh](tools/assemble-layout.sh).
Step-by-step for a real game: [BRING-YOUR-GAME.md](BRING-YOUR-GAME.md).

## Launch contract

| Piece | Status |
| --- | --- |
| Wrapper entry (no argv → FRT argv) | **Done** (`frt-boot`) |
| FRT + `.pck` assembly script | **Done** (`assemble-layout.sh`) |
| `StreamPeerUnix` inside FRT for Mun saves | Still required for real card saves |
| Comfortable GUI “Godot 3 project” wizard | Not yet (Browse to a folder with `mun-project.toml`) |
| Guaranteed window inside Docker Desktop | Not guaranteed (KMS/DRM); editor play is fine for iteration |

SIGTERM within the console’s grace period must still become a normal Godot
quit (exit 0) in the FRT build you ship.
