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


def _docker_candidates() -> List[str]:
    """Where `docker` may live: PATH first, then Docker Desktop's Windows bind from WSL."""
    found: List[str] = []
    for name in ("docker", "docker.exe"):
        path = shutil.which(name)
        if path:
            found.append(path)
    # Docker Desktop on Windows, visible from WSL even before the distro integration
    # puts `docker` on PATH. Prefer these only when PATH had nothing.
    for rel in (
        "/mnt/c/Program Files/Docker/Docker/resources/bin/docker",
        "/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe",
    ):
        if Path(rel).is_file():
            found.append(rel)
    # Deduplicate while keeping order.
    seen = set()
    ordered: List[str] = []
    for path in found:
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    return ordered


def docker() -> str:
    candidates = _docker_candidates()
    if candidates:
        return candidates[0]
    remedy = (
        "Install Docker Desktop (or another runtime that runs linux/arm64). "
        "On Windows: install Docker Desktop, turn on WSL integration for your Ubuntu distro, "
        "leave Docker Desktop running, then try again. "
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
