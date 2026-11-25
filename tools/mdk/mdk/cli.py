# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0

"""mdk: the MUN Devkit host tool.

    mdk doctor          what this computer has and lacks for each step
    mdk os fetch        get the MUN OS revision this devkit is pinned to
    mdk env build       build the SDK build environment (once; needs the network)
    mdk new NAME        start a project from the native sample
    mdk build           build the project inside that environment
    mdk check           inspect the build against its runtime profile
    mdk pack            make the card image with MUN OS's card tool, and record it
    mdk sim             run the game in the session simulator
    mdk gui             open the friendly desktop front-end (docs/gui.md)

Run it in a project directory (one with mun-project.toml), or name one with
--project. Packing and the simulator use MUN OS's own tools from a checkout:
--mun-os, MUN_OS_DIR, the copy `mdk os fetch` makes, or ../mun-os beside the
devkit."""

import argparse
import json
import shutil
import subprocess  # nosec B404: CalledProcessError; cmd_gui starts the local mdk-gui with a fixed argv list
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__, checks, container, new, osrepo, pack, project, sim
from .errors import MdkError


def _project(args) -> "tuple[project.Project, Path]":
    mun_os = osrepo.require(args.mun_os, quiet=getattr(args, "json", False))
    return project.load(Path(args.project), mun_os), mun_os


def cmd_doctor(args) -> int:
    rows: List["tuple[str, str, str]"] = []
    missing = False
    version = sys.version_info
    ok = version >= (3, 9)
    rows.append(("ok" if ok else "MISSING", "Python", f"{version.major}.{version.minor}.{version.micro}"
                 + ("" if ok else " (3.9 or later is needed)")))
    missing |= not ok
    try:
        mun_os = osrepo.find(args.mun_os)
        found = osrepo.identity(mun_os)
        rows.append(("ok" if found["pin"] != "differs" else "differs", "MUN OS tools", osrepo.describe(found)[14:]))
        try:
            image = osrepo.mun_card(mun_os).image
            for name in ("mke2fs", "debugfs"):
                tool = image.find_tool(name)
                rows.append(("ok", name, f"{image.tool_version(tool)} ({tool})"))
        except Exception as exc:  # the card tool raises its own error type
            rows.append(("MISSING", "e2fsprogs", f"{exc}; needed to make cards (macOS: brew install e2fsprogs)"))
            missing = True
    except MdkError as exc:
        rows.append(("MISSING", "MUN OS tools", exc.message + " " + exc.remedy.splitlines()[0]))
        missing = True
    compiler = shutil.which("cc")
    rows.append(("ok" if compiler else "absent", "C compiler", compiler or "only needed for the devkit's own host tests"))
    try:
        container.docker()
    except MdkError as exc:
        rows.append(("absent", "container runtime", exc.message + " Needed for `mdk build`."))
    else:
        try:
            built = container.image_exists()
            # Always name the runtime when it answers: the GUI checklist keys off this row.
            rows.append(("ok", "container runtime", "docker (needed for `mdk build`)"))
            rows.append(("ok" if built else "not built", "SDK environment",
                         container.image_tag() + ("" if built else "; run `mdk env build` (needed for `mdk build`)")))
        except MdkError as exc:      # installed and not answering: nothing to build, something to start
            rows.append(("stopped", "container runtime", f"{exc.message} {exc.remedy} Needed for `mdk build`."))
    for state, name, text in rows:
        print(f"{state:9} {name:16} {text}")
    return 1 if missing else 0


def cmd_os(args) -> int:
    if args.action == "fetch":
        root = osrepo.fetch(args.source)
        print(f"fetched  {root}")
    else:
        root = osrepo.find(args.mun_os)
    found = osrepo.identity(root)
    print(osrepo.describe(found))
    for line in found["differences"]:
        print("  " + line)
    return 0 if found["pin"] != "differs" else 2


def cmd_new(args) -> int:
    mun_os = osrepo.require(args.mun_os)
    made = new.create(args.name, Path(args.directory or args.name), args.title, args.card_id, mun_os)
    print(f"created  {made}")
    print("next     cd there, then: mdk build && mdk pack && mdk sim --container")
    return 0


