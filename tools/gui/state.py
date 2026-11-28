# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
"""Persisted GUI choices (project folder, etc.) and WSL path helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

GUI_STATE_VERSION = 1


def gui_state_path() -> Path:
    """Where the last Project-tab choices are kept between launches."""
    override = os.environ.get("MDK_GUI_STATE")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "mun-devkit" / "gui-state.json"
    return Path.home() / ".config" / "mun-devkit" / "gui-state.json"


def load_gui_state(path: Optional[Path] = None) -> Dict[str, Any]:
    file = path or gui_state_path()
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict) or data.get("version") != GUI_STATE_VERSION:
        return {}
    return data


def save_gui_state(state: Dict[str, Any], path: Optional[Path] = None) -> None:
    file = path or gui_state_path()
    payload = {"version": GUI_STATE_VERSION, **state}
    try:
        file.parent.mkdir(parents=True, exist_ok=True)
        tmp = file.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(file)
    except OSError:
        pass


def windows_explorer_path(path: Path) -> Optional[str]:
    """Map a WSL /mnt/<drive>/… path to a Windows path for explorer.exe."""
    win = path.as_posix().rstrip("/")
    if not (win.startswith("/mnt/") and len(win) >= 6):
        return None
    # /mnt/c or /mnt/c/... → C:\...  (drive letter at index 5)
    if not win[5].isalpha():
        return None
    if len(win) > 6 and win[6] != "/":
        return None
    drive = win[5].upper()
    rest = win[7:].replace("/", "\\") if len(win) > 7 else ""
    return f"{drive}:\\{rest}" if rest else f"{drive}:\\"
