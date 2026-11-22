from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from jotta.budget.guard import recorded_usage
from jotta.cli import main
from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict
from jotta.telemetry import measure, transcripts

HALF_DOLLAR_PER_OUTPUT_TOKEN = {"claude-*": {"input": 0.0, "output": 500_000.0, "cache_read": 0.0, "cache_write": 0.0}}


def moment(offset_seconds: float = 0.0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()


def message(message_id: str, time: str, output: int, model: str = "claude-opus-5-5", **usage: int) -> JSONDict:
    return {
        "type": "assistant",
        "sessionId": "s-1",
        "timestamp": time,
        "message": {"id": message_id, "model": model, "usage": {"output_tokens": output, **usage}},
    }


def transcript(project: Path, name: str, entries: list[JSONDict]) -> Path:
    path = transcripts.claude_project_dir(project) / f"{name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")
    return path


def usage(project: Path) -> JSONDict:
    data: JSONDict = json.loads((project / ".jotta" / "runtime" / "state" / "usage.json").read_text(encoding="utf-8"))
    return data


@pytest.fixture
def running(project: Path, capsys: pytest.CaptureFixture[str]) -> Path:
    """A project with priced models and a prepared task."""
    pricing = project / ".jotta" / "policy" / "pricing.json"
    pricing.write_text(json.dumps({"models": HALF_DOLLAR_PER_OUTPUT_TOKEN}), encoding="utf-8")
    assert main(["--root", str(project), "sync-tasks"]) == 0
    assert main(["--root", str(project), "prepare", "F01"]) == 0
    capsys.readouterr()
    return project


@pytest.mark.parametrize(
    ("dollars", "status", "code"),
    [(10, "continue", 0), (15, "warning", 0), (18, "human-gate", 2), (19.5, "hard-stop", 3)],
)
def test_the_guard_decides_with_measured_usage(
    running: Path, capsys: pytest.CaptureFixture[str], dollars: float, status: str, code: int
) -> None:
    half = int(dollars * 2)
    transcript(running, "s-1", [message("m1", moment(), half // 2), message("m2", moment(), half - half // 2)])
    assert main(["--root", str(running), "checkpoint", "--status", "completed"]) == code
    result = json.loads(capsys.readouterr().out)
    budget = result["budget"]
    assert (budget["status"], budget["execution"]["measurement"]) == (status, "measured")
    assert budget["execution"]["including_reservations"]["estimated_cost_usd"] == pytest.approx(half / 2)
    recorded = usage(running)
    assert recorded["measurement"] == "measured"
    assert recorded["measured"]["messages"] == 2
    assert recorded["measured"]["by_model"]["claude-opus-5-5"]["output_tokens"] == half


def test_messages_outside_the_run_periods_do_not_count(running: Path, capsys: pytest.CaptureFixture[str]) -> None:
    transcript(
        running,
        "s-1",
        [message("old", moment(-3600), 19), message("now", moment(), 3), message("bad", "not a time", 19)],
    )
    main(["--root", str(running), "checkpoint", "--status", "completed"])
    capsys.readouterr()
    assert usage(running)["measured"]["estimated_cost_usd"] == pytest.approx(1.5)


def test_without_transcripts_the_estimates_still_decide(running: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--root", str(running), "budget", "record", "--estimated-cost-usd", "18"]) == 0
    assert main(["--root", str(running), "checkpoint", "--status", "completed"]) == 2
    budget = json.loads(capsys.readouterr().out.split("\n", 1)[1])["budget"]
    assert (budget["status"], budget["execution"]["measurement"]) == ("human-gate", "estimated")
    assert usage(running)["measurement"] == "estimated"


def test_cache_reads_count_in_cost_but_not_in_the_token_limit() -> None:
    measured = {
        "messages": 3,
        "input_tokens": 100,
        "output_tokens": 50,
        "cache_read_tokens": 10_000_000,
        "cache_creation_tokens": 400,
        "estimated_cost_usd": 2.5,
        "unpriced_messages": 0,
    }
    values, source = recorded_usage({"measurement": "measured", "measured": measured, "estimated_cost_usd": 9.0})
    assert (values, source) == ({"input_tokens": 500, "output_tokens": 50, "estimated_cost_usd": 2.5}, "measured")
    partial = {**measured, "unpriced_messages": 1}
    values, _ = recorded_usage({"measurement": "measured", "measured": partial, "estimated_cost_usd": 9.0})
    assert values["estimated_cost_usd"] == 9.0
    assert recorded_usage({"measurement": "estimated", "measured": measured, "input_tokens": 7})[1] == "estimated"


def test_a_measurement_of_another_run_is_discarded(project: Path) -> None:
    paths = ProjectPaths(project)
    state = paths.usage
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({"measurement": "measured", "measured": {"run_id": "old", "messages": 1}}), "utf-8")
    assert measure.refresh(paths, "new") is None
    assert "measured" not in usage(project)
    assert usage(project)["measurement"] == "estimated"


def test_old_transcripts_are_not_read(running: Path) -> None:
    path = transcript(running, "old", [message("m1", moment(), 5)])
    old = datetime.now(timezone.utc).timestamp() - 86_400
    os.utime(path, (old, old))
    assert (
        measure.measure_run(
            ProjectPaths(running),
            json.loads((running / ".jotta" / "runtime" / "state" / "current-run.json").read_text(encoding="utf-8"))[
                "run_id"
            ],
        )
        is None
    )


def test_a_failing_measurement_falls_back_to_the_estimates(
    running: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def broken(_paths: ProjectPaths, _run_id: str | None) -> JSONDict:
        raise OSError("unreadable transcript")

    monkeypatch.setattr(measure, "measure_run", broken)
    assert main(["--root", str(running), "checkpoint", "--status", "completed"]) == 0
    capsys.readouterr()
    assert usage(running)["measurement"] == "estimated"
