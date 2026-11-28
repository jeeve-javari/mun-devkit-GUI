# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0

"""`mdk doctor` tells apart the three states of the container runtime: not
installed, installed and not running, and running without the SDK
environment built. Each has a different next step.

The runtime is a stand-in here: a `docker` first on PATH that answers as
the real one does in each state."""

import os
import subprocess  # nosec B404: runs mdk as a developer would
import sys
from unittest import mock

from support import ROOT, Scratch

from mdk import container
from mdk.errors import MdkError

STOPPED = """#!/bin/sh
echo "failed to connect to the docker API at unix:///var/run/docker.sock; check if the path is correct and if the daemon is running" >&2
exit 1
"""
RUNNING_WITHOUT_IMAGE = """#!/bin/sh
[ "$1" = info ] && { echo 29.0.0; exit 0; }
echo "Error response from daemon: No such image" >&2
exit 1
"""
RUNNING_WITH_IMAGE = "#!/bin/sh\nexit 0\n"


class Doctor(Scratch):
    def runtime(self, script: str) -> dict:
        """An environment whose `docker` is `script`."""
        (self.scratch / "bin").mkdir(exist_ok=True)
        program = self.scratch / "bin" / "docker"
        program.write_text(script, encoding="utf-8")
        program.chmod(0o755)
        return dict(os.environ, PATH=f"{self.scratch / 'bin'}{os.pathsep}{os.environ['PATH']}")

    def doctor(self, environment: dict) -> str:
        done = subprocess.run(  # nosec B603: this Python and this repository's mdk, no shell, with arguments the test wrote
            [sys.executable, str(ROOT / "mdk"), "doctor"], capture_output=True, text=True, env=environment)
        lines = done.stdout.splitlines()
        for line in lines:
            if "SDK environment" in line:
                return line
        for line in lines:
            if "runtime" in line:
                return line
        return done.stdout + done.stderr

    def test_a_runtime_that_is_not_running_is_said_to_be_stopped_not_unbuilt(self):
        line = self.doctor(self.runtime(STOPPED))
        self.assertTrue(line.startswith("stopped"), line)
        self.assertIn("not running", line)
        self.assertNotIn("env build", line)

    def test_a_running_runtime_without_the_environment_asks_for_the_build(self):
        line = self.doctor(self.runtime(RUNNING_WITHOUT_IMAGE))
        self.assertTrue(line.startswith("not built"), line)
        self.assertIn("mdk env build", line)

    def test_a_running_runtime_with_the_environment_is_ok(self):
        self.assertTrue(self.doctor(self.runtime(RUNNING_WITH_IMAGE)).startswith("ok"))

    def test_no_runtime_at_all_is_absent(self):
        # A PATH with nothing on it: this Python is started by its own path,
        # and doctor reports whatever else it then lacks without stopping.
        empty = self.scratch / "empty"
        empty.mkdir()
        line = self.doctor(dict(os.environ, PATH=str(empty)))
        self.assertTrue(line.startswith("absent"), line)

    def test_what_needs_the_environment_says_why_it_cannot_run(self):
        with mock.patch.dict(os.environ, self.runtime(STOPPED)):
            with self.assertRaises(MdkError) as raised:
                container.require_image()
        self.assertEqual(raised.exception.code, "E-ENV-RUNTIME")
        with mock.patch.dict(os.environ, self.runtime(RUNNING_WITHOUT_IMAGE)):
            with self.assertRaises(MdkError) as raised:
                container.require_image()
        self.assertEqual(raised.exception.code, "E-ENV")


if __name__ == "__main__":
    import unittest
    unittest.main()
