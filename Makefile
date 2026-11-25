# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
# MUN Devkit. `make check` runs what this computer can run and says what it
# skipped; `make check-full` fails on what it cannot run; `make sample`
# builds and packs the native sample; `make dev-tools` installs the pinned
# analysers and `make analyse` runs them.
PYTHON ?= python3
MDK     = $(PYTHON) mdk
VENV    = .local/venv
PYTHON_SOURCES = mdk tools tests samples engines

check:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v
	$(MAKE) -C samples/hello-mun test BUILD=build/host

# The same tests as a gate: one that cannot run here fails instead of being
# skipped. Needs the SDK environment, the sample's build, the engine and the
# analysers (`make env sample dev-tools`, `engines/godot/fetch.sh`).
check-full:
	MDK_REQUIRE_ALL=1 $(PYTHON) -m unittest discover -s tests -p 'test_*.py'
	$(MAKE) -C samples/hello-mun test BUILD=build/host

sample:
	$(MDK) build --project samples/hello-mun
	$(MDK) pack --project samples/hello-mun

env:
	$(MDK) env build

# The analysers, at the versions and hashes of tools/dev-requirements.txt,
# in a virtual environment of the devkit's own (needs the network once).
dev-tools:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install --disable-pip-version-check --require-hashes -r tools/dev-requirements.txt

# Every warning is either fixed or marked on its line with its rule and the
# reason (tests/test_static.py holds the marks to what the analyser says).
# Bandit takes each word of a reason for a rule's name, and says of each
# that it knows no such rule: that log is shown only when the run fails.
analyse:
	$(VENV)/bin/pyflakes $(PYTHON_SOURCES)
	$(VENV)/bin/bandit -q -r $(PYTHON_SOURCES) 2>$(VENV)/bandit.log || { cat $(VENV)/bandit.log; exit 1; }
	@echo "analyse: nothing unreviewed"

doctor:
	$(MDK) doctor

gui:
	$(PYTHON) mdk-gui

clean:
	$(MAKE) -C samples/hello-mun clean

.PHONY: check check-full sample env dev-tools analyse doctor gui clean
