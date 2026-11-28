# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
"""The GUI runner finds the tree and parses doctor without opening a window."""

import sys
import unittest

from support import ROOT

sys.path.insert(0, str(ROOT / "tools" / "gui"))
from runner import (  # after the path above, on purpose
    find_root,
    next_setup_step,
    parse_doctor,
    readiness_from_doctor,
)


class GuiRunner(unittest.TestCase):
    def test_find_root_from_tools_gui(self):
        self.assertEqual(find_root(ROOT / "tools" / "gui" / "runner.py"), ROOT)

    def test_parse_doctor_rows(self):
        text = (
            "ok        Python           3.12.3\n"
            "MISSING   MUN OS tools     run mdk os fetch\n"
            "not built SDK environment  mun-devkit-sdk; run `mdk env build`\n"
            "absent    container runtime No container runtime found (docker).\n"
        )
        rows = parse_doctor(text)
        self.assertEqual(rows[0]["state"], "ok")
        self.assertEqual(rows[0]["name"], "Python")
        self.assertIn("3.12", rows[0]["detail"])
        self.assertEqual(rows[1]["state"], "MISSING")
        self.assertEqual(rows[1]["name"], "MUN OS tools")
        self.assertEqual(rows[2]["state"], "not built")
        self.assertEqual(rows[2]["name"], "SDK environment")
        self.assertEqual(rows[3]["state"], "absent")
        self.assertEqual(rows[3]["name"], "container runtime")
        ready = readiness_from_doctor(rows)
        self.assertTrue(ready["python"])
        self.assertFalse(ready["mun_os"])
        self.assertFalse(ready["docker"])
        self.assertFalse(ready["can_build"])
        self.assertIn("Get MUN OS tools", next_setup_step(ready))
        docker_next = readiness_from_doctor([
            {"state": "ok", "name": "Python", "detail": "3"},
            {"state": "ok", "name": "MUN OS tools", "detail": "x"},
            {"state": "absent", "name": "container runtime", "detail": "no"},
        ])
        self.assertIn("Docker Desktop", next_setup_step(docker_next))
        # Doctor used to omit "container runtime ok" when the engine answered;
        # SDK environment "not built" still means Docker works.
        inferred = readiness_from_doctor([
            {"state": "ok", "name": "Python", "detail": "3"},
            {"state": "ok", "name": "MUN OS tools", "detail": "x"},
            {"state": "not built", "name": "SDK environment", "detail": "run mdk env build"},
        ])
        self.assertTrue(inferred["docker"])
        self.assertFalse(inferred["sdk_env"])
        self.assertIn("Build SDK environment", next_setup_step(inferred))

    def test_gui_entry_points_exist(self):
        self.assertTrue((ROOT / "mdk-gui").is_file())
        self.assertTrue((ROOT / "MUN Devkit.bat").is_file())
        self.assertTrue((ROOT / "tools" / "gui" / "app.py").is_file())
        self.assertTrue((ROOT / "docs" / "gui.md").is_file())
        self.assertTrue((ROOT / "scripts" / "windows" / "Launch-MdkGui.bat").is_file())
        self.assertTrue((ROOT / "scripts" / "windows" / "launch-mdk-gui-wsl.sh").is_file())
        self.assertTrue((ROOT / "scripts" / "windows" / "Install-MdkGui.ps1").is_file())


