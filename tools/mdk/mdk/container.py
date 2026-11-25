# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0

"""The SDK build environment: a pinned Debian 13 ARM64 container with the
compiler and the development packages of the libraries a console provides,
taken from the same dated Debian snapshot MUN OS's image is built from
(tools/env/Dockerfile). A game built in it links against the console's own
library versions; the same container runs the session simulator for programs
the host cannot run."""

import hashlib
import os
import shutil
import subprocess  # nosec B404: starts the container runtime; each call is reviewed on its line
import sys
from pathlib import Path
from typing import Dict, List, Optional

from . import osrepo
from .errors import MdkError

DOCKERFILE = osrepo.DEVKIT_ROOT / "tools" / "env" / "Dockerfile"
PLATFORM = "linux/arm64"


def image_tag() -> str:
    """The image is named after its definition: a changed Dockerfile is another image."""
    return "mun-devkit-env:" + hashlib.sha256(DOCKERFILE.read_bytes()).hexdigest()[:12]


def _looks_like_docker(path: Path) -> bool:
    name = path.name.lower()
    return name in ("docker", "docker.exe") and path.is_file()


def _docker_from_windows_where() -> List[str]:
    """Ask Windows where docker is (works from WSL when Docker Desktop added it to PATH)."""
    found: List[str] = []
    try:
        done = subprocess.run(  # nosec B603, B607: fixed argv; asks Windows where docker is
            ["cmd.exe", "/c", "where", "docker"],
            capture_output=True, text=True, check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return found
    if done.returncode != 0:
        return found
    for line in done.stdout.splitlines():
        win = line.strip()
        if not win:
            continue
        # C:\Program Files\... -> /mnt/c/Program Files/...
        if len(win) >= 3 and win[1] == ":" and win[2] in ("\\", "/"):
            drive = win[0].lower()
            rest = win[3:].replace("\\", "/")
            unix = f"/mnt/{drive}/{rest}"
            if _looks_like_docker(Path(unix)):
                found.append(unix)
            found.append(win)  # docker.exe can be started with the Windows path from WSL
    return found


def _windows_user_names() -> List[str]:
    """Windows account folders under /mnt/c/Users (WSL home name may differ)."""
    names = []
    users = Path("/mnt/c/Users")
    if users.is_dir():
        for entry in users.iterdir():
            if entry.is_dir() and entry.name not in ("Public", "Default", "Default User", "All Users"):
                names.append(entry.name)
    # Also try the WSL username when it matches a Windows profile.
    home_name = Path.home().name
    if home_name and home_name not in names:
        names.append(home_name)
    return names


def _docker_under_program_files() -> List[str]:
    """Scan Docker Desktop folders: all-users Program Files and per-user LocalAppData."""
    found: List[str] = []
    roots = [
        Path("/mnt/c/Program Files/Docker"),
        Path("/mnt/c/Program Files (x86)/Docker"),
        Path.home() / "AppData/Local/Docker",
        Path.home() / "AppData/Local/Programs/DockerDesktop",
        Path.home() / "AppData/Local/Programs/Docker",
    ]
    for user in _windows_user_names():
        roots.append(Path(f"/mnt/c/Users/{user}/AppData/Local/Programs/DockerDesktop"))
        roots.append(Path(f"/mnt/c/Users/{user}/AppData/Local/Programs/Docker"))
        roots.append(Path(f"/mnt/c/Users/{user}/AppData/Local/Docker"))
    for root in roots:
        if not root.is_dir():
            continue
        for pattern in ("**/resources/bin/docker.exe", "**/resources/bin/docker", "**/docker.exe"):
            for path in root.glob(pattern):
                if _looks_like_docker(path):
                    found.append(str(path))
    return found


def _docker_candidates() -> List[str]:
    """Where `docker` may live: PATH, Windows where.exe, then Docker Desktop folders."""
    found: List[str] = []
    for name in ("docker", "docker.exe"):
        path = shutil.which(name)
        if path:
            found.append(path)
    found += _docker_from_windows_where()
    found += _docker_under_program_files()
    for rel in (
        "/mnt/c/Program Files/Docker/Docker/resources/bin/docker",
        "/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe",
    ):
        if _looks_like_docker(Path(rel)):
            found.append(rel)
    seen = set()
    ordered: List[str] = []
    for path in found:
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    return ordered


def diagnose_docker() -> str:
    """Plain text for the GUI: what this computer can see about Docker."""
    lines = ["Docker diagnose:"]
    which_docker = shutil.which("docker")
    which_exe = shutil.which("docker.exe")
    lines.append(f"  PATH docker:      {which_docker or '(not found)'}")
    lines.append(f"  PATH docker.exe:  {which_exe or '(not found)'}")
    sock = Path("/var/run/docker.sock")
    lines.append(f"  docker.sock:      {'yes' if sock.exists() else 'no'} ({sock})")
    desktop_hits = []
    for user in _windows_user_names():
        for rel in (
            f"/mnt/c/Users/{user}/AppData/Local/Programs/DockerDesktop/Docker Desktop.exe",
            f"/mnt/c/Users/{user}/AppData/Local/Programs/Docker/Docker/Docker Desktop.exe",
        ):
            if Path(rel).is_file():
                desktop_hits.append(rel)
    for rel in (
        "/mnt/c/Program Files/Docker/Docker/Docker Desktop.exe",
        "/mnt/c/Program Files (x86)/Docker/Docker/Docker Desktop.exe",
    ):
        if Path(rel).is_file():
            desktop_hits.append(rel)
    if desktop_hits:
        lines.append("  Docker Desktop.exe: yes")
        for hit in desktop_hits[:4]:
            lines.append(f"    - {hit}")
    else:
        lines.append("  Docker Desktop.exe: no (checked Program Files and LocalAppData\\Programs)")
        lines.append("  tip: per-user installs live under %LOCALAPPDATA%\\Programs\\DockerDesktop")
    candidates = _docker_candidates()
    lines.append(f"  candidates:       {len(candidates)}")
    for path in candidates[:8]:
        lines.append(f"    - {path}")
    if candidates:
        try:
            done = subprocess.run(  # nosec B603: docker by a path we just found; fixed subcommand
                [candidates[0], "info", "--format", "{{.ServerVersion}}"],
                capture_output=True, text=True, check=False, timeout=20)
            if done.returncode == 0:
                lines.append(f"  docker info:      ok (server {done.stdout.strip() or 'unknown'})")
            else:
                err = (done.stderr or done.stdout or "").strip().splitlines()
                lines.append("  docker info:      failed")
                if err:
                    lines.append(f"    {err[0][:200]}")
                lines.append("  tip: open Docker Desktop and wait until it says Engine running,")
                lines.append("       then in PowerShell: wsl --shutdown   and reopen this app.")
        except (OSError, subprocess.TimeoutExpired) as exc:
            lines.append(f"  docker info:      could not start ({exc})")
    else:
        lines.append("  docker info:      skipped (no docker binary found)")
        lines.append("  tip: Docker Desktop Settings -> Resources -> WSL integration:")
        lines.append("       enable your Ubuntu distro by name (not only 'default'), Apply & Restart,")
        lines.append("       then: wsl --shutdown   and reopen this app.")
    return "\n".join(lines)


def docker() -> str:
    candidates = _docker_candidates()
    if candidates:
        return candidates[0]
    remedy = (
        "Install Docker Desktop (or another runtime that runs linux/arm64). "
        "On Windows: install Docker Desktop, turn on WSL integration for your Ubuntu distro "
        "(enable the Ubuntu row, not only 'default'), leave Docker Desktop running, "
        "run `wsl --shutdown` in PowerShell, reopen this app, then try again. "
        "On an ARM64 computer containers run natively; elsewhere they are emulated and slow."
    )
    raise MdkError("E-ENV-DOCKER", "No container runtime found (docker).", remedy)


def running() -> bool:
    """Whether the container runtime answers: installed is not running."""
    done = subprocess.run(  # nosec B603: docker by the full path which() found; a fixed subcommand
        [docker(), "info", "--format", "{{.ServerVersion}}"], capture_output=True, check=False)
    return done.returncode == 0


def image_exists() -> bool:
    """Whether the environment is built. A runtime that does not answer is
    another matter, with another next step: E-ENV-RUNTIME."""
    done = subprocess.run(  # nosec B603: docker by the full path which() found; a fixed subcommand and the image's own tag
        [docker(), "image", "inspect", image_tag()], capture_output=True, check=False)
    if done.returncode != 0 and not running():
        raise MdkError("E-ENV-RUNTIME", "The container runtime is installed but not running.",
                       "Start it (Docker Desktop, OrbStack, Colima, or `systemctl start docker`) and try again.",
                       done.stderr.decode("utf-8", "replace").strip())
    return done.returncode == 0


def build_image() -> None:
    """Build the environment. Needs the network once: the base image and the
    packages of the dated snapshot."""
    command = [docker(), "build", "--platform", PLATFORM, "-t", image_tag(), "-f", str(DOCKERFILE),
               str(DOCKERFILE.parent)]
    built = subprocess.run(  # nosec B603: docker by its full path, no shell; fixed options and the devkit's own Dockerfile
        command, check=False)
    if built.returncode != 0:
        raise MdkError("E-ENV-BUILD", "The SDK environment could not be built.",
                       "See the output above. It needs the network for the pinned base image and Debian snapshot.")


def require_image() -> None:
    if not image_exists():
        raise MdkError("E-ENV", f"The SDK environment ({image_tag()}) has not been built on this computer.",
                       "Run `mdk env build` once (needs the network; later builds do not).")


def run(argv: List[str], project_dir: Path, mun_os: Path, env: Optional[Dict[str, str]] = None,
        capture: bool = False, tee: bool = False) -> subprocess.CompletedProcess:
    """Run `argv` in the environment with the project at /work (writable),
    the devkit at /opt/mun-devkit and the card package at /opt/mun-os (both
    read-only), without network, as the calling user.

    With `tee`, what it prints (both streams, as one) is shown as it comes
    and also returned in `stdout`."""
    require_image()
    command = [docker(), "run", "--rm", "--init", "--platform", PLATFORM, "--network", "none",
               "--user", f"{os.getuid()}:{os.getgid()}",
               "-v", f"{Path(project_dir).resolve()}:/work",
               "-v", f"{osrepo.DEVKIT_ROOT}:/opt/mun-devkit:ro",
               "-v", f"{Path(mun_os).resolve() / 'tools' / 'mun-card'}:/opt/mun-os/tools/mun-card:ro",
               "-e", "MUN_DEVKIT=/opt/mun-devkit", "-e", "MUN_OS_DIR=/opt/mun-os", "-e", "HOME=/tmp",
               "-e", "PYTHONDONTWRITEBYTECODE=1", "-w", "/work"]
    for name, value in (env or {}).items():
        command += ["-e", f"{name}={value}"]
    command += [image_tag(), *argv]
    if not tee:
        return subprocess.run(  # nosec B603: docker by its full path, no shell; inside runs the developer's own build or game: the purpose
            command, check=False, capture_output=capture, text=capture)
    lines: List[str] = []
    with subprocess.Popen(  # nosec B603: the same command as above, its output read as it comes
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace") as process:
        for line in process.stdout or ():
            sys.stdout.write(line)
            sys.stdout.flush()
            lines.append(line)
    return subprocess.CompletedProcess(command, process.returncode, "".join(lines), "")


def describe() -> Dict[str, str]:
    """What the environment holds: its own record of compiler and library versions."""
    done = subprocess.run(  # nosec B603: docker by its full path, no shell; fixed arguments that print one file of the image
        [docker(), "run", "--rm", "--platform", PLATFORM, "--network", "none", image_tag(),
         "cat", "/etc/mun-devkit-env"], capture_output=True, text=True, check=False)
    record = {"image": image_tag()}
    for line in done.stdout.splitlines():
        name, _, value = line.partition("=")
        if name:
            record[name] = value
    return record
