# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
"""The Godot 3.5 / FRT track has its adapter, sample and packing notes in
tree. Runtime checks need a Godot 3.5 editor or FRT build; those are not
fetched here yet."""

import unittest

from support import ROOT


class Godot3Track(unittest.TestCase):
    def test_adapter_and_sample_exist(self):
        adapter = ROOT / "engines" / "godot3" / "addons" / "mun" / "mun.gd"
        sample = ROOT / "samples" / "hello-mun-godot3" / "addons" / "mun" / "mun.gd"
        self.assertTrue(adapter.is_file(), adapter)
        self.assertTrue(sample.is_file(), sample)
        self.assertTrue((ROOT / "samples" / "hello-mun-godot3" / "project.godot").is_file())
        self.assertTrue((ROOT / "samples" / "hello-mun-godot3" / "main.gd").is_file())
        self.assertTrue((ROOT / "engines" / "godot3" / "README.md").is_file())
        self.assertTrue((ROOT / "engines" / "godot3" / "pack.md").is_file())
        self.assertTrue((ROOT / "engines" / "godot3" / "uds" / "README.md").is_file())

    def test_adapter_is_godot3_shaped(self):
        text = (ROOT / "engines" / "godot3" / "addons" / "mun" / "mun.gd").read_text(encoding="utf-8")
        self.assertIn("StreamPeerUnix", text)
        self.assertIn("yield(get_tree(), \"idle_frame\")", text)
        self.assertIn("File.new()", text)
        self.assertNotIn("StreamPeerUDS.new()", text)
        self.assertNotIn("await ", text)
        self.assertNotIn("FileAccess.", text)

    def test_sample_autoload_points_at_mun(self):
        project = (ROOT / "samples" / "hello-mun-godot3" / "project.godot").read_text(encoding="utf-8")
        self.assertIn('Mun="*res://addons/mun/mun.gd"', project)
        self.assertIn("config_version=4", project)


if __name__ == "__main__":
    unittest.main()
