# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0

"""Run `mdk` for the GUI: find the tree, start a command, stream its output."""

from __future__ import annotations

import os
import queue
import subprocess  # nosec B404: starts only the local mdk entry point with fixed argv lists
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Sequence


def find_root(start: Optional[Path] = None) -> Path:
    """The directory that holds `mdk` and `tools/mdk`."""
    here = (start or Path(__file__)).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "mdk").is_file() and (candidate / "tools" / "mdk").is_dir():
            return candidate
    raise FileNotFoundError("Could not find the MUN Devkit root (mdk and tools/mdk).")


def python_for_mdk() -> str:
    return sys.executable or "python3"


@dataclass
class RunResult:
    command: List[str]
    returncode: int
    cancelled: bool = False


class CommandRunner:
    """One long-running `mdk` process at a time, with line callbacks on a queue."""

    def __init__(self, root: Path, on_line: Callable[[str], None],
                 on_done: Callable[[RunResult], None]):
        self.root = root
        self.on_line = on_line
        self.on_done = on_done
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._lines: "queue.Queue[Optional[str]]" = queue.Queue()

    @property
    def busy(self) -> bool:
        with self._lock:
            return self._proc is not None and self._proc.poll() is None

    def run(self, args: Sequence[str], cwd: Optional[Path] = None,
            env: Optional[dict] = None) -> None:
        if self.busy:
            raise RuntimeError("Another command is still running.")
        command = [python_for_mdk(), str(self.root / "mdk"), *args]
        work = str(cwd or self.root)
        merged = os.environ.copy()
        if env:
            merged.update(env)
        # Force line buffering so the log pane updates as the tool prints.
        merged.setdefault("PYTHONUNBUFFERED", "1")

        def worker() -> None:
            cancelled = False
            try:
                proc = subprocess.Popen(  # nosec B603: argv list, no shell; only local mdk
                    command,
                    cwd=work,
                    env=merged,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
            except OSError as exc:
                self.on_line(f"Could not start mdk: {exc}")
                self.on_done(RunResult(command=command, returncode=127))
                return
            with self._lock:
                self._proc = proc
            out = proc.stdout
            if out is None:
                self.on_line("Could not read mdk output.")
                self.on_done(RunResult(command=command, returncode=proc.wait() or 1))
                return
            try:
                for line in out:
                    self.on_line(line.rstrip("\n"))
                returncode = proc.wait()
            except Exception as exc:  # unexpected reader failure: still finish cleanly
                self.on_line(f"(log reader stopped: {exc})")
                returncode = proc.poll() if proc.poll() is not None else 1
                cancelled = True
            finally:
                with self._lock:
                    self._proc = None
            self.on_done(RunResult(command=command, returncode=returncode or 0, cancelled=cancelled))

        threading.Thread(target=worker, name="mdk-gui-runner", daemon=True).start()

    def cancel(self) -> None:
        with self._lock:
            proc = self._proc
        if proc is None or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


# States and need-names doctor prints today (cli.cmd_doctor). Matched longest-first
# because a few names are longer than the 16-character column width.
_DOCTOR_STATES = ("not built", "MISSING", "differs", "absent", "stopped", "ok")
_DOCTOR_NEEDS = (
    "container runtime", "SDK environment", "MUN OS tools", "C compiler",
    "e2fsprogs", "mke2fs", "debugfs", "Python",
)


def parse_doctor(text: str) -> List[dict]:
    """Turn `mdk doctor` output into rows the setup pane can show."""
    rows = []
    for line in text.splitlines():
        raw = line.rstrip()
        if not raw:
            continue
        state = None
        for candidate in _DOCTOR_STATES:
            if raw == candidate or raw.startswith(candidate + " "):
                state = candidate
                rest = raw[len(candidate):].lstrip()
                break
        if state is None or not rest:
            continue
        name = None
        detail = ""
        for candidate in _DOCTOR_NEEDS:
            if rest == candidate or rest.startswith(candidate + " "):
                name = candidate
                detail = rest[len(candidate):].lstrip()
                break
        if name is None:
            parts = rest.split(None, 1)
            name, detail = parts[0], (parts[1] if len(parts) > 1 else "")
        rows.append({"state": state, "name": name, "detail": detail})
    return rows
