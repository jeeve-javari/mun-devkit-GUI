# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0

"""Desktop window: guided setup, then project build / check / pack / sim."""

from __future__ import annotations

import subprocess  # nosec B404: opens a folder or a help URL with a fixed argv
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from . import __version__
from .runner import (
    CommandRunner,
    RunResult,
    find_root,
    next_setup_step,
    parse_doctor,
    readiness_from_doctor,
)
from .theme import COLORS, FONTS, pick_font

DOCKER_HELP_URL = "https://docs.docker.com/desktop/setup/install/windows-install/"


def _windows_docker_desktop_present() -> bool:
    """True when Docker Desktop's files are on the Windows side (seen from WSL)."""
    return any(Path(p).is_file() for p in (
        "/mnt/c/Program Files/Docker/Docker/Docker Desktop.exe",
        "/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe",
        "/mnt/c/Program Files/Docker/Docker/resources/bin/docker",
    ))


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
        self.project_dir = tk.StringVar(value=str(self.devkit / "samples" / "hello-mun"))
        self.status = tk.StringVar(value="Ready")
        self.next_step = tk.StringVar(value="Press Check to see what this computer still needs.")
        self._doctor_cache = ""
        self._ready = readiness_from_doctor([])
        self._refresh_after = False
        self._pending_doctor = False
        self._last_args: List[str] = []

        self.title("MUN Devkit")
        self.geometry("980x720")
        self.minsize(860, 600)
        self.configure(bg=COLORS["bg"])
        self._style()
        self._build()
        self.runner = CommandRunner(self.devkit, self._on_line, self._on_done)
        self.after(200, self.refresh_doctor)

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
            text="Do these once on this computer. The banner above always says the next thing to press.",
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
        self.btn_docker = ttk.Button(actions, text="3. Docker help",
                                     command=self._docker_help)
        self.btn_env = ttk.Button(actions, text="4. Build SDK environment",
                                  command=self._build_env)
        for btn in (self.btn_check, self.btn_fetch, self.btn_docker, self.btn_env):
            btn.pack(side="left", padx=(0, 8))

        ttk.Label(
            self.setup_tab,
            text=("There is no Install Docker button inside this app — Docker Desktop is a separate "
                  "Windows installer. After you install it: open Docker Desktop, enable WSL integration "
                  "for Ubuntu, leave it running, then press 1. Check again."),
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
        ttk.Button(path_row, text="Browse…", command=self._browse_project).pack(side="left")

        new_box = ttk.LabelFrame(self.project_tab, text="New project from the sample", padding=10)
        new_box.pack(fill="x", pady=(0, 12))
        self.new_name = tk.StringVar(value="star-well")
        self.new_title = tk.StringVar(value="Star Well")
        self.new_id = tk.StringVar(value="org.example.star-well")
        grid = ttk.Frame(new_box)
        grid.pack(fill="x")
        for col, (label, var) in enumerate((
            ("Name", self.new_name),
            ("Title", self.new_title),
            ("Card id", self.new_id),
        )):
            cell = ttk.Frame(grid)
            cell.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0))
            ttk.Label(cell, text=label, style="Dim.TLabel").pack(anchor="w")
            ttk.Entry(cell, textvariable=var).pack(fill="x")
            grid.columnconfigure(col, weight=1)
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

        ttk.Label(
            self.sim_tab,
            text="Run your built game as a short MUN session (saves, restore, quit).",
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

        self.btn_sim = ttk.Button(self.sim_tab, text="Simulate session", style="Accent.TButton",
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
        if self._ready.get("docker"):
            return ("Docker is already available here.\n\n"
                    "Press 4. Build SDK environment next.")
        if _windows_docker_desktop_present():
            return (
                "Docker Desktop is installed on Windows, but this app (running in WSL) "
                "still cannot see it.\n\n"
                "Do this:\n"
                "  1. Open Docker Desktop (whale icon in the tray)\n"
                "  2. Settings -> Resources -> WSL integration\n"
                "  3. Turn on integration for Ubuntu\n"
                "  4. Apply & Restart\n"
                "  5. Come back here and press 1. Check again\n\n"
                "If it still fails: in PowerShell run  wsl --shutdown  then reopen this app."
            )
        return (
            "This app cannot install Docker for you - Docker Desktop is a separate Windows program.\n\n"
            "After you download it:\n"
            "  1. Run the Docker Desktop installer\n"
            "  2. Open Docker Desktop -> Settings -> Resources -> WSL integration\n"
            "     and turn it on for Ubuntu\n"
            "  3. Leave Docker Desktop running\n"
            "  4. Press 1. Check again in this window\n\n"
            "On Snapdragon X Elite, containers run natively once that works."
        )

    def _docker_help(self) -> None:
        text = self._docker_help_text()
        if self._ready.get("docker"):
            messagebox.showinfo("Docker", text)
            return
        if _windows_docker_desktop_present():
            messagebox.showinfo("Docker Desktop needs WSL integration", text)
            return
        if messagebox.askyesno("Docker help", text + "\n\nOpen the Docker Desktop download page in your browser?"):
            if not open_url(DOCKER_HELP_URL):
                messagebox.showinfo(
                    "Open this link yourself",
                    "Could not open a browser from WSL.\n\nPaste this into Edge or Chrome:\n"
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

    def _browse_project(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.project_dir.get() or str(self.devkit))
        if chosen:
            self.project_dir.set(chosen)

    def _open_folder(self) -> None:
        path = Path(self.project_dir.get())
        if not path.is_dir():
            messagebox.showerror("Project", f"Not a folder:\n{path}")
            return
        try:
            system = self.tk.call("tk", "windowingsystem")
            if system == "win32":
                opener = ["explorer", str(path)]
            elif system == "aqua":
                opener = ["open", str(path)]
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
        parent = filedialog.askdirectory(title="Where should the project be created?",
                                         initialdir=str(Path.home()))
        if not parent:
            return
        target = Path(parent) / name
        args = ["new", name, "--directory", str(target), "--title", self.new_title.get().strip() or name]
        card_id = self.new_id.get().strip()
        if card_id:
            args += ["--id", card_id]
        self.project_dir.set(str(target))
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
        if not (path / "mun-project.toml").is_file():
            messagebox.showerror("Project", f"No mun-project.toml in:\n{path}")
            return
        self._run([*verb, *self._project_args()], cwd=path)

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
        if capture_for_doctor:
            self._doctor_cache = ""
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
        self.after(0, lambda: self._append_log(line))
        if getattr(self, "_capture_doctor", False):
            self._doctor_cache += line + "\n"

    def _on_done(self, result: RunResult) -> None:
        def finish() -> None:
            was_doctor = self._pending_doctor
            if getattr(self, "_capture_doctor", False):
                self._fill_doctor(self._doctor_cache)
                self._capture_doctor = False
            self._pending_doctor = False
            if result.cancelled:
                self.status.set("Stopped")
                self._append_log("(stopped)")
            elif result.returncode == 0:
                self.status.set("Done")
                self._append_log("(ok)")
            elif was_doctor:
                # doctor exits 1 when something is missing — expected during setup
                self.status.set("Checked")
                self._append_log("(check finished — see checklist above)")
            else:
                self.status.set("Needs attention")
                self._append_log(f"(could not finish - code {result.returncode})")
                self._explain_failure(result)
            if self._refresh_after and result.returncode == 0 and not result.cancelled:
                self._refresh_after = False
                self.refresh_doctor()
            elif self._refresh_after:
                self._refresh_after = False
        self.after(0, finish)

    def _explain_failure(self, result: RunResult) -> None:
        joined = " ".join(self._last_args)
        log_text = self.log.get("1.0", "end")
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
            messagebox.showinfo(
                "Something went wrong",
                f"The step '{joined}' did not finish.\n\n"
                "Read the Details log below - it has the same message mdk prints.")

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
    app = MdkGui()
    app.mainloop()
    return 0
