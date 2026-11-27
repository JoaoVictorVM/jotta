"""The ``jotta status`` command: the current run, where its tokens and cost went, and the budget decision."""

from __future__ import annotations

from jotta.budget import guard
from jotta.core.context import profile_token_estimates
from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict, default_run, default_usage, load_json, print_json
from jotta.telemetry import measure

STAGE_ORDER = ("planning", "spec", "implementation", "quality", "review", "unassigned")
COLUMNS = (
    ("Feature", "task"),
    ("Stage", "stage"),
    ("Messages", "messages"),
    ("Input", "input_tokens"),
    ("Output", "output_tokens"),
    ("Cache read", "cache_read_tokens"),
    ("Cache write", "cache_creation_tokens"),
    ("Cost USD", "estimated_cost_usd"),
)


def stage_key(stage: str) -> tuple[int, str]:
    return (STAGE_ORDER.index(stage) if stage in STAGE_ORDER else len(STAGE_ORDER), stage)


def measured_rows(report: JSONDict) -> list[JSONDict]:
    rows = []
    for task, stages in report["by_task_stage"].items():
        for stage in sorted(stages, key=stage_key):
            rows.append({"task": task, "stage": stage, **stages[stage]})
    return rows


def estimated_rows(usage: JSONDict) -> list[JSONDict]:
    rows = []
    for stage, values in sorted((usage.get("by_stage") or {}).items(), key=lambda item: stage_key(item[0])):
        if values.get("input_tokens") or values.get("output_tokens"):
            rows.append(
                {
                    "task": "run",
                    "stage": stage,
                    "input_tokens": values.get("input_tokens", 0),
                    "output_tokens": values.get("output_tokens", 0),
                }
            )
    return rows


def cell(row: JSONDict, key: str) -> str:
    value = row.get(key)
    if value is None:
        return "-"
    if key == "estimated_cost_usd":
        unpriced = int(row.get("unpriced_messages") or 0)
        if unpriced and unpriced >= int(row.get("messages") or 0):
            return "-"
        return f"{float(value):.4f}{'*' if unpriced else ''}"
    return f"{value:,}" if isinstance(value, int) else str(value)


def table(rows: list[JSONDict]) -> list[str]:
    grid = [[title for title, _ in COLUMNS], *[[cell(row, key) for _, key in COLUMNS] for row in rows]]
    widths = [max(len(line[index]) for line in grid) for index in range(len(COLUMNS))]

    def line(values: list[str]) -> str:
        return "  ".join(
            value.ljust(width) if index < 2 else value.rjust(width)
            for index, (value, width) in enumerate(zip(values, widths, strict=True))
        ).rstrip()

    return [line(grid[0]), line(["-" * width for width in widths]), *[line(values) for values in grid[1:]]]


def collect(paths: ProjectPaths) -> JSONDict:
    run = load_json(paths.run, default_run())
    usage = load_json(paths.usage, default_usage())
    try:
        report = measure.run_report(paths, run.get("run_id"))
    except (OSError, ValueError):
        report = None
    try:
        decision, _code = guard.evaluate(load_json(paths.budget_policy), usage, "run", None)
        budget: JSONDict | None = {
            "status": decision["status"],
            "effective_percent": decision["effective_percent"],
            "effective_source": decision["effective_source"],
            "measurement": decision["execution"]["measurement"],
        }
    except (OSError, ValueError, KeyError):
        budget = None
    measured: JSONDict | None = None
    if report is not None:
        measured = {
            "transcripts": report["transcripts"],
            "sessions": report["sessions"],
            "totals": report["totals"],
            "by_task": report["by_task"],
            "by_task_stage": report["by_task_stage"],
            "by_model": report["by_model"],
            "unpriced_models": report["unpriced_models"],
        }
    return {
        "run": run,
        "measurement": "measured" if measured else "estimated",
        "measured": measured,
        "usage_by_stage": usage.get("by_stage", {}),
        "budget": budget,
        "token_estimates": profile_token_estimates(paths.skills),
    }


def render(data: JSONDict) -> list[str]:
    run = data["run"]
    lines = [
        f"Run: {run.get('run_id') or 'none'} ({run.get('status')})",
        f"Task: {run.get('current_task') or '-'}  Stage: {run.get('stage') or '-'}  "
        f"Profile: {run.get('profile') or '-'}",
        "",
    ]
    measured = data["measured"]
    if measured:
        lines.append(f"Usage measured from {measured['transcripts']} transcript(s), {measured['sessions']} session(s):")
        lines += table([*measured_rows(measured), {"task": "Total", "stage": "", **measured["totals"]}])
        if measured["unpriced_models"]:
            models = ", ".join(measured["unpriced_models"])
            lines.append(f"No price in pricing.json for {models}: cost shown as - when unknown, * when partial.")
    else:
        rows = estimated_rows({"by_stage": data["usage_by_stage"]})
        lines.append("Usage estimated: no transcript of this run could be measured.")
        lines += table(rows) if rows else ["No usage recorded yet."]
    budget = data["budget"]
    if budget is None:
        lines += ["", "Budget: unavailable; check .jotta/policy/budget.json"]
    else:
        lines += [
            "",
            f"Budget: {budget['status']} at {budget['effective_percent']:.1f}% "
            f"({budget['effective_source']}, {budget['measurement']})",
        ]
    return lines


def run(paths: ProjectPaths, as_json: bool) -> int:
    data = collect(paths)
    if as_json:
        print_json(data)
    else:
        print("\n".join(render(data)))
    return 0
