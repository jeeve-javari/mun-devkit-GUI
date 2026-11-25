# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0

"""Desktop window: set up the machine, open a project, build / check / pack / sim."""

from __future__ import annotations

import subprocess  # nosec B404: opens a folder with a fixed argv, or starts nothing else
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from . import __version__
from .runner import CommandRunner, RunResult, find_root, parse_doctor
from .theme import COLORS, FONTS, pick_font


class MdkGui(tk.Tk):
    def __init__(self, root: Optional[Path] = None):
        super().__init__()
        self.devkit = find_root(root)
        self.project_dir = tk.StringVar(value=str(self.devkit / "samples" / "hello-mun"))
        self.status = tk.StringVar(value="Ready")
        self._doctor_cache = ""
        self._log_buffer: List[str] = []

        self.title("MUN Devkit")
        self.geometry("980x680")
        self.minsize(820, 560)
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
        style.configure("Card.TFrame", background=COLORS["bg_raised"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=ui)
        style.configure("Dim.TLabel", foreground=COLORS["text_dim"], font=small)
        style.configure("Title.TLabel", font=display, foreground=COLORS["text"], background=COLORS["bg"])
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
                        fieldbackground=COLORS["bg_sunken"], font=small, rowheight=26,
                        borderwidth=0)
        style.configure("Treeview.Heading", background=COLORS["bg_raised"], foreground=COLORS["text_dim"], font=small)
        style.map("Treeview", background=[("selected", COLORS["border"])],
                  foreground=[("selected", COLORS["text"])])

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=18)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="MUN Devkit", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text=f"  friendly front-end · v{__version__}", style="Dim.TLabel").pack(side="left", pady=(8, 0))
        ttk.Label(header, textvariable=self.status, style="Dim.TLabel").pack(side="right", pady=(8, 0))

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)

        self.setup_tab = ttk.Frame(self.notebook, padding=12)
        self.project_tab = ttk.Frame(self.notebook, padding=12)
        self.sim_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.setup_tab, text="  Setup  ")
        self.notebook.add(self.project_tab, text="  Project  ")
        self.notebook.add(self.sim_tab, text="  Simulate  ")

        self._build_setup()
        self._build_project()
        self._build_sim()
        self._build_log(outer)

    def _build_setup(self) -> None:
        ttk.Label(
            self.setup_tab,
            text="One-time setup for this computer. Run these in order; each button calls the same mdk command the CLI uses.",
            style="Dim.TLabel",
            wraplength=700,
        ).pack(anchor="w", pady=(0, 10))

        actions = ttk.Frame(self.setup_tab)
        actions.pack(fill="x", pady=(0, 10))
        ttk.Button(actions, text="Check this computer", style="Accent.TButton",
                   command=self.refresh_doctor).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Fetch MUN OS tools", command=lambda: self._run(["os", "fetch"])).pack(
            side="left", padx=(0, 8))
        ttk.Button(actions, text="Build SDK environment",
                   command=lambda: self._run(["env", "build"])).pack(side="left", padx=(0, 8))

        hint = (
            "Windows (ARM or x86): install WSL 2 + Docker Desktop first, then open this GUI from inside Linux. "
            "On Snapdragon X Elite, ARM64 containers run natively. On x86, Docker emulates linux/arm64."
        )
        ttk.Label(self.setup_tab, text=hint, style="Dim.TLabel", wraplength=720).pack(anchor="w", pady=(0, 10))

        cols = ("state", "name", "detail")
        self.doctor_tree = ttk.Treeview(self.setup_tab, columns=cols, show="headings", height=8)
        self.doctor_tree.heading("state", text="State")
        self.doctor_tree.heading("name", text="Need")
        self.doctor_tree.heading("detail", text="Detail")
        self.doctor_tree.column("state", width=90, stretch=False)
        self.doctor_tree.column("name", width=140, stretch=False)
        self.doctor_tree.column("detail", width=560)
        self.doctor_tree.pack(fill="both", expand=True)

    def _build_project(self) -> None:
        ttk.Label(
            self.project_tab,
            text="Open a project (a folder with mun-project.toml), or start one from the native sample.",
            style="Dim.TLabel",
            wraplength=700,
        ).pack(anchor="w", pady=(0, 10))

        path_row = ttk.Frame(self.project_tab)
        path_row.pack(fill="x", pady=(0, 8))
        ttk.Label(path_row, text="Project").pack(side="left")
        entry = ttk.Entry(path_row, textvariable=self.project_dir)
        entry.pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(path_row, text="Browse…", command=self._browse_project).pack(side="left")

        new_box = ttk.LabelFrame(self.project_tab, text="New project", padding=10)
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

        flow = ttk.LabelFrame(self.project_tab, text="Journey", padding=10)
        flow.pack(fill="x")
        ttk.Label(
            flow,
            text="Same steps as the README: build → check → pack. Each button runs the real mdk command.",
            style="Dim.TLabel",
            wraplength=700,
        ).pack(anchor="w", pady=(0, 8))
        row = ttk.Frame(flow)
        row.pack(fill="x")
        ttk.Button(row, text="Build", style="Accent.TButton",
                   command=lambda: self._run_project(["build"])).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Check", command=lambda: self._run_project(["check"])).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Pack card", command=lambda: self._run_project(["pack"])).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Open project folder", command=self._open_folder).pack(side="left")

    def _build_sim(self) -> None:
        ttk.Label(
            self.sim_tab,
            text="Run the built game as a MUN session. Prefer the container on non-ARM64 hosts.",
            style="Dim.TLabel",
            wraplength=700,
        ).pack(anchor="w", pady=(0, 10))

        self.sim_container = tk.BooleanVar(value=True)
        self.sim_fresh = tk.BooleanVar(value=False)
        self.sim_headless = tk.BooleanVar(value=True)
        opts = ttk.Frame(self.sim_tab)
        opts.pack(fill="x", pady=(0, 8))
        ttk.Checkbutton(opts, text="Run in SDK container (--container)",
                        variable=self.sim_container).pack(anchor="w")
        ttk.Checkbutton(opts, text="Fresh card (no previous save)",
                        variable=self.sim_fresh).pack(anchor="w")
        ttk.Checkbutton(opts, text="Headless sample script (hello-mun)",
                        variable=self.sim_headless).pack(anchor="w")

        self.sim_script = tk.StringVar(value="up up up save wait quit")
        script_row = ttk.Frame(self.sim_tab)
        script_row.pack(fill="x", pady=(4, 12))
        ttk.Label(script_row, text="Sample script", style="Dim.TLabel").pack(anchor="w")
        ttk.Entry(script_row, textvariable=self.sim_script).pack(fill="x")

        ttk.Button(self.sim_tab, text="Simulate session", style="Accent.TButton",
                   command=self._run_sim).pack(anchor="w")

    def _build_log(self, parent: ttk.Frame) -> None:
        bar = ttk.Frame(parent)
        bar.pack(fill="x", pady=(12, 4))
        ttk.Label(bar, text="Log", style="Dim.TLabel").pack(side="left")
        ttk.Button(bar, text="Stop", command=self._cancel).pack(side="right", padx=(8, 0))
        ttk.Button(bar, text="Clear", command=self._clear_log).pack(side="right")

        wrap = tk.Frame(parent, bg=COLORS["border"], bd=0, highlightthickness=0)
        wrap.pack(fill="both", expand=True)
        inner = tk.Frame(wrap, bg=COLORS["bg_sunken"])
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        self.log = tk.Text(
            inner,
            height=12,
            wrap="word",
            bg=COLORS["bg_sunken"],
            fg=COLORS["log"],
            insertbackground=COLORS["text"],
            relief="flat",
            font=self._fonts["mono"],
            padx=10,
            pady=8,
        )
        scroll = ttk.Scrollbar(inner, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.log.configure(state="disabled")

    # --- actions -----------------------------------------------------------------

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

    def _run_project(self, verb: List[str]) -> None:
        path = Path(self.project_dir.get())
        if not (path / "mun-project.toml").is_file():
            messagebox.showerror("Project", f"No mun-project.toml in:\n{path}")
            return
        self._run([*verb, *self._project_args()], cwd=path)

    def _run_sim(self) -> None:
        args = ["sim", *self._project_args()]
        if self.sim_container.get():
            args.append("--container")
        if self.sim_fresh.get():
            args.append("--fresh")
        if self.sim_headless.get():
            args += ["--env", "MUN_HELLO_HEADLESS=1",
                     "--env", f"MUN_HELLO_SCRIPT={self.sim_script.get().strip()}"]
        self._run_project_raw(args)

    def _run_project_raw(self, args: List[str]) -> None:
        path = Path(self.project_dir.get())
        if not (path / "mun-project.toml").is_file():
            messagebox.showerror("Project", f"No mun-project.toml in:\n{path}")
            return
        self._run(args, cwd=path)

    def refresh_doctor(self) -> None:
        self._run(["doctor"], capture_for_doctor=True)

    def _run(self, args: List[str], cwd: Optional[Path] = None, capture_for_doctor: bool = False) -> None:
        if self.runner.busy:
            messagebox.showinfo("Busy", "Wait for the current command to finish, or press Stop.")
            return
        self._capture_doctor = capture_for_doctor
        if capture_for_doctor:
            self._doctor_cache = ""
        shown = " ".join(["mdk", *args])
        self._append_log(f"\n› {shown}")
        self.status.set("Running…")
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
            if getattr(self, "_capture_doctor", False):
                self._fill_doctor(self._doctor_cache)
                self._capture_doctor = False
            if result.cancelled:
                self.status.set("Stopped")
                self._append_log("(stopped)")
            elif result.returncode == 0:
                self.status.set("Done")
                self._append_log(f"(exit {result.returncode})")
            else:
                self.status.set(f"Finished with code {result.returncode}")
                self._append_log(f"(exit {result.returncode})")
        self.after(0, finish)

    def _fill_doctor(self, text: str) -> None:
        for item in self.doctor_tree.get_children():
            self.doctor_tree.delete(item)
        for row in parse_doctor(text):
            self.doctor_tree.insert("", "end", values=(row["state"], row["name"], row["detail"]))

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
