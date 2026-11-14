"""Regression checks on the packaged templates and the quality output compaction."""

from __future__ import annotations

import pytest

from jotta.core.context import profile_token_estimates
from jotta.core.paths import templates_root
from jotta.quality.runner import compact

HARNESS = templates_root() / ".jotta"
CONTRACTS = HARNESS / "skills"


def test_lean_context_is_much_smaller_than_strict() -> None:
    estimates = profile_token_estimates(HARNESS / "skills")
    assert estimates["lean"] < estimates["strict"]
    assert estimates["strict"] >= estimates["lean"] * 3


@pytest.mark.parametrize(
    "relative",
    [
        "profiles/manual-classic.yaml",
        "profiles/lean.yaml",
        "profiles/strict.yaml",
        "skills/prd-writer/references/full-contract.md",
        "skills/spec-writer/references/manual-classic.md",
        "skills/implement-feature/references/manual-classic-and-strict.md",
        "skills/final-qa/SKILL.md",
        "adapters/orca.md",
    ],
)
def test_required_template_file_exists(relative: str) -> None:
    assert (HARNESS / relative).is_file()


@pytest.mark.parametrize("gate", ["G1", "G2", "G3", "G4"])
def test_preserved_contracts_keep_the_gates(gate: str) -> None:
    specs = (CONTRACTS / "spec-writer" / "references" / "manual-classic.md").read_text(encoding="utf-8")
    implementation = (CONTRACTS / "implement-feature" / "references" / "manual-classic-and-strict.md").read_text(
        encoding="utf-8"
    )
    assert gate in specs or gate in implementation


def test_compact_announces_omitted_lines() -> None:
    lines = compact("\n".join(f"line {index}" for index in range(100)), limit=12)
    assert len(lines) <= 12
    assert any("omitted" in line for line in lines)


def test_compact_prefers_error_lines() -> None:
    log = "\n".join(["ok"] * 50 + ["ERROR: test_login failed"] + ["ok"] * 50)
    assert "ERROR: test_login failed" in compact(log, limit=5)


def test_compact_keeps_short_output_whole() -> None:
    assert compact("one\n\ntwo", limit=10) == ["one", "two"]
