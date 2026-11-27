from __future__ import annotations

import json
import socket
import threading
from collections.abc import Iterator
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from jotta.cli import main
from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict
from jotta.telemetry import otel, transcripts

PRICING = {"claude-opus-*": {"input": 0.0, "output": 1000.0, "cache_read": 0.0, "cache_write": 0.0}}


def jotta(project: Path, *args: str) -> int:
    return main(["--root", str(project), *args])


def say(project: Path, number: int, output_tokens: int, model: str = "claude-opus-5-5") -> None:
    path = transcripts.claude_project_dir(project) / "s-1.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "type": "assistant",
        "sessionId": "s-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": {"id": f"m{number}", "model": model, "usage": {"output_tokens": output_tokens}},
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def enable(project: Path, endpoint: str) -> None:
    config = project / ".jotta" / "config.yaml"
    text = config.read_text(encoding="utf-8")
    default = "    enabled: false\n    endpoint: http://localhost:4318/v1/traces\n    service_name: jotta\n"
    assert default in text
    chosen = f'    enabled: true  # on\n    endpoint: "{endpoint}"\n    service_name: demo\n'
    config.write_text(text.replace(default, chosen), encoding="utf-8")


@pytest.fixture(autouse=True)
def no_otel_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "OTEL_EXPORTER_OTLP_HEADERS",
        "OTEL_EXPORTER_OTLP_TRACES_HEADERS",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def worked(project: Path, capsys: pytest.CaptureFixture[str]) -> Path:
    """A run where F01 was implemented and reviewed, and F03 is being implemented with an unpriced model."""
    (project / ".jotta" / "policy" / "pricing.json").write_text(json.dumps({"models": PRICING}), encoding="utf-8")
    assert jotta(project, "sync-tasks") == 0
    assert jotta(project, "prepare", "F01") == 0
    say(project, 1, 1000)
    say(project, 2, 500)
    assert jotta(project, "checkpoint", "--status", "completed") == 0
    assert jotta(project, "prepare", "F01", "--role", "reviewer") == 0
    say(project, 3, 200)
    assert jotta(project, "checkpoint", "--status", "completed") == 0
    assert jotta(project, "prepare", "F03") == 0
    say(project, 4, 300, model="gpt-unpriced")
    capsys.readouterr()
    return project


class Collector:
    """A local OTLP/HTTP endpoint that keeps what it receives."""

    def __init__(self) -> None:
        self.requests: list[tuple[dict[str, str], JSONDict]] = []
        collector = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                body = self.rfile.read(int(self.headers["Content-Length"]))
                collector.requests.append((dict(self.headers), json.loads(body)))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *_args: object) -> None:
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}/v1/traces"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)


@pytest.fixture
def collector() -> Iterator[Collector]:
    receiver = Collector()
    receiver.thread.start()
    yield receiver
    receiver.server.shutdown()
    receiver.server.server_close()


def closed_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
    return port


def spans_of(payload: JSONDict) -> list[JSONDict]:
    spans: list[JSONDict] = payload["resourceSpans"][0]["scopeSpans"][0]["spans"]
    return spans


def attributes(span: JSONDict) -> dict[str, object]:
    return {item["key"]: next(iter(item["value"].values())) for item in span["attributes"]}


def test_the_config_is_off_by_default_and_the_environment_wins(project: Path) -> None:
    paths = ProjectPaths(project)
    config = otel.load_config(paths, {})
    assert config.enabled is False
    assert config.endpoint == otel.DEFAULT_ENDPOINT
    environ = {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "https://cloud.langfuse.com/api/public/otel/",
        "OTEL_EXPORTER_OTLP_HEADERS": "Authorization=Basic%20abc,x-langfuse-ingestion-version=4",
    }
    config = otel.load_config(paths, environ)
    assert config.endpoint == "https://cloud.langfuse.com/api/public/otel/v1/traces"
    assert config.headers == {"Authorization": "Basic abc", "x-langfuse-ingestion-version": "4"}
    environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = "http://collector:4318/v1/traces"
    assert otel.load_config(paths, environ).endpoint == "http://collector:4318/v1/traces"


def test_yaml_section_reads_only_the_nested_mapping() -> None:
    text = (
        "otel:\n  enabled: true\ntelemetry:\n  enabled: true\n  otel:\n    enabled: 'true'\n    x: 1 # note\nnext: 2\n"
    )
    assert otel.yaml_section(text, "telemetry", "otel") == {"enabled": "true", "x": "1"}


