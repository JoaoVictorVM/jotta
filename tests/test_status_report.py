from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from jotta.cli import main
from jotta.core.state import JSONDict
from jotta.telemetry import transcripts

PRICING = {"claude-opus-*": {"input": 0.0, "output": 1000.0, "cache_read": 0.0, "cache_write": 0.0}}


class Session:
    """A Claude Code transcript that grows as the test adds messages."""

    def __init__(self, project: Path) -> None:
        self.path = transcripts.claude_project_dir(project) / "s-1.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.count = 0

    def say(self, output_tokens: int, model: str = "claude-opus-5-5", cache_read: int = 0) -> None:
        self.count += 1
        entry = {
            "type": "assistant",
            "sessionId": "s-1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": {
                "id": f"m{self.count}",
                "model": model,
                "usage": {"output_tokens": output_tokens, "cache_read_input_tokens": cache_read},
            },
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")


def jotta(project: Path, *args: str) -> int:
    return main(["--root", str(project), *args])


@pytest.fixture
def worked(project: Path, capsys: pytest.CaptureFixture[str]) -> Path:
    """A run where F01 was implemented and reviewed, and F03 is being implemented."""
    (project / ".jotta" / "policy" / "pricing.json").write_text(json.dumps({"models": PRICING}), encoding="utf-8")
    session = Session(project)
    assert jotta(project, "sync-tasks") == 0
    assert jotta(project, "prepare", "F01") == 0
    session.say(1000, cache_read=50_000)
    session.say(500)
    assert jotta(project, "checkpoint", "--status", "completed") == 0
    assert jotta(project, "prepare", "F01", "--role", "reviewer") == 0
    session.say(200)
    assert jotta(project, "checkpoint", "--status", "completed") == 0
    assert jotta(project, "prepare", "F03") == 0
    session.say(300, model="gpt-unpriced")
    capsys.readouterr()
    return project


def status_json(project: Path, capsys: pytest.CaptureFixture[str]) -> JSONDict:
    assert jotta(project, "status", "--json") == 0
    data: JSONDict = json.loads(capsys.readouterr().out)
    return data


def test_the_json_status_splits_usage_by_feature_and_stage(worked: Path, capsys: pytest.CaptureFixture[str]) -> None:
    data = status_json(worked, capsys)
    assert data["measurement"] == "measured"
    by_stage = data["measured"]["by_task_stage"]
    assert {task: sorted(stages) for task, stages in by_stage.items()} == {
        "F01": ["implementation", "review"],
        "F03": ["implementation"],
    }
    assert by_stage["F01"]["implementation"]["output_tokens"] == 1500
    assert by_stage["F01"]["implementation"]["cache_read_tokens"] == 50_000
    assert by_stage["F01"]["implementation"]["estimated_cost_usd"] == pytest.approx(1.5)
    assert by_stage["F01"]["review"]["estimated_cost_usd"] == pytest.approx(0.2)
    assert data["measured"]["by_task"]["F01"]["messages"] == 3
    assert data["measured"]["totals"]["estimated_cost_usd"] == pytest.approx(1.7)
    assert data["measured"]["unpriced_models"] == ["gpt-unpriced"]
    assert data["budget"]["measurement"] == "measured"
    assert data["run"]["current_task"] == "F03"


def test_the_text_status_shows_where_the_cost_went(worked: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert jotta(worked, "status") == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("Run: run-")
    assert "Usage measured from 1 transcript(s), 1 session(s):" in lines
    header = next(line for line in lines if line.startswith("Feature"))
    assert header.split() == ["Feature", "Stage", "Messages", "Input", "Output", "Cache", "read", "Cache", "write"] + [
        "Cost",
        "USD",
    ]
    rows = {tuple(line.split()[:2]): line.split() for line in lines if line.startswith(("F0", "Total"))}
    assert rows[("F01", "implementation")][2:] == ["2", "0", "1,500", "50,000", "0", "1.5000"]
    assert rows[("F01", "review")][-1] == "0.2000"
    assert rows[("F03", "implementation")][-1] == "-"
    assert next(line for line in lines if line.startswith("Total")).split()[-1] == "1.7000*"
    assert "No price in pricing.json for gpt-unpriced: cost shown as - when unknown, * when partial." in lines
    assert lines[-1].startswith("Budget: continue at ")
    assert lines[-1].endswith("measured)")


def test_without_transcripts_the_estimates_are_shown(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert jotta(project, "sync-tasks") == 0
    assert jotta(project, "prepare", "F01") == 0
    args = ["checkpoint", "--status", "completed", "--stage", "implementation", "--input-tokens", "1200"]
    assert jotta(project, *args, "--output-tokens", "300") == 0
    capsys.readouterr()
    assert jotta(project, "status") == 0
    lines = capsys.readouterr().out.splitlines()
    assert "Usage estimated: no transcript of this run could be measured." in lines
    row = next(line for line in lines if line.startswith("run "))
    assert row.split() == ["run", "implementation", "-", "1,200", "300", "-", "-", "-"]
    assert status_json(project, capsys)["measured"] is None


def test_a_fresh_project_has_nothing_to_show(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert jotta(project, "status") == 0
    out = capsys.readouterr().out
    assert "Run: none (idle)" in out
    assert "No usage recorded yet." in out


def test_a_broken_budget_policy_does_not_hide_the_status(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (project / ".jotta" / "policy" / "budget.json").write_text("{}", encoding="utf-8")
    assert jotta(project, "status") == 0
    assert "Budget: unavailable; check .jotta/policy/budget.json" in capsys.readouterr().out
    assert status_json(project, capsys)["budget"] is None
