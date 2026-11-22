"""Feed the budget with the usage measured from the agents' transcripts.

``jotta prepare`` and ``jotta checkpoint`` call :func:`refresh` before the budget guard decides. It sums the
transcript messages that fall inside the task periods of the current run and stores them in ``usage.json`` under
``measured``, with ``measurement: measured``. When no message can be measured, for example before the first task
of a run or when the agent keeps no transcripts, ``measurement`` stays ``estimated`` and the guard keeps using the
recorded estimates. A measurement that fails never blocks a command: it falls back to the estimates.
"""

from __future__ import annotations

from datetime import datetime

from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict, default_usage, load_json, now, write_json_atomic
from jotta.telemetry import transcripts
from jotta.telemetry.usage import load_periods, load_pricing, parse_time, summarize

# A transcript last written before the run started holds none of its messages. File times can trail the clock by a
# few milliseconds on some file systems, so the cut keeps a margin.
MTIME_TOLERANCE_SECONDS = 60.0


def run_periods(paths: ProjectPaths, run_id: str) -> list[tuple[datetime, datetime | None]]:
    periods = []
    for period in load_periods(paths):
        start = parse_time(period.get("started_at"))
        if period.get("run_id") == run_id and start is not None:
            periods.append((start, parse_time(period.get("ended_at"))))
    return periods


def inside_periods(timestamp: str, periods: list[tuple[datetime, datetime | None]]) -> bool:
    moment = parse_time(timestamp)
    return moment is not None and any(start <= moment and (end is None or moment < end) for start, end in periods)


def measure_run(paths: ProjectPaths, run_id: str | None) -> JSONDict | None:
    """The measured usage of the run's task periods, or ``None`` when nothing could be measured."""
    if not run_id:
        return None
    periods = run_periods(paths, run_id)
    if not periods:
        return None
    first = min(start for start, _ in periods).timestamp() - MTIME_TOLERANCE_SECONDS
    sources = [(agent, path) for agent, path in transcripts.discover(paths.root) if path.stat().st_mtime >= first]
    records = [
        record
        for agent, path in sources
        for record in transcripts.parse_file(path, agent)
        if inside_periods(record.timestamp, periods)
    ]
    if not records:
        return None
    summary = summarize(records, load_pricing(paths))
    return {
        "run_id": run_id,
        **summary["totals"],
        "unpriced_models": summary["unpriced_models"],
        "by_model": summary["by_model"],
        "transcripts": len(sources),
        "measured_at": now(),
    }


def refresh(paths: ProjectPaths, run_id: str | None) -> JSONDict | None:
    """Store the measured usage of ``run_id`` in ``usage.json`` and return it."""
    try:
        measured = measure_run(paths, run_id)
    except (OSError, ValueError):
        measured = None
    usage = load_json(paths.usage, default_usage())
    previous = usage.get("measured")
    if measured is not None:
        usage["measured"] = measured
    elif isinstance(previous, dict) and previous.get("run_id") != run_id:
        usage.pop("measured", None)
    usage["measurement"] = "measured" if isinstance(usage.get("measured"), dict) else "estimated"
    usage["updated_at"] = now()
    write_json_atomic(paths.usage, usage)
    return measured
