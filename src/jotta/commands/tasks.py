"""Validate the PRD and keep the task list in sync with it."""

from __future__ import annotations

from jotta.core.paths import ProjectPaths
from jotta.core.prd import parse_prd
from jotta.core.state import JSONDict, load_json, now, sha256, write_json_atomic

DONE_STATUSES = {"merged", "completed-local", "completed"}


def validate_prd(paths: ProjectPaths) -> int:
    features, errors = parse_prd(paths.prd)
    if not features:
        errors.append("no feature found in dependency table")
    for error in errors:
        print(f"- {error}")
    print(f"PRD OK: {len(features)} features" if not errors else "PRD INVALID")
    return 1 if errors else 0


def sync_tasks(paths: ProjectPaths) -> int:
    features, errors = parse_prd(paths.prd)
    if errors or not features:
        for error in errors or ["no feature found"]:
            print(f"- {error}")
        return 1
    current = load_json(paths.tasks, {"tasks": []})
    old = {item["id"]: item for item in current.get("tasks", [])}
    completed = {task_id for task_id, item in old.items() if item.get("status") in DONE_STATUSES}
    tasks: list[JSONDict] = []
    for feature in features:
        previous = old.get(feature["id"], {})
        ready = all(dep in completed for dep in feature["dependencies"])
        status = previous.get("status") or ("ready" if ready else "pending")
        tasks.append(
            {
                **feature,
                "type": "feature",
                "source": "prd",
                "status": status,
                "branch": previous.get("branch"),
                "pull_request": previous.get("pull_request"),
                "merge_sha": previous.get("merge_sha"),
                "evidence": previous.get("evidence", []),
            }
        )
    write_json_atomic(
        paths.tasks,
        {
            "schema_version": 2,
            "prd_path": ".planning/PRD.md",
            "prd_hash": f"sha256:{sha256(paths.prd)}",
            "updated_at": now(),
            "tasks": tasks,
        },
    )
    print(f"TASKS SYNCED: {len(tasks)}")
    return 0


def progress(paths: ProjectPaths) -> int:
    data = load_json(paths.tasks, {"tasks": []})
    groups: dict[str, list[str]] = {}
    for item in data.get("tasks", []):
        label = f"{item.get('id')} {item.get('name', '')}".strip()
        groups.setdefault(item.get("status", "unknown"), []).append(label)
    lines = ["# Progress", "", f"PRD hash: {data.get('prd_hash')}", ""]
    for status in sorted(groups):
        lines.extend([f"## {status}", "", *[f"- {label}" for label in groups[status]], ""])
    (paths.state / "progress.md").write_text("\n".join(lines), encoding="utf-8")
    print("PROGRESS UPDATED")
    return 0
