"""Export a run's measured usage as an OpenTelemetry trace, over OTLP/HTTP with JSON.

The export is optional and off by default. ``telemetry.otel`` in ``config.yaml`` turns it on and names the
endpoint; the standard ``OTEL_EXPORTER_OTLP_*`` environment variables override the endpoint and carry the headers,
so credentials never live in a versioned file. ``jotta finish`` exports the run when the export is on, and
``jotta export-trace`` exports it on demand.

A run becomes one trace:

- ``jotta.run`` spans the run's task periods;
- ``jotta.feature`` spans the periods of one task;
- ``jotta.stage`` spans the periods of one task in one stage, such as ``implementation`` or ``review``;
- ``chat <model>`` is a generation with the tokens and cost of one model in that stage.

Only the generations carry ``gen_ai.*`` usage attributes, so a backend that sums them, such as Langfuse, counts
every token once; the parent spans carry their totals under ``jotta.*``. Trace and span ids derive from the run id,
so exporting the same run again updates the trace instead of duplicating it. A failed export never blocks a
command: it is reported and the run goes on.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone

from jotta import __version__
from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict, default_run, load_json
from jotta.telemetry import measure
from jotta.telemetry.transcripts import Usage
from jotta.telemetry.usage import UNASSIGNED, add, cost, empty_totals, load_pricing, parse_time, price_for, task_for

DEFAULT_ENDPOINT = "http://localhost:4318/v1/traces"
DEFAULT_SERVICE = "jotta"
TIMEOUT_SECONDS = 10.0
PROVIDERS = {"claude": "anthropic", "codex": "openai"}
SPAN_KIND_INTERNAL = 1
STATUS_ERROR = 2
KEY_VALUE = re.compile(r"^(\s*)([A-Za-z0-9_.-]+):\s*(.*?)\s*$")


class OtelError(Exception):
    """The trace could not be delivered."""


@dataclass(frozen=True)
class OtelConfig:
    enabled: bool = False
    endpoint: str = DEFAULT_ENDPOINT
    service_name: str = DEFAULT_SERVICE
    headers: dict[str, str] = field(default_factory=dict)


def yaml_section(text: str, *keys: str) -> dict[str, str]:
    """The scalar values directly under the nested mapping ``keys`` of a simple block-style YAML document."""
    path: list[tuple[int, str]] = []
    values: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = KEY_VALUE.match(line.split(" #", 1)[0])
        if match is None:
            continue
        indent, key, value = len(match.group(1)), match.group(2), match.group(3)
        while path and path[-1][0] >= indent:
            path.pop()
        if tuple(name for _, name in path) == keys and value:
            values[key] = value.strip("\"'")
        if not value:
            path.append((indent, key))
    return values


def parse_headers(value: str) -> dict[str, str]:
    """``key=value`` pairs separated by commas, as in ``OTEL_EXPORTER_OTLP_HEADERS``."""
    headers = {}
    for pair in value.split(","):
        key, separator, item = pair.partition("=")
        if separator and key.strip():
            headers[urllib.parse.unquote(key.strip())] = urllib.parse.unquote(item.strip())
    return headers


def load_config(paths: ProjectPaths, environ: Mapping[str, str] | None = None) -> OtelConfig:
    """The export settings from ``config.yaml``, with the endpoint and headers from the environment."""
    env = os.environ if environ is None else environ
    try:
        section = yaml_section((paths.harness / "config.yaml").read_text(encoding="utf-8"), "telemetry", "otel")
    except OSError:
        section = {}
    endpoint = section.get("endpoint") or DEFAULT_ENDPOINT
    if env.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"):
        endpoint = env["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"]
    elif env.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        endpoint = env["OTEL_EXPORTER_OTLP_ENDPOINT"].rstrip("/") + "/v1/traces"
    headers = env.get("OTEL_EXPORTER_OTLP_TRACES_HEADERS") or env.get("OTEL_EXPORTER_OTLP_HEADERS") or ""
    return OtelConfig(
        enabled=section.get("enabled", "false").lower() == "true",
        endpoint=endpoint,
        service_name=section.get("service_name") or DEFAULT_SERVICE,
        headers=parse_headers(headers),
    )


def identifier(*parts: str, length: int) -> str:
    return hashlib.sha256("\x1f".join(("jotta", *parts)).encode("utf-8")).hexdigest()[:length]


def nanos(moment: datetime) -> str:
    return str(int(moment.timestamp() * 1_000_000) * 1000)


def attribute(key: str, value: object) -> JSONDict:
    if isinstance(value, bool):
        return {"key": key, "value": {"boolValue": value}}
    if isinstance(value, int):
        return {"key": key, "value": {"intValue": str(value)}}
    if isinstance(value, float):
        return {"key": key, "value": {"doubleValue": value}}
    return {"key": key, "value": {"stringValue": str(value)}}


def priced_cost(totals: JSONDict) -> float | None:
    """The cost of a group, or ``None`` when no message in it has a price."""
    if totals["unpriced_messages"] >= totals["messages"]:
        return None
    return round(float(totals["estimated_cost_usd"]), 6)


def total_attributes(totals: JSONDict) -> dict[str, object]:
    values: dict[str, object] = {
        "jotta.messages": totals["messages"],
        "jotta.input_tokens": totals["input_tokens"],
        "jotta.output_tokens": totals["output_tokens"],
        "jotta.cache_read_tokens": totals["cache_read_tokens"],
        "jotta.cache_creation_tokens": totals["cache_creation_tokens"],
        "jotta.unpriced_messages": totals["unpriced_messages"],
    }
    value = priced_cost(totals)
    if value is not None:
        values["jotta.cost_usd"] = value
    return values


def generation_attributes(agent: str, model: str, totals: JSONDict) -> dict[str, object]:
    fresh, read, write = totals["input_tokens"], totals["cache_read_tokens"], totals["cache_creation_tokens"]
    values: dict[str, object] = {
        "langfuse.observation.type": "generation",
        "gen_ai.operation.name": "chat",
        "gen_ai.provider.name": PROVIDERS.get(agent, agent),
        "gen_ai.request.model": model,
        "gen_ai.response.model": model,
        "gen_ai.usage.input_tokens": fresh + read + write,
        "gen_ai.usage.output_tokens": totals["output_tokens"],
        "gen_ai.usage.cache_read.input_tokens": read,
        "gen_ai.usage.cache_creation.input_tokens": write,
        "langfuse.observation.usage_details": json.dumps(
            {
                "input": fresh,
                "output": totals["output_tokens"],
                "cache_read_input_tokens": read,
                "cache_creation_input_tokens": write,
            }
        ),
        "jotta.agent": agent,
        "jotta.messages": totals["messages"],
        "jotta.unpriced_messages": totals["unpriced_messages"],
    }
    value = priced_cost(totals)
    if value is not None:
        values["gen_ai.usage.cost"] = value
        values["langfuse.observation.cost_details"] = json.dumps({"total": value})
    return values


@dataclass
class Group:
    """Messages that share a span, with the time the span covers."""

    totals: JSONDict = field(default_factory=empty_totals)
    start: datetime | None = None
    end: datetime | None = None

    def cover(self, start: datetime | None, end: datetime | None) -> None:
        if start is not None:
            self.start = start if self.start is None else min(self.start, start)
        if end is not None:
            self.end = end if self.end is None else max(self.end, end)


def period_bounds(period: JSONDict, moment: datetime) -> tuple[datetime | None, datetime]:
    return parse_time(period.get("started_at")), parse_time(period.get("ended_at")) or moment


def build_trace(
    run_id: str,
    run: JSONDict,
    records: list[Usage],
    periods: list[JSONDict],
    pricing: dict[str, JSONDict],
    service_name: str = DEFAULT_SERVICE,
    moment: datetime | None = None,
) -> JSONDict:
    """The OTLP/JSON document of one run: a span per run, feature, stage and model."""
    moment = moment or datetime.now(timezone.utc)
    root = Group()
    tasks: dict[str, Group] = {}
    stages: dict[tuple[str, str], Group] = {}
    models: dict[tuple[str, str, str, str], Group] = {}
    for period in periods:
        start, end = period_bounds(period, moment)
        task, stage = str(period.get("task")), str(period.get("stage") or UNASSIGNED)
        for group in (root, tasks.setdefault(task, Group()), stages.setdefault((task, stage), Group())):
            group.cover(start, end)
    for record in records:
        prices = price_for(record.model, pricing)
        value = cost(record, prices) if prices is not None else None
        task, stage = task_for(record, periods, {})
        when = parse_time(record.timestamp) or moment
        key = (task, stage, record.agent, record.model)
        for group in (
            root,
            tasks.setdefault(task, Group()),
            stages.setdefault((task, stage), Group()),
            models.setdefault(key, Group()),
        ):
            add(group.totals, record, value)
        models[key].cover(when, when)
        for group in (root, tasks[task], stages[(task, stage)]):
            group.cover(when, when)

    trace_id = identifier(run_id, length=32)
    common = {"jotta.run.id": run_id, "langfuse.trace.metadata.run_id": run_id}

    def span(name: str, span_id: str, parent: str | None, group: Group, attributes: dict[str, object]) -> JSONDict:
        start = group.start or moment
        document: JSONDict = {
            "traceId": trace_id,
            "spanId": span_id,
            "name": name,
            "kind": SPAN_KIND_INTERNAL,
            "startTimeUnixNano": nanos(start),
            "endTimeUnixNano": nanos(max(group.end or start, start)),
            "attributes": [attribute(key, value) for key, value in {**common, **attributes}.items()],
        }
        if parent:
            document["parentSpanId"] = parent
        return document

    root_id = identifier(run_id, "run", length=16)
    root_span = span(
        "jotta.run",
        root_id,
        None,
        root,
        {
            "langfuse.observation.type": "span",
            "langfuse.trace.name": f"jotta {run_id}",
            "jotta.run.status": str(run.get("status") or "unknown"),
            "jotta.profile": str(run.get("profile") or "-"),
            **total_attributes(root.totals),
        },
    )
    if run.get("status") == "blocked":
        root_span["status"] = {"code": STATUS_ERROR, "message": str(run.get("blocker") or "blocked")}
    spans = [root_span]
    for task, group in sorted(tasks.items()):
        task_id = identifier(run_id, "task", task, length=16)
        attributes = {"langfuse.observation.type": "span", "jotta.task.id": task, **total_attributes(group.totals)}
        spans.append(span("jotta.feature", task_id, root_id, group, attributes))
    for (task, stage), group in sorted(stages.items()):
        stage_id = identifier(run_id, "stage", task, stage, length=16)
        parent = identifier(run_id, "task", task, length=16)
        attributes = {
            "langfuse.observation.type": "span",
            "jotta.task.id": task,
            "jotta.stage": stage,
            **total_attributes(group.totals),
        }
        spans.append(span("jotta.stage", stage_id, parent, group, attributes))
    for (task, stage, agent, model), group in sorted(models.items()):
        model_id = identifier(run_id, "model", task, stage, agent, model, length=16)
        parent = identifier(run_id, "stage", task, stage, length=16)
        attributes = {"jotta.task.id": task, "jotta.stage": stage, **generation_attributes(agent, model, group.totals)}
        spans.append(span(f"chat {model}", model_id, parent, group, attributes))
    return {
        "resourceSpans": [
            {
                "resource": {"attributes": [attribute("service.name", service_name)]},
                "scopeSpans": [{"scope": {"name": "jotta", "version": __version__}, "spans": spans}],
            }
        ]
    }


def send(payload: JSONDict, config: OtelConfig) -> int:
    """POST the trace to the OTLP/HTTP endpoint and return the HTTP status."""
    if urllib.parse.urlsplit(config.endpoint).scheme not in {"http", "https"}:
        raise OtelError(f"endpoint must be an http or https URL: {config.endpoint}")
    request = urllib.request.Request(  # noqa: S310 - the scheme is checked above
        config.endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={**config.headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            return int(response.status)
    except urllib.error.HTTPError as exc:
        raise OtelError(f"{config.endpoint} answered HTTP {exc.code}") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise OtelError(f"{config.endpoint} unreachable: {exc}") from exc


def export_run(
    paths: ProjectPaths,
    run_id: str | None = None,
    dry_run: bool = False,
    environ: Mapping[str, str] | None = None,
) -> JSONDict:
    """Export a run, by default the current one, and report what happened; never raises."""
    config = load_config(paths, environ)
    run = load_json(paths.run, default_run())
    run_id = run_id or run.get("run_id")
    if not run_id:
        return {"status": "skipped", "reason": "no run to export"}
    if run_id != run.get("run_id"):
        run = {"run_id": run_id}
    try:
        _count, records, periods = measure.run_records(paths, run_id)
        if not periods:
            return {"status": "skipped", "run_id": run_id, "reason": "the run has no task periods"}
        payload = build_trace(run_id, run, records, periods, load_pricing(paths), config.service_name)
    except (OSError, ValueError) as exc:
        return {"status": "failed", "run_id": run_id, "error": str(exc)}
    spans = len(payload["resourceSpans"][0]["scopeSpans"][0]["spans"])
    result: JSONDict = {
        "run_id": run_id,
        "trace_id": identifier(run_id, length=32),
        "endpoint": config.endpoint,
        "spans": spans,
        "messages": len(records),
    }
    if dry_run:
        return {"status": "dry-run", **result, "payload": payload}
    try:
        result["http_status"] = send(payload, config)
    except OtelError as exc:
        return {"status": "failed", **result, "error": str(exc)}
    return {"status": "exported", **result}
