"""Command line interface for Jotta.

The subcommands are placeholders until the runtime scripts move into the package.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from jotta import __version__

EXIT_OK = 0
EXIT_NOT_IMPLEMENTED = 1

COMMANDS: dict[str, str] = {
    "install": "Install the harness into a project.",
    "doctor": "Check the harness installation and configuration.",
    "prepare": "Prepare a task with budget, risk and context gates.",
    "checkpoint": "Record a finished task with its quality evidence.",
    "finish": "Close the current run.",
    "status": "Show the current run status.",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jotta",
        description="A structured workflow harness for AI-assisted development.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    for name, help_text in COMMANDS.items():
        subparsers.add_parser(name, help=help_text, description=help_text)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_OK
    print(f"jotta {args.command}: not implemented yet", file=sys.stderr)
    return EXIT_NOT_IMPLEMENTED
