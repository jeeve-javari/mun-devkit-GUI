# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
"""Install a packed card into a mun-os checkout and launch `mun play` (QEMU)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess  # nosec B404: starts mun play with a fixed argv / PowerShell -Command
import sys
from pathlib import Path
from typing import Optional, Tuple

try:
    from .state import windows_explorer_path
except ImportError:  # unittest loads tools/gui on sys.path as flat modules
    from state import windows_explorer_path

# mun play --card NAME: 2–16 characters (same rule as mun-os).
_CARD_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,15}$")


def sanitize_card_name(raw: str, fallback: str = "game") -> str:
    """Turn a project name into a legal short card stem for `mun play --card`."""
    text = (raw or "").strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-._")
    if len(text) < 2:
        text = fallback
    if len(text) > 16:
        text = text[:16].rstrip("-._")
    if len(text) < 2:
        text = "game"
    if not _CARD_RE.match(text):
        text = "game"
    return text


def find_packed_image(project_dir: Path, project_name: Optional[str] = None) -> Path:
    """`build/<name>.img` after `mdk pack`, or the newest `build/*.img`."""
    build = project_dir / "build"
    if project_name:
        preferred = build / f"{project_name}.img"
        if preferred.is_file():
            return preferred
    if not build.is_dir():
        raise FileNotFoundError(f"No build/ folder in {project_dir} — Pack the card first.")
    imgs = sorted(build.glob("*.img"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not imgs:
        raise FileNotFoundError(
            f"No .img in {build} — press Pack card first.")
    return imgs[0]


def read_project_name(project_dir: Path) -> str:
    path = project_dir / "mun-project.toml"
    if not path.is_file():
        return "game"
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("name") and "=" in line:
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    return "game"


def install_card_image(image: Path, mun_os: Path, card_name: str) -> Path:
    """Copy the packed image to mun-os `.local/gamecards/<card_name>.img`."""
    if not _CARD_RE.match(card_name):
        raise ValueError(
            f"Card name {card_name!r} must be 2–16 characters "
            "(letters, digits, . _ -).")
    if not (mun_os / "mun").is_file():
        raise FileNotFoundError(
            f"Not a mun-os checkout (no mun script):\n{mun_os}")
    if not image.is_file():
        raise FileNotFoundError(f"Packed card not found:\n{image}")
    dest_dir = mun_os / ".local" / "gamecards"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{card_name}.img"
    shutil.copy2(image, dest)
    return dest


def _in_wsl() -> bool:
    if not Path("/mnt/c").is_dir():
        return False
    version = Path("/proc/version")
    if not version.is_file():
        return False
    return "microsoft" in version.read_text(encoding="utf-8", errors="ignore").lower()


def launch_mun_play(mun_os: Path, card_name: str) -> Tuple[subprocess.Popen, str]:
    """Start `mun play --card` detached so the GUI stays usable. Returns (proc, how)."""
    if not _CARD_RE.match(card_name):
        raise ValueError(f"Bad card name: {card_name}")
    mun_script = mun_os / "mun"
    if not mun_script.is_file():
        raise FileNotFoundError(f"No mun script in {mun_os}")

    # Prefer the Windows host path when the GUI runs under WSL: that matches
    # `py mun play` in PowerShell (MSYS2 QEMU on Windows ARM64).
    win = windows_explorer_path(mun_os.resolve())
    if win and (_in_wsl() or os.name == "nt"):
        if os.name == "nt":
            command = ["py", "-3", "mun", "play", "--card", card_name]
            how = f"py mun play --card {card_name}"
            proc = subprocess.Popen(  # nosec B603: fixed argv, no shell
                command,
                cwd=str(mun_os),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                | getattr(subprocess, "DETACHED_PROCESS", 0),
            )
            return proc, how
        # WSL → Windows Python
        ps = (
            f"Set-Location -LiteralPath '{win}'; "
            f"py -3 mun play --card {card_name}"
        )
        command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps]
        how = f"powershell: py mun play --card {card_name}"
        proc = subprocess.Popen(  # nosec B603: fixed argv list
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        return proc, how

    command = [sys.executable, str(mun_script), "play", "--card", card_name]
    how = f"{sys.executable} mun play --card {card_name}"
    proc = subprocess.Popen(  # nosec B603: fixed argv, no shell
        command,
        cwd=str(mun_os),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    return proc, how


def install_and_play(project_dir: Path, mun_os: Path, card_name: Optional[str] = None) -> Tuple[Path, str]:
    """Copy the project's packed .img into mun-os and launch QEMU. Returns (dest, how)."""
    name = read_project_name(project_dir)
    card = sanitize_card_name(card_name or name)
    image = find_packed_image(project_dir, name)
    dest = install_card_image(image, mun_os, card)
    _proc, how = launch_mun_play(mun_os, card)
    return dest, how
