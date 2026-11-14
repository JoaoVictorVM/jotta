from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pytest

from jotta.budget import guard
from jotta.core.paths import ProjectPaths, templates_root
from jotta.core.state import JSONDict, default_usage, load_json


@pytest.fixture
def policy() -> JSONDict:
    data: JSONDict = json.loads((templates_root() / ".jotta" / "policy" / "budget.json").read_text(encoding="utf-8"))
    return data


def usage_at(percent: float | None, **extra: Any) -> JSONDict:
    usage = default_usage()
    usage["provider_usage_percent"] = percent
    usage.update(extra)
    return usage


@pytest.mark.parametrize(
    ("percent", "status", "code"),
    [
        (10, "continue", guard.EXIT_CONTINUE),
        (69.9, "continue", guard.EXIT_CONTINUE),
        (70, "warning", guard.EXIT_CONTINUE),
        (84.9, "warning", guard.EXIT_CONTINUE),
        (85, "human-gate", guard.EXIT_HUMAN_GATE),
        (94.9, "human-gate", guard.EXIT_HUMAN_GATE),
        (95, "hard-stop", guard.EXIT_HARD_STOP),
        (100, "hard-stop", guard.EXIT_HARD_STOP),
    ],
)
def test_provider_percent_maps_to_each_threshold(policy: JSONDict, percent: float, status: str, code: int) -> None:
    result, exit_code = guard.evaluate(policy, usage_at(percent), "feature", None)
    assert (result["status"], exit_code) == (status, code)
    assert result["effective_source"] == "provider"


def test_authorization_applies_only_to_its_scope(policy: JSONDict) -> None:
    usage = usage_at(88, authorization={"scope": "feature", "until_percent": 90})
    feature, feature_code = guard.evaluate(policy, usage, "feature", None)
    wave, wave_code = guard.evaluate(policy, usage, "wave", None)
    assert (feature["status"], feature_code) == ("authorized", guard.EXIT_CONTINUE)
    assert (wave["status"], wave_code) == ("human-gate", guard.EXIT_HUMAN_GATE)


def test_run_authorization_covers_every_scope(policy: JSONDict) -> None:
    usage = usage_at(88, authorization={"scope": "run", "until_percent": 90})
    result, code = guard.evaluate(policy, usage, "wave", None)
    assert (result["status"], code) == ("authorized", guard.EXIT_CONTINUE)


def test_authorization_expires_above_its_limit(policy: JSONDict) -> None:
    usage = usage_at(91, authorization={"scope": "feature", "until_percent": 90})
    result, code = guard.evaluate(policy, usage, "feature", None)
    assert (result["status"], code) == ("human-gate", guard.EXIT_HUMAN_GATE)


def test_hard_stop_ignores_authorization(policy: JSONDict) -> None:
    usage = usage_at(95, authorization={"scope": "run", "until_percent": 99})
    result, code = guard.evaluate(policy, usage, "feature", None)
    assert (result["status"], code) == ("hard-stop", guard.EXIT_HARD_STOP)


def test_reservations_count_before_dispatch(policy: JSONDict) -> None:
    usage = usage_at(None, input_tokens=300_000)
    before, _ = guard.evaluate(policy, usage, "feature", None)
    usage["reservations"] = [{"id": "agents", "input_tokens": 125_000}]
    after, code = guard.evaluate(policy, usage, "feature", None)
    assert before["status"] == "continue"
    assert after["execution_percent"] == pytest.approx(85.0)
    assert (after["status"], code) == ("human-gate", guard.EXIT_HUMAN_GATE)


def test_execution_percent_uses_the_highest_dimension(policy: JSONDict) -> None:
    usage = usage_at(None, input_tokens=50_000, estimated_cost_usd=15.0)
    result, _ = guard.evaluate(policy, usage, "feature", None)
    assert result["execution_percent"] == pytest.approx(75.0)
    assert result["status"] == "warning"


