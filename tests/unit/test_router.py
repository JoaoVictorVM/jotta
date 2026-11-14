from __future__ import annotations

import copy
import json
from typing import Any

import pytest

from jotta.core.paths import templates_root
from jotta.core.state import JSONDict
from jotta.routing import router


@pytest.fixture
def routing() -> JSONDict:
    data: JSONDict = json.loads((templates_root() / ".jotta" / "policy" / "routing.json").read_text(encoding="utf-8"))
    return data


def test_template_routing_is_valid(routing: JSONDict) -> None:
    assert router.validate(routing) == []


@pytest.mark.parametrize(
    ("task", "tier"),
    [
        ("spec-writer", "efficient"),
        ("implement-feature", "balanced"),
        ("implement-feature-high-risk", "strong"),
        ("final-qa", "review"),
    ],
)
def test_tasks_request_their_tier(routing: JSONDict, task: str, tier: str) -> None:
    result, code = router.resolve(routing, task, None)
    assert code == router.EXIT_RESOLVED
    assert result["requested_tier"] == tier


def test_null_model_inherits_the_platform_model(routing: JSONDict) -> None:
    result, code = router.resolve(routing, "spec-writer", None)
    assert code == router.EXIT_RESOLVED
    assert (result["status"], result["model"], result["source"]) == ("inherit", None, "platform-default")


@pytest.mark.parametrize("behavior", ["gate", "fail"])
def test_null_model_without_inherit_is_unavailable(routing: JSONDict, behavior: str) -> None:
    routing["unavailable_behavior"] = behavior
    result, code = router.resolve(routing, "spec-writer", None)
    assert (result["status"], code) == ("unavailable", router.EXIT_UNAVAILABLE)


def test_configured_provider_model_resolves(routing: JSONDict) -> None:
    routing["providers"]["anthropic"]["efficient"] = "model-small"
    result, code = router.resolve(routing, "spec-writer", "anthropic")
    assert code == router.EXIT_RESOLVED
    assert (result["status"], result["model"], result["source"]) == ("resolved", "model-small", "provider-tier")


def test_missing_tier_follows_the_fallback_chain(routing: JSONDict) -> None:
    routing["providers"]["anthropic"]["strong"] = "model-large"
    result, _ = router.resolve(routing, "spec-writer", "anthropic")
    assert result["requested_tier"] == "efficient"
    assert (result["resolved_tier"], result["model"]) == ("strong", "model-large")


def test_preferred_model_wins_over_the_provider(routing: JSONDict) -> None:
    routing["providers"]["anthropic"]["efficient"] = "model-small"
    routing["task_routes"]["spec-writer"]["preferred_model"] = "model-pinned"
    result, _ = router.resolve(routing, "spec-writer", "anthropic")
    assert (result["model"], result["source"]) == ("model-pinned", "task")


@pytest.mark.parametrize(("task", "provider"), [("missing", None), ("spec-writer", "missing")])
def test_unknown_task_or_provider_is_invalid(routing: JSONDict, task: str, provider: str | None) -> None:
    result, code = router.resolve(routing, task, provider)
    assert (result["status"], code) == ("error", router.EXIT_INVALID)


def changed(routing: JSONDict, path: list[str], value: Any) -> JSONDict:
    data = copy.deepcopy(routing)
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return data


@pytest.mark.parametrize(
    ("path", "value", "expected"),
    [
        (["unavailable_behavior"], "guess", "unavailable_behavior must be"),
        (["task_routes", "final-qa", "tier"], "huge", "final-qa: unknown tier huge"),
        (["tiers", "strong", "fallback_tier"], "missing", "strong: unknown fallback missing"),
        (["tiers", "strong", "fallback_tier"], "efficient", "fallback cycle detected"),
        (["providers", "openai", "giant"], None, "openai: unknown tiers"),
        (["default_provider"], "missing", "default_provider is not listed"),
    ],
)
def test_validate_reports_each_problem(routing: JSONDict, path: list[str], value: Any, expected: str) -> None:
    errors = router.validate(changed(routing, path, value))
    assert any(expected in error for error in errors), errors
