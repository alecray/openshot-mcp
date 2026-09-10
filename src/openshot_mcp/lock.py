"""Detect whether OpenShot currently has a given project open.

OpenShot autosaves the open project every few minutes, so a file-level write while it is open
gets clobbered. Detection is heuristic: a running ``openshot-qt`` process whose main window
title contains the project's stem. On non-Windows hosts, or if the process query fails, we fall
back to "not open" and let the caller decide.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def openshot_window_titles() -> list[str]:
    if sys.platform != "win32":
        return []
    cmd = [
        "powershell", "-NoProfile", "-Command",
        "Get-Process openshot-qt -ErrorAction SilentlyContinue | ForEach-Object { $_.MainWindowTitle }",
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def is_open_in_openshot(path: str | Path) -> bool:
    stem = Path(path).stem.lower()
    return any(stem in t.lower() for t in openshot_window_titles())


def has_unsaved_changes(path: str | Path) -> bool:
    """OpenShot prefixes the title with '*' when the project has unsaved edits."""
    stem = Path(path).stem.lower()
    return any(stem in t.lower() and t.lstrip().startswith("*") for t in openshot_window_titles())
