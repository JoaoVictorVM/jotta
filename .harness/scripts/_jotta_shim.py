"""Forward the legacy harness scripts to the jotta command line."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src"
INSTALL_HINT = "python -m pip install git+https://github.com/JoaoVictorVM/jotta"


def run(*command: str) -> int:
    """Run ``jotta --root <project> <command> <script arguments>``."""
    if (SOURCE / "jotta" / "cli.py").is_file():
        sys.path.insert(0, str(SOURCE))
    try:
        from jotta.cli import main
    except ImportError:
        print(f"jotta package not found. Install it with: {INSTALL_HINT}", file=sys.stderr)
        return 2
    return main(["--root", str(ROOT), *command, *sys.argv[1:]])
