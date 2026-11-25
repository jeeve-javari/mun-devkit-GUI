#!/usr/bin/env bash
# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
# Starts the MUN Devkit GUI from inside WSL. Called by Launch-MdkGui.bat.
set -u

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT" || {
  echo "Could not enter the Devkit folder: $ROOT"
  exit 1
}

LOG_DIR="${TMPDIR:-/tmp}"
WINUSER="$(cmd.exe /c echo %USERNAME% 2>/dev/null | tr -d '\r' || true)"
if [ -n "${WINUSER}" ] && [ -d "/mnt/c/Users/${WINUSER}/AppData/Local/Temp" ]; then
  LOG_DIR="/mnt/c/Users/${WINUSER}/AppData/Local/Temp"
fi
LOG="${LOG_DIR}/mun-devkit-launch.log"
: >"$LOG"

say() {
  echo "$*" | tee -a "$LOG"
}

say "MUN Devkit launch log: $LOG"
say "Repo: $ROOT"
say ""

# Docker Desktop CLI (all-users and per-user installs) for doctor / build later.
export PATH="/mnt/c/Program Files/Docker/Docker/resources/bin:/mnt/c/Users/${WINUSER}/AppData/Local/Programs/DockerDesktop/resources/bin:/mnt/c/Users/${WINUSER}/AppData/Local/Programs/Docker/Docker/resources/bin:${PATH}"

# WSLg display: non-login `wsl -e` shells sometimes miss these after a restart.
if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
  if [ -d /mnt/wslg ] || [ -S /tmp/.X11-unix/X0 ]; then
    export DISPLAY="${DISPLAY:-:0}"
    export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
    export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/mnt/wslg/runtime-dir}"
    say "Set DISPLAY=${DISPLAY} for WSLg."
  fi
fi
say "DISPLAY=${DISPLAY:-<unset>}  WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-<unset>}"

if ! command -v python3 >/dev/null 2>&1; then
  say "python3 is not installed in this WSL distro."
  say "In Ubuntu run:  sudo apt update && sudo apt install -y python3 python3-tk"
  exit 2
fi

if ! python3 -c 'import tkinter' 2>/dev/null; then
  say "Python Tk is missing. Trying to install python3-tk..."
  if sudo -n true 2>/dev/null; then
    sudo apt-get update -qq >>"$LOG" 2>&1
    sudo apt-get install -y -qq python3 python3-tk git make >>"$LOG" 2>&1
  else
    say ""
    say "Could not install automatically (this window cannot ask for your Linux password)."
    say "Open the Ubuntu app and run:"
    say "  sudo apt update && sudo apt install -y python3 python3-tk"
    say "Then double-click MUN Devkit again."
    exit 2
  fi
  if ! python3 -c 'import tkinter' 2>/dev/null; then
    say "python3-tk is still missing after install."
    exit 2
  fi
fi

chmod +x mdk-gui mdk 2>/dev/null || true
say "Starting GUI..."
say ""

# Keep stdout/stderr attached to this console (and append crashes to the log).
./mdk-gui 2> >(tee -a "$LOG" >&2)
status=$?
if [ "$status" -ne 0 ]; then
  say ""
  say "mdk-gui exited with status $status"
fi
exit "$status"
