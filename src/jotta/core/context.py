"""Rough context size estimates for packets and skill bundles."""

from __future__ import annotations

from pathlib import Path


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def profile_token_estimates(skills: Path) -> dict[str, int]:
    """Estimate the static skill context each profile loads."""
    paths = {
        "lean": [
            skills / "spec-writer" / "SKILL.md",
            skills / "spec-writer" / "references" / "lean.md",
            skills / "implement-feature" / "SKILL.md",
            skills / "implement-feature" / "references" / "lean.md",
        ],
        "strict": [
            skills / "spec-writer" / "SKILL.md",
            skills / "spec-writer" / "references" / "manual-classic.md",
            skills / "implement-feature" / "SKILL.md",
            skills / "implement-feature" / "references" / "manual-classic-and-strict.md",
        ],
    }
    return {
        name: sum(estimate_tokens(path.read_text(encoding="utf-8")) for path in files if path.exists())
        for name, files in paths.items()
    }
