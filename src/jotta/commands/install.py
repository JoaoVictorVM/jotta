"""The ``jotta install`` command."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from jotta.core.state import print_json
from jotta.install.installer import InstallRefusedError, apply_install, plan_install

EXIT_OK = 0
EXIT_BLOCKED = 2

Confirm = Callable[[str], bool]


def ask(question: str) -> bool:
    """Ask a yes or no question on the terminal; anything but yes is a no."""
    if not sys.stdin.isatty():
        return False
    return input(f"{question} [y/N] ").strip().lower() in {"y", "yes", "s", "sim"}


def run(args: argparse.Namespace, confirm: Confirm = ask) -> int:
    target = Path(args.target or Path.cwd())
    try:
        plan = plan_install(target, git_exclude=not args.no_git_exclude)
    except InstallRefusedError as exc:
        print_json({"status": "refused", "reason": str(exc)}, indent=None)
        return EXIT_BLOCKED

    summary = plan.summary()
    if args.dry_run:
        print_json({"status": "dry-run", **summary})
        return EXIT_OK

    if plan.conflicts and not args.force_overwrite:
        print_json(
            {
                "status": "conflict",
                "message": "no files were written; merge the listed paths or use --force-overwrite",
                **summary,
            }
        )
        return EXIT_BLOCKED

    if plan.conflicts and not args.yes:
        question = f"Overwrite {len(plan.conflicts)} existing file(s) in {plan.target}?"
        if not confirm(question):
            print_json({"status": "cancelled", "message": "overwrite was not confirmed; use --yes", **summary})
            return EXIT_BLOCKED

    apply_install(plan)
    print_json({"status": "installed", "overwritten": summary["conflicts"], **summary})
    return EXIT_OK
