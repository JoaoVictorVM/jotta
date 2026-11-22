from __future__ import annotations

import json
from pathlib import Path

import pytest

from jotta.cli import main
from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict
from jotta.telemetry import transcripts
from jotta.telemetry.transcripts import Usage, parse_claude, parse_codex
from jotta.telemetry.usage import cost, open_period, price_for, summarize


def claude_entry(message_id: str, model: str, time: str, **usage: int) -> JSONDict:
    return {
        "type": "assistant",
        "sessionId": "c-1",
        "timestamp": time,
        "message": {"id": message_id, "model": model, "role": "assistant", "usage": usage, "content": []},
    }


CLAUDE = [
    {"type": "user", "sessionId": "c-1", "message": {"role": "user", "content": "hi"}},
    claude_entry(
        "msg_1",
        "claude-opus-5-5",
        "2026-11-20T10:00:00Z",
        input_tokens=10,
        output_tokens=200,
        cache_read_input_tokens=5000,
        cache_creation_input_tokens=1000,
    ),
    claude_entry(
        "msg_1",
        "claude-opus-5-5",
        "2026-11-20T10:00:01Z",
        input_tokens=10,
        output_tokens=200,
        cache_read_input_tokens=5000,
        cache_creation_input_tokens=1000,
    ),
    claude_entry("msg_2", "claude-haiku-5-5", "2026-11-20T11:00:00Z", input_tokens=4, output_tokens=50),
    claude_entry("msg_3", "<synthetic>", "2026-11-20T11:00:00Z", input_tokens=0, output_tokens=0),
]


def codex_usage(input_tokens: int, cached: int, output: int) -> JSONDict:
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached,
        "output_tokens": output,
        "reasoning_output_tokens": 0,
        "total_tokens": input_tokens + output,
    }


def codex_lines(with_records: bool) -> list[JSONDict]:
    meta = {"type": "session_meta", "payload": {"id": "x-1", "session_id": "x-1", "cwd": "/work/app"}}
    turn = {"type": "turn_context", "payload": {"model": "gpt-test"}}
    first, second = codex_usage(1000, 800, 20), codex_usage(1500, 1200, 30)
    counts = [
        {"timestamp": "2026-11-20T10:00:00Z", "type": "event_msg", "payload": {"type": "token_count", "info": None}},
        token_count(first, first, "2026-11-20T10:00:01Z"),
        token_count(first, first, "2026-11-20T10:00:02Z"),
        token_count(second, codex_usage(2500, 2000, 50), "2026-11-20T10:00:03Z"),
    ]
    records = [
        usage_record("r-1", first, "2026-11-20T10:00:01Z"),
        usage_record("r-1", first, "2026-11-20T10:00:01Z"),
        usage_record("r-2", second, "2026-11-20T10:00:03Z"),
    ]
    return [meta, turn, *counts, *(records if with_records else [])]


def token_count(last: JSONDict, total: JSONDict, time: str) -> JSONDict:
    info = {"last_token_usage": last, "total_token_usage": total}
    return {"timestamp": time, "type": "event_msg", "payload": {"type": "token_count", "info": info}}


def usage_record(response: str, usage: JSONDict, time: str) -> JSONDict:
    payload = {"session_id": "x-1", "turn_id": "t", "response_id": response, "usage": usage}
    return {"timestamp": time, "type": "token_usage_record", "payload": payload}


def lines(items: list[JSONDict]) -> list[str]:
    return [json.dumps(item) for item in items] + ["not json", "[]"]


def write(path: Path, items: list[JSONDict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines(items)) + "\n", encoding="utf-8")
    return path


def test_claude_counts_each_response_once() -> None:
    records = parse_claude(lines(CLAUDE))
    assert [(record.message_id, record.model) for record in records] == [
        ("msg_1", "claude-opus-5-5"),
        ("msg_2", "claude-haiku-5-5"),
    ]
    opus = records[0]
    assert (opus.input_tokens, opus.output_tokens, opus.cache_read_tokens, opus.cache_creation_tokens) == (
        10,
        200,
        5000,
        1000,
    )
    assert (opus.session_id, opus.total_tokens) == ("c-1", 6210)


@pytest.mark.parametrize("with_records", [True, False])
def test_codex_reads_each_response_without_double_counting(with_records: bool) -> None:
    records = parse_codex(lines(codex_lines(with_records)))
    assert len(records) == 2
    assert {(record.session_id, record.model, record.agent) for record in records} == {("x-1", "gpt-test", "codex")}
    assert sum(record.input_tokens for record in records) == 500
    assert sum(record.cache_read_tokens for record in records) == 2000
    assert sum(record.output_tokens for record in records) == 50


def test_the_agent_is_detected_from_the_content(tmp_path: Path) -> None:
    claude = write(tmp_path / "claude.jsonl", CLAUDE)
    codex = write(tmp_path / "codex.jsonl", codex_lines(True))
    assert {record.agent for record in transcripts.parse_file(claude)} == {"claude"}
    assert {record.agent for record in transcripts.parse_file(codex)} == {"codex"}


