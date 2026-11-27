# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0

"""Desktop window: guided setup, then project build / check / pack / sim."""

from __future__ import annotations

import os
import re
import subprocess  # nosec B404: opens a folder or a help URL with a fixed argv
import sys
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any, Dict, List, Optional

from . import __version__
from .runner import (
    CommandRunner,
    RunResult,
    find_root,
    next_setup_step,
    parse_doctor,
    readiness_from_doctor,
)
from .play import install_and_play, read_project_name, sanitize_card_name
from .state import load_gui_state, save_gui_state, windows_explorer_path
from .theme import COLORS, FONTS, pick_font

DOCKER_HELP_URL = "https://docs.docker.com/desktop/setup/install/windows-install/"


def _windows_docker_desktop_present() -> bool:
    """True when Docker Desktop's files are on the Windows side (seen from WSL)."""
    roots = [
        Path("/mnt/c/Program Files/Docker"),
        Path("/mnt/c/Program Files (x86)/Docker"),
    ]
    users = Path("/mnt/c/Users")
    if users.is_dir():
        for entry in users.iterdir():
            if entry.is_dir():
                roots.append(entry / "AppData/Local/Programs/DockerDesktop")
                roots.append(entry / "AppData/Local/Programs/Docker")
    for root in roots:
        if not root.is_dir():
            continue
        try:
            if any(root.rglob("Docker Desktop.exe")) or any(root.rglob("docker.exe")):
                return True
        except OSError:
            continue
    return False


def open_url(url: str) -> bool:
    """Open a URL in the host browser. From WSL, webbrowser often does nothing."""
    attempts = [
        ["cmd.exe", "/c", "start", "", url],
        ["powershell.exe", "-NoProfile", "-Command", f"Start-Process '{url}'"],
        ["xdg-open", url],
        ["open", url],
    ]
    for command in attempts:
        try:
            done = subprocess.run(  # nosec B603: fixed argv; opens a https URL only
                command, capture_output=True, check=False, timeout=10)
            if done.returncode == 0:
                return True
        except (OSError, subprocess.TimeoutExpired):
            continue
    return bool(webbrowser.open(url))