def test_unavailable_provider_falls_back_to_the_execution_budget(policy: JSONDict) -> None:
    result, code = guard.evaluate(policy, usage_at(None), "feature", None)
    assert (result["status"], code) == ("continue", guard.EXIT_CONTINUE)
    assert result["effective_source"] == "execution"
    assert result["provider_usage_percent"] is None


def test_unavailable_provider_can_gate(policy: JSONDict) -> None:
    policy["provider_usage_unavailable"] = "gate"
    result, code = guard.evaluate(policy, usage_at(None), "feature", None)
    assert (result["status"], code) == ("measurement-unavailable", guard.EXIT_MEASUREMENT_UNAVAILABLE)


def test_disabled_policy_never_blocks(policy: JSONDict) -> None:
    policy["enabled"] = False
    result, code = guard.evaluate(policy, usage_at(99), "feature", None)
    assert (result["status"], code) == ("disabled", guard.EXIT_CONTINUE)


def namespace(**values: Any) -> argparse.Namespace:
    defaults: dict[str, Any] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "estimated_cost_usd": 0.0,
        "provider_usage_unavailable": False,
        "provider_usage_percent": None,
        "source": "manual",
    }
    return argparse.Namespace(**{**defaults, **values})


def stored_usage(paths: ProjectPaths) -> JSONDict:
    return load_json(paths.usage)


def test_record_accumulates_and_persists(project: Path) -> None:
    paths = ProjectPaths(project)
    assert guard.command_record(paths, namespace(input_tokens=10, provider_usage_percent=40), default_usage()) == 0
    assert guard.command_record(paths, namespace(input_tokens=5), stored_usage(paths)) == 0
    saved = stored_usage(paths)
    assert saved["input_tokens"] == 15
    assert saved["provider_usage_percent"] == 40


def test_record_marks_the_provider_unavailable(project: Path) -> None:
    paths = ProjectPaths(project)
    guard.command_record(paths, namespace(provider_usage_unavailable=True), usage_at(40))
    saved = stored_usage(paths)
    assert saved["provider_usage_percent"] is None
    assert saved["provider_usage_source"] == "unavailable"


@pytest.mark.parametrize(
    "values",
    [{"input_tokens": -1}, {"estimated_cost_usd": -0.1}, {"provider_usage_percent": 101}],
)
def test_record_rejects_invalid_values(project: Path, values: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        guard.command_record(ProjectPaths(project), namespace(**values), default_usage())


def test_reserve_and_release(project: Path) -> None:
    paths = ProjectPaths(project)
    args = namespace(id="agents", scope="wave", input_tokens=1000)
    assert guard.command_reserve(paths, args, default_usage()) == 0
    assert guard.command_reserve(paths, args, stored_usage(paths)) == 1
    assert [item["id"] for item in stored_usage(paths)["reservations"]] == ["agents"]
    assert guard.command_release(paths, namespace(id="agents"), stored_usage(paths)) == 0
    assert stored_usage(paths)["reservations"] == []
    assert guard.command_release(paths, namespace(id="agents"), stored_usage(paths)) == 1


def test_reserve_rejects_negative_values(project: Path) -> None:
    args = namespace(id="agents", scope="wave", output_tokens=-1)
    with pytest.raises(ValueError):
        guard.command_reserve(ProjectPaths(project), args, default_usage())


@pytest.mark.parametrize(("until", "code"), [(84, 1), (85, 0), (94.9, 0), (95, 1)])
def test_authorize_stays_between_gate_and_hard_stop(project: Path, policy: JSONDict, until: float, code: int) -> None:
    args = namespace(scope="feature", until_percent=until, reason="test")
    assert guard.command_authorize(ProjectPaths(project), args, policy, default_usage()) == code


def test_clear_authorization(project: Path, policy: JSONDict) -> None:
    paths = ProjectPaths(project)
    guard.command_authorize(paths, namespace(scope="run", until_percent=90, reason="test"), policy, default_usage())
    assert stored_usage(paths)["authorization"]["scope"] == "run"
    guard.command_clear_authorization(paths, stored_usage(paths))
    assert stored_usage(paths)["authorization"] is None
