#!/usr/bin/env python3
"""Offline regression checks for the jotta runtime."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / ".harness"
SOURCE = ROOT / "src"
if (SOURCE / "jotta" / "cli.py").is_file():
    sys.path.insert(0, str(SOURCE))

try:
    from jotta.budget.guard import evaluate
    from jotta.core.context import profile_token_estimates
    from jotta.core.risk import risk_for
    from jotta.quality.runner import compact
except ImportError:
    print("jotta package not found. Install it with: python -m pip install git+https://github.com/JoaoVictorVM/jotta")
    raise SystemExit(2) from None


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    estimates = profile_token_estimates(HARNESS / "skills")
    check(estimates["lean"] < estimates["strict"], "lean context must be smaller than strict")
    check(estimates["strict"] >= estimates["lean"] * 3, "strict must preserve the detailed contract")

    high = risk_for("alterar autenticacao, pagamentos e migracao destrutiva")
    low = risk_for("ajustar texto vazio na tela inicial")
    check(high["level"] == "high", "high risk classifier failed")
    check(low["level"] == "normal", "normal risk classifier failed")

    compacted = compact("\n".join(f"line {i}" for i in range(100)), limit=12)
    check(len(compacted) <= 12, "quality output was not compacted")
    check(any("omitted" in line for line in compacted), "compact output must announce omission")

    policy = json.loads((HARNESS / "budgets" / "policy.json").read_text(encoding="utf-8"))
    synthetic_usage = json.loads((HARNESS / "state" / "usage.json").read_text(encoding="utf-8"))
    synthetic_usage["provider_usage_percent"] = 86
    budget_result, budget_code = evaluate(policy, synthetic_usage, "feature", "before-feature")
    check(budget_code == 2 and budget_result["status"] == "human-gate", "provider threshold gate failed")

    routing = json.loads((HARNESS / "models" / "routing.json").read_text(encoding="utf-8"))
    check("final-qa" in routing["task_routes"], "final QA route is missing")

    required = [
        HARNESS / "profiles" / "manual-classic.yaml",
        HARNESS / "profiles" / "lean.yaml",
        HARNESS / "profiles" / "strict.yaml",
        HARNESS / "skills" / "prd-writer" / "references" / "full-contract.md",
        HARNESS / "skills" / "spec-writer" / "references" / "manual-classic.md",
        HARNESS / "skills" / "implement-feature" / "references" / "manual-classic-and-strict.md",
        HARNESS / "skills" / "final-qa" / "SKILL.md",
        HARNESS / "adapters" / "orca.md",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    check(not missing, f"missing required files: {missing}")

    old_specs = (HARNESS / "skills" / "spec-writer" / "references" / "manual-classic.md").read_text(encoding="utf-8")
    old_impl = (HARNESS / "skills" / "implement-feature" / "references" / "manual-classic-and-strict.md").read_text(
        encoding="utf-8"
    )
    for marker in ["G1", "G2", "G3", "G4"]:
        check(marker in old_specs or marker in old_impl, f"preserved contract is missing {marker}")

    print(json.dumps({"status": "ok", "checks": 13, "token_estimates": estimates}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
