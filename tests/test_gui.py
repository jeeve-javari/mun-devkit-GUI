# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
"""The GUI runner finds the tree and parses doctor without opening a window."""

import sys
import unittest
from pathlib import Path

from support import ROOT

sys.path.insert(0, str(ROOT / "tools" / "gui"))
from runner import find_root, parse_doctor  # after the path above, on purpose


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

    def test_gui_entry_points_exist(self):
        self.assertTrue((ROOT / "mdk-gui").is_file())
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
