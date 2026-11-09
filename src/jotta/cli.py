"""Command line interface for Jotta."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from jotta import __version__
from jotta.budget import guard
from jotta.commands import doctor, gates, run, tasks
from jotta.core.paths import ProjectNotFoundError, ProjectPaths, find_root
from jotta.isolation import orca
from jotta.quality import runner
from jotta.routing import router

EXIT_OK = 0
EXIT_NOT_IMPLEMENTED = 1
EXIT_USAGE = 2

STAGES = ["planning", "spec", "implementation", "quality", "review"]
MEASUREMENTS = ["actual", "estimated"]

Handler = Callable[[argparse.Namespace, ProjectPaths], int]
if TYPE_CHECKING:
    SubParsers = argparse._SubParsersAction[argparse.ArgumentParser]


def _paths(args: argparse.Namespace) -> ProjectPaths:
    root = Path(args.root) if args.root else find_root(Path.cwd())
    return ProjectPaths(root.resolve())


def _add_usage_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--stage", choices=STAGES)
    parser.add_argument("--input-tokens", type=int, default=0)
    parser.add_argument("--output-tokens", type=int, default=0)
    parser.add_argument("--measurement", choices=MEASUREMENTS, default="estimated")


def _add_lifecycle_commands(subparsers: SubParsers) -> None:
    subparsers.add_parser("install", help="Install the harness into a project.").set_defaults(handler=None)
    subparsers.add_parser("doctor", help="Check the harness installation and configuration.").set_defaults(
        handler=lambda _args, paths: doctor.run(paths)
    )
    subparsers.add_parser("status", help="Show the current run status.").set_defaults(
        handler=lambda _args, paths: run.status(paths)
    )
    subparsers.add_parser("validate-prd", help="Validate the PRD feature table.").set_defaults(
        handler=lambda _args, paths: tasks.validate_prd(paths)
    )
    subparsers.add_parser("sync-tasks", help="Synchronize tasks with the PRD.").set_defaults(
        handler=lambda _args, paths: tasks.sync_tasks(paths)
    )
    subparsers.add_parser("progress", help="Regenerate the progress summary.").set_defaults(
        handler=lambda _args, paths: tasks.progress(paths)
    )

    prepare = subparsers.add_parser("prepare", help="Prepare a task with budget, risk and context gates.")
    prepare.add_argument("task")
    prepare.add_argument("--profile", default="lean")
    prepare.add_argument("--interaction", choices=["supervised", "autonomous"], default="autonomous")
    prepare.add_argument("--destination", choices=["local", "github"], default="local")
    prepare.add_argument("--scope", choices=["product", "next-wave", "feature", "change"], default="feature")
    prepare.add_argument("--role", default="implementer")
    prepare.add_argument(
        "--launch-orca", action="store_true", help="compatibility flag; autonomous GitHub launches by default"
    )
    prepare.add_argument(
        "--defer-worktree", action="store_true", help="prepare only; do not launch the required Orca worktree"
    )
    prepare.add_argument("--agent", default="codex")
    prepare.add_argument("--model")
    prepare.add_argument("--provider", help="routing provider key, for example platform, openai or anthropic")
    prepare.add_argument("--effort")
    prepare.add_argument("--prompt")
    prepare.set_defaults(handler=lambda args, paths: run.prepare(paths, args))

    checkpoint = subparsers.add_parser("checkpoint", help="Record a finished task with its quality evidence.")
    checkpoint.add_argument("--task")
    checkpoint.add_argument("--status", choices=["completed", "blocked", "failed"], default="completed")
    checkpoint.add_argument("--evidence")
    checkpoint.add_argument("--blocker")
    _add_usage_arguments(checkpoint)
    checkpoint.set_defaults(handler=lambda args, paths: run.checkpoint(paths, args))

    finish = subparsers.add_parser("finish", help="Close the current run.")
    finish.add_argument(
        "--status", required=True, choices=["merged", "completed-local", "blocked", "failed", "cancelled"]
    )
    finish.add_argument("--pull-request")
    finish.add_argument("--merge-sha")
    finish.add_argument("--blocker")
    finish.add_argument("--evidence")
    finish.add_argument("--cleanup", action="store_true")
    finish.add_argument("--worktree-clean", action="store_true")
    _add_usage_arguments(finish)
    finish.set_defaults(handler=lambda args, paths: run.finish(paths, args))


def _add_gate_commands(subparsers: SubParsers) -> None:
    gate = subparsers.add_parser("gate", help="Run a deterministic text, staging, branch or commit gate.")
    gate_sub = gate.add_subparsers(dest="gate", required=True, metavar="<gate>")
    gate_sub.add_parser("text", help="Reject forbidden dash characters in tracked text files.").set_defaults(
        handler=lambda _args, paths: gates.gate_text(paths)
    )
    gate_sub.add_parser("staged", help="Reject staged local-only files.").set_defaults(
        handler=lambda _args, paths: gates.gate_staged(paths)
    )
    branch = gate_sub.add_parser("branch", help="Validate a branch name.")
    branch.add_argument("--name")
    branch.set_defaults(handler=lambda args, paths: gates.gate_branch(paths, args.name))
    commit = gate_sub.add_parser("commit", help="Validate a commit message.")
    commit.add_argument("--message", required=True)
    commit.set_defaults(handler=lambda args, _paths: gates.gate_commit(args.message), needs_project=False)


def _add_budget_commands(subparsers: SubParsers) -> None:
    budget = subparsers.add_parser("budget", help="Check and record the execution budget.")
    budget.set_defaults(handler=lambda args, paths: guard.run(paths, args))
    sub = budget.add_subparsers(dest="budget_command", required=True, metavar="<budget-command>")
    check = sub.add_parser("check", help="Evaluate the budget gate.")
    check.add_argument("--checkpoint")
    check.add_argument("--scope", choices=["feature", "wave", "run"], default="run")
    sub.add_parser("status", help="Show the budget evaluation without gating.")
    record = sub.add_parser("record", help="Record usage deltas or provider usage.")
    record.add_argument("--input-tokens", type=int, default=0)
    record.add_argument("--output-tokens", type=int, default=0)
    record.add_argument("--estimated-cost-usd", type=float, default=0.0)
    record.add_argument("--provider-usage-percent", type=float)
    record.add_argument("--provider-usage-unavailable", action="store_true")
    record.add_argument("--source", default="local-estimate")
    reserve = sub.add_parser("reserve", help="Reserve budget before dispatching parallel agents.")
    reserve.add_argument("--id", required=True)
    reserve.add_argument("--scope", choices=["feature", "wave", "run"], default="feature")
    reserve.add_argument("--input-tokens", type=int, default=0)
    reserve.add_argument("--output-tokens", type=int, default=0)
    reserve.add_argument("--estimated-cost-usd", type=float, default=0.0)
    release = sub.add_parser("release", help="Release a reservation.")
    release.add_argument("--id", required=True)
    authorize = sub.add_parser("authorize", help="Authorize continuing past the human gate.")
    authorize.add_argument("--scope", choices=["feature", "wave", "run"], required=True)
    authorize.add_argument("--until-percent", type=float, required=True)
    authorize.add_argument("--reason", required=True)
    sub.add_parser("clear-authorization", help="Remove the current authorization.")


def _add_models_commands(subparsers: SubParsers) -> None:
    models = subparsers.add_parser("models", help="Validate and resolve model routing.")
    models.set_defaults(handler=lambda args, paths: router.run(paths, args))
    sub = models.add_subparsers(dest="models_command", required=True, metavar="<models-command>")
    sub.add_parser("validate", help="Validate the routing configuration.")
    sub.add_parser("list", help="List the task routes.")
    resolve = sub.add_parser("resolve", help="Resolve the model for a task.")
    resolve.add_argument("--task", required=True)
    resolve.add_argument("--provider")


def _add_quality_command(subparsers: SubParsers) -> None:
    quality = subparsers.add_parser("quality", help="Run a computational quality profile.")
    quality.add_argument("profile", nargs="?", default="smoke")
    quality.add_argument("--max-lines", type=int, default=40)
    quality.set_defaults(handler=lambda args, paths: runner.run_profile(paths, args.profile, args.max_lines))


def _add_orca_commands(subparsers: SubParsers) -> None:
    orca_parser = subparsers.add_parser("orca", help="Manage Orca worktrees.")
    orca_parser.set_defaults(handler=lambda args, _paths: orca.run(args), needs_project=False)
    sub = orca_parser.add_subparsers(dest="orca_command", required=True, metavar="<orca-command>")
    sub.add_parser("guide", help="Load the Orca CLI guide.")
    create = sub.add_parser("create", help="Create a worktree with a visible agent session.")
    create.add_argument("--name", required=True)
    create.add_argument("--agent", default="codex")
    create.add_argument("--prompt", required=True)
    create.add_argument("--model")
    create.add_argument("--effort")
    remove = sub.add_parser("cleanup", help="Close terminals and remove a worktree.")
    remove.add_argument("--worktree", required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jotta",
        description="A structured workflow harness for AI-assisted development.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--root", help="project root; defaults to the closest directory containing .harness/")
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    _add_lifecycle_commands(subparsers)
    _add_gate_commands(subparsers)
    _add_budget_commands(subparsers)
    _add_models_commands(subparsers)
    _add_quality_command(subparsers)
    _add_orca_commands(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_OK
    handler: Handler | None = getattr(args, "handler", None)
    if handler is None:
        print(f"jotta {args.command}: not implemented yet", file=sys.stderr)
        return EXIT_NOT_IMPLEMENTED
    if not getattr(args, "needs_project", True):
        return handler(args, ProjectPaths(Path.cwd()))
    try:
        paths = _paths(args)
    except ProjectNotFoundError as exc:
        print(f"jotta: {exc}", file=sys.stderr)
        return EXIT_USAGE
    return handler(args, paths)