def cmd_env(args) -> int:
    if args.action == "build":
        container.build_image()
    container.require_image()
    for name, value in container.describe().items():
        print(f"{name:16} {value}")
    return 0


def cmd_build(args) -> int:
    found, mun_os = _project(args)
    print(found.build["run"], flush=True)
    done = container.run(["sh", "-c", found.build["run"]], found.directory, mun_os, tee=True)
    # The build's own commands, kept: some of what a program was built with
    # (stack-clash protection) leaves no mark in the program itself. A build
    # that compiled nothing leaves the record of the one that did.
    log = found.build["run"] + "\n" + done.stdout
    found.output.mkdir(parents=True, exist_ok=True)
    (found.output / "build.log").write_text(log, encoding="utf-8")
    commands = checks.compiler_commands(log)
    if commands:
        (found.output / checks.COMMANDS_FILE).write_text(
            json.dumps({"format": "mdk-compile-commands/1", "commands": commands}, indent=2) + "\n", encoding="utf-8")
    if done.returncode != 0:
        raise MdkError("E-BUILD", f"The build command failed (exit code {done.returncode}).", "Its output is above.")
    if not found.entry.is_file():
        raise MdkError("E-BUILD", f"The build finished without producing {found.build['entry']}.",
                       "Check build.entry in mun-project.toml.")
    found.output.mkdir(parents=True, exist_ok=True)
    record = {"format": "mdk-build-record/1", "mdk": __version__, "environment": container.describe(),
              "entry": found.build["entry"], "entry_sha256": checks.sha256_file(found.entry)}
    (found.output / "BUILD-INFO.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    report = checks.check_project(found, mun_os)
    print(checks.render(report))
    return 0 if report["ok"] else 2


def cmd_check(args) -> int:
    found, mun_os = _project(args)
    report = checks.check_project(found, mun_os)
    if args.json:
        print(json.dumps({**report, "errors": [e.to_dict() for e in report["errors"]],
                          "warnings": [w.to_dict() for w in report["warnings"]]}, indent=2))
    else:
        print(checks.render(report))
    return 0 if report["ok"] else 2


def cmd_pack(args) -> int:
    found, mun_os = _project(args)
    pack.pack(found, mun_os)
    return 0


def _sim_arguments(args) -> List[str]:
    """The simulator's own options, to repeat inside the environment."""
    passed: List[str] = []
    for name in ("stop_after", "stop_when", "timeout", "save_delay", "display"):
        value = getattr(args, name)
        if value is not None:
            passed += ["--" + name.replace("_", "-"), str(value)]
    for value in args.fail or []:
        passed += ["--fail", value]
    for value in args.env or []:
        passed += ["--env", value]
    for flag in ("console_env", "json", "fresh", "hold_saves"):
        if getattr(args, flag):
            passed.append("--" + flag.replace("_", "-"))
    return passed


def cmd_gui(args) -> int:
    """Open the desktop front-end; same tool, buttons instead of argv."""
    del args
    root = Path(__file__).resolve().parents[3]
    script = root / "mdk-gui"
    if not script.is_file():
        raise MdkError("E-GUI", f"The GUI entry point is missing: {script}.",
                       "Use a full checkout of the devkit, or run ./mdk-gui from its root.")
    return subprocess.call([sys.executable, str(script)])  # nosec B603: fixed argv; only the local mdk-gui


def cmd_sim(args) -> int:
    found, mun_os = _project(args)
    if args.container:
        done = container.run(["python3", "/opt/mun-devkit/mdk", "sim", "--project", "/work", *_sim_arguments(args)],
                             found.directory, mun_os)
        return done.returncode
    card_dir = found.output / "sim-card"
    if args.fresh and card_dir.exists():
        shutil.rmtree(card_dir)
    saves = osrepo.mun_card(mun_os).saves
    card = sim.SimCard(card_dir, found.card["id"], found.card["version"], saves)
    extra = {}
    for item in args.env or []:
        name, separator, value = item.partition("=")
        if not separator or not name:
            raise MdkError("E-ARGUMENT", f"--env needs NAME=VALUE, not {item!r}.")
        extra[name] = value
    log = (lambda line: print(line, file=sys.stderr)) if args.json else print
    record = sim.run_session(found.entry, card, found.card["profile"], content=found.content,
                             display=args.display, extra_env=extra, console_env=args.console_env,
                             stop_after=args.stop_after, timeout=args.timeout, fail=sim.parse_fail(args.fail),
                             save_delay=args.save_delay or 0.0, log=log, stop_when=args.stop_when,
                             hold_saves=args.hold_saves)
    print(json.dumps(record, indent=2) if args.json else sim.describe(record))
    return 0 if record["result"] == "exited" and not record["stop"].get("killed") else 3


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(prog="mdk", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    top.add_argument("--version", action="version", version=f"mdk {__version__}")
    sub = top.add_subparsers(dest="command", metavar="COMMAND")

    def command(name: str, function, help_text: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text)
        p.set_defaults(function=function)
        p.add_argument("--project", default=".", metavar="DIR", help="the project directory (default: here)")
        p.add_argument("--mun-os", metavar="DIR", help="the MUN OS checkout to use")
        return p

    command("doctor", cmd_doctor, "what this computer has and lacks")
    p = command("os", cmd_os, "the MUN OS revision the devkit works with")
    p.add_argument("action", choices=("fetch", "info"))
    p.add_argument("--from", dest="source", metavar="PATH_OR_URL",
                   help="fetch from this repository instead of the one the lock names (a local clone avoids the network)")
    p = command("new", cmd_new, "start a project from the native sample")
    p.add_argument("name", help="the project's name: lowercase letters, digits and '-'")
    p.add_argument("--directory", metavar="DIR", help="where to make it (default: ./NAME)")
    p.add_argument("--title", help="the game's title on the card (default: from the name)")
    p.add_argument("--id", dest="card_id", metavar="ID", help="card.id, which names the save (default: game.NAME)")
    p = command("env", cmd_env, "the SDK build environment")
    p.add_argument("action", choices=("build", "info"))
    command("build", cmd_build, "build the project inside the SDK environment")
    p = command("check", cmd_check, "inspect the build against its runtime profile")
    p.add_argument("--json", action="store_true")
    command("pack", cmd_pack, "make the card image and record it")
    p = sub.add_parser("gui", help="open the friendly desktop front-end")
    p.set_defaults(function=cmd_gui)
    p = command("sim", cmd_sim, "run the game in the session simulator")
    p.add_argument("--container", action="store_true",
                   help="run inside the SDK environment (for an AArch64 Linux build on another host)")
    p.add_argument("--stop-after", type=float, metavar="SECONDS",
                   help="end the session as the console does: SIGTERM, then SIGKILL after 3 s")
    p.add_argument("--stop-when", choices=[state for state in sim.STOP_STATES if state], metavar="STATE",
                   help="end it the same way once a save is in the card, unanswered (saving), "
                        "or once the card holds a save of this session (saved)")
    p.add_argument("--timeout", type=float, metavar="SECONDS", help="the simulator's own bound for the run")
    p.add_argument("--fail", action="append", metavar="CODE[:N]",
                   help="answer saves with this code (every save, or the next N): " + ", ".join(sorted(sim.FAULTS)))
    p.add_argument("--save-delay", type=float, metavar="SECONDS", help="how long the simulated card takes to save")
    p.add_argument("--hold-saves", action="store_true",
                   help="the simulated card does not answer a save while the session lasts; "
                        "the save is written when the session ends")
    p.add_argument("--display", default="1920x1080", metavar="WxH", help="MUN_DISPLAY_MODE for a GL-profile game")
    p.add_argument("--env", action="append", metavar="NAME=VALUE", help="add a variable to the game's environment")
    p.add_argument("--console-env", action="store_true",
                   help="also set the profile's device hints as a console does (KMS, ALSA)")
    p.add_argument("--fresh", action="store_true", help="start from a card with no save")
    p.add_argument("--json", action="store_true", help="print the session record as JSON")
    return top


def main(argv: Optional[List[str]] = None) -> int:
    args = parser().parse_args(argv)
    if not getattr(args, "function", None):
        parser().print_help()
        return 64
    try:
        return args.function(args)
    except MdkError as exc:
        print(exc.render(), file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"E-TOOL  {exc}", file=sys.stderr)
        return 1
