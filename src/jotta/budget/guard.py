"""Track execution usage and enforce provider or local budget thresholds."""

from __future__ import annotations

import argparse

from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict, default_usage, load_json, now, print_json, write_json_atomic

EXIT_CONTINUE = 0
EXIT_HUMAN_GATE = 2
EXIT_HARD_STOP = 3
EXIT_MEASUREMENT_UNAVAILABLE = 4


def reservation_totals(usage: JSONDict) -> JSONDict:
    totals: JSONDict = {"input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0}
    for item in usage.get("reservations", []):
        totals["input_tokens"] += int(item.get("input_tokens", 0))
        totals["output_tokens"] += int(item.get("output_tokens", 0))
        totals["estimated_cost_usd"] += float(item.get("estimated_cost_usd", 0.0))
    return totals


def execution_percent(policy: JSONDict, usage: JSONDict) -> tuple[float, JSONDict]:
    limits = policy.get("execution_limits", {})
    reserved = reservation_totals(usage)
    values = {
        "input_tokens": int(usage.get("input_tokens", 0)) + reserved["input_tokens"],
        "output_tokens": int(usage.get("output_tokens", 0)) + reserved["output_tokens"],
        "estimated_cost_usd": float(usage.get("estimated_cost_usd", 0.0)) + reserved["estimated_cost_usd"],
    }
    ratios: dict[str, float] = {}
    for key, value in values.items():
        limit = limits.get(key)
        if limit is not None and float(limit) > 0:
            ratios[key] = 100.0 * float(value) / float(limit)
    return max(ratios.values(), default=0.0), {
        "including_reservations": values,
        "limits": limits,
        "percent_by_dimension": ratios,
    }


def authorization_applies(usage: JSONDict, scope: str, percent: float) -> bool:
    authorization = usage.get("authorization")
    if not authorization:
        return False
    allowed_scope = authorization.get("scope")
    if allowed_scope not in {"run", scope}:
        return False
    return percent <= float(authorization.get("until_percent", 0.0))


def evaluate(policy: JSONDict, usage: JSONDict, scope: str, checkpoint: str | None) -> tuple[JSONDict, int]:
    execution, details = execution_percent(policy, usage)
    provider = usage.get("provider_usage_percent")
    known = {"execution": execution}
    if provider is not None:
        known["provider"] = float(provider)
    effective = max(known.values(), default=0.0)
    source = max(known, key=lambda name: known[name]) if known else "unavailable"
    thresholds = policy["provider_thresholds"]
    warning = float(thresholds["warning_percent"])
    gate = float(thresholds["human_gate_percent"])
    hard_stop = float(thresholds["hard_stop_percent"])
    provider_unavailable = provider is None
    unavailable_behavior = policy.get("provider_usage_unavailable", "use-execution-budget")

    status = "continue"
    code = EXIT_CONTINUE
    message = "budget within limits"
    if not policy.get("enabled", True):
        status = "disabled"
        message = "budget guard disabled"
    elif provider_unavailable and unavailable_behavior == "gate":
        status = "measurement-unavailable"
        message = "provider usage percent unavailable"
        code = EXIT_MEASUREMENT_UNAVAILABLE
    elif effective >= hard_stop:
        status = "hard-stop"
        message = "budget hard stop reached"
        code = EXIT_HARD_STOP
    elif effective >= gate and not authorization_applies(usage, scope, effective):
        status = "human-gate"
        message = "human decision required to continue"
        code = EXIT_HUMAN_GATE
    elif effective >= gate:
        status = "authorized"
        message = "continuation authorized for this scope"
    elif effective >= warning:
        status = "warning"
        message = "warning threshold reached; reduce parallelism and reassess at the next checkpoint"

    payload = {
        "status": status,
        "message": message,
        "scope": scope,
        "checkpoint": checkpoint,
        "effective_percent": round(effective, 4),
        "effective_source": source,
        "provider_usage_percent": provider,
        "provider_usage_source": usage.get("provider_usage_source", "unavailable"),
        "execution_percent": round(execution, 4),
        "execution": details,
        "thresholds": thresholds,
        "authorization": usage.get("authorization"),
    }
    return payload, code


def check(paths: ProjectPaths, scope: str, checkpoint: str | None) -> tuple[JSONDict, int]:
    """Evaluate the project's policy against its recorded usage."""
    return evaluate(load_json(paths.budget_policy), load_json(paths.usage, default_usage()), scope, checkpoint)


def command_record(paths: ProjectPaths, args: argparse.Namespace, usage: JSONDict) -> int:
    if args.input_tokens < 0 or args.output_tokens < 0 or args.estimated_cost_usd < 0:
        raise ValueError("usage deltas cannot be negative")
    usage["input_tokens"] = int(usage.get("input_tokens", 0)) + args.input_tokens
    usage["output_tokens"] = int(usage.get("output_tokens", 0)) + args.output_tokens
    usage["estimated_cost_usd"] = round(float(usage.get("estimated_cost_usd", 0.0)) + args.estimated_cost_usd, 8)
    if args.provider_usage_unavailable:
        usage["provider_usage_percent"] = None
        usage["provider_usage_source"] = "unavailable"
        usage["provider_usage_checked_at"] = now()
    elif args.provider_usage_percent is not None:
        if not 0 <= args.provider_usage_percent <= 100:
            raise ValueError("provider usage percent must be between 0 and 100")
        usage["provider_usage_percent"] = args.provider_usage_percent
        usage["provider_usage_source"] = args.source
        usage["provider_usage_checked_at"] = now()
    usage["updated_at"] = now()
    write_json_atomic(paths.usage, usage)
    print("USAGE RECORDED")
    return 0


def command_reserve(paths: ProjectPaths, args: argparse.Namespace, usage: JSONDict) -> int:
    if args.input_tokens < 0 or args.output_tokens < 0 or args.estimated_cost_usd < 0:
        raise ValueError("reservations cannot be negative")
    reservations = usage.setdefault("reservations", [])
    if any(item.get("id") == args.id for item in reservations):
        print(f"RESERVATION EXISTS: {args.id}")
        return 1
    reservations.append(
        {
            "id": args.id,
            "scope": args.scope,
            "input_tokens": args.input_tokens,
            "output_tokens": args.output_tokens,
            "estimated_cost_usd": args.estimated_cost_usd,
            "created_at": now(),
        }
    )
    usage["updated_at"] = now()
    write_json_atomic(paths.usage, usage)
    print(f"RESERVED: {args.id}")
    return 0


def command_release(paths: ProjectPaths, args: argparse.Namespace, usage: JSONDict) -> int:
    before = len(usage.get("reservations", []))
    usage["reservations"] = [item for item in usage.get("reservations", []) if item.get("id") != args.id]
    if len(usage["reservations"]) == before:
        print(f"RESERVATION NOT FOUND: {args.id}")
        return 1
    usage["updated_at"] = now()
    write_json_atomic(paths.usage, usage)
    print(f"RELEASED: {args.id}")
    return 0


def command_authorize(paths: ProjectPaths, args: argparse.Namespace, policy: JSONDict, usage: JSONDict) -> int:
    hard_stop = float(policy["provider_thresholds"]["hard_stop_percent"])
    gate = float(policy["provider_thresholds"]["human_gate_percent"])
    if args.until_percent < gate:
        print(f"AUTHORIZATION REJECTED: until-percent must be at least {gate}")
        return 1
    if args.until_percent >= hard_stop:
        print(f"AUTHORIZATION REJECTED: until-percent must be lower than {hard_stop}")
        return 1
    usage["authorization"] = {
        "scope": args.scope,
        "until_percent": args.until_percent,
        "reason": args.reason,
        "created_at": now(),
    }
    usage["updated_at"] = now()
    write_json_atomic(paths.usage, usage)
    print("BUDGET AUTHORIZED")
    return 0


def command_clear_authorization(paths: ProjectPaths, usage: JSONDict) -> int:
    usage["authorization"] = None
    usage["updated_at"] = now()
    write_json_atomic(paths.usage, usage)
    print("BUDGET AUTHORIZATION CLEARED")
    return 0


def run(paths: ProjectPaths, args: argparse.Namespace) -> int:
    """Dispatch a ``jotta budget`` subcommand."""
    policy = load_json(paths.budget_policy)
    usage = load_json(paths.usage, default_usage())
    if args.budget_command == "record":
        return command_record(paths, args, usage)
    if args.budget_command == "reserve":
        return command_reserve(paths, args, usage)
    if args.budget_command == "release":
        return command_release(paths, args, usage)
    if args.budget_command == "authorize":
        return command_authorize(paths, args, policy, usage)
    if args.budget_command == "clear-authorization":
        return command_clear_authorization(paths, usage)
    payload, code = evaluate(policy, usage, getattr(args, "scope", "run"), getattr(args, "checkpoint", None))
    print_json(payload)
    return 0 if args.budget_command == "status" else code
