"""Run lifecycle: prepare a task, checkpoint it, finish the run and report status."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone

from jotta.budget import guard
from jotta.core.context import estimate_tokens, profile_token_estimates
from jotta.core.git import in_git, run_git
from jotta.core.paths import ProjectPaths
from jotta.core.prd import feature_folder, feature_for, prd_excerpt
from jotta.core.risk import risk_for
from jotta.core.state import (
    JSONDict,
    default_run,
    default_tasks,
    default_usage,
    load_json,
    now,
    print_json,
    write_json_atomic,
)
from jotta.isolation.orca import OrcaError, cleanup, create_worktree
from jotta.routing import router

PROFILES = {"manual-classic", "lean", "strict"}
DONE_STATUSES = {"merged", "completed-local", "completed"}
EXIT_INVALID = 2
ROLE_ROUTES = {
    "spec-author": "spec-writer",
    "qa-reviewer": "final-qa",
    "orchestrator": "product-orchestrator",
}
BUDGET_SCOPES = {"product": "run", "next-wave": "wave"}
RECOVERABLE_ERRORS = (OSError, ValueError, KeyError)


def _invalid(error: str) -> int:
    print(json.dumps({"status": "invalid", "error": error}, ensure_ascii=False))
    return EXIT_INVALID


def record_usage(paths: ProjectPaths, stage: str, input_tokens: int, output_tokens: int, measurement: str) -> None:
    data = load_json(paths.usage, default_usage())
    by_stage = data.setdefault("by_stage", {})
    entry = by_stage.setdefault(stage, {"input_tokens": 0, "output_tokens": 0, "measurement": measurement})
    entry["input_tokens"] += input_tokens
    entry["output_tokens"] += output_tokens
    entry["measurement"] = measurement
    data["input_tokens"] = sum(value.get("input_tokens", 0) for value in by_stage.values())
    data["output_tokens"] = sum(value.get("output_tokens", 0) for value in by_stage.values())
    data["updated_at"] = now()
    write_json_atomic(paths.usage, data)


def _route_task(role: str, effective_profile: str) -> str:
    if role == "implementer":
        return "implement-feature-high-risk" if effective_profile == "strict" else "implement-feature"
    return ROLE_ROUTES.get(role, "implement-feature")


def prepare(paths: ProjectPaths, args: argparse.Namespace) -> int:
    if args.profile not in PROFILES:
        print(json.dumps({"status": "invalid", "error": f"unknown profile {args.profile}"}))
        return EXIT_INVALID
    try:
        budget, budget_code = guard.check(paths, BUDGET_SCOPES.get(args.scope, "feature"), "before-feature")
    except RECOVERABLE_ERRORS as exc:
        return _invalid(f"budget guard unavailable: {exc}")
    if budget_code != 0:
        blocked_run = load_json(paths.run, default_run())
        blocked_run.update({"status": "blocked", "blocker": budget, "updated_at": now()})
        write_json_atomic(paths.run, blocked_run)
        print_json({"status": "blocked", "budget": budget})
        return budget_code

    feature = feature_for(paths.prd, args.task)
    folder = feature_folder(paths.planning, feature)
    excerpt = prd_excerpt(paths.prd, feature)
    spec_path = folder / "spec.md" if folder else None
    plan_path = folder / "plan.md" if folder else None
    spec_text = spec_path.read_text(encoding="utf-8") if spec_path and spec_path.exists() else ""
    risk = risk_for("\n".join(filter(None, [args.task, excerpt, spec_text])))
    effective_profile = "strict" if args.profile == "lean" and risk["level"] == "high" else args.profile
    try:
        routing_data = router.load(paths.routing)
        routing_errors = router.validate(routing_data)
        if routing_errors:
            raise ValueError("; ".join(routing_errors))
        model_route, model_code = router.resolve(routing_data, _route_task(args.role, effective_profile), args.provider)
    except RECOVERABLE_ERRORS as exc:
        return _invalid(f"model routing unavailable: {exc}")
    if model_code != 0:
        print_json({"status": "blocked", "model_route": model_route})
        return model_code
    effective_model = args.model or model_route.get("model")
    if args.model:
        model_route = {**model_route, "status": "resolved", "model": args.model, "source": "command-line"}
    requires_worktree = args.destination == "github" and args.interaction == "autonomous"

    all_tasks = load_json(paths.tasks, default_tasks()).get("tasks", [])
    task_state = next((item for item in all_tasks if feature and item.get("id") == feature["id"]), None)
    if task_state:
        completed = {item.get("id") for item in all_tasks if item.get("status") in DONE_STATUSES}
        missing = [dep for dep in task_state.get("dependencies", []) if dep not in completed]
        if missing:
            print_json({"status": "blocked", "missing_dependencies": missing})
            return 1

    task = feature or {"id": args.task, "name": args.task}
    packet: JSONDict = {
        "schema_version": 1,
        "task": task,
        "scope": args.scope,
        "interaction": args.interaction,
        "destination": args.destination,
        "requested_profile": args.profile,
        "effective_profile": effective_profile,
        "risk": risk,
        "budget": budget,
        "model_route": model_route,
        "control_root": str(paths.root),
        "prd_excerpt": excerpt,
        "spec_path": paths.relative(spec_path) if spec_path and spec_path.exists() else None,
        "plan_path": paths.relative(plan_path) if plan_path and plan_path.exists() else None,
        "requires_worktree": requires_worktree,
    }
    packet["estimated_tokens"] = estimate_tokens(json.dumps(packet, ensure_ascii=False))
    safe = re.sub(r"[^a-z0-9-]+", "-", task["id"].lower()).strip("-") or "task"
    packet_path = paths.runtime / "context" / f"{safe}-{args.role}.json"
    write_json_atomic(packet_path, packet)

    run = load_json(paths.run, default_run())
    existing_worktree = run.get("worktree")
    existing_workers = run.get("workers", [])
    run.update(
        {
            "schema_version": 2,
            "run_id": run.get("run_id") or f"run-{safe}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "status": "preparing",
            "scope": args.scope,
            "profile": effective_profile,
            "requested_profile": args.profile,
            "interaction": args.interaction,
            "destination": args.destination,
            "current_task": task["id"],
            "stage": "prepared",
            "context_packet": paths.relative(packet_path),
            "risk": risk,
            "workers": existing_workers if existing_worktree else [],
            "updated_at": now(),
        }
    )
    if requires_worktree and not existing_worktree:
        run["workers"] = [
            {
                "role": args.role,
                "status": "awaiting-worktree",
                "worktree_id": None,
                "worktree_path": None,
                "handle": None,
            }
        ]
    elif requires_worktree and existing_worktree:
        run["status"] = "running"
        run["stage"] = "implementing"
        packet["reused_worktree"] = existing_worktree
        write_json_atomic(packet_path, packet)

    should_launch_orca = requires_worktree and not args.defer_worktree
    if args.launch_orca and not requires_worktree:
        print(json.dumps({"status": "invalid", "error": "Orca worktree is not required for this run"}))
        return EXIT_INVALID
    if should_launch_orca and existing_worktree:
        write_json_atomic(paths.run, run)
        print_json({"status": "running", "reused_worktree": existing_worktree, "context_packet": run["context_packet"]})
        return 0
    if should_launch_orca:
        prompt = args.prompt or f"Implement {args.task} using {packet_path}"
        try:
            launch = create_worktree(safe, args.agent, prompt, effective_model, args.effort)
        except OrcaError as exc:
            run["status"] = "blocked"
            run["blocker"] = str(exc)
            write_json_atomic(paths.run, run)
            print_json({"status": "blocked", "error": str(exc)})
            return EXIT_INVALID
        run["workers"] = [
            {
                "role": args.role,
                "status": "running",
                "worktree_id": launch.get("worktree_id"),
                "worktree_path": launch.get("worktree_path"),
                "handle": launch.get("worker_handle"),
                "branch": launch.get("branch"),
                "surface": launch.get("surface"),
            }
        ]
        run["worktree"] = launch.get("worktree_id")
        run["branch"] = launch.get("branch")
        run["stage"] = "implementing"
        run["status"] = "running"
        packet["orca"] = {key: value for key, value in launch.items() if key != "raw"}
        write_json_atomic(packet_path, packet)

    write_json_atomic(paths.run, run)
    print_json(
        {
            "status": run["status"],
            "context_packet": run["context_packet"],
            "profile": effective_profile,
            "risk": risk,
            "budget": budget,
            "model_route": model_route,
            "requires_worktree": requires_worktree,
            "workers": run["workers"],
        }
    )
    return 0


def finish(paths: ProjectPaths, args: argparse.Namespace) -> int:
    run = load_json(paths.run, default_run())
    if not run.get("run_id"):
        print(json.dumps({"status": "invalid", "error": "no active run"}))
        return EXIT_INVALID
    merged = args.status == "merged"
    if merged and not args.merge_sha:
        print(json.dumps({"status": "invalid", "error": "merged status requires --merge-sha"}))
        return EXIT_INVALID
    cleanup_result: JSONDict | None = None
    if args.cleanup:
        if not (merged and args.worktree_clean and run.get("worktree")):
            error = "cleanup requires merged status, merge SHA, clean confirmation and recorded worktree"
            print(json.dumps({"status": "blocked", "error": error}))
            return EXIT_INVALID
        try:
            cleanup_result = cleanup(run["worktree"])
        except OrcaError as exc:
            run["status"] = "blocked"
            run["blocker"] = f"cleanup unverifiable: {exc}"
            write_json_atomic(paths.run, run)
            print_json({"status": "blocked", "error": run["blocker"]})
            return EXIT_INVALID
        branch = run.get("branch")
        root = paths.root
        if branch and in_git(root) and run_git(root, "branch", "--show-current").stdout.strip() != branch:
            deletion = run_git(root, "branch", "-d", branch)
            if deletion.returncode != 0:
                cleanup_result["branch_warning"] = (deletion.stderr or deletion.stdout).strip()
    run.update(
        {
            "status": args.status,
            "stage": "finished",
            "pull_request": args.pull_request or run.get("pull_request"),
            "merge_sha": args.merge_sha,
            "last_checkpoint": now(),
            "blocker": args.blocker,
            "cleanup": cleanup_result,
            "updated_at": now(),
        }
    )
    if cleanup_result:
        run["worktree"] = None
        run["workers"] = []
    write_json_atomic(paths.run, run)
    tasks = load_json(paths.tasks, default_tasks())
    for task in tasks.get("tasks", []):
        if task.get("id") == run.get("current_task"):
            task["status"] = args.status
            task["pull_request"] = run.get("pull_request")
            task["merge_sha"] = args.merge_sha
            task.setdefault("evidence", []).append({"at": now(), "receipt": args.evidence})
    write_json_atomic(paths.tasks, tasks)
    if args.stage and (args.input_tokens or args.output_tokens):
        record_usage(paths, args.stage, args.input_tokens, args.output_tokens, args.measurement)
    print_json({"status": args.status, "cleanup": cleanup_result})
    return 0


def checkpoint(paths: ProjectPaths, args: argparse.Namespace) -> int:
    run = load_json(paths.run, default_run())
    if not run.get("run_id"):
        print(json.dumps({"status": "invalid", "error": "no active run"}))
        return EXIT_INVALID
    task_id = args.task or run.get("current_task")
    tasks = load_json(paths.tasks, default_tasks())
    target = next((item for item in tasks.get("tasks", []) if item.get("id") == task_id), None)
    if target is None:
        return _invalid(f"unknown task {task_id}")
    target["status"] = args.status
    target.setdefault("evidence", []).append({"at": now(), "receipt": args.evidence})
    tasks["updated_at"] = now()
    write_json_atomic(paths.tasks, tasks)
    run.update({"current_task": task_id, "last_checkpoint": now(), "stage": "checkpoint", "updated_at": now()})
    if args.status in {"blocked", "failed"}:
        run["status"] = args.status
        run["blocker"] = args.blocker
    else:
        run["status"] = "running"
        run["blocker"] = None
    write_json_atomic(paths.run, run)
    if args.stage and (args.input_tokens or args.output_tokens):
        record_usage(paths, args.stage, args.input_tokens, args.output_tokens, args.measurement)
    try:
        budget, code = guard.check(paths, "feature", "after-feature")
    except RECOVERABLE_ERRORS as exc:
        return _invalid(f"budget guard unavailable: {exc}")
    if code != 0:
        run.update({"status": "blocked", "blocker": budget, "updated_at": now()})
        write_json_atomic(paths.run, run)
    print_json({"status": run["status"], "task": task_id, "task_status": args.status, "budget": budget})
    return code


def status(paths: ProjectPaths) -> int:
    run = load_json(paths.run, default_run())
    usage = load_json(paths.usage, default_usage())
    print_json(
        {
            "run": run,
            "usage_by_stage": usage.get("by_stage", {}),
            "token_estimates": profile_token_estimates(paths.skills),
        }
    )
    return 0
