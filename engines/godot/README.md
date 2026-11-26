# Godot

For Godot 4.7. Checked with exactly one build: 4.7.2-stable, the official
Linux ARM64 editor, which `fetch.sh` downloads and verifies by its SHA-512.
No other version has been tried; a report of one that works, or does not,
is welcome.

Games on **Godot 3.5** (including FRT / handheld-style exports) use the
parallel track in [`engines/godot3`](../godot3/README.md). That path is
intentional: 4.7 is not required for every game.

| Part | State |
| --- | --- |
| `addons/mun/mun.gd`: session facts, restored save, acknowledged saves, in GDScript | Tested with the pinned engine build against the session simulator |
| `samples/hello-mun-godot`: the probe (count, sound, save, exit) | Runs headless with the engine's editor build; never drawn on a display yet |
| An exported game for a console | **Not yet**: see below |

## The adapter

Copy or link `addons/mun` into the project and add the autoload. The
add-on is under MIT No Attribution: it becomes part of your project with
nothing to include.

```ini
[autoload]
Mun="*res://addons/mun/mun.gd"
```

```gdscript
func _ready() -> void:
    var loaded := Mun.save_load()
    if loaded["status"] == Mun.Status.OK and loaded["schema"] == SAVE_SCHEMA:
        apply(loaded["data"])

func save_progress() -> void:
    var result: Dictionary = await Mun.save_write(state(), SAVE_SCHEMA)
    if result["status"] == Mun.Status.OK:
        hud.show_saved()                      # only now: the card holds it
    elif result["status"] != Mun.Status.UNAVAILABLE:
        hud.show_not_saved(result.get("code", ""))
```

No native code is involved: Godot 4.7's `StreamPeerUDS` (part of the engine
core, so a reduced export template keeps it) speaks the console's save
socket, and `save_write` waits across frames instead of blocking one. In
the editor and in desktop builds every call reports `UNAVAILABLE`.

Numbers come back from a save as floating point, as JSON has one number
type in the engine: convert with `int()` what was saved as an integer.

## What an exported game still needs

The engine's own behaviour, read from its 4.7.2 source and seen in the
tests, leaves three things an export for a console must add. None is in
this repository yet.

1. **A way to present.** Godot draws through Wayland or X11; it has no
   direct KMS back end. MUN OS's runtime profiles give a game the display
   directly and run no window system, so a Godot game has nowhere to open a
   window until a profile provides one. The probe's project already selects
   the Wayland driver.
2. **Clean termination.** The engine installs no handler for SIGTERM: the
   stock build ends by the signal instead of exiting 0
   (`tests/test_godot.py` records it). A console stops a game with SIGTERM
   and three seconds of grace, so the export template must be built with a
   small module that turns the signal into the engine's normal quit. A
   GDExtension cannot do it: a card's content is not executable, so a
   library there cannot be loaded.
3. **One executable of at most 64 MiB with the data beside it on the
   card.** The stock release template is larger; a template built for size
   with unused modules off fits. The game's pack then loads from the
   content directory through a small boot scene embedded in the executable
   (`ProjectSettings.load_resource_pack(Mun.content_path("game.pck"))`),
   since a console starts the entry with no arguments.

What the official 4.7.2 Linux ARM64 build links against is the C library
only (glibc 2.28 or later). Everything else it opens at run time by name:
`libwayland-client.so.0`, `libwayland-cursor.so.0`, `libwayland-egl.so.1`,
`libxkbcommon.so.0`, `libdecor-0.so.0` (optional), `libvulkan.so.1` or
`libEGL.so.1` with `libGLESv2.so.2` or `libGL.so.1`, `libasound.so.2` or
`libpulse.so.0`, `libudev.so.1`, and optionally `libfontconfig.so.1`,
`libdbus-1.so.3`, `libspeechd.so.2` and the X11 libraries. A runtime
profile for Godot has to provide the ones in use.

## Fetching the engine

`engines/godot/fetch.sh` downloads the pinned release into `.local/godot/`
and verifies it by SHA-512; `fetch.sh source` also fetches the source, for
building export templates.
