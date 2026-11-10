#!/usr/bin/env python3
"""Prepare local harness directories and Git exclusions."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCAL_DIRS = [
    ROOT / ".planning" / "features",
    ROOT / ".planning" / "changes",
    ROOT / ".planning" / "decisions",
    ROOT / ".planning" / "commit-plans",
    ROOT / ".planning" / "archive",
    ROOT / ".harness" / "state",
]
EXCLUDES = ["/.harness/", "/.planning/", "/AGENTS.md", "/CLAUDE.md", "/.claude/"]


def git_exclude_path() -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--git-path", "info/exclude"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    path = Path(result.stdout.strip())
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    for directory in LOCAL_DIRS:
        directory.mkdir(parents=True, exist_ok=True)

    exclude = git_exclude_path()
    if exclude is None:
        print("BOOTSTRAP OK: projeto sem Git, exclusoes nao foram necessarias")
        return 0

    exclude.parent.mkdir(parents=True, exist_ok=True)
    current = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    lines = {line.strip() for line in current.splitlines()}
    missing = [entry for entry in EXCLUDES if entry not in lines]
    if missing:
        with exclude.open("a", encoding="utf-8", newline="\n") as handle:
            if current and not current.endswith("\n"):
                handle.write("\n")
            handle.write("\n# jotta local\n")
            handle.write("\n".join(missing) + "\n")
    print(f"BOOTSTRAP OK: {exclude}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