def test_prices_use_exact_ids_then_patterns_and_never_invent_one() -> None:
    pricing = {"claude-opus-5-5": {"input": 1.0}, "claude-*": {"input": 2.0}}
    assert price_for("claude-opus-5-5", pricing) == {"input": 1.0}
    assert price_for("claude-haiku-5-5", pricing) == {"input": 2.0}
    assert price_for("gpt-test", pricing) is None
    record = Usage("claude", "s", "m", "x", "", input_tokens=1_000_000, output_tokens=1_000_000, cache_read_tokens=2)
    assert cost(record, {"input": 3.0, "output": 15.0}) == pytest.approx(18.000006)
    assert cost(record, {"input": 3.0}) is None


def test_summary_totals_and_costs() -> None:
    records = parse_claude(lines(CLAUDE)) + parse_codex(lines(codex_lines(True)))
    pricing = {
        "claude-opus-*": {"input": 5.0, "output": 25.0, "cache_read": 0.5, "cache_write": 6.25},
        "claude-haiku-*": {"input": 1.0, "output": 5.0},
    }
    summary = summarize(records, pricing)
    assert summary["sessions"] == 2
    assert summary["totals"] == {
        "messages": 4,
        "input_tokens": 514,
        "output_tokens": 300,
        "cache_read_tokens": 7000,
        "cache_creation_tokens": 1000,
        "estimated_cost_usd": pytest.approx(0.014054),
        "unpriced_messages": 2,
    }
    assert summary["by_model"]["claude-opus-5-5"]["estimated_cost_usd"] == pytest.approx(0.0138)
    assert summary["by_agent"]["codex"]["messages"] == 2
    assert summary["unpriced_models"] == ["gpt-test"]
    assert summary["by_task"] == {"unassigned": summary["totals"]}


def test_usage_goes_to_the_task_of_its_period_or_session() -> None:
    records = parse_claude(lines(CLAUDE)) + parse_codex(lines(codex_lines(True)))
    periods: list[JSONDict] = [
        {"task": "F01", "started_at": "2026-11-20T09:00:00+00:00", "ended_at": "2026-11-20T10:30:00+00:00"},
        {"task": "F02", "started_at": "2026-11-20T10:30:00+00:00", "ended_at": None},
    ]
    by_task = summarize(records, {}, periods)["by_task"]
    assert {task: value["messages"] for task, value in by_task.items()} == {"F01": 3, "F02": 1}
    by_session = summarize(records, {}, periods, {"x-1": "F09"})["by_task"]
    assert {task: value["messages"] for task, value in by_session.items()} == {"F01": 1, "F02": 1, "F09": 2}


def test_prepare_and_checkpoint_open_and_close_periods(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--root", str(project), "sync-tasks"]) == 0
    assert main(["--root", str(project), "prepare", "F01"]) == 0
    assert main(["--root", str(project), "prepare", "F03"]) == 0
    assert main(["--root", str(project), "checkpoint", "--status", "completed"]) == 0
    capsys.readouterr()
    data = json.loads((project / ".jotta" / "runtime" / "state" / "task-periods.json").read_text(encoding="utf-8"))
    periods = data["periods"]
    assert [period["task"] for period in periods] == ["F01", "F03"]
    assert all(period["ended_at"] for period in periods)
    assert periods[0]["ended_at"] == periods[1]["started_at"]


def test_the_usage_command_reads_the_project_transcripts(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    claude_home, codex_home = tmp_path / "claude-home", tmp_path / "codex-home"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude_home))
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    folder = transcripts.claude_project_dir(project)
    write(folder / "c-1.jsonl", CLAUDE)
    write(
        folder / "c-1" / "subagents" / "agent-1.jsonl",
        [claude_entry("msg_9", "claude-haiku-5-5", "x", output_tokens=7)],
    )
    inside = codex_lines(True)
    inside[0]["payload"]["cwd"] = str(project / "src")
    write(codex_home / "sessions" / "2026" / "11" / "20" / "rollout-a.jsonl", inside)
    write(codex_home / "sessions" / "2026" / "11" / "20" / "rollout-b.jsonl", codex_lines(True))
    pricing = project / ".jotta" / "policy" / "pricing.json"
    pricing.write_text(json.dumps({"models": {"claude-*": {"input": 1.0, "output": 1.0}}}), encoding="utf-8")

    assert main(["--root", str(project), "usage"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert (result["status"], result["transcripts"], result["totals"]["messages"]) == ("measured", 3, 5)
    assert result["unpriced_models"] == ["gpt-test"]

    assert main(["--root", str(project), "usage", "--agent", "codex", "--session", "x-1=F03"]) == 0
    assert list(json.loads(capsys.readouterr().out)["by_task"]) == ["F03"]
    assert main(["--root", str(project), "usage", "--since", "2026-11-20T10:30:00Z"]) == 0
    assert json.loads(capsys.readouterr().out)["totals"]["messages"] == 1


@pytest.mark.parametrize("argument", [["--session", "nope"], ["--since", "yesterday"]])
def test_invalid_usage_arguments(project: Path, capsys: pytest.CaptureFixture[str], argument: list[str]) -> None:
    assert main(["--root", str(project), "usage", *argument]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid"


def test_periods_survive_a_missing_state_file(project: Path) -> None:
    paths = ProjectPaths(project)
    open_period(paths, "F01", None)
    assert json.loads((paths.state / "task-periods.json").read_text(encoding="utf-8"))["periods"][0]["task"] == "F01"
