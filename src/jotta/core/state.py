"""JSON state helpers with atomic writes."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

JSONDict = dict[str, Any]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: JSONDict | None = None) -> JSONDict:
    if not path.exists() and default is not None:
        return default
    data: JSONDict = json.loads(path.read_text(encoding="utf-8"))
    return data


def write_json_atomic(path: Path, data: JSONDict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def print_json(data: JSONDict, indent: int | None = 2) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=indent))


def default_run() -> JSONDict:
    """State of a project with no recorded run."""
    return {
        "schema_version": 2,
        "run_id": None,
        "status": "idle",
        "scope": None,
        "profile": None,
        "requested_profile": None,
        "interaction": None,
        "destination": None,
        "current_task": None,
        "stage": None,
        "context_packet": None,
        "risk": None,
        "branch": None,
        "worktree": None,
        "workers": [],
        "pull_request": None,
        "merge_sha": None,
        "last_checkpoint": None,
        "blocker": None,
        "cleanup": None,
        "updated_at": None,
    }


def default_tasks() -> JSONDict:
    """Task list of a project whose PRD was never synchronized."""
    return {"schema_version": 2, "prd_path": ".planning/PRD.md", "prd_hash": None, "updated_at": None, "tasks": []}


def default_usage() -> JSONDict:
    """Usage of a project with nothing recorded yet."""
    stages = ("planning", "spec", "implementation", "quality", "review")
    return {
        "schema_version": 2,
        "input_tokens": 0,
        "output_tokens": 0,
        "estimated_cost_usd": 0.0,
        "provider_usage_percent": None,
        "provider_usage_source": "unavailable",
        "provider_usage_checked_at": None,
        "by_stage": {stage: {"input_tokens": 0, "output_tokens": 0, "measurement": "estimated"} for stage in stages},
        "reservations": [],
        "authorization": None,
        "updated_at": None,
    }