def test_a_run_becomes_one_trace_of_features_stages_and_models(
    worked: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert jotta(worked, "export-trace", "--dry-run") == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "dry-run"
    assert result["messages"] == 4
    spans = spans_of(result["payload"])
    by_id = {span["spanId"]: span for span in spans}
    assert {span["traceId"] for span in spans} == {result["trace_id"]}

    def path(span: JSONDict) -> list[str]:
        names = [span["name"]]
        while "parentSpanId" in span:
            span = by_id[span["parentSpanId"]]
            names.append(span["name"])
        return names[::-1]

    leaves = {
        (attributes(span)["jotta.task.id"], attributes(span)["jotta.stage"], span["name"]): span
        for span in spans
        if span["name"].startswith("chat ")
    }
    assert sorted(leaves) == [
        ("F01", "implementation", "chat claude-opus-5-5"),
        ("F01", "review", "chat claude-opus-5-5"),
        ("F03", "implementation", "chat gpt-unpriced"),
    ]
    implementation = leaves[("F01", "implementation", "chat claude-opus-5-5")]
    assert path(implementation) == ["jotta.run", "jotta.feature", "jotta.stage", "chat claude-opus-5-5"]
    values = attributes(implementation)
    assert values["langfuse.observation.type"] == "generation"
    assert values["gen_ai.provider.name"] == "anthropic"
    assert values["gen_ai.usage.output_tokens"] == "1500"
    assert values["gen_ai.usage.cost"] == pytest.approx(1.5)
    assert json.loads(str(values["langfuse.observation.usage_details"]))["output"] == 1500
    unpriced = attributes(leaves[("F03", "implementation", "chat gpt-unpriced")])
    assert "gen_ai.usage.cost" not in unpriced
    assert unpriced["jotta.unpriced_messages"] == "1"
    root = next(span for span in spans if span["name"] == "jotta.run")
    assert attributes(root)["jotta.cost_usd"] == pytest.approx(1.7)
    parents = [span for span in spans if not span["name"].startswith("chat ")]
    assert not any(key.startswith("gen_ai.usage") for span in parents for key in attributes(span))
    assert int(root["startTimeUnixNano"]) <= int(implementation["startTimeUnixNano"])


def test_exporting_again_keeps_the_same_ids(worked: Path) -> None:
    first = otel.export_run(ProjectPaths(worked), dry_run=True)
    second = otel.export_run(ProjectPaths(worked), dry_run=True)
    assert [span["spanId"] for span in spans_of(first["payload"])] == [
        span["spanId"] for span in spans_of(second["payload"])
    ]


def test_the_trace_is_posted_as_otlp_json(
    worked: Path, collector: Collector, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", collector.endpoint)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_HEADERS", "Authorization=Basic%20secret")
    assert jotta(worked, "export-trace") == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "exported"
    assert result["http_status"] == 200
    assert "secret" not in json.dumps(result)
    [(headers, body)] = collector.requests
    assert headers["Content-Type"] == "application/json"
    assert headers["Authorization"] == "Basic secret"
    assert len(spans_of(body)) == result["spans"]
    resource = body["resourceSpans"][0]["resource"]["attributes"]
    assert resource == [{"key": "service.name", "value": {"stringValue": "jotta"}}]


def test_finish_exports_the_run_when_the_export_is_on(
    worked: Path, collector: Collector, capsys: pytest.CaptureFixture[str]
) -> None:
    enable(worked, collector.endpoint)
    assert jotta(worked, "finish", "--status", "completed-local") == 0
    trace = json.loads(capsys.readouterr().out)["trace"]
    assert trace["status"] == "exported"
    [(_headers, body)] = collector.requests
    root = next(span for span in spans_of(body) if span["name"] == "jotta.run")
    assert attributes(root)["jotta.run.status"] == "completed-local"
    assert body["resourceSpans"][0]["resource"]["attributes"][0]["value"]["stringValue"] == "demo"


def test_an_unreachable_endpoint_does_not_block_finish(worked: Path, capsys: pytest.CaptureFixture[str]) -> None:
    enable(worked, f"http://127.0.0.1:{closed_port()}/v1/traces")
    assert jotta(worked, "finish", "--status", "completed-local") == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "completed-local"
    assert out["trace"]["status"] == "failed"
    assert "unreachable" in out["trace"]["error"]
    assert jotta(worked, "export-trace") == 1


def test_finish_does_not_export_by_default(worked: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert jotta(worked, "finish", "--status", "completed-local") == 0
    assert "trace" not in json.loads(capsys.readouterr().out)


def test_only_http_endpoints_are_used(worked: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "ftp://collector/v1/traces")
    result = otel.export_run(ProjectPaths(worked))
    assert result["status"] == "failed"
    assert "http or https" in result["error"]


def test_nothing_to_export_without_a_run(project: Path) -> None:
    assert otel.export_run(ProjectPaths(project))["status"] == "skipped"
    assert otel.export_run(ProjectPaths(project), "run-missing")["status"] == "skipped"
