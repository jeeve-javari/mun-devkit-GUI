# MUN Devkit

**English** · [Español](README.es.md)

[![Checks](https://github.com/Play-MUN/mun-devkit/actions/workflows/checks.yml/badge.svg?branch=main)](https://github.com/Play-MUN/mun-devkit/actions/workflows/checks.yml)
[![Licence: Apache-2.0 and MIT-0](https://img.shields.io/badge/licence-Apache--2.0%20%C2%B7%20MIT--0-blue)](docs/licensing.md)

Tools for making and porting games for MUN™: a host tool (`mdk`), a small
static C client for what a console gives a game, a session simulator, and a
sample that goes from source to a Game Card image.

A MUN game is an ordinary AArch64 Linux program that follows a few contracts
of [MUN OS](https://github.com/Play-MUN/mun-os): a card with a manifest, a
runtime profile, facts in the environment, and saves the console writes to
the card. The devkit does not replace or wrap those contracts. It reuses
MUN OS's own card tool and validator, so a card `mdk` makes is a card the
console's code has already read.

**MUN Disk** and **Game Card** are one thing: MUN Disk is the name of the
console's medium, the product a player holds; Game Card is what its format
and its tools call it, and so do these pages when they speak of the image,
the manifest or the card tool.

## The project

MUN is a console in development for physical games you own, made by Play
MUN: [playmun.com](https://playmun.com). The devkit is one of its two open
repositories:

| | |
| --- | --- |
| [MUN OS](https://github.com/Play-MUN/mun-os) | The console's open operating system. It runs on your computer in QEMU, and a card made with the devkit goes into it |
| [Running a game](https://github.com/Play-MUN/mun-os/blob/main/docs/runtime.md) | The session a game gets: its runtime profile, its environment, how it ends |
| [Saves](https://github.com/Play-MUN/mun-os/blob/main/docs/saves.md) | What a save is, the service that writes it and every code it answers with |
| [Game Cards](https://github.com/Play-MUN/mun-os/blob/main/docs/game-cards.md) | The card's format, its manifest and the card tool |
| [Bring a game to MUN](https://github.com/Play-MUN/mun-os/blob/main/docs/guides/port-a-game.md) | MUN OS's own guide to porting a game, step by step |

Those pages are the contracts; this repository follows them and says which
revision it was checked against (`mun-os.lock.json`).

## Status

Early. What exists is what is listed here, and nothing in it has been run on
a console's hardware.

| Part | State |
| --- | --- |
| `mdk doctor`, `os`, `env`, `new`, `build`, `check`, `pack`, `sim` | Work on macOS (Apple Silicon) and on Linux ARM64 with a container runtime: every pull request runs the whole journey there (Ubuntu 24.04). On Linux x86-64 the host checks run; building for a console there needs emulation and has not been tried |
| MUN OS followed | v0.1.0-dev.5 (`mun-os.lock.json`); the checks also pass with v0.1.0-dev.4's tools |
| Static C client (`client/c`): session facts, restore and acknowledged save | Tested against the simulator and against save files as a console writes them |
| Session simulator | Reproduces the session layout, the save service and how a session ends; not the sandbox or any device |
| Sample `samples/hello-mun` (SDL2, OpenGL, OpenAL; profile `linux-arm64-gl-v0`) | Builds, passes the checks, packs, and runs in the simulator, drawing with Mesa's software renderer |
| Godot 4.7 adapter (`engines/godot`): GDScript, no native code | Written for Godot 4.7 and checked with exactly one build, the official 4.7.2-stable for Linux ARM64, which `engines/godot/fetch.sh` fetches and verifies. It saves and restores against the simulator; an exported game for a console is not possible yet ([why](engines/godot/README.md)) |
| Godot 3.5 / FRT track (`engines/godot3`) | Adapter and probe for Godot **3.5.x** (and FRT-style cards) so games need not move to 4.7. Save socket needs a Unix stream peer in the engine; packing into `mdk` is not wired yet ([engines/godot3](engines/godot3/README.md)) |
| Other engines | Nothing yet |

The runtime profiles are MUN OS's and are provisional there: its documents
say they are measured in virtual machines only.

## What you need

- Python 3.9 or later.
- MUN OS's own tools, at the revision `mun-os.lock.json` names. `mdk os
  fetch` clones exactly that revision into `.local/mun-os`; `--mun-os` or
  `MUN_OS_DIR` name another checkout, and `../mun-os` beside the devkit is
  used when there is no other. `mdk` reports the revision it finds and says
  when it differs from the pinned one.
- e2fsprogs 1.47 or later, to make card images (macOS: `brew install e2fsprogs`).
- A container runtime that runs `linux/arm64` (`docker`), to build for a
  console. On an ARM64 computer the build runs natively.

`./mdk doctor` checks each of these and says what to do about a missing one.

### Optional: downloadable Friendly GUI app

The **primary path remains the CLI** (`./mdk` and the journey below). For
developers who prefer a desktop window, there is an **optional** Friendly GUI
that wraps the same commands — it does not replace `mdk`, the contracts, or
this repository's layout.

**Download the app package** from this repository's
[GitHub Releases](https://github.com/Play-MUN/mun-devkit/releases) (a zip of
the full Devkit with GUI launchers). Unzip, then:

| Platform | Open the app |
| --- | --- |
| Windows (ARM or x86) | Double-click **`MUN Devkit.bat`**, or run `scripts/windows/Install-MdkGui.ps1` once |
| macOS / Linux | `./mdk-gui` (Python 3.9+ with Tk) |

From a git clone instead of a Release zip:

```sh
./mdk-gui
# or
./mdk gui
```

Setup, new project, build, check, pack and simulate each call `mdk` with the
same arguments the CLI uses. Building for a console still needs Docker (and
on Windows, WSL 2). Details: [docs/gui.md](docs/gui.md). A Release zip has no
`.git`, so use a new download (or a clone + **Update…** in the GUI) for later
Devkit updates.

## From nothing to a saved game

```sh
./mdk doctor                    # what this computer has and lacks
./mdk os fetch                  # once: MUN OS's tools at the pinned revision
./mdk env build                 # once: the build environment (needs the network)

./mdk new star-well --title "Star Well" --id org.example.star-well
cd star-well
../mdk build                    # compile inside the environment
../mdk check                    # the build against its runtime profile
../mdk pack                     # build/star-well.img, and a record of what is in it
../mdk sim --container --fresh --env MUN_HELLO_HEADLESS=1 \
           --env "MUN_HELLO_SCRIPT=up up up save wait quit"     # a session that saves
../mdk sim --container --env MUN_HELLO_HEADLESS=1 \
           --env "MUN_HELLO_SCRIPT=up save wait quit"           # the next one restores
```

`mdk new` copies the native sample under the project's name; from then on
the project is its own. `tests/test_journey.py` runs exactly these steps and
requires each result. `make sample` at the top builds and packs the sample
itself; `make check` runs the tests this computer can run and names the ones
it skipped, and `make check-full` fails on any it cannot run.

`make dev-tools` installs the two Python analysers at pinned versions and
hashes (`tools/dev-requirements.txt`) into `.local/venv`, and `make analyse`
runs them. A warning is fixed, or, when it is not a defect, marked on its own
line with the rule and the reason (`# nosec B603: ...`); never for a file or
a rule as a whole. The C sources are compiled with the compiler's analyser
in the build environment and give no warning.

To see the card in MUN OS's virtual console, from the MUN OS checkout
(`.local/mun-os` after `mdk os fetch`): `./mun get`, `./mun dev run
--window`, then `./mun dev vm dev card-attach NAME` with the image copied to
its `.local/gamecards/NAME.img` (MUN OS's `docs/getting-started.md`).

### The build environment

`mdk build` runs the project's build command in a Debian 13 ARM64 container
whose packages come from the same dated Debian snapshot as MUN OS's image
(`tools/env/Dockerfile`), without network access. The program therefore
links against the library versions a console of that MUN OS line has, and
the build does not depend on what the host has installed. `mdk env info`
prints the compiler and library versions.

### The checks

`mdk check` reads the entry and the content before a card is made:

```
E-ARCH    game is a 64-bit little-endian x86-64 program. MUN runs 64-bit AArch64 Linux programs.
          Build or export it for Linux ARM64 (aarch64); a Windows, macOS or x86-64 build must be made again.

E-LIB     game needs libcurl.so.4, which the profile linux-arm64-gl-v0 does not provide.
          The profile provides: libEGL.so.1, libGL.so.1, libSDL2-2.0.so.0, ...
          Link it into the game statically, or drop the feature that uses it. The card's content is
          read-only data: a library placed there cannot be loaded.
```

Each finding has a stable code, what is wrong and what to do. The codes:
`E-ENTRY`, `E-NOT-ELF`, `E-ARCH`, `E-NOT-PROGRAM`, `E-SIZE`, `E-INTERP`,
`E-LIB`, `E-GLIBC`, `E-CONTENT`, `E-CONTENT-LINK`, `E-CONTENT-ENTRY`,
`E-CARD-ID`, `E-CARD-VERSION`, `E-CARD-TITLE`, `E-PROFILE`, `E-HARDEN`,
`E-HARDEN-BUILD`, and the warnings `W-RUNPATH`, `W-CODE`, `W-CARD-SIZE`,
`W-HARDEN`, `W-HARDEN-BUILD`. The card itself is validated by MUN OS's tool,
whose own codes are in MUN OS's `docs/game-cards.md`.

### Hardening

The sample, a project started from it and the client are compiled with the
options in `mk/hardening.mk`: `-fstack-protector-strong`,
`-fstack-clash-protection`, `-D_FORTIFY_SOURCE=3` (in an optimising build),
`-mbranch-protection=standard`, `-fPIE -pie` and `-Wl,-z,relro -Wl,-z,now
-Wl,-z,noexecstack`. Each is tried on the compiler first and left out if it
is refused, so the same makefile builds on another system.

`mdk check` then reads the result, not the makefile:

```
hardening position-independent executable: yes; full RELRO: yes; non-executable stack: yes;
          stack protector: yes; fortified calls: yes; branch protection: yes
```

Six properties are in the program itself. Stack-clash protection leaves no
mark there, and a program shows only that *some* function has a canary: for
those, `mdk build` keeps the compiler commands the build printed
(`build/compile-commands.json`) and `mdk check` requires every option in
every one of them.

`build.hardening` in `mun-project.toml` says which case a project is:

| Value | For | A missing property or option |
| --- | --- | --- |
| `"required"` | A program you compile yourself. The sample and `mdk new` say this | An error: `E-HARDEN`, `E-HARDEN-BUILD` |
| `"report"` (the default) | An entry you did not compile: an engine's export template, a program linked with a library built elsewhere | One warning, `W-HARDEN`. The check passes |

The second case exists because of branch protection: the linker marks a
program for BTI and PAC only when every object in it is marked, and an
engine's or a library's objects are not the developer's to rebuild.

### The card

`mdk pack` runs MUN OS's `mun-card create` and then `mun-card inspect`, and
writes `build/<name>.card.json`: the image's SHA-256, what a console reads
from it, the entry's hash and libraries, and the tool revisions. The same
inputs and the same e2fsprogs give the same image, byte for byte.

### The simulator

`mdk sim` runs the game as a session: a copy of the entry started with no
arguments, `work/` as its home, the `MUN_*` facts, the save restored from a
card directory (`build/sim-card`), and a save socket that answers as the
console's does, with its codes and sentences.

```sh
mdk sim --container --fail no_space      # every save is refused as a full card
mdk sim --container --fail save_failed:1 # the next save is not attended; the one after is
mdk sim --container --fail closed:1      # the console closes the next save's connection unanswered
mdk sim --container --stop-after 5       # SIGTERM after 5 s, SIGKILL 3 s later
mdk sim --container --save-delay 2       # a slow card
mdk sim --container --hold-saves --stop-when saving   # stopped while a save is unanswered
mdk sim --container --stop-when saved    # stopped once the card holds a save
mdk sim --fresh                          # start from a card with no save
```

It does not reproduce the sandbox (user, devices, read-only system,
non-executable content, memory and task limits), the display, sound or
input devices, or a real card. A game that passes in it follows the
contracts; whether it runs on a console is established on a console.

## Saves from C

```c
#include "mun.h"

mun_session *session;
mun_open(&session);

static char payload[MUN_SAVE_LOAD_MAX_BYTES];
size_t length;
mun_save_info info;
switch (mun_save_load(session, payload, sizeof payload, &length, &info)) {
case MUN_OK:      /* parse `payload`, a JSON object, by info.schema */ break;
case MUN_NO_SAVE: /* a new game */ break;
default:          /* unavailable or damaged: start without it */ break;
}

mun_save_result result;
if (mun_save_write(session, 1, "{\"level\":3}", 11, 25000, &result) == MUN_OK)
    show_saved();                       /* only now: the card holds it */
else
    show_not_saved(result.code);        /* "no_space", "card_removed", ... */
```

What a refusal means for the game:

| `result.code` | What happened | What to do |
| --- | --- | --- |
| `no_space`, `card_removed`, `card_mismatch`, `card_unavailable`, `save_path_unsafe`, `write_failed`, `sync_failed`, `reader_unavailable` | The card, or the reader, could not take the save. The save it held before is intact | Tell the player; the next attempt needs the card's situation to change |
| `save_failed`, `save_busy` | The console could not attend this request (it was busy with another save, or could not pass this one on). Nothing was written | Passing: say "not saved" and offer the save again at the game's next save point. Do not retry in a loop |
| `save_too_large`, `save_invalid` | The request itself | A fault in the game: fix the payload |

Two things a game does not see as a save's answer, on MUN OS after
v0.1.0-dev.5:

- A session that could not be prepared ends before the game starts, with
  the launch result `prepare_failed`. The player is back in the console's
  menu; no game code runs, so there is nothing to handle, and the simulator
  does not produce it.
- The console's card service runs within a memory limit. The largest save
  a card can hold fits well inside it. If the service were ended while it
  wrote, the card keeps its last complete save, and the game is told the
  save was not made (a refusal, or a closed connection: `MUN_IO`).

A connection the console closes without answering is `MUN_IO`, and no
answer in time is `MUN_TIMEOUT`: both end the call, never a wait without
end, and both leave the outcome unknown until the next start reads the save
back.

`mun_save_write` blocks until the console answers: call it off the thread
that draws. `client/c/mun.h` documents every function, status and rule.
Compile `mun.c` into the game; there is no shared library.

## Layout

```
mdk                    the host tool's entry point (primary)
mdk-gui                optional friendly desktop front-end (also: mdk gui)
tools/mdk/             its source (Python, standard library only)
tools/gui/             the optional desktop front-end (Tk; standard library only)
tools/env/             the build environment's definition
scripts/windows/       optional WSL setup and launch helpers for Windows ARM and x86
client/c/              mun.h, mun.c and the client's test program
mk/hardening.mk        the options a console program is compiled with
contracts/profiles/    what mdk checks a build against, per runtime profile
samples/hello-mun/     the native sample
samples/hello-mun-godot/   the same small game as a Godot 4.7 project
samples/hello-mun-godot3/  the same idea for Godot 3.5
engines/godot/         Godot 4.7 adapter, and how to fetch the pinned engine
engines/godot3/        Godot 3.5 / FRT adapter and packing notes
tests/                 host tests; the sample's run in the environment
mun-os.lock.json       the MUN OS revision the devkit was checked against
LICENSE, LICENSES/     the licence texts; docs/licensing.md says which covers what
```

## Contributing

Fixes, tests, samples, translations and reports of what happened on your
computer are welcome: [contributing](CONTRIBUTING.md) says how a change
travels and what it must come with, and everyone taking part follows the
[code of conduct](CODE_OF_CONDUCT.md). Questions go in an issue or in the
developers' channel of the [MUN Discord](https://discord.gg/UxgExjjhxH); decisions are recorded in
issues. A security problem goes privately to the maintainer
([security](SECURITY.md)).

## Licence

Three licences, by where each part ends up ([licensing](docs/licensing.md)):

- the tools, under the [Apache License 2.0](LICENSE);
- the client a game compiles in (`client/c`), under the Apache License 2.0
  with the LLVM Exceptions, so that a game ships it with nothing to include;
- the samples, the engine add-ons and what `mdk new` copies, under
  [MIT No Attribution](LICENSES/MIT-0.txt): yours to use as you like.

The devkit is free to make, test and distribute games with. Publishing on
an official MUN Disk is a separate service with its own agreement, and the
MUN and Play MUN names and logos are not licensed
([NAME-AND-LOGO.txt](NAME-AND-LOGO.txt)).
[docs/third-party.md](docs/third-party.md) lists what the devkit uses.
