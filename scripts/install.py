#!/usr/bin/env python3
"""Install jotta into a consumer project without overwriting files."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]


def ignore_generated(_: str, names: list[str]) -> set[str]:
    ignored = {name for name in names if name in {"runtime", "__pycache__"}}
    ignored.update(name for name in names if name.endswith((".pyc", ".pyo")))
    return ignored


def conflicts(target: Path) -> list[str]:
    candidates = [
        target / ".harness",
        target / ".planning" / "README.md",
        target / ".planning" / "PRD.md",
        target / "AGENTS.md",
        target / "CLAUDE.md",
    ]
    return [str(path) for path in candidates if path.exists()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="consumer project root")
    parser.add_argument("--no-bootstrap", action="store_true")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    source = SOURCE.resolve()
    if target == source or source in target.parents:
        print(json.dumps({"status": "refused", "reason": "target cannot be the harness source or a child of it"}))
        return 2

    found = conflicts(target)
    if found:
        print(json.dumps({
            "status": "conflict",
            "message": "no files were written; merge the listed paths manually",
            "paths": found,
        }, ensure_ascii=False, indent=2))
        return 2

    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE / ".harness", target / ".harness", ignore=ignore_generated)
    planning = target / ".planning"
    planning.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE / ".planning" / "README.md", planning / "README.md")
    shutil.copy2(SOURCE / ".planning" / "PRD.md", planning / "PRD.md")
    shutil.copy2(SOURCE / "AGENTS.md", target / "AGENTS.md")
    shutil.copy2(SOURCE / "CLAUDE.md", target / "CLAUDE.md")

    bootstrap = None
    if not args.no_bootstrap:
        process = subprocess.run(
            [sys.executable, str(target / ".harness" / "scripts" / "bootstrap.py")],
            cwd=target,
            text=True,
            capture_output=True,
        )
        bootstrap = {
            "returncode": process.returncode,
            "stdout": process.stdout.strip(),
            "stderr": process.stderr.strip(),
        }
        if process.returncode != 0:
            print(json.dumps({"status": "installed-with-bootstrap-error", "target": str(target), "bootstrap": bootstrap}, ensure_ascii=False, indent=2))
            return 1

    print(json.dumps({"status": "installed", "target": str(target), "bootstrap": bootstrap}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
