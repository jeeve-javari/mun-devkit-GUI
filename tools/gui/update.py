# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
"""Self-update the Devkit checkout from its git remote, then restart the GUI.

Pulls with --ff-only so local commits are never rewritten. A dirty tree or a
diverged branch is reported; the developer can still use the terminal.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404: runs git and re-launches mdk-gui with fixed argv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple


class UpdateError(Exception):
    """Something the GUI can show without a traceback."""


@dataclass(frozen=True)
class UpdateStatus:
    """What `check_for_updates` found."""

    branch: str
    remote: str
    upstream: str
    local_sha: str
    remote_sha: str
    behind: int
    ahead: int
    dirty: bool
    summary: str  # short human line for the UI
    log: str      # recent commits on the remote (empty if up to date)


def _run_git(repo: Path, args: Sequence[str], *, timeout: int = 120) -> str:
    command = ["git", "-C", str(repo), *args]
    try:
        done = subprocess.run(  # nosec B603, B607: no shell; git from PATH, fixed argv on this repo
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except FileNotFoundError as exc:
        raise UpdateError(
            "git is not installed (or not on PATH).\n"
            "In Ubuntu:  sudo apt install -y git") from exc
    except subprocess.TimeoutExpired as exc:
        raise UpdateError(f"git {' '.join(args)} timed out.") from exc
    if done.returncode != 0:
        err = (done.stderr or done.stdout or "").strip() or f"exit {done.returncode}"
        raise UpdateError(f"git {' '.join(args)} failed:\n{err}")
    return (done.stdout or "").strip()


def is_git_checkout(repo: Path) -> bool:
    try:
        out = _run_git(repo, ["rev-parse", "--is-inside-work-tree"])
    except UpdateError:
        return False
    return out == "true"


def _current_branch(repo: Path) -> str:
    name = _run_git(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    if not name or name == "HEAD":
        raise UpdateError(
            "This checkout is not on a branch (detached HEAD).\n"
            "Check out main in a terminal, then try Update again.")
    return name


def _upstream_ref(repo: Path, branch: str) -> Tuple[str, str]:
    """Return (remote, upstream_ref like origin/main)."""
    try:
        upstream = _run_git(
            repo, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
        remote = upstream.split("/", 1)[0] if "/" in upstream else "origin"
        return remote, upstream
    except UpdateError:
        pass
    # No upstream configured — prefer origin/<branch>, else origin/main.
    remotes = _run_git(repo, ["remote"]).splitlines()
    if "origin" not in remotes:
        raise UpdateError(
            "No git remote named origin.\n"
            "This folder may not be a clone of mun-devkit-GUI.")
    for candidate in (f"origin/{branch}", "origin/main", "origin/master"):
        try:
            _run_git(repo, ["rev-parse", "--verify", candidate])
            return "origin", candidate
        except UpdateError:
            continue
    raise UpdateError(
        f"Could not find origin/{branch} or origin/main after fetch.\n"
        "Check your network and that this is a clone of the Devkit.")


def _porcelain_dirty(repo: Path) -> bool:
    return bool(_run_git(repo, ["status", "--porcelain"]))


def check_for_updates(repo: Path, *, fetch: bool = True) -> UpdateStatus:
    """Fetch (optional) and compare HEAD to its upstream."""
    repo = Path(repo).resolve()
    if not is_git_checkout(repo):
        raise UpdateError(
            f"Not a git checkout:\n{repo}\n\n"
            "Update only works when you run the Devkit from a cloned repository.")
    branch = _current_branch(repo)
    if fetch:
        # Fetch all remotes quietly; failures surface as UpdateError.
        _run_git(repo, ["fetch", "--all", "--prune"], timeout=180)
    remote, upstream = _upstream_ref(repo, branch)
    local_sha = _run_git(repo, ["rev-parse", "HEAD"])
    remote_sha = _run_git(repo, ["rev-parse", upstream])
    behind_s = _run_git(repo, ["rev-list", "--count", f"HEAD..{upstream}"])
    ahead_s = _run_git(repo, ["rev-list", "--count", f"{upstream}..HEAD"])
    behind = int(behind_s or "0")
    ahead = int(ahead_s or "0")
    dirty = _porcelain_dirty(repo)
    log = ""
    if behind:
        log = _run_git(
            repo,
            ["log", "--oneline", "--no-decorate", f"HEAD..{upstream}", "-n", "12"])
    if behind == 0 and ahead == 0:
        summary = f"Up to date with {upstream}."
    elif behind and ahead == 0:
        summary = f"{behind} update(s) available from {upstream}."
    elif behind == 0 and ahead:
        summary = (
            f"Your branch is {ahead} commit(s) ahead of {upstream} "
            "(nothing to download).")
    else:
        summary = (
            f"Diverged from {upstream}: {behind} behind, {ahead} ahead. "
            "Use a terminal to merge or rebase — Update will not rewrite history.")
    if dirty:
        summary += " Local changes present — Update will refuse until the tree is clean."
    return UpdateStatus(
        branch=branch,
        remote=remote,
        upstream=upstream,
        local_sha=local_sha,
        remote_sha=remote_sha,
        behind=behind,
        ahead=ahead,
        dirty=dirty,
        summary=summary,
        log=log,
    )


def apply_update(repo: Path, status: Optional[UpdateStatus] = None) -> UpdateStatus:
    """Fast-forward the current branch to its upstream. Returns the new status."""
    repo = Path(repo).resolve()
    status = status or check_for_updates(repo, fetch=True)
    if status.dirty:
        raise UpdateError(
            "Your Devkit folder has local changes.\n\n"
            "Commit, stash, or discard them in a terminal, then Update again.\n"
            f"Folder:\n{repo}")
    if status.ahead and status.behind:
        raise UpdateError(
            f"Branch {status.branch!r} has diverged from {status.upstream}.\n\n"
            "Update only fast-forwards. In a terminal:\n"
            f"  cd {repo}\n"
            f"  git status\n"
            f"  git pull --ff-only\n"
            "Or check out main and pull there.")
    if status.behind == 0:
        return status
    # Ensure upstream tracking when we fell back to origin/<branch>.
    try:
        _run_git(repo, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    except UpdateError:
        _run_git(repo, ["branch", f"--set-upstream-to={status.upstream}", status.branch])
    _run_git(repo, ["pull", "--ff-only", status.remote, status.branch], timeout=180)
    return check_for_updates(repo, fetch=False)


def restart_command(devkit: Path) -> List[str]:
    """Argv that re-opens the GUI after an update."""
    script = Path(devkit) / "mdk-gui"
    if script.is_file():
        return [sys.executable or "python3", str(script)]
    # Fallback: same interpreter, -m gui via tools on path (less reliable).
    return [sys.executable or "python3", "-c",
            "import sys; from pathlib import Path; "
            f"sys.path.insert(0, r'{Path(devkit) / 'tools'}'); "
            "from gui.app import main; raise SystemExit(main())"]


def relaunch_and_exit(devkit: Path) -> None:
    """Start a new GUI process, then ask the current one to quit.

    Does not call sys.exit itself — the GUI should destroy the window after.
    """
    command = restart_command(devkit)
    kwargs = {
        "cwd": str(Path(devkit).resolve()),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "start_new_session": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
        kwargs.pop("start_new_session", None)
    subprocess.Popen(command, **kwargs)  # nosec B603: fixed argv, re-launch local mdk-gui
