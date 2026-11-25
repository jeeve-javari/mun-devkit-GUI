# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0

"""Visual tokens for the desktop GUI: one clear direction, no default purple."""

# Deep slate workspace with a single copper accent — reads as a workshop, not a dashboard.
COLORS = {
    "bg": "#1a1f24",
    "bg_raised": "#232a31",
    "bg_sunken": "#12161a",
    "border": "#343d46",
    "text": "#e8eef2",
    "text_dim": "#8b9aa8",
    "accent": "#d4894a",
    "accent_hover": "#e49a5c",
    "accent_text": "#1a1f24",
    "ok": "#5fad7a",
    "warn": "#d4a84a",
    "bad": "#d4655a",
    "log": "#c5d0da",
}

FONTS = {
    # Prefer distinctive UI faces where present; fall back cleanly on each OS.
    "ui": ("Segoe UI", "SF Pro Text", "Cantarell", "DejaVu Sans", "Helvetica"),
    "display": ("Segoe UI Semibold", "SF Pro Display", "Cantarell", "DejaVu Sans", "Helvetica"),
    "mono": ("Cascadia Mono", "SF Mono", "Consolas", "DejaVu Sans Mono", "Courier"),
}


def pick_font(families, size: int, weight: str = "normal") -> tuple:
    """Return a tk font tuple using the first family the platform knows."""
    import tkinter.font as tkfont

    available = set(tkfont.families())
    for name in families:
        if name in available:
            return (name, size, weight) if weight != "normal" else (name, size)
    return ("TkDefaultFont", size, weight) if weight != "normal" else ("TkDefaultFont", size)
