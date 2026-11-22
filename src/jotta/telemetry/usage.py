"""Price usage records and group them by model and by task.

Prices come from ``.jotta/policy/pricing.json``, in US dollars per million tokens. Each key of ``models`` is an
exact model id or a pattern such as ``claude-opus-*``; an exact id wins, then the first matching pattern. A model
without a price is reported under ``unpriced_models`` with a ``null`` cost: the harness never invents a price.

A record belongs to a task when its session was assigned to that task, or else when its timestamp falls inside one
of the task's periods, which ``jotta prepare`` opens and ``jotta checkpoint`` and ``jotta finish`` close.
"""

from __future__ import annotations

import fnmatch
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict, load_json, now, write_json_atomic
from jotta.telemetry.transcripts import Usage

PRICE_FIELDS = {
    "input_tokens": "input",
    "output_tokens": "output",
    "cache_read_tokens": "cache_read",
    "cache_creation_tokens": "cache_write",
}
TOKEN_FIELDS = tuple(PRICE_FIELDS)
UNASSIGNED = "unassigned"


def pricing_path(paths: ProjectPaths) -> Path:
    return paths.policy / "pricing.json"


def periods_path(paths: ProjectPaths) -> Path:
    return paths.state / "task-periods.json"


def load_pricing(paths: ProjectPaths) -> dict[str, JSONDict]:
    models = load_json(pricing_path(paths), {}).get("models") or {}
    return {str(key): value for key, value in models.items() if isinstance(value, dict)}


def price_for(model: str, pricing: dict[str, JSONDict]) -> JSONDict | None:
    if model in pricing:
        return pricing[model]
    return next((prices for pattern, prices in pricing.items() if fnmatch.fnmatchcase(model, pattern)), None)


def cost(record: Usage, prices: JSONDict) -> float | None:
    """The cost of a record; a missing cache price falls back to the input price, so the estimate never drops."""
    total = 0.0
    for field, key in PRICE_FIELDS.items():
        tokens = getattr(record, field)
        if not tokens:
            continue
        price = prices.get(key, prices.get("input")) if key.startswith("cache") else prices.get(key)
        if not isinstance(price, (int, float)):
            return None
        total += tokens * float(price) / 1_000_000
    return total


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def load_periods(paths: ProjectPaths) -> list[JSONDict]:
    periods = load_json(periods_path(paths), {}).get("periods") or []
    return [period for period in periods if isinstance(period, dict)]


def close_open_periods(periods: list[JSONDict], moment: str) -> None:
    for period in periods:
        if period.get("ended_at") is None:
            period["ended_at"] = moment


def open_period(paths: ProjectPaths, task: str, run_id: str | None) -> None:
    """Start a usage period for ``task``, closing the one before it."""
    periods = load_periods(paths)
    moment = now()
    close_open_periods(periods, moment)
    periods.append({"task": task, "run_id": run_id, "started_at": moment, "ended_at": None})
    write_json_atomic(periods_path(paths), {"schema_version": 1, "periods": periods})


def close_period(paths: ProjectPaths) -> None:
    """End the open usage period, if any."""
    periods = load_periods(paths)
    if any(period.get("ended_at") is None for period in periods):
        close_open_periods(periods, now())
        write_json_atomic(periods_path(paths), {"schema_version": 1, "periods": periods})


def task_for(record: Usage, periods: list[JSONDict], sessions: dict[str, str]) -> str:
    if record.session_id in sessions:
        return sessions[record.session_id]
    moment = parse_time(record.timestamp)
    if moment is None:
        return UNASSIGNED
    for period in reversed(periods):
        start = parse_time(period.get("started_at"))
        end = parse_time(period.get("ended_at"))
        if start is not None and start <= moment and (end is None or moment < end):
            return str(period.get("task"))
    return UNASSIGNED


def empty_totals() -> JSONDict:
    return {"messages": 0, **dict.fromkeys(TOKEN_FIELDS, 0), "estimated_cost_usd": 0.0, "unpriced_messages": 0}


def add(totals: JSONDict, record: Usage, value: float | None) -> None:
    totals["messages"] += 1
    for field in TOKEN_FIELDS:
        totals[field] += getattr(record, field)
    if value is None:
        totals["unpriced_messages"] += 1
    else:
        totals["estimated_cost_usd"] += value


def rounded(totals: JSONDict) -> JSONDict:
    return {**totals, "estimated_cost_usd": round(float(totals["estimated_cost_usd"]), 6)}


def summarize(
    records: Iterable[Usage],
    pricing: dict[str, JSONDict],
    periods: list[JSONDict] | None = None,
    sessions: dict[str, str] | None = None,
) -> JSONDict:
    """Totals of ``records`` overall, per model, per agent and per task."""
    overall = empty_totals()
    by_model: dict[str, JSONDict] = {}
    by_agent: dict[str, JSONDict] = {}
    by_task: dict[str, JSONDict] = {}
    unpriced: set[str] = set()
    session_ids: set[str] = set()
    for record in records:
        prices = price_for(record.model, pricing)
        value = cost(record, prices) if prices is not None else None
        if value is None:
            unpriced.add(record.model)
        task = task_for(record, periods or [], sessions or {})
        for group in (overall, by_model.setdefault(record.model, empty_totals())):
            add(group, record, value)
        add(by_agent.setdefault(record.agent, empty_totals()), record, value)
        add(by_task.setdefault(task, empty_totals()), record, value)
        session_ids.add(record.session_id)
    return {
        "sessions": len(session_ids),
        "totals": rounded(overall),
        "by_model": {name: rounded(value) for name, value in sorted(by_model.items())},
        "by_agent": {name: rounded(value) for name, value in sorted(by_agent.items())},
        "by_task": {name: rounded(value) for name, value in sorted(by_task.items())},
        "unpriced_models": sorted(unpriced),
    }
