"""Read token usage from the local session transcripts of Claude Code and Codex.

Both agents keep one JSONL file per session:

- Claude Code writes ``~/.claude/projects/<project>/<session>.jsonl``, and its subagents write
  ``<session>/subagents/*.jsonl`` next to it. Every ``assistant`` entry carries the
  ``message.usage`` of its API response, and a response with several content blocks repeats the same usage in one
  entry per block, so usage is counted once per ``message.id``.
- Codex writes ``~/.codex/sessions/<yyyy>/<mm>/<dd>/rollout-*.jsonl``. A ``token_usage_record`` entry carries the
  usage of one response. Older files only have ``token_count`` events, whose ``last_token_usage`` is the usage of
  the latest call and may be repeated, so an event whose cumulative total did not change is skipped. The model comes
  from the latest ``turn_context``.

Every record is normalized to four disjoint counts: uncached input, output, cache read and cache creation. Codex
reports cached tokens inside ``input_tokens``, so they are subtracted. A malformed line is skipped, never guessed.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from jotta.core.state import JSONDict

AGENTS = ("claude", "codex")


@dataclass(frozen=True)
class Usage:
    """The tokens of one model response."""

    agent: str
    session_id: str
    message_id: str
    model: str
    timestamp: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_read_tokens + self.cache_creation_tokens


def entries(lines: Iterable[str]) -> Iterable[JSONDict]:
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            yield entry


def number(data: object, key: str) -> int:
    value = data.get(key) if isinstance(data, dict) else None
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


def parse_claude(lines: Iterable[str]) -> list[Usage]:
    """One record per Claude Code API response."""
    records: dict[str, Usage] = {}
    for entry in entries(lines):
        message = entry.get("message")
        if entry.get("type") != "assistant" or not isinstance(message, dict):
            continue
        usage = message.get("usage")
        model = str(message.get("model") or "")
        if not isinstance(usage, dict) or not model or model.startswith("<"):
            continue
        message_id = str(message.get("id") or entry.get("requestId") or entry.get("uuid") or "")
        if not message_id or message_id in records:
            continue
        records[message_id] = Usage(
            agent="claude",
            session_id=str(entry.get("sessionId") or ""),
            message_id=message_id,
            model=model,
            timestamp=str(entry.get("timestamp") or ""),
            input_tokens=number(usage, "input_tokens"),
            output_tokens=number(usage, "output_tokens"),
            cache_read_tokens=number(usage, "cache_read_input_tokens"),
            cache_creation_tokens=number(usage, "cache_creation_input_tokens"),
        )
    return list(records.values())


def codex_usage(usage: JSONDict, **fields: str) -> Usage:
    cached = number(usage, "cached_input_tokens")
    return Usage(
        agent="codex",
        input_tokens=max(number(usage, "input_tokens") - cached, 0),
        output_tokens=number(usage, "output_tokens"),
        cache_read_tokens=cached,
        cache_creation_tokens=number(usage, "cache_write_input_tokens"),
        **fields,
    )


def parse_codex(lines: Iterable[str]) -> list[Usage]:
    """One record per Codex response, from ``token_usage_record`` entries or, without them, ``token_count`` events."""
    session_id, model = "", ""
    records: list[Usage] = []
    fallback: list[Usage] = []
    seen: set[str] = set()
    last_total: object = None
    for entry in entries(lines):
        kind = entry.get("type")
        payload = entry.get("payload")
        if not isinstance(payload, dict):
            continue
        timestamp = str(entry.get("timestamp") or "")
        if kind == "session_meta":
            session_id = str(payload.get("session_id") or payload.get("id") or session_id)
        elif kind == "turn_context":
            model = str(payload.get("model") or model)
        elif kind == "token_usage_record" and isinstance(payload.get("usage"), dict):
            response = str(payload.get("response_id") or f"{payload.get('turn_id')}:{len(records)}")
            if response in seen:
                continue
            seen.add(response)
            session = str(payload.get("session_id") or session_id)
            records.append(
                codex_usage(payload["usage"], session_id=session, message_id=response, model=model, timestamp=timestamp)
            )
        elif kind == "event_msg" and payload.get("type") == "token_count":
            info = payload.get("info")
            if not isinstance(info, dict) or not isinstance(info.get("last_token_usage"), dict):
                continue
            total = info.get("total_token_usage")
            if total == last_total:
                continue
            last_total = total
            fallback.append(
                codex_usage(
                    info["last_token_usage"],
                    session_id=session_id,
                    message_id=f"token-count:{len(fallback)}",
                    model=model,
                    timestamp=timestamp,
                )
            )
    chosen = records or fallback
    return [record if record.session_id else replace_session(record, session_id) for record in chosen]


def replace_session(record: Usage, session_id: str) -> Usage:
    return Usage(**{**record.__dict__, "session_id": session_id})


def parse_file(path: Path, agent: str | None = None) -> list[Usage]:
    """The usage records of one transcript, detecting its agent from the content when not given."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if agent is None:
        agent = "codex" if any('"session_meta"' in line or '"token_count"' in line for line in lines[:50]) else "claude"
    return parse_codex(lines) if agent == "codex" else parse_claude(lines)


def claude_home() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def claude_project_dir(root: Path) -> Path:
    """The folder where Claude Code keeps the transcripts of a project: its path with every symbol as ``-``."""
    return claude_home() / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(root.resolve()))


def codex_session_cwd(path: Path) -> str | None:
    """The working directory recorded in the first ``session_meta`` entry of a Codex transcript."""
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for _ in range(20):
                line = handle.readline()
                if not line:
                    break
                for entry in entries([line]):
                    payload = entry.get("payload")
                    if entry.get("type") == "session_meta" and isinstance(payload, dict):
                        return str(payload.get("cwd") or "") or None
    except OSError:
        return None
    return None


def inside(child: str, root: Path) -> bool:
    try:
        Path(child).resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def discover(root: Path, agents: Iterable[str] = AGENTS) -> list[tuple[str, Path]]:
    """The local transcripts of the sessions that ran in ``root`` or below it."""
    found: list[tuple[str, Path]] = []
    if "claude" in agents:
        folder = claude_project_dir(root)
        transcripts = [*folder.glob("*.jsonl"), *folder.glob("*/subagents/*.jsonl")]
        found += [("claude", path) for path in sorted(transcripts)]
    if "codex" in agents:
        for path in sorted((codex_home() / "sessions").glob("*/*/*/*.jsonl")):
            cwd = codex_session_cwd(path)
            if cwd and inside(cwd, root):
                found.append(("codex", path))
    return found
