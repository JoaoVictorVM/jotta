"""Resolve model preferences without assuming a provider supports per-agent routing."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict, load_json, print_json

EXIT_RESOLVED = 0
EXIT_INVALID = 2
EXIT_UNAVAILABLE = 3


def load(path: Path) -> JSONDict:
    return load_json(path)


def validate(data: JSONDict) -> list[str]:
    errors: list[str] = []
    tiers = data.get("tiers", {})
    routes = data.get("task_routes", {})
    providers = data.get("providers", {})
    if data.get("unavailable_behavior") not in {"inherit", "gate", "fail"}:
        errors.append("unavailable_behavior must be inherit, gate or fail")
    for task, route in routes.items():
        tier = route.get("tier")
        if tier not in tiers:
            errors.append(f"{task}: unknown tier {tier}")
    for tier, settings in tiers.items():
        fallback = settings.get("fallback_tier")
        if fallback is not None and fallback not in tiers:
            errors.append(f"{tier}: unknown fallback {fallback}")
        visited = {tier}
        while fallback is not None and fallback in tiers:
            if fallback in visited:
                errors.append(f"{tier}: fallback cycle detected")
                break
            visited.add(fallback)
            fallback = tiers[fallback].get("fallback_tier")
    for provider, mapping in providers.items():
        unknown = set(mapping) - set(tiers)
        if unknown:
            errors.append(f"{provider}: unknown tiers {sorted(unknown)}")
    if data.get("default_provider") not in providers:
        errors.append("default_provider is not listed in providers")
    return errors


def resolve(data: JSONDict, task: str, provider: str | None) -> tuple[JSONDict, int]:
    routes = data["task_routes"]
    if task not in routes:
        return {"status": "error", "message": f"unknown task: {task}"}, EXIT_INVALID
    provider = provider or data["default_provider"]
    if provider not in data["providers"]:
        return {"status": "error", "message": f"unknown provider: {provider}"}, EXIT_INVALID
    route = routes[task]
    requested_tier = route["tier"]
    preferred = route.get("preferred_model")
    resolved_tier = requested_tier
    configured = data["providers"][provider].get(resolved_tier)
    while not configured:
        fallback = data["tiers"][resolved_tier].get("fallback_tier")
        if fallback is None:
            break
        resolved_tier = fallback
        configured = data["providers"][provider].get(resolved_tier)
    model = preferred or configured
    if model:
        return {
            "status": "resolved",
            "task": task,
            "provider": provider,
            "requested_tier": requested_tier,
            "resolved_tier": requested_tier if preferred else resolved_tier,
            "model": model,
            "source": "task" if preferred else "provider-tier",
        }, EXIT_RESOLVED
    behavior = data.get("unavailable_behavior", "inherit")
    payload = {
        "status": "inherit" if behavior == "inherit" else "unavailable",
        "task": task,
        "provider": provider,
        "requested_tier": requested_tier,
        "resolved_tier": None,
        "model": None,
        "source": "platform-default",
        "message": "no exact model configured for the route",
    }
    return payload, EXIT_RESOLVED if behavior == "inherit" else EXIT_UNAVAILABLE


def run(paths: ProjectPaths, args: argparse.Namespace) -> int:
    """Dispatch a ``jotta models`` subcommand."""
    data = load(paths.routing)
    errors = validate(data)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    if args.models_command == "validate":
        print("MODEL ROUTING OK")
        return 0
    if args.models_command == "list":
        print(json.dumps(data["task_routes"], ensure_ascii=False, indent=2))
        return 0
    payload, code = resolve(data, args.task, args.provider)
    print_json(payload)
    return code
