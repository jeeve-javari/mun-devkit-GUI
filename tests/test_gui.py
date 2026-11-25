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

    def test_gui_entry_points_exist(self):
        self.assertTrue((ROOT / "mdk-gui").is_file())
        self.assertTrue((ROOT / "MUN Devkit.bat").is_file())
        self.assertTrue((ROOT / "tools" / "gui" / "app.py").is_file())
        self.assertTrue((ROOT / "docs" / "gui.md").is_file())
        self.assertTrue((ROOT / "scripts" / "windows" / "Launch-MdkGui.bat").is_file())
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
