"""Thin wrappers around the git command line."""

from __future__ import annotations

import subprocess
from pathlib import Path


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)


def in_git(root: Path) -> bool:
    return run_git(root, "rev-parse", "--is-inside-work-tree").returncode == 0
