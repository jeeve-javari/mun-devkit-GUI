# Godot 3.5 (and FRT)

Support for **Godot 3.5.x** games on MUN, including builds that use
[FRT](https://github.com/efornara/frt) (framebuffer / KMS / SDL2) instead of a
desktop window system. This is a parallel track to the Godot **4.7** adapter
in [`engines/godot`](../godot/README.md). Many shipping games still target
3.5; the Devkit should not require 4.7.

| Part | State |
| --- | --- |
| `addons/mun/mun.gd`: session facts + saves for Godot **3.5** GDScript | Written; save socket needs a Unix-stream peer (below) |
| `samples/hello-mun-godot3`: small probe | Opens in Godot 3.5; exercises facts + load; save needs UDS |
| FRT as card entry + `.pck` in content | **Recipe sketched** ([pack.md](pack.md)); not wired into `mdk pack` yet |
| `mdk build` / GUI project type for Godot 3 / FRT | **Not yet** |
| Official MUN OS runtime profile for FRT | **Needs discussion with MUN OS** |

## Why a separate tree

Godot 3 and 4 are different languages and APIs (`File` vs `FileAccess`,
`yield` vs `await`, no `StreamPeerUDS` in 3.x). Keeping `engines/godot3`
beside `engines/godot` avoids breaking the pinned 4.7 tests while games on
3.5 can move forward.

## The adapter

Copy `addons/mun` into the project and add the autoload:

```ini
[autoload]
Mun="*res://addons/mun/mun.gd"
```

```gdscript
func _ready():
    var loaded = Mun.save_load()
    if loaded["status"] == Mun.Status.OK and loaded["schema"] == SAVE_SCHEMA:
        apply(loaded["data"])

func save_progress():
    var result = yield(Mun.save_write(state(), SAVE_SCHEMA), "completed")
    if result["status"] == Mun.Status.OK:
        hud.show_saved()
```

Outside a MUN session (editor, desktop run) every call reports
`UNAVAILABLE`; nothing fails.

### Unix domain sockets on Godot 3

Godot 3.5 has **no** `StreamPeerUDS`. Saves that talk to the console need
one of:

1. **Preferred for FRT cards:** build FRT / the export template with a
   `StreamPeerUnix` engine module (see [uds/README.md](uds/README.md)).
2. **GDNative** plugin that exposes the same class name (arm64 `.so` beside
   the project for editor tests).

At runtime the adapter does `ClassDB.class_exists("StreamPeerUnix")` (and
falls back to `StreamPeerUDS` if a 3.x build ever gains it). If neither
exists, `save_write` returns `UNAVAILABLE` so the game still runs.

## FRT and the card

A console starts **one ELF**, with no arguments, at most 64 MiB. A Godot 3
handheld-style game is usually:

| On the card | Role |
| --- | --- |
| Entry ELF | FRT (or a tiny wrapper that execs FRT) |
| Content | `game.pck` (+ any raw assets the game loads) |

FRT already solves “no X11/Wayland” for many ARM Linux devices. Mapping that
onto a MUN runtime profile (libraries, GLES2, SIGTERM → clean quit) is the
remaining platform work — see [pack.md](pack.md).

## Upstream

This track is meant for [Play-MUN/mun-devkit](https://github.com/Play-MUN/mun-devkit)
`dev`. Per CONTRIBUTING, a new engine path should also be recorded as an
issue there so the maintainer can agree the shape before `mdk` grows a
Godot 3 project type.
