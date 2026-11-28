# Unix stream peers for Godot 3.5

The Mun adapter’s `save_write` needs a client Unix-domain stream. Godot 4.7
has `StreamPeerUDS` in core. Godot 3.5 does not.

## Option A — engine module (best for FRT cards)

Compile Godot / FRT with a module that registers `StreamPeerUnix` (same idea
as [lihop/stream_peer_unix](https://github.com/lihop/stream_peer_unix)):

1. Place the module under `godot/modules/stream_peer_unix/`.
2. Build the Linux **arm64** FRT or export template you ship as the card
   entry.
3. Confirm in-game: `ClassDB.class_exists("StreamPeerUnix")` is true.

The card’s content is not executable, so a `.so` sitting next to the `.pck`
cannot be loaded as a GDNative library on a locked-down console profile.
The peer must live **inside** the entry ELF.

## Option B — GDNative for the editor / desktop

For iterating on Windows/Linux with stock Godot 3.5.2, a GDNative build of a
Unix-socket peer can be used on Linux/WSL hosts. It does not replace Option A
for a real card.

## Adapter detection

`addons/mun/mun.gd` looks up, in order:

1. `StreamPeerUnix` (module / GDNative)
2. `StreamPeerUDS` (if a future 3.x build adds it)

If neither exists, saves that need the socket report `UNAVAILABLE`.