class MdkGui(tk.Tk):
    def __init__(self, root: Optional[Path] = None):
        super().__init__()
        self.devkit = find_root(root)
        saved = load_gui_state()
        default_project = str(self.devkit / "samples" / "hello-mun")
        project = saved.get("project_dir") or default_project
        if not Path(project).is_dir():
            project = default_project
        self.project_dir = tk.StringVar(value=project)
        self.status = tk.StringVar(value="Ready")
        self.next_step = tk.StringVar(value="Press Check to see what this computer still needs.")
        self._doctor_cache = ""
        self._ready = readiness_from_doctor([])
        self._refresh_after = False
        self._pending_doctor = False
        self._pending_project_dir: Optional[str] = None
        self._pending_play = False
        self._last_args: List[str] = []
        self._run_log: List[str] = []
        self._saved_state = saved

        self.title("MUN Devkit")
        self.geometry(saved.get("geometry") or "980x720")
        self.minsize(860, 600)
        self.configure(bg=COLORS["bg"])
        self._style()
        self._build()
        self._apply_saved_new_fields()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.runner = CommandRunner(self.devkit, self._on_line, self._on_done)
        self.after(200, self.refresh_doctor)

    def _apply_saved_new_fields(self) -> None:
        saved = self._saved_state
        if saved.get("new_name"):
            self.new_name.set(str(saved["new_name"]))
        if saved.get("new_title"):
            self.new_title.set(str(saved["new_title"]))
        if saved.get("new_id"):
            self.new_id.set(str(saved["new_id"]))
        parent = saved.get("new_parent")
        if parent and Path(parent).is_dir():
            self.new_parent.set(str(parent))
        mun_os = saved.get("mun_os_dir")
        if mun_os and Path(mun_os).is_dir():
            self.mun_os_dir.set(str(mun_os))
        if saved.get("play_card_name"):
            self.play_card_name.set(str(saved["play_card_name"]))

    def _collect_state(self) -> Dict[str, Any]:
        return {
            "project_dir": self.project_dir.get().strip(),
            "new_name": self.new_name.get().strip(),
            "new_title": self.new_title.get().strip(),
            "new_id": self.new_id.get().strip(),
            "new_parent": self.new_parent.get().strip(),
            "mun_os_dir": self.mun_os_dir.get().strip(),
            "play_card_name": self.play_card_name.get().strip(),
            "geometry": self.geometry(),
        }

    def _persist_state(self) -> None:
        save_gui_state(self._collect_state())

    def _on_close(self) -> None:
        self._persist_state()
        self.destroy()

    def _style(self) -> None:
        ui = pick_font(FONTS["ui"], 11)
        display = pick_font(FONTS["display"], 20, "bold")
        small = pick_font(FONTS["ui"], 10)
        mono = pick_font(FONTS["mono"], 10)
        self._fonts = {"ui": ui, "display": display, "small": small, "mono": mono}

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=COLORS["bg"], foreground=COLORS["text"], font=ui)
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=ui)
        style.configure("Dim.TLabel", foreground=COLORS["text_dim"], font=small)
        style.configure("Title.TLabel", font=display, foreground=COLORS["text"], background=COLORS["bg"])
        style.configure("Banner.TLabel", foreground=COLORS["accent"], font=ui, background=COLORS["bg_raised"])
        style.configure("Ok.TLabel", foreground=COLORS["ok"], background=COLORS["bg"], font=small)
        style.configure("Bad.TLabel", foreground=COLORS["bad"], background=COLORS["bg"], font=small)
        style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=COLORS["bg_raised"], foreground=COLORS["text_dim"],
                        padding=(14, 8), font=ui)
        style.map("TNotebook.Tab", background=[("selected", COLORS["bg"])],
                  foreground=[("selected", COLORS["accent"])])
        style.configure("Accent.TButton", background=COLORS["accent"], foreground=COLORS["accent_text"],
                        font=ui, padding=(14, 8))
        style.map("Accent.TButton", background=[("active", COLORS["accent_hover"]), ("disabled", COLORS["border"])])
        style.configure("TButton", background=COLORS["bg_raised"], foreground=COLORS["text"],
                        font=ui, padding=(12, 7))
        style.map("TButton", background=[("active", COLORS["border"]), ("disabled", COLORS["bg_sunken"])])
        style.configure("TEntry", fieldbackground=COLORS["bg_sunken"], foreground=COLORS["text"],
                        insertcolor=COLORS["text"])
        style.configure("TLabelframe", background=COLORS["bg"], foreground=COLORS["text_dim"])
        style.configure("TLabelframe.Label", background=COLORS["bg"], foreground=COLORS["text_dim"], font=small)
        style.configure("Treeview", background=COLORS["bg_sunken"], foreground=COLORS["text"],
                        fieldbackground=COLORS["bg_sunken"], font=small, rowheight=26, borderwidth=0)
        style.configure("Treeview.Heading", background=COLORS["bg_raised"], foreground=COLORS["text_dim"], font=small)
        style.map("Treeview", background=[("selected", COLORS["border"])],
                  foreground=[("selected", COLORS["text"])])

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=18)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, text="MUN Devkit", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text=f"  v{__version__}", style="Dim.TLabel").pack(side="left", pady=(8, 0))
        ttk.Label(header, textvariable=self.status, style="Dim.TLabel").pack(side="right", pady=(8, 0))

        banner = tk.Frame(outer, bg=COLORS["bg_raised"], highlightthickness=0)
        banner.pack(fill="x", pady=(0, 12))
        ttk.Label(banner, textvariable=self.next_step, style="Banner.TLabel",
                  wraplength=900, padding=(12, 10)).pack(fill="x")

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)

        self.setup_tab = ttk.Frame(self.notebook, padding=12)
        self.project_tab = ttk.Frame(self.notebook, padding=12)
        self.sim_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.setup_tab, text="  1. Setup  ")
        self.notebook.add(self.project_tab, text="  2. Project  ")
        self.notebook.add(self.sim_tab, text="  3. Simulate  ")

        self._build_setup()
        self._build_project()
        self._build_sim()
        self._build_log(outer)

    def _build_setup(self) -> None:
        ttk.Label(
            self.setup_tab,
            text=("Do these once on this computer. The banner above always says the next thing to press.\n"
                  "Why Docker? MUN games are Linux ARM64 programs; Build / Pack / Simulate run inside a "
                  "container so your Windows PC can compile and run them. Docker is that container engine."),
            style="Dim.TLabel",
            wraplength=720,
        ).pack(anchor="w", pady=(0, 10))

        checklist = ttk.LabelFrame(self.setup_tab, text="Checklist", padding=10)
        checklist.pack(fill="x", pady=(0, 10))
        self.chk_python = ttk.Label(checklist, text="Python — checking…", style="Dim.TLabel")
        self.chk_mun_os = ttk.Label(checklist, text="MUN OS tools — checking…", style="Dim.TLabel")
        self.chk_docker = ttk.Label(checklist, text="Docker — checking…", style="Dim.TLabel")
        self.chk_env = ttk.Label(checklist, text="SDK environment — checking…", style="Dim.TLabel")
        for label in (self.chk_python, self.chk_mun_os, self.chk_docker, self.chk_env):
            label.pack(anchor="w", pady=2)

        actions = ttk.Frame(self.setup_tab)
        actions.pack(fill="x", pady=(0, 8))
        self.btn_check = ttk.Button(actions, text="1. Check again", style="Accent.TButton",
                                    command=self.refresh_doctor)
        self.btn_fetch = ttk.Button(actions, text="2. Get MUN OS tools",
                                    command=self._fetch_os)
        self.btn_docker = ttk.Button(actions, text="3. Diagnose Docker",
                                     command=self._docker_help)
        self.btn_env = ttk.Button(actions, text="4. Build SDK environment",
                                  command=self._build_env)
        for btn in (self.btn_check, self.btn_fetch, self.btn_docker, self.btn_env):
            btn.pack(side="left", padx=(0, 8))

        ttk.Label(
            self.setup_tab,
            text=("If the table already shows SDK environment as “not built”, Docker is working — "
                  "press 4. Build SDK environment. If Docker still needs attention, press 3. Diagnose "
                  "Docker. Typical fix: Docker Desktop → Settings → Resources → WSL integration → "
                  "Ubuntu ON → Apply & Restart, then in PowerShell: wsl --shutdown, reopen this app."),
            style="Dim.TLabel",
            wraplength=720,
        ).pack(anchor="w", pady=(0, 8))

        cols = ("state", "name", "detail")
        self.doctor_tree = ttk.Treeview(self.setup_tab, columns=cols, show="headings", height=5)
        self.doctor_tree.heading("state", text="State")
        self.doctor_tree.heading("name", text="Need")
        self.doctor_tree.heading("detail", text="Detail")
        self.doctor_tree.column("state", width=90, stretch=False)
        self.doctor_tree.column("name", width=140, stretch=False)
        self.doctor_tree.column("detail", width=560)
        self.doctor_tree.pack(fill="both", expand=True)

    def _build_project(self) -> None:
        self.project_gate = ttk.Label(
            self.project_tab,
            text="Finish Setup first (especially Docker) before building.",
            style="Bad.TLabel",
            wraplength=720,
        )
        self.project_gate.pack(anchor="w", pady=(0, 10))

        path_row = ttk.Frame(self.project_tab)
        path_row.pack(fill="x", pady=(0, 8))
        ttk.Label(path_row, text="Project folder").pack(side="left")
        ttk.Entry(path_row, textvariable=self.project_dir).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(path_row, text="Browse…", command=self._browse_project).pack(side="left", padx=(0, 4))
        ttk.Button(path_row, text="New folder…", command=self._new_folder).pack(side="left")

        new_box = ttk.LabelFrame(self.project_tab, text="New project from the sample", padding=10)
        new_box.pack(fill="x", pady=(0, 12))
        self.new_name = tk.StringVar(value="star-well")
        self.new_title = tk.StringVar(value="Star Well")
        self.new_id = tk.StringVar(value="org.example.star-well")
        self.new_parent = tk.StringVar(value=str(self._default_projects_parent()))
        grid = ttk.Frame(new_box)
        grid.pack(fill="x")
        for col, (label, var) in enumerate((
            ("Name", self.new_name),
            ("Title", self.new_title),
            ("Card id (lowercase)", self.new_id),
        )):
            cell = ttk.Frame(grid)
            cell.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0))
            ttk.Label(cell, text=label, style="Dim.TLabel").pack(anchor="w")
            ttk.Entry(cell, textvariable=var).pack(fill="x")
            grid.columnconfigure(col, weight=1)
        parent_row = ttk.Frame(new_box)
        parent_row.pack(fill="x", pady=(10, 0))
        ttk.Label(parent_row, text="Create inside", style="Dim.TLabel").pack(anchor="w")
        parent_pick = ttk.Frame(new_box)
        parent_pick.pack(fill="x", pady=(2, 0))
        ttk.Entry(parent_pick, textvariable=self.new_parent).pack(side="left", fill="x", expand=True)
        ttk.Button(parent_pick, text="Browse…", command=self._browse_new_parent).pack(side="left", padx=(8, 4))
        ttk.Button(parent_pick, text="New folder…",
                   command=lambda: self._new_folder(into=self.new_parent)).pack(side="left")
        ttk.Label(
            new_box,
            text="Creates a new folder named after the project inside that location. Card id must be lowercase.",
            style="Dim.TLabel",
            wraplength=700,
        ).pack(anchor="w", pady=(8, 0))
        ttk.Button(new_box, text="Create project", style="Accent.TButton",
                   command=self._new_project).pack(anchor="w", pady=(10, 0))

        flow = ttk.LabelFrame(self.project_tab, text="Build journey", padding=10)
        flow.pack(fill="x")
        ttk.Label(
            flow,
            text="Build → Check → Pack. These need Docker + the SDK environment from Setup.",
            style="Dim.TLabel",
            wraplength=700,
        ).pack(anchor="w", pady=(0, 8))
        row = ttk.Frame(flow)
        row.pack(fill="x")
        self.btn_build = ttk.Button(row, text="Build", style="Accent.TButton",
                                    command=lambda: self._run_project(["build"]))
        self.btn_check_proj = ttk.Button(row, text="Check", command=lambda: self._run_project(["check"]))
        self.btn_pack = ttk.Button(row, text="Pack card", command=lambda: self._run_project(["pack"]))
        self.btn_open = ttk.Button(row, text="Open folder", command=self._open_folder)
        for btn in (self.btn_build, self.btn_check_proj, self.btn_pack, self.btn_open):
            btn.pack(side="left", padx=(0, 8))

    def _build_sim(self) -> None:
        self.sim_gate = ttk.Label(
            self.sim_tab,
            text="Finish Setup and Build a project first.",
            style="Bad.TLabel",
            wraplength=720,
        )
        self.sim_gate.pack(anchor="w", pady=(0, 10))

        play_box = ttk.LabelFrame(
            self.sim_tab, text="Play in MUN OS (QEMU window)", padding=10)
        play_box.pack(fill="x", pady=(0, 12))
        ttk.Label(
            play_box,
            text="Copies build/<name>.img into mun-os .local/gamecards/ and runs "
                 "`mun play --card …` (same virtual console as PowerShell). "
                 "Pack the card first, or use Pack then Play.",
            style="Dim.TLabel",
            wraplength=860,
        ).pack(anchor="w", pady=(0, 8))

        self.mun_os_dir = tk.StringVar(value=self._default_mun_os_dir())
        mun_row = ttk.Frame(play_box)
        mun_row.pack(fill="x", pady=(0, 6))
        ttk.Label(mun_row, text="mun-os folder").pack(side="left")
        ttk.Entry(mun_row, textvariable=self.mun_os_dir).pack(
            side="left", fill="x", expand=True, padx=8)
        ttk.Button(mun_row, text="Browse…", command=self._browse_mun_os).pack(side="left")

        self.play_card_name = tk.StringVar(
            value=sanitize_card_name(read_project_name(Path(self.project_dir.get()))))
        card_row = ttk.Frame(play_box)
        card_row.pack(fill="x", pady=(0, 8))
        ttk.Label(card_row, text="Card name (2–16 chars)").pack(side="left")
        ttk.Entry(card_row, textvariable=self.play_card_name, width=18).pack(
            side="left", padx=8)
        ttk.Label(
            card_row, text="Short name for mun play --card", style="Dim.TLabel",
        ).pack(side="left")

        play_btns = ttk.Frame(play_box)
        play_btns.pack(fill="x")
        self.btn_play_os = ttk.Button(
            play_btns, text="Play in MUN OS", style="Accent.TButton",
            command=self._play_in_mun_os)
        self.btn_pack_play = ttk.Button(
            play_btns, text="Pack then Play", command=self._pack_then_play)
        self.btn_play_os.pack(side="left", padx=(0, 8))
        self.btn_pack_play.pack(side="left")

        ttk.Separator(self.sim_tab, orient="horizontal").pack(fill="x", pady=(4, 12))

        ttk.Label(
            self.sim_tab,
            text="SDK simulate (container) — short session, not the full QEMU console.",
            style="Dim.TLabel",
            wraplength=700,
        ).pack(anchor="w", pady=(0, 10))

        self.sim_container = tk.BooleanVar(value=True)
        self.sim_fresh = tk.BooleanVar(value=False)
        self.sim_headless = tk.BooleanVar(value=True)
        opts = ttk.Frame(self.sim_tab)
        opts.pack(fill="x", pady=(0, 8))
        ttk.Checkbutton(opts, text="Run inside the SDK container (recommended on Windows)",
                        variable=self.sim_container).pack(anchor="w")
        ttk.Checkbutton(opts, text="Start with a fresh card (no previous save)",
                        variable=self.sim_fresh).pack(anchor="w")
        ttk.Checkbutton(opts, text="Use the hello-mun headless demo script",
                        variable=self.sim_headless).pack(anchor="w")

        self.sim_script = tk.StringVar(value="up up up save wait quit")
        script_row = ttk.Frame(self.sim_tab)
        script_row.pack(fill="x", pady=(4, 12))
        ttk.Label(script_row, text="Demo script", style="Dim.TLabel").pack(anchor="w")
        ttk.Entry(script_row, textvariable=self.sim_script).pack(fill="x")

        self.btn_sim = ttk.Button(self.sim_tab, text="Simulate session",
                                  command=self._run_sim)
        self.btn_sim.pack(anchor="w")

    def _build_log(self, parent: ttk.Frame) -> None:
        bar = ttk.Frame(parent)
        bar.pack(fill="x", pady=(12, 4))
        ttk.Label(bar, text="Details (log)", style="Dim.TLabel").pack(side="left")
        ttk.Button(bar, text="Stop", command=self._cancel).pack(side="right", padx=(8, 0))
        ttk.Button(bar, text="Clear", command=self._clear_log).pack(side="right")

        wrap = tk.Frame(parent, bg=COLORS["border"], bd=0, highlightthickness=0)
        wrap.pack(fill="both", expand=True)
        inner = tk.Frame(wrap, bg=COLORS["bg_sunken"])
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        self.log = tk.Text(
            inner, height=8, wrap="word", bg=COLORS["bg_sunken"], fg=COLORS["log"],
            insertbackground=COLORS["text"], relief="flat", font=self._fonts["mono"],
            padx=10, pady=8,
        )
        scroll = ttk.Scrollbar(inner, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.log.configure(state="disabled")

    # --- setup helpers -----------------------------------------------------------

    def _mark(self, label: ttk.Label, title: str, ok: bool, detail: str) -> None:
        mark = "Ready" if ok else "Needs attention"
        label.configure(text=f"{title} — {mark}. {detail}",
                        style="Ok.TLabel" if ok else "Bad.TLabel")

    def _apply_readiness(self, ready: dict) -> None:
        self._ready = ready
        self.next_step.set(next_setup_step(ready))
        self._mark(self.chk_python, "Python", ready["python"],
                   "3.9+ is installed." if ready["python"] else "Install Python 3.9 or later.")
        self._mark(self.chk_mun_os, "MUN OS tools", ready["mun_os"],
                   "Fetched." if ready["mun_os"] else "Press Get MUN OS tools.")
        if ready["docker"]:
            docker_detail = "Found."
        elif _windows_docker_desktop_present():
            docker_detail = ("Docker Desktop is on Windows, but this app cannot use it yet. "
                             "Turn on WSL integration for Ubuntu, leave Docker running, press Check again.")
        else:
            docker_detail = "Install Docker Desktop, enable WSL integration, then press Check again."
        self._mark(self.chk_docker, "Docker", ready["docker"], docker_detail)
        self._mark(self.chk_env, "SDK environment", ready["sdk_env"],
                   "Built." if ready["sdk_env"] else "Press Build SDK environment after Docker works.")

        can_build = ready["can_build"] and ready["sdk_env"]
        state = "normal" if can_build else "disabled"
        for btn in (self.btn_build, self.btn_check_proj, self.btn_pack, self.btn_sim):
            btn.configure(state=state)
        self.btn_env.configure(state="normal" if ready["docker"] and ready["mun_os"] else "disabled")
        self.btn_fetch.configure(state="normal" if ready["python"] else "disabled")

        if can_build:
            self.project_gate.configure(
                text="Setup looks good. Create or open a project, then Build -> Check -> Pack.",
                style="Ok.TLabel")
            self.sim_gate.configure(
                text="After a successful Build, simulate a session here.",
                style="Ok.TLabel")
        elif not ready["docker"]:
            if _windows_docker_desktop_present():
                msg = ("Docker Desktop is installed, but WSL cannot see it yet. "
                       "Enable WSL integration, restart Docker Desktop, then press 1. Check again.")
            else:
                msg = "Docker is missing - Build and Simulate stay locked until Docker Desktop works in WSL."
            self.project_gate.configure(text=msg, style="Bad.TLabel")
            self.sim_gate.configure(text=msg, style="Bad.TLabel")
        else:
            msg = "Finish Setup (SDK environment) before building."
            self.project_gate.configure(text=msg, style="Bad.TLabel")
            self.sim_gate.configure(text=msg, style="Bad.TLabel")

    def _docker_help_text(self) -> str:
        try:
            import sys
            mdk_tools = str(self.devkit / "tools" / "mdk")
            if mdk_tools not in sys.path:
                sys.path.insert(0, mdk_tools)
            from mdk.container import diagnose_docker
            report = diagnose_docker()
        except Exception as exc:  # diagnosis must never crash the window
            report = f"(diagnose failed: {exc})"
        if self._ready.get("docker"):
            advice = "Docker is available. Press 4. Build SDK environment next."
        else:
            advice = (
                "Docker is still not usable from this app.\n\n"
                "Important:\n"
                "  - Run helper scripts from Windows PowerShell, not from Ubuntu.\n"
                "  - Inside Ubuntu type:  docker version\n"
                "    (never type: wsl -e docker ... inside Ubuntu)\n"
                "  - Per-user Docker installs under:\n"
                "    %LOCALAPPDATA%\\Programs\\DockerDesktop\n"
                "    not only C:\\Program Files\\Docker\n"
                "  - On Snapdragon, use Docker Desktop for Windows - Arm.\n\n"
                "Then:\n"
                "  1. Open Docker Desktop -> Settings -> Resources -> WSL integration\n"
                "  2. Default ON, and Ubuntu (by name) ON\n"
                "  3. Apply & Restart\n"
                "  4. Close this app; in PowerShell: wsl --shutdown\n"
                "  5. Reopen MUN Devkit and press 1. Check again\n"
                "  6. Or run: scripts\\windows\\Fix-DockerInWsl.ps1\n"
            )
        return advice + "\n\n" + report

    def _show_scroll_text(self, title: str, text: str) -> None:
        """messagebox truncates long diagnose output; keep the full report readable."""
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("720x520")
        win.configure(bg=COLORS["bg"])
        frame = ttk.Frame(win, padding=12)
        frame.pack(fill="both", expand=True)
        body = tk.Text(frame, wrap="word", height=24, font=self._fonts["mono"],
                       bg=COLORS["bg_sunken"], fg=COLORS["text"], relief="flat", padx=8, pady=8)
        scroll = ttk.Scrollbar(frame, command=body.yview)
        body.configure(yscrollcommand=scroll.set)
        body.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        body.insert("1.0", text)
        body.configure(state="disabled")
        ttk.Button(win, text="OK", command=win.destroy).pack(pady=(0, 12))
        win.transient(self)
        win.grab_set()
        win.focus_set()

    def _docker_help(self) -> None:
        text = self._docker_help_text()
        self._append_log("\n" + text)
        self._show_scroll_text("Diagnose Docker", text)
        if not self._ready.get("docker") and not _windows_docker_desktop_present():
            if messagebox.askyesno("Docker help", "Open the Docker Desktop download page?"):
                if not open_url(DOCKER_HELP_URL):
                    messagebox.showinfo(
                        "Open this link yourself",
                        "Could not open a browser from WSL.\n\nPaste into Edge or Chrome:\n"
                        + DOCKER_HELP_URL)

    def _fetch_os(self) -> None:
        self._refresh_after = True
        self._run(["os", "fetch"])

    def _build_env(self) -> None:
        if not self._ready.get("docker"):
            self._docker_help()
            return
        self._refresh_after = True
        self._run(["env", "build"])

    # --- project actions ---------------------------------------------------------

    def _default_projects_parent(self) -> Path:
        """Prefer Windows Documents\\MUN Projects when the repo lives under /mnt/c."""
        candidates: List[Path] = []
        parts = self.devkit.resolve().parts
        if "Users" in parts:
            idx = parts.index("Users")
            if idx + 1 < len(parts):
                candidates.append(Path("/mnt/c/Users") / parts[idx + 1] / "Documents")
        users = Path("/mnt/c/Users")
        if users.is_dir():
            for entry in users.iterdir():
                if entry.is_dir() and entry.name not in ("Public", "Default", "Default User", "All Users"):
                    candidates.append(entry / "Documents")
        for docs in candidates:
            if not docs.is_dir():
                continue
            mun = docs / "MUN Projects"
            try:
                mun.mkdir(exist_ok=True)
                return mun
            except OSError:
                return docs
        home = Path.home() / "mun-projects"
        try:
            home.mkdir(exist_ok=True)
        except OSError:
            return Path.home()
        return home

    def _browse_project(self) -> None:
        initial = self.project_dir.get() or str(self._default_projects_parent())
        chosen = filedialog.askdirectory(title="Open an existing project folder",
                                         initialdir=initial, mustexist=True)
        if chosen:
            self.project_dir.set(chosen)
            self._persist_state()

    def _browse_new_parent(self) -> None:
        initial = self.new_parent.get() or str(self._default_projects_parent())
        chosen = filedialog.askdirectory(title="Create the project inside this folder",
                                         initialdir=initial, mustexist=True)
        if chosen:
            self.new_parent.set(chosen)
            self._persist_state()

    def _new_folder(self, into: Optional[tk.StringVar] = None) -> None:
        """Create a folder on disk (Tk's directory picker cannot)."""
        if into is not None:
            start = into.get() or str(self._default_projects_parent())
        else:
            start = self.project_dir.get() or str(self._default_projects_parent())
        parent = filedialog.askdirectory(title="Create a new folder inside…",
                                         initialdir=start, mustexist=True)
        if not parent:
            return
        name = simpledialog.askstring(
            "New folder",
            "Folder name:",
            parent=self,
            initialvalue=self.new_name.get().strip() or "my-game")
        if not name:
            return
        name = name.strip()
        if not name or "/" in name or "\\" in name or name in (".", ".."):
            messagebox.showerror("New folder", "Use a plain folder name (no slashes).")
            return
        path = Path(parent) / name
        try:
            path.mkdir(parents=False, exist_ok=False)
        except FileExistsError:
            messagebox.showerror("New folder", f"Already exists:\n{path}")
            return
        except OSError as exc:
            messagebox.showerror("New folder", f"Could not create folder:\n{exc}")
            return
        if into is not None:
            into.set(str(path))
        else:
            self.project_dir.set(str(path))
        messagebox.showinfo("New folder", f"Created:\n{path}")

    def _open_folder(self) -> None:
        path = Path(self.project_dir.get())
        if not path.is_dir():
            messagebox.showerror(
                "Project",
                f"That folder does not exist yet:\n{path}\n\n"
                "Use New folder… or Create project first, or Browse… to an existing project.")
            return
        try:
            system = self.tk.call("tk", "windowingsystem")
            if system == "win32":
                opener = ["explorer", str(path)]
            elif system == "aqua":
                opener = ["open", str(path)]
            else:
                # From WSL, prefer Windows Explorer for /mnt/<drive>/… paths.
                win_path = windows_explorer_path(path)
                if win_path:
                    opener = ["explorer.exe", win_path]
                else:
                    opener = ["xdg-open", str(path)]
            subprocess.Popen(opener)  # nosec B603: no shell; opens the project folder only
        except OSError as exc:
            messagebox.showerror("Project", str(exc))

    def _new_project(self) -> None:
        name = self.new_name.get().strip()
        if not name:
            messagebox.showerror("New project", "Give the project a name.")
            return
        if not re.fullmatch(r"[a-z][a-z0-9-]{1,39}", name):
            messagebox.showerror(
                "New project",
                "Name must be 2–40 characters: lowercase letters, digits or '-', "
                "starting with a letter.\nExample: tails-from-alteria")
            return
        card_id = self.new_id.get().strip()
        if card_id:
            lowered = card_id.lower()
            if lowered != card_id:
                self.new_id.set(lowered)
                card_id = lowered
            if not re.fullmatch(r"[a-z0-9._-]{3,64}", card_id):
                messagebox.showerror(
                    "New project",
                    "Card id must be 3–64 characters: lowercase letters, digits, "
                    "'.', '-' or '_'.\nExample: org.example.tails-from-alteria")
                return
        parent = Path(self.new_parent.get().strip() or str(self._default_projects_parent()))
        if not parent.is_dir():
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                messagebox.showerror("New project", f"Cannot use parent folder:\n{parent}\n\n{exc}")
                return
        target = parent / name
        if target.exists() and (not target.is_dir() or any(target.iterdir())):
            messagebox.showerror(
                "New project",
                f"Already exists and is not empty:\n{target}\n\n"
                "Pick another name, or Browse… to a different Create inside folder.")
            return
        title = self.new_title.get().strip() or name
        args = ["new", name, "--directory", str(target), "--title", title]
        if card_id:
            args += ["--id", card_id]
        self._pending_project_dir = str(target)
        self._run(args)

    def _project_args(self) -> List[str]:
        return ["--project", self.project_dir.get()]

    def _ensure_can_build(self) -> bool:
        if self._ready.get("can_build") and self._ready.get("sdk_env"):
            return True
        if not self._ready.get("docker"):
            self._docker_help()
        else:
            messagebox.showinfo(
                "Finish Setup",
                "Build needs the SDK environment.\n\nGo to the Setup tab and press "
                "Build SDK environment, then try again.")
            self.notebook.select(self.setup_tab)
        return False

    def _run_project(self, verb: List[str]) -> None:
        if verb[0] in ("build", "pack") and not self._ensure_can_build():
            return
        path = Path(self.project_dir.get())
        if not path.is_dir():
            messagebox.showerror(
                "Project",
                f"That folder does not exist yet:\n{path}\n\n"
                "Create project first, or Browse… to an existing project "
                "(for example samples/hello-mun).")
            return
        if not (path / "mun-project.toml").is_file():
            messagebox.showerror("Project", f"No mun-project.toml in:\n{path}")
            return
        self._run([*verb, *self._project_args()], cwd=path)

    def _default_mun_os_dir(self) -> str:
        saved = (self._saved_state or {}).get("mun_os_dir")
        if saved and Path(saved).is_dir():
            return str(saved)
        home = Path.home()
        for candidate in (
            home / "mun-os",
            Path("/mnt/c/Users") / (os.environ.get("USER") or "user") / "mun-os",
        ):
            if (candidate / "mun").is_file():
                return str(candidate)
        # Common Windows layout when the GUI runs under WSL.
        users = Path("/mnt/c/Users")
        if users.is_dir():
            try:
                for entry in users.iterdir():
                    guess = entry / "mun-os"
                    if (guess / "mun").is_file():
                        return str(guess)
            except OSError:
                pass
        return str(home / "mun-os")

    def _browse_mun_os(self) -> None:
        initial = self.mun_os_dir.get() or str(Path.home())
        chosen = filedialog.askdirectory(
            title="Select your mun-os checkout", initialdir=initial)
        if chosen:
            self.mun_os_dir.set(chosen)

    def _play_in_mun_os(self) -> None:
        project = Path(self.project_dir.get().strip())
        mun_os = Path(self.mun_os_dir.get().strip())
        card = sanitize_card_name(self.play_card_name.get().strip() or read_project_name(project))
        self.play_card_name.set(card)
        try:
            dest, how = install_and_play(project, mun_os, card)
        except (OSError, ValueError, FileNotFoundError) as exc:
            messagebox.showerror("Play in MUN OS", str(exc))
            return
        self._append_log(f"\n> installed card → {dest}")
        self._append_log(f"> launched {how}")
        self._persist_state()
        messagebox.showinfo(
            "Play in MUN OS",
            f"Copied the card as {card}.img and started the console.\n\n{how}\n\n"
            "The QEMU window is separate — this GUI stays usable.")
        # Detached process: do not leave the status stuck on "starting".
        self.status.set("Ready")

    def _pack_then_play(self) -> None:
        if not self._ensure_can_build():
            return
        self._pending_play = True
        self._run_project(["pack"])

    def _run_sim(self) -> None:
        if self.sim_container.get() and not self._ensure_can_build():
            return
        args = ["sim", *self._project_args()]
        if self.sim_container.get():
            args.append("--container")
        if self.sim_fresh.get():
            args.append("--fresh")
        if self.sim_headless.get():
            args += ["--env", "MUN_HELLO_HEADLESS=1",
                     "--env", f"MUN_HELLO_SCRIPT={self.sim_script.get().strip()}"]
        path = Path(self.project_dir.get())
        if not (path / "mun-project.toml").is_file():
            messagebox.showerror("Project", f"No mun-project.toml in:\n{path}")
            return
        self._run(args, cwd=path)

    def refresh_doctor(self) -> None:
        self._run(["doctor"], capture_for_doctor=True)

    def _run(self, args: List[str], cwd: Optional[Path] = None, capture_for_doctor: bool = False) -> None:
        if self.runner.busy:
            messagebox.showinfo("Busy", "Wait for the current step to finish, or press Stop.")
            return
        self._capture_doctor = capture_for_doctor
        self._pending_doctor = capture_for_doctor
        self._last_args = list(args)
        self._run_log = []
        if capture_for_doctor:
            self._doctor_cache = ""
        if args[:1] != ["new"]:
            self._pending_project_dir = None
        shown = " ".join(["mdk", *args])
        self._append_log(f"\n> {shown}")
        self.status.set("Working...")
        self.runner.run(args, cwd=cwd)

    def _cancel(self) -> None:
        self.runner.cancel()
        self.status.set("Stopping…")

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _on_line(self, line: str) -> None:
        self._run_log.append(line)
        self.after(0, lambda text=line: self._append_log(text))
        if getattr(self, "_capture_doctor", False):
            self._doctor_cache += line + "\n"

    def _on_done(self, result: RunResult) -> None:
        def finish() -> None:
            was_doctor = self._pending_doctor
            pending_project = self._pending_project_dir
            if getattr(self, "_capture_doctor", False):
                self._fill_doctor(self._doctor_cache)
                self._capture_doctor = False
            self._pending_doctor = False
            if result.cancelled:
                self.status.set("Stopped")
                self._append_log("(stopped)")
                self._pending_project_dir = None
                self._pending_play = False
            elif result.returncode == 0:
                self.status.set("Done")
                self._append_log("(ok)")
                if pending_project:
                    self.project_dir.set(pending_project)
                    self._pending_project_dir = None
                    self._persist_state()
                    messagebox.showinfo(
                        "Project created",
                        f"Created:\n{pending_project}\n\n"
                        "Next: press Build on this tab.")
                else:
                    self._persist_state()
                if self._pending_play:
                    self._pending_play = False
                    self.after(100, self._play_in_mun_os)
            elif was_doctor:
                # doctor exits 1 when something is missing — expected during setup
                self.status.set("Checked")
                self._append_log("(check finished — see checklist above)")
                self._pending_play = False
            else:
                self.status.set("Needs attention")
                self._append_log(f"(could not finish - code {result.returncode})")
                self._pending_project_dir = None
                self._pending_play = False
                self._explain_failure(result)
            if self._refresh_after and result.returncode == 0 and not result.cancelled:
                self._refresh_after = False
                self.refresh_doctor()
            elif self._refresh_after:
                self._refresh_after = False
        self.after(0, finish)

    def _explain_failure(self, result: RunResult) -> None:
        joined = " ".join(self._last_args)
        log_text = "\n".join(self._run_log) + "\n" + self.log.get("1.0", "end")
        if "E-ENV-DOCKER" in log_text or "No container runtime found" in log_text:
            self._docker_help()
            return
        if "E-OS-TOOLS" in log_text or "No MUN OS checkout" in log_text:
            messagebox.showinfo(
                "MUN OS tools",
                "The MUN OS tools are not on this computer yet.\n\n"
                "On the Setup tab, press Get MUN OS tools, then try again.")
            self.notebook.select(self.setup_tab)
            return
        if result.returncode not in (0, 2):
            detail_lines = [line for line in self._run_log if line.strip()]
            # Prefer the mdk error code line when present.
            interesting = [line for line in detail_lines
                           if line.startswith("E-") or "error" in line.lower()
                           or "cannot" in line.lower() or "not valid" in line.lower()]
            snippet = "\n".join((interesting or detail_lines)[-8:])
            message = f"The step '{joined}' did not finish."
            if snippet:
                message += f"\n\n{snippet}"
            if "E-CARD-ID" in log_text or "card.id" in log_text:
                message += ("\n\nCard id must be lowercase "
                            "(example: org.example.tails-from-alteria).")
            messagebox.showerror("Something went wrong", message)

    def _fill_doctor(self, text: str) -> None:
        for item in self.doctor_tree.get_children():
            self.doctor_tree.delete(item)
        rows = parse_doctor(text)
        for row in rows:
            friendly = {
                "ok": "ok",
                "MISSING": "missing",
                "absent": "missing",
                "not built": "not built",
                "stopped": "stopped",
                "differs": "ok*",
            }.get(row["state"], row["state"])
            self.doctor_tree.insert("", "end", values=(friendly, row["name"], row["detail"]))
        self._apply_readiness(readiness_from_doctor(rows))

    def _append_log(self, line: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")


def main(argv: Optional[List[str]] = None) -> int:
    del argv  # reserved for future flags
    try:
        app = MdkGui()
    except tk.TclError as exc:
        print("MUN Devkit could not open a window.", file=sys.stderr)
        print(f"  {exc}", file=sys.stderr)
        print("On Windows 11, WSLg draws the GUI. Try in PowerShell:", file=sys.stderr)
        print("  wsl --update", file=sys.stderr)
        print("  wsl --shutdown", file=sys.stderr)
        print("Then open MUN Devkit again.", file=sys.stderr)
        return 1
    app.mainloop()
    return 0