class GuiHelp(unittest.TestCase):
    def test_mdk_lists_gui(self):
        import subprocess  # nosec B404: runs the local mdk --help only

        done = subprocess.run(  # nosec B603: fixed argv, no shell
            [sys.executable, str(ROOT / "mdk"), "--help"],
            capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(done.returncode, 0)
        self.assertIn("gui", done.stdout)

    def test_diagnose_docker_runs(self):
        from mdk.container import diagnose_docker

        text = diagnose_docker()
        self.assertIn("Docker diagnose:", text)
        self.assertIn("PATH docker:", text)


class GuiPlay(unittest.TestCase):
    def test_sanitize_card_name(self):
        from play import sanitize_card_name

        self.assertEqual(sanitize_card_name("tails-from-alteria"), "tails-from-alter")
        self.assertEqual(sanitize_card_name("Tails"), "tails")
        self.assertEqual(sanitize_card_name("x"), "game")
        self.assertTrue(2 <= len(sanitize_card_name("ab")) <= 16)

    def test_find_packed_image_prefers_project_name(self):
        import tempfile
        from pathlib import Path
        from play import find_packed_image

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build = root / "build"
            build.mkdir()
            (build / "other.img").write_bytes(b"a")
            wanted = build / "tails.img"
            wanted.write_bytes(b"b")
            self.assertEqual(find_packed_image(root, "tails"), wanted)


class GuiUpdate(unittest.TestCase):
    def test_check_and_ff_pull(self):
        import subprocess
        import tempfile
        from pathlib import Path

        import gitenv
        from update import UpdateError, apply_update, check_for_updates, restart_command

        tmp = Path(tempfile.mkdtemp(prefix="mdk-upd-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        env = gitenv.isolate(self, tmp / "git-home")
        bare = tmp / "remote.git"
        work = tmp / "work"
        clone = tmp / "clone"
        bare.mkdir()
        subprocess.run(  # nosec B603, B607: no shell; git from PATH, fixed argv for a temp bare repo
            ["git", "init", "--bare", str(bare)], check=True, env=env,
            capture_output=True)
        subprocess.run(  # nosec B603, B607: no shell; git from PATH, fixed argv to clone the temp bare
            ["git", "clone", str(bare), str(work)], check=True, env=env,
            capture_output=True)
        (work / "README").write_text("one\n", encoding="utf-8")
        for cmd in (
            ["git", "-C", str(work), "add", "README"],
            ["git", "-C", str(work), "commit", "-m", "one"],
            ["git", "-C", str(work), "branch", "-M", "main"],
            ["git", "-C", str(work), "push", "-u", "origin", "main"],
        ):
            subprocess.run(cmd, check=True, env=env, capture_output=True)  # nosec B603: no shell; fixed git argv list the test built
        subprocess.run(  # nosec B603, B607: no shell; git from PATH, fixed argv to clone again for the updater
            ["git", "clone", str(bare), str(clone)], check=True, env=env,
            capture_output=True)

        status = check_for_updates(clone, fetch=True)
        self.assertEqual(status.behind, 0)
        self.assertFalse(status.dirty)

        (work / "README").write_text("two\n", encoding="utf-8")
        for cmd in (
            ["git", "-C", str(work), "add", "README"],
            ["git", "-C", str(work), "commit", "-m", "two"],
            ["git", "-C", str(work), "push"],
        ):
            subprocess.run(cmd, check=True, env=env, capture_output=True)  # nosec B603: no shell; fixed git argv list the test built

        status = check_for_updates(clone, fetch=True)
        self.assertEqual(status.behind, 1)
        self.assertIn("two", status.log)
        after = apply_update(clone, status)
        self.assertEqual(after.behind, 0)
        self.assertEqual((clone / "README").read_text(encoding="utf-8"), "two\n")

        (clone / "dirty.txt").write_text("x", encoding="utf-8")
        dirty = check_for_updates(clone, fetch=False)
        self.assertTrue(dirty.dirty)
        with self.assertRaises(UpdateError):
            apply_update(clone, dirty)

        cmd = restart_command(ROOT)
        self.assertEqual(cmd[0], sys.executable)
        self.assertTrue(str(cmd[1]).endswith("mdk-gui"))

    def test_restart_command_prefers_mdk_gui(self):
        from update import restart_command

        cmd = restart_command(ROOT)
        self.assertIn("mdk-gui", cmd[1])


class GuiEngines(unittest.TestCase):
    def test_lanes_cover_major_engines(self):
        from engines import LANES, get_lane, lane_from_combo, summary_rows

        ids = {lane.id for lane in LANES}
        self.assertTrue({"native", "godot35", "godot47", "unity", "unreal", "other"} <= ids)
        self.assertEqual(get_lane("unity").status, "planned")
        self.assertEqual(get_lane("godot35").status, "ready")
        self.assertEqual(get_lane("native").action, "mdk_new")
        self.assertEqual(get_lane("godot35").action, "copy_sample")
        self.assertEqual(get_lane("godot36").action, "guide")
        picked = lane_from_combo(get_lane("unreal").combo_label)
        self.assertEqual(picked.id, "unreal")
        rows = summary_rows()
        self.assertEqual(len(rows), len(LANES))
        self.assertTrue(all("status" in row and "blurb" in row for row in rows))

    def test_copy_sample_and_detect(self):
        import tempfile
        from pathlib import Path
        from engines import copy_sample_project, detect_lane

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "probe"
            copy_sample_project(
                ROOT, "samples/hello-mun-godot3", dest,
                title="Probe", name="probe")
            self.assertTrue((dest / "project.godot").is_file())
            self.assertTrue((dest / "addons" / "mun" / "mun.gd").is_file())
            self.assertTrue((dest / "mun-project.toml").is_file())
            self.assertFalse((dest / "build").exists())
            self.assertEqual(detect_lane(dest), "godot35")
            self.assertEqual(detect_lane(ROOT / "samples" / "hello-mun"), "native")
            self.assertEqual(detect_lane(ROOT / "samples" / "hello-mun-godot"), "godot47")


class GuiState(unittest.TestCase):
    def test_windows_explorer_path_maps_mnt_drive(self):
        from pathlib import Path
        from state import windows_explorer_path

        self.assertEqual(
            windows_explorer_path(Path("/mnt/c/Godot Game Development/Projects/Tails")),
            r"C:\Godot Game Development\Projects\Tails")
        self.assertEqual(windows_explorer_path(Path("/mnt/c")), "C:\\")
        self.assertIsNone(windows_explorer_path(Path("/home/user/project")))

    def test_gui_state_round_trip(self):
        import tempfile
        from pathlib import Path
        from state import load_gui_state, save_gui_state

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gui-state.json"
            save_gui_state({
                "project_dir": "/mnt/c/Godot Game Development/Projects/Tails From Alteria GD 3.5",
                "new_name": "tails-from-alteria",
                "new_title": "Tails From Alteria",
                "new_id": "org.jeeve.tails-from-alteria",
            }, path)
            loaded = load_gui_state(path)
            self.assertEqual(
                loaded["project_dir"],
                "/mnt/c/Godot Game Development/Projects/Tails From Alteria GD 3.5")
            self.assertEqual(loaded["new_id"], "org.jeeve.tails-from-alteria")
            self.assertEqual(load_gui_state(Path(tmp) / "missing.json"), {})
