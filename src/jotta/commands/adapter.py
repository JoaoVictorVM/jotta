"""The ``jotta adapter`` command."""

from __future__ import annotations

import argparse

from jotta.adapters import claude
from jotta.core.paths import ProjectPaths
from jotta.core.state import print_json

EXIT_OK = 0
EXIT_BLOCKED = 2


def run(paths: ProjectPaths, args: argparse.Namespace) -> int:
    plan = claude.plan_adapter(paths)
    summary = plan.summary()
    if plan.error:
        print_json({"status": "blocked", "message": "no files were written; fix the settings file", **summary})
        return EXIT_BLOCKED
    if args.dry_run:
        print_json({"status": "dry-run", **summary})
        return EXIT_OK
    claude.apply_adapter(plan)
    print_json({"status": "configured", **summary})
    return EXIT_OK
