#!/usr/bin/env python3
"""Cross-platform runtime, validation and state CLI for jotta v0.5."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / ".harness"
PLANNING = ROOT / ".planning"
STATE = HARNESS / "state"
RUNTIME = HARNESS / "runtime"
TASKS = STATE / "tasks.json"
RUN = STATE / "current-run.json"
USAGE = STATE / "usage.json"
PRD = PLANNING / "PRD.md"
PROFILES = HARNESS / "profiles"

REQUIRED = [
    ROOT / "AGENTS.md", HARNESS / "README.md", HARNESS / "AGENT-MANUAL.md",
    HARNESS / "ARCHITECTURE.md", HARNESS / "config.yaml",
    HARNESS / "workflows" / "product.md", HARNESS / "workflows" / "change.md",
    HARNESS / "workflows" / "quality.md", HARNESS / "adapters" / "orca.md",
    HARNESS / "adapters" / "opencode" / "README.md",
    HARNESS / "guides" / "operations" / "worktrees-and-agents.md",
    HARNESS / "permissions" / "permissions.md", HARNESS / "permissions" / "human-gates.md",
    PROFILES / "manual-classic.yaml", PROFILES / "lean.yaml", PROFILES / "strict.yaml",
    TASKS, RUN, USAGE, PRD,
]

KNOWN_STATES = {
    "pending", "blocked", "ready", "specifying", "spec-review", "implementing",
    "validating", "committing", "pr-open", "reviewing", "merging", "merged",
    "completed-local", "completed", "failed", "cancelled",
}
LOCAL_PATHS = (".harness/", ".planning/", ".claude/", ".opencode/", "AGENTS.md", "CLAUDE.md")
TEXT_EXTS = {".md", ".txt", ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".yaml", ".yml"}
BRANCH_RE = re.compile(r"^(feat|fix|refactor|test|docs|style|perf|build|ci|chore)/[a-z0-9]+(?:-[a-z0-9]+)*$")
COMMIT_RE = re.compile(r"^(feat|fix|refactor|test|docs|style|perf|build|ci|chore)\([a-z0-9_-]+\): [a-z0-9].+$")
HIGH_RISK = re.compile(
    r"(?i)\b(auth|authentication|authorization|autenticacao|autenticação|login|oauth|payment|pagamento|billing|security|secret|"
    r"migration|migracao|migração|schema migration|migracao destrutiva|migração destrutiva|personal data|dados pessoais|permissao|permissão|criptografia|"
    r"production|infraestrutura|public api|breaking change)\b"
)
FORBIDDEN_META = [
    re.compile(r"[\u2013\u2014]"), re.compile(r"co-authored-by", re.I),
    re.compile(r"generated with", re.I), re.compile(r"\b(?:claude|anthropic)\b", re.I),
    re.compile(r"\b(?:PRD|spec\.md|plan\.md)\b", re.I), re.compile(r"\b(?:F|RF|US)\d+\b", re.I),
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: dict | None = None) -> dict:
    if not path.exists() and default is not None:
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


def in_git() -> bool:
    return run_git("rev-parse", "--is-inside-work-tree").returncode == 0


def flat_yaml(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or line.rstrip().endswith(":"):
            continue
        match = re.match(r"^\s*([A-Za-z0-9_-]+):\s*(.*?)\s*$", line)
        if match:
            values[match.group(1)] = match.group(2).strip("'\"")
    return values


def parse_prd() -> tuple[list[dict], list[str]]:
    if not PRD.exists():
        return [], [f"PRD absent: {PRD}"]
    features, errors, seen = [], [], set()
    lines = PRD.read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, 1):
        if not re.match(r"^\|\s*F\d+\s*\|", line, re.I):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            errors.append(f"line {line_number}: incomplete feature table row")
            continue
        feature_id = cells[0].upper()
        if feature_id in seen:
            errors.append(f"line {line_number}: duplicate {feature_id}")
            continue
        seen.add(feature_id)
        dependencies = [] if cells[3].lower() in {"none", "nenhuma", "-"} else re.findall(r"F\d+", cells[3].upper())
        try:
            priority = int(cells[2])
        except ValueError:
            priority = None
            errors.append(f"invalid priority in {feature_id}")
        features.append({"id": feature_id, "name": cells[1], "priority": priority, "dependencies": dependencies})
    ids = {item["id"] for item in features}
    for item in features:
        for dependency in item["dependencies"]:
            if dependency not in ids:
                errors.append(f"{item['id']}: missing dependency {dependency}")
    waves: dict[str, int] = {}
    for line in lines:
        match = re.search(r"\*\*Wave\s+(\d+)\*\*\s*:\s*(.*)", line, re.I)
        if match:
            for feature_id in re.findall(r"F\d+", match.group(2).upper()):
                waves[feature_id] = int(match.group(1))
    for item in features:
        item["wave"] = waves.get(item["id"])
    return features, errors


def feature_for(reference: str) -> dict | None:
    features, _ = parse_prd()
    normalized = reference.strip().lower()
    for feature in features:
        if normalized == feature["id"].lower() or normalized == feature["name"].lower():
            return feature
    candidates = [feature for feature in features if normalized in feature["name"].lower()]
    return candidates[0] if len(candidates) == 1 else None


def feature_folder(feature: dict | None) -> Path | None:
    if not feature:
        return None
    matches = list((PLANNING / "features").glob(f"{feature['id']}-*")) if (PLANNING / "features").exists() else []
    return matches[0] if len(matches) == 1 else None


def prd_excerpt(feature: dict | None) -> str:
    if not PRD.exists() or not feature:
        return ""
    lines = PRD.read_text(encoding="utf-8").splitlines()
    needles = [feature["id"].lower(), feature["name"].lower()]
    selected: set[int] = set()
    for index, line in enumerate(lines):
        lowered = line.lower()
        if any(needle and needle in lowered for needle in needles):
            selected.update(range(max(0, index - 2), min(len(lines), index + 4)))
    return "\n".join(lines[index] for index in sorted(selected))


def risk_for(text: str) -> dict:
    reasons = sorted({match.group(0).lower() for match in HIGH_RISK.finditer(text)})
    return {"level": "high" if reasons else "normal", "reasons": reasons}


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def profile_token_estimates() -> dict:
    base = HARNESS / "skills"
    paths = {
        "lean": [
            base / "spec-writer" / "SKILL.md", base / "spec-writer" / "references" / "lean.md",
            base / "implement-feature" / "SKILL.md", base / "implement-feature" / "references" / "lean.md",
        ],
        "strict": [
            base / "spec-writer" / "SKILL.md", base / "spec-writer" / "references" / "manual-classic.md",
            base / "implement-feature" / "SKILL.md", base / "implement-feature" / "references" / "manual-classic-and-strict.md",
        ],
    }
    return {name: sum(estimate_tokens(path.read_text(encoding="utf-8")) for path in files if path.exists()) for name, files in paths.items()}


def command_doctor() -> int:
    errors, warnings = [], []
    for path in REQUIRED:
        if not path.exists():
            errors.append(f"absent: {path.relative_to(ROOT)}")
    json_files = (TASKS, RUN, USAGE, HARNESS / "models" / "routing.json", HARNESS / "budgets" / "policy.json", HARNESS / "budgets" / "providers.json", HARNESS / "sensors" / "computational" / "gates.json")
    for path in json_files:
        if path.exists():
            try:
                load_json(path)
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"invalid JSON {path.relative_to(ROOT)}: {exc}")
    for skill in (HARNESS / "skills").glob("*/SKILL.md"):
        text = skill.read_text(encoding="utf-8")
        if not text.startswith("---\n") or "\nname:" not in text or "\ndescription:" not in text:
            errors.append(f"invalid skill frontmatter: {skill.relative_to(ROOT)}")
        for reference in re.findall(r"\]\((references/[^)]+)\)", text):
            if not (skill.parent / reference).exists():
                errors.append(f"broken skill reference: {skill.parent.relative_to(ROOT)}/{reference}")
    try:
        from model_router import load as load_routing, validate as validate_routing
        errors.extend(f"model routing: {error}" for error in validate_routing(load_routing()))
    except (ImportError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        errors.append(f"model routing unavailable: {exc}")
    if not shutil.which("orca") and not shutil.which("orca-dev") and not shutil.which("orca-ide"):
        warnings.append("Orca CLI unavailable in this shell; autonomous GitHub worktree launch will stop")
    print("DOCTOR FAILED" if errors else "DOCTOR OK")
    for error in errors:
        print(f"- {error}")
    for warning in warnings:
        print(f"- WARNING: {warning}")
    estimates = profile_token_estimates()
    print(f"- static skill estimate lean: {estimates.get('lean', 0)} tokens")
    print(f"- static skill estimate strict: {estimates.get('strict', 0)} tokens")
    return 1 if errors else 0


def command_validate_prd() -> int:
    features, errors = parse_prd()
    if not features:
        errors.append("no feature found in dependency table")
    for error in errors:
        print(f"- {error}")
    print(f"PRD OK: {len(features)} features" if not errors else "PRD INVALID")
    return 1 if errors else 0


def command_sync_tasks() -> int:
    features, errors = parse_prd()
    if errors or not features:
        for error in errors or ["no feature found"]:
            print(f"- {error}")
        return 1
    current = load_json(TASKS, {"tasks": []})
    old = {item["id"]: item for item in current.get("tasks", [])}
    completed = {task_id for task_id, item in old.items() if item.get("status") in {"merged", "completed-local", "completed"}}
    tasks = []
    for feature in features:
        previous = old.get(feature["id"], {})
        status = previous.get("status") or ("ready" if all(dep in completed for dep in feature["dependencies"]) else "pending")
        tasks.append({
            **feature, "type": "feature", "source": "prd", "status": status,
            "branch": previous.get("branch"), "pull_request": previous.get("pull_request"),
            "merge_sha": previous.get("merge_sha"), "evidence": previous.get("evidence", []),
        })
    write_json_atomic(TASKS, {
        "schema_version": 2, "prd_path": ".planning/PRD.md",
        "prd_hash": f"sha256:{sha256(PRD)}", "updated_at": now(), "tasks": tasks,
    })
    print(f"TASKS SYNCED: {len(tasks)}")
    return 0


def command_progress() -> int:
    data = load_json(TASKS, {"tasks": []})
    groups: dict[str, list[str]] = {}
    for item in data.get("tasks", []):
        groups.setdefault(item.get("status", "unknown"), []).append(f"{item.get('id')} {item.get('name', '')}".strip())
    lines = ["# Progress", "", f"PRD hash: {data.get('prd_hash')}", ""]
    for status in sorted(groups):
        lines.extend([f"## {status}", "", *[f"- {label}" for label in groups[status]], ""])
    (STATE / "progress.md").write_text("\n".join(lines), encoding="utf-8")
    print("PROGRESS UPDATED")
    return 0


def record_usage(stage: str, input_tokens: int, output_tokens: int, measurement: str) -> None:
    data = load_json(USAGE, {"schema_version": 2, "by_stage": {}})
    by_stage = data.setdefault("by_stage", {})
    entry = by_stage.setdefault(stage, {"input_tokens": 0, "output_tokens": 0, "measurement": measurement})
    entry["input_tokens"] += input_tokens
    entry["output_tokens"] += output_tokens
    entry["measurement"] = measurement
    data["input_tokens"] = sum(value.get("input_tokens", 0) for value in by_stage.values())
    data["output_tokens"] = sum(value.get("output_tokens", 0) for value in by_stage.values())
    data["updated_at"] = now()
    write_json_atomic(USAGE, data)


def command_prepare(args: argparse.Namespace) -> int:
    if args.profile not in {"manual-classic", "lean", "strict"}:
        print(json.dumps({"status": "invalid", "error": f"unknown profile {args.profile}"}))
        return 2
    try:
        from budget_guard import POLICY_PATH, evaluate, load
        budget_scope = {"product": "run", "next-wave": "wave"}.get(args.scope, "feature")
        budget, budget_code = evaluate(load(POLICY_PATH), load(USAGE), budget_scope, "before-feature")
    except (ImportError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "invalid", "error": f"budget guard unavailable: {exc}"}, ensure_ascii=False))
        return 2
    if budget_code != 0:
        run = load_json(RUN, {})
        run.update({"status": "blocked", "blocker": budget, "updated_at": now()})
        write_json_atomic(RUN, run)
        print(json.dumps({"status": "blocked", "budget": budget}, ensure_ascii=False, indent=2))
        return budget_code

    feature = feature_for(args.task)
    folder = feature_folder(feature)
    excerpt = prd_excerpt(feature)
    spec_path = folder / "spec.md" if folder else None
    plan_path = folder / "plan.md" if folder else None
    spec_text = spec_path.read_text(encoding="utf-8") if spec_path and spec_path.exists() else ""
    risk_text = "\n".join(filter(None, [args.task, excerpt, spec_text]))
    risk = risk_for(risk_text)
    effective_profile = "strict" if args.profile == "lean" and risk["level"] == "high" else args.profile
    route_task = {
        "implementer": "implement-feature-high-risk" if effective_profile == "strict" else "implement-feature",
        "spec-author": "spec-writer",
        "qa-reviewer": "final-qa",
        "orchestrator": "product-orchestrator",
    }.get(args.role, "implement-feature")
    try:
        from model_router import load as load_routing, resolve as resolve_model, validate as validate_routing
        routing_data = load_routing()
        routing_errors = validate_routing(routing_data)
        if routing_errors:
            raise ValueError("; ".join(routing_errors))
        model_route, model_code = resolve_model(routing_data, route_task, args.provider)
    except (ImportError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "invalid", "error": f"model routing unavailable: {exc}"}, ensure_ascii=False))
        return 2
    if model_code != 0:
        print(json.dumps({"status": "blocked", "model_route": model_route}, ensure_ascii=False, indent=2))
        return model_code
    effective_model = args.model or model_route.get("model")
    if args.model:
        model_route = {**model_route, "status": "resolved", "model": args.model, "source": "command-line"}
    requires_worktree = args.destination == "github" and args.interaction == "autonomous"

    all_tasks = load_json(TASKS, {"tasks": []}).get("tasks", [])
    task_state = next((item for item in all_tasks if feature and item.get("id") == feature["id"]), None)
    if task_state:
        completed = {item.get("id") for item in all_tasks if item.get("status") in {"merged", "completed-local", "completed"}}
        missing = [dep for dep in task_state.get("dependencies", []) if dep not in completed]
        if missing:
            print(json.dumps({"status": "blocked", "missing_dependencies": missing}, ensure_ascii=False, indent=2))
            return 1

    packet = {
        "schema_version": 1,
        "task": feature or {"id": args.task, "name": args.task},
        "scope": args.scope,
        "interaction": args.interaction,
        "destination": args.destination,
        "requested_profile": args.profile,
        "effective_profile": effective_profile,
        "risk": risk,
        "budget": budget,
        "model_route": model_route,
        "control_root": str(ROOT),
        "prd_excerpt": excerpt,
        "spec_path": str(spec_path.relative_to(ROOT)).replace("\\", "/") if spec_path and spec_path.exists() else None,
        "plan_path": str(plan_path.relative_to(ROOT)).replace("\\", "/") if plan_path and plan_path.exists() else None,
        "requires_worktree": requires_worktree,
    }
    packet["estimated_tokens"] = estimate_tokens(json.dumps(packet, ensure_ascii=False))
    context_dir = RUNTIME / "context"
    safe = re.sub(r"[^a-z0-9-]+", "-", (feature or {"id": args.task})["id"].lower()).strip("-") or "task"
    packet_path = context_dir / f"{safe}-{args.role}.json"
    write_json_atomic(packet_path, packet)

    run = load_json(RUN, {})
    existing_worktree = run.get("worktree")
    existing_workers = run.get("workers", [])
    run.update({
        "schema_version": 2,
        "run_id": run.get("run_id") or f"run-{safe}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "status": "preparing",
        "scope": args.scope,
        "profile": effective_profile,
        "requested_profile": args.profile,
        "interaction": args.interaction,
        "destination": args.destination,
        "current_task": (feature or {"id": args.task})["id"],
        "stage": "prepared",
        "context_packet": str(packet_path.relative_to(ROOT)).replace("\\", "/"),
        "risk": risk,
        "workers": existing_workers if existing_worktree else [],
        "updated_at": now(),
    })
    if requires_worktree and not existing_worktree:
        run["workers"] = [{"role": args.role, "status": "awaiting-worktree", "worktree_id": None, "worktree_path": None, "handle": None}]
    elif requires_worktree and existing_worktree:
        run["status"] = "running"
        run["stage"] = "implementing"
        packet["reused_worktree"] = existing_worktree
        write_json_atomic(packet_path, packet)

    should_launch_orca = requires_worktree and not args.defer_worktree
    if args.launch_orca and not requires_worktree:
        print(json.dumps({"status": "invalid", "error": "Orca worktree is not required for this run"}))
        return 2
    if should_launch_orca and existing_worktree:
        write_json_atomic(RUN, run)
        print(json.dumps({"status": "running", "reused_worktree": existing_worktree, "context_packet": run["context_packet"]}, ensure_ascii=False, indent=2))
        return 0
    if should_launch_orca:
        try:
            from orca_adapter import OrcaError, create_worktree
            launch = create_worktree(safe, args.agent, args.prompt or f"Implement {args.task} using {packet_path}", effective_model, args.effort)
        except (ImportError, OrcaError) as exc:
            run["status"] = "blocked"
            run["blocker"] = str(exc)
            write_json_atomic(RUN, run)
            print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2))
            return 2
        run["workers"] = [{
            "role": args.role,
            "status": "running",
            "worktree_id": launch.get("worktree_id"),
            "worktree_path": launch.get("worktree_path"),
            "handle": launch.get("worker_handle"),
            "branch": launch.get("branch"),
            "surface": launch.get("surface"),
        }]
        run["worktree"] = launch.get("worktree_id")
        run["branch"] = launch.get("branch")
        run["stage"] = "implementing"
        run["status"] = "running"
        packet["orca"] = {key: value for key, value in launch.items() if key != "raw"}
        write_json_atomic(packet_path, packet)

    write_json_atomic(RUN, run)
    output = {
        "status": run["status"],
        "context_packet": run["context_packet"],
        "profile": effective_profile,
        "risk": risk,
        "budget": budget,
        "model_route": model_route,
        "requires_worktree": requires_worktree,
        "workers": run["workers"],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0

def command_finish(args: argparse.Namespace) -> int:
    run = load_json(RUN, {})
    if not run.get("run_id"):
        print(json.dumps({"status": "invalid", "error": "no active run"}))
        return 2
    merged = args.status == "merged"
    if merged and not args.merge_sha:
        print(json.dumps({"status": "invalid", "error": "merged status requires --merge-sha"}))
        return 2
    cleanup_result = None
    if args.cleanup:
        if not (merged and args.worktree_clean and run.get("worktree")):
            print(json.dumps({"status": "blocked", "error": "cleanup requires merged status, merge SHA, clean confirmation and recorded worktree"}))
            return 2
        try:
            from orca_adapter import OrcaError, cleanup
            cleanup_result = cleanup(run["worktree"])
        except (ImportError, OrcaError) as exc:
            run["status"] = "blocked"
            run["blocker"] = f"cleanup unverifiable: {exc}"
            write_json_atomic(RUN, run)
            print(json.dumps({"status": "blocked", "error": run["blocker"]}, ensure_ascii=False, indent=2))
            return 2
        branch = run.get("branch")
        if branch and in_git() and run_git("branch", "--show-current").stdout.strip() != branch:
            deletion = run_git("branch", "-d", branch)
            if deletion.returncode != 0:
                cleanup_result["branch_warning"] = (deletion.stderr or deletion.stdout).strip()
    run.update({
        "status": args.status, "stage": "finished", "pull_request": args.pull_request or run.get("pull_request"),
        "merge_sha": args.merge_sha, "last_checkpoint": now(), "blocker": args.blocker,
        "cleanup": cleanup_result, "updated_at": now(),
    })
    if cleanup_result:
        run["worktree"] = None
        run["workers"] = []
    write_json_atomic(RUN, run)
    tasks = load_json(TASKS, {"tasks": []})
    for task in tasks.get("tasks", []):
        if task.get("id") == run.get("current_task"):
            task["status"] = args.status
            task["pull_request"] = run.get("pull_request")
            task["merge_sha"] = args.merge_sha
            task.setdefault("evidence", []).append({"at": now(), "receipt": args.evidence})
    write_json_atomic(TASKS, tasks)
    if args.stage and (args.input_tokens or args.output_tokens):
        record_usage(args.stage, args.input_tokens, args.output_tokens, args.measurement)
    print(json.dumps({"status": args.status, "cleanup": cleanup_result}, ensure_ascii=False, indent=2))
    return 0


def command_checkpoint(args: argparse.Namespace) -> int:
    run = load_json(RUN, {})
    if not run.get("run_id"):
        print(json.dumps({"status": "invalid", "error": "no active run"}))
        return 2
    task_id = args.task or run.get("current_task")
    tasks = load_json(TASKS, {"tasks": []})
    target = next((item for item in tasks.get("tasks", []) if item.get("id") == task_id), None)
    if target is None:
        print(json.dumps({"status": "invalid", "error": f"unknown task {task_id}"}, ensure_ascii=False))
        return 2
    target["status"] = args.status
    target.setdefault("evidence", []).append({"at": now(), "receipt": args.evidence})
    tasks["updated_at"] = now()
    write_json_atomic(TASKS, tasks)
    run.update({"current_task": task_id, "last_checkpoint": now(), "stage": "checkpoint", "updated_at": now()})
    if args.status in {"blocked", "failed"}:
        run["status"] = args.status
        run["blocker"] = args.blocker
    else:
        run["status"] = "running"
        run["blocker"] = None
    write_json_atomic(RUN, run)
    if args.stage and (args.input_tokens or args.output_tokens):
        record_usage(args.stage, args.input_tokens, args.output_tokens, args.measurement)
    try:
        from budget_guard import POLICY_PATH, evaluate, load
        budget, code = evaluate(load(POLICY_PATH), load(USAGE), "feature", "after-feature")
    except (ImportError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "invalid", "error": f"budget guard unavailable: {exc}"}, ensure_ascii=False))
        return 2
    if code != 0:
        run.update({"status": "blocked", "blocker": budget, "updated_at": now()})
        write_json_atomic(RUN, run)
    print(json.dumps({"status": run["status"], "task": task_id, "task_status": args.status, "budget": budget}, ensure_ascii=False, indent=2))
    return code


def command_status() -> int:
    run = load_json(RUN, {})
    usage = load_json(USAGE, {})
    output = {"run": run, "usage_by_stage": usage.get("by_stage", {}), "token_estimates": profile_token_estimates()}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def tracked_files() -> list[Path]:
    if in_git():
        return [ROOT / value for value in run_git("ls-files", "-z").stdout.split("\0") if value]
    return [path for path in ROOT.rglob("*") if path.is_file() and ".harness" not in path.parts and ".planning" not in path.parts]


def gate_text() -> int:
    errors = []
    for path in tracked_files():
        if path.suffix.lower() not in TEXT_EXTS:
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if "\u2013" in line or "\u2014" in line:
                errors.append(f"{path.relative_to(ROOT)}:{line_number}: forbidden dash")
    for error in errors:
        print(error)
    print("TEXT OK" if not errors else "TEXT FAILED")
    return 1 if errors else 0


def gate_staged() -> int:
    if not in_git():
        print("STAGED SKIPPED: no Git")
        return 0
    paths = [value.replace("\\", "/") for value in run_git("diff", "--cached", "--name-only", "-z").stdout.split("\0") if value]
    errors = []
    for value in paths:
        if value == ".gitkeep" or value.endswith("/.gitkeep"):
            errors.append(f"forbidden .gitkeep: {value}")
        if value in LOCAL_PATHS or any(value.startswith(prefix) for prefix in LOCAL_PATHS if prefix.endswith("/")):
            errors.append(f"local file staged: {value}")
    for error in errors:
        print(error)
    print("STAGED OK" if not errors else "STAGED FAILED")
    return 1 if errors else 0


def gate_branch(name: str | None) -> int:
    name = name or (run_git("branch", "--show-current").stdout.strip() if in_git() else "")
    print("BRANCH OK" if BRANCH_RE.fullmatch(name) else f"BRANCH FAILED: {name}")
    return 0 if BRANCH_RE.fullmatch(name) else 1


def gate_commit(message: str) -> int:
    errors = [] if COMMIT_RE.fullmatch(message) and not message.endswith(".") else ["invalid format"]
    errors.extend(f"forbidden text: {pattern.pattern}" for pattern in FORBIDDEN_META if pattern.search(message))
    for error in errors:
        print(f"COMMIT FAILED: {error}")
    print("COMMIT OK" if not errors else "COMMIT FAILED")
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("status")
    sub.add_parser("validate-prd")
    sub.add_parser("sync-tasks")
    sub.add_parser("progress")
    prepare = sub.add_parser("prepare")
    prepare.add_argument("task")
    prepare.add_argument("--profile", default="lean")
    prepare.add_argument("--interaction", choices=["supervised", "autonomous"], default="autonomous")
    prepare.add_argument("--destination", choices=["local", "github"], default="local")
    prepare.add_argument("--scope", choices=["product", "next-wave", "feature", "change"], default="feature")
    prepare.add_argument("--role", default="implementer")
    prepare.add_argument("--launch-orca", action="store_true", help="compatibility flag; autonomous GitHub launches by default")
    prepare.add_argument("--defer-worktree", action="store_true", help="prepare only; do not launch the required Orca worktree")
    prepare.add_argument("--agent", default="codex")
    prepare.add_argument("--model")
    prepare.add_argument("--provider", help="routing provider key, for example platform, openai or anthropic")
    prepare.add_argument("--effort")
    prepare.add_argument("--prompt")
    checkpoint = sub.add_parser("checkpoint")
    checkpoint.add_argument("--task")
    checkpoint.add_argument("--status", choices=["completed", "blocked", "failed"], default="completed")
    checkpoint.add_argument("--evidence")
    checkpoint.add_argument("--blocker")
    checkpoint.add_argument("--stage", choices=["planning", "spec", "implementation", "quality", "review"])
    checkpoint.add_argument("--input-tokens", type=int, default=0)
    checkpoint.add_argument("--output-tokens", type=int, default=0)
    checkpoint.add_argument("--measurement", choices=["actual", "estimated"], default="estimated")
    finish = sub.add_parser("finish")
    finish.add_argument("--status", required=True, choices=["merged", "completed-local", "blocked", "failed", "cancelled"])
    finish.add_argument("--pull-request")
    finish.add_argument("--merge-sha")
    finish.add_argument("--blocker")
    finish.add_argument("--evidence")
    finish.add_argument("--cleanup", action="store_true")
    finish.add_argument("--worktree-clean", action="store_true")
    finish.add_argument("--stage", choices=["planning", "spec", "implementation", "quality", "review"])
    finish.add_argument("--input-tokens", type=int, default=0)
    finish.add_argument("--output-tokens", type=int, default=0)
    finish.add_argument("--measurement", choices=["actual", "estimated"], default="estimated")
    gate = sub.add_parser("gate")
    gate_sub = gate.add_subparsers(dest="gate", required=True)
    gate_sub.add_parser("text")
    gate_sub.add_parser("staged")
    branch = gate_sub.add_parser("branch")
    branch.add_argument("--name")
    commit = gate_sub.add_parser("commit")
    commit.add_argument("--message", required=True)
    args = parser.parse_args()
    if args.command == "doctor": return command_doctor()
    if args.command == "status": return command_status()
    if args.command == "validate-prd": return command_validate_prd()
    if args.command == "sync-tasks": return command_sync_tasks()
    if args.command == "progress": return command_progress()
    if args.command == "prepare": return command_prepare(args)
    if args.command == "checkpoint": return command_checkpoint(args)
    if args.command == "finish": return command_finish(args)
    if args.gate == "text": return gate_text()
    if args.gate == "staged": return gate_staged()
    if args.gate == "branch": return gate_branch(args.name)
    if args.gate == "commit": return gate_commit(args.message)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
