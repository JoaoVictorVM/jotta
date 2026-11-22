"""The ``jotta usage`` command: measured tokens and cost of the project's agent sessions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from jotta.core.paths import ProjectPaths
from jotta.core.state import print_json
from jotta.telemetry import transcripts
from jotta.telemetry.usage import load_periods, load_pricing, parse_time, summarize

EXIT_OK = 0
EXIT_INVALID = 2


def session_tasks(values: list[str]) -> dict[str, str]:
    """``ID=TASK`` pairs as a mapping; raises ``ValueError`` on a malformed pair."""
    pairs = {}
    for value in values:
        session, separator, task = value.partition("=")
        if not separator or not session or not task:
            raise ValueError(f"expected ID=TASK, got {value!r}")
        pairs[session] = task
    return pairs


def run(paths: ProjectPaths, args: argparse.Namespace) -> int:
    try:
        sessions = session_tasks(args.session)
        since = parse_time(args.since) if args.since else None
        if args.since and since is None:
            raise ValueError(f"invalid --since time {args.since!r}")
        sources: list[tuple[str | None, Path]]
        if args.transcript:
            sources = [(None, path) for path in args.transcript]
        else:
            sources = list(transcripts.discover(paths.root, args.agent or transcripts.AGENTS))
        records = [record for agent, path in sources for record in transcripts.parse_file(path, agent)]
        pricing = load_pricing(paths)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print_json({"status": "invalid", "error": str(exc)}, indent=None)
        return EXIT_INVALID
    if since is not None:
        records = [record for record in records if (moment := parse_time(record.timestamp)) and moment >= since]
    summary = summarize(records, pricing, load_periods(paths), sessions)
    print_json({"status": "measured", "measurement": "transcripts", "transcripts": len(sources), **summary})
    return EXIT_OK
