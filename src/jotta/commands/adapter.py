"""The ``jotta adapter`` command."""

from __future__ import annotations

import argparse
from collections.abc import Callable

from jotta.adapters import claude, codex, opencode
from jotta.adapters.common import AdapterPlan, apply_adapter
from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict, print_json

EXIT_OK = 0
EXIT_BLOCKED = 2
PLANNERS: dict[str, Callable[[ProjectPaths], AdapterPlan]] = {
    "claude": claude.plan_adapter,
    "codex": codex.plan_adapter,
    "opencode": opencode.plan_adapter,
}


def configure(paths: ProjectPaths, agent: str) -> JSONDict:
    """Write the configuration of ``agent`` unless an existing hook file cannot be merged."""
    plan = PLANNERS[agent](paths)
    if plan.error is None:
        apply_adapter(plan)
    return plan.summary()


def run(paths: ProjectPaths, args: argparse.Namespace) -> int:
    plan = PLANNERS[args.agent](paths)
    summary = plan.summary()
    if plan.error:
        print_json({"status": "blocked", "message": "no files were written; fix the hook file", **summary})
        return EXIT_BLOCKED
    if args.dry_run:
        print_json({"status": "dry-run", **summary})
        return EXIT_OK
    apply_adapter(plan)
    print_json({"status": "configured", **summary})
    return EXIT_OK
