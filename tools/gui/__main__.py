# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
"""python -m gui from tools/ on sys.path, or: ./mdk-gui."""

from .app import main

if __name__ == "__main__":
    raise SystemExit(main())
