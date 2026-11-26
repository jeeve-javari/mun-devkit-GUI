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
