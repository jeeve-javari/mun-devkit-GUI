# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
"""Engine lanes the Devkit GUI offers — every developer, not only one stack.

A MUN game is always an AArch64 Linux program on a Game Card. Engines differ
only in how far the Devkit can walk someone from editor → card today.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# What Create project does for this lane.
ACTION_MDK_NEW = "mdk_new"          # native C/SDL sample via `mdk new`
ACTION_COPY_SAMPLE = "copy_sample"  # copy a Devkit sample tree
ACTION_GUIDE = "guide"              # no scaffold yet — show the path clearly

STATUS_READY = "ready"        # can create + pack with current tools
STATUS_PARTIAL = "partial"    # sample / adapter exist; console export incomplete
STATUS_PLANNED = "planned"    # hardware may allow it; Devkit has no lane yet


@dataclass(frozen=True)
class EngineLane:
    id: str
    label: str
    status: str
    blurb: str
    next_steps: Tuple[str, ...]
    action: str
    sample_rel: Optional[str] = None   # under the Devkit root
    docs_rel: Optional[str] = None
    profile: str = "linux-arm64-gl-v0"

    @property
    def status_label(self) -> str:
        return {
            STATUS_READY: "Ready to start",
            STATUS_PARTIAL: "In progress",
            STATUS_PLANNED: "Planned",
        }.get(self.status, self.status)

    @property
    def combo_label(self) -> str:
        return f"{self.label}  ·  {self.status_label}"


# Order = how the Project tab lists them.
LANES: Tuple[EngineLane, ...] = (
    EngineLane(
        id="native",
        label="Native (C / SDL2)",
        status=STATUS_READY,
        blurb=("The reference path. Creates a small OpenGL game you can Build, "
               "Check, Pack, and run in QEMU today."),
        next_steps=(
            "Create project (copies the hello-mun sample).",
            "Setup → Build SDK environment if you have not.",
            "Build → Check → Pack → Play in MUN OS.",
        ),
        action=ACTION_MDK_NEW,
        docs_rel="samples/hello-mun/README.md",
    ),
    EngineLane(
        id="godot35",
        label="Godot 3.5 + FRT",
        status=STATUS_READY,
        blurb=("Shipping Godot 3.5 games (GLES2 / FRT). Creates the hello-mun-godot3 "
               "probe with the Mun save adapter. Wire your .pck + FRT on the card."),
        next_steps=(
            "Create project (copies the Godot 3.5 sample).",
            "Open it in Godot 3.5.x; keep the Mun autoload.",
            "Follow engines/godot3/BRING-YOUR-GAME.md for FRT + Pack.",
            "Play in MUN OS when build/<name>.img exists.",
        ),
        action=ACTION_COPY_SAMPLE,
        sample_rel="samples/hello-mun-godot3",
        docs_rel="engines/godot3/BRING-YOUR-GAME.md",
    ),
    EngineLane(
        id="godot36",
        label="Godot 3.6+",
        status=STATUS_PARTIAL,
        blurb=("Still Godot 3 family — use the 3.5 + FRT lane and match FRT / "
               "export template to your exact engine build. No separate scaffold yet."),
        next_steps=(
            "Prefer Godot 3.5.x for MUN cards today, or",
            "Start from the Godot 3.5 sample and retarget your 3.6 export carefully.",
            "Report which 3.6.x + FRT pair worked so we can pin a lane.",
        ),
        action=ACTION_GUIDE,
        docs_rel="engines/godot3/README.md",
    ),
    EngineLane(
        id="godot47",
        label="Godot 4.7",
        status=STATUS_PARTIAL,
        blurb=("Adapter + simulator probe exist (pinned 4.7.2 Linux ARM64). "
               "A full console export is not ready yet (display, SIGTERM, slim template)."),
        next_steps=(
            "Create project to try the GDScript Mun adapter in the editor / sim.",
            "Read engines/godot/README.md for what console export still needs.",
            "Do not expect Pack → Play for a Godot 4 game until that lands.",
        ),
        action=ACTION_COPY_SAMPLE,
        sample_rel="samples/hello-mun-godot",
        docs_rel="engines/godot/README.md",
    ),
    EngineLane(
        id="unity",
        label="Unity",
        status=STATUS_PLANNED,
        blurb=("Board / image work may allow a Linux ARM64 player later. The Devkit "
               "has no Unity export target or runtime profile extras yet."),
        next_steps=(
            "Build or obtain an AArch64 Linux player that fits a MUN profile.",
            "Entry ELF ≤ 64 MiB; card content/ is data only (noexec).",
            "Wire saves via MUN_SAVE_FILE / MUN_SAVE_SOCKET (see mun-os docs).",
            "Until a Unity lane exists, use Bring your own binary below.",
        ),
        action=ACTION_GUIDE,
        docs_rel="docs/gui.md",
    ),
    EngineLane(
        id="unreal",
        label="Unreal Engine",
        status=STATUS_PLANNED,
        blurb=("Same story as Unity: silicon may run it; MUN needs a profile "
               "(likely Vulkan), a cooked arm64 binary, and Devkit packaging."),
        next_steps=(
            "Track runtime profile work with MUN OS (GL today; Vulkan may be needed).",
            "Cook a Linux ARM64 game that links only allowed libs (or static).",
            "Use Bring your own binary when you have an entry ELF + content tree.",
        ),
        action=ACTION_GUIDE,
        docs_rel="docs/gui.md",
    ),
    EngineLane(
        id="other",
        label="Bring your own binary",
        status=STATUS_READY,
        blurb=("Any engine or custom stack: if you can produce an AArch64 Linux "
               "ELF for a MUN runtime profile, the Devkit can pack and play it."),
        next_steps=(
            "Create a folder with mun-project.toml (or start from Native and replace the binary).",
            "Point build.run / entry at your arm64 game; put data under content/.",
            "mdk check → mdk pack → Play in MUN OS.",
            "Read mun-os docs/guides/port-a-game.md for the contracts.",
        ),
        action=ACTION_MDK_NEW,  # scaffold shell; developer replaces the game
        docs_rel="samples/hello-mun/README.md",
    ),
)

_BY_ID: Dict[str, EngineLane] = {lane.id: lane for lane in LANES}


def get_lane(lane_id: str) -> EngineLane:
    try:
        return _BY_ID[lane_id]
    except KeyError as exc:
        raise KeyError(f"Unknown engine lane: {lane_id!r}") from exc


def combo_choices() -> List[str]:
    return [lane.combo_label for lane in LANES]


def lane_from_combo(label: str) -> EngineLane:
    for lane in LANES:
        if lane.combo_label == label or lane.label == label or lane.id == label:
            return lane
    return get_lane("native")


def sample_skip_names() -> frozenset:
    """Dirs/files not copied when scaffolding from a sample."""
    return frozenset({
        ".git", ".import", "build", "__pycache__", ".godot",
        "README.md",  # sample README often points at the sample name
    })


def copy_sample_project(
    devkit: Path,
    sample_rel: str,
    dest: Path,
    *,
    title: str,
    name: str,
) -> Path:
    """Copy a Devkit sample into `dest` (must not exist or be empty)."""
    source = (devkit / sample_rel).resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"Sample missing: {source}")
    dest = Path(dest)
    if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
        raise FileExistsError(f"{dest} already exists and is not empty")
    dest.mkdir(parents=True, exist_ok=True)
    skip = sample_skip_names()
    for item in source.iterdir():
        if item.name in skip:
            continue
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target, ignore=shutil.ignore_patterns(
                ".import", "build", "__pycache__", "*.pyc"))
        else:
            shutil.copy2(item, target)
    readme = dest / "README.md"
    readme.write_text(
        f"# {title}\n\n"
        f"Started from the MUN Devkit sample `{sample_rel}` "
        f"(project name `{name}`).\n\n"
        f"See the Devkit docs for this engine lane, then Pack / Play.\n",
        encoding="utf-8",
    )
    return dest


def detect_lane(project_dir: Path) -> Optional[str]:
    """Best-effort guess from an open project folder."""
    root = Path(project_dir)
    if not root.is_dir():
        return None
    godot = root / "project.godot"
    if godot.is_file():
        text = godot.read_text(encoding="utf-8", errors="ignore")
        # Godot 4 configs often mention config_version=5; 3.x uses 4.
        if "config_version=5" in text or "Godot 4" in text:
            return "godot47"
        return "godot35"
    if (root / "src" / "main.c").is_file() and (root / "mun-project.toml").is_file():
        return "native"
    if (root / "mun-project.toml").is_file():
        return "other"
    return None


def summary_rows() -> List[Dict[str, str]]:
    """Rows for the Engines tab table."""
    return [
        {
            "engine": lane.label,
            "status": lane.status_label,
            "blurb": lane.blurb,
            "id": lane.id,
        }
        for lane in LANES
    ]
