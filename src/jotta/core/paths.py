"""Locate a Jotta project and the files the runtime reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

HARNESS_DIR = ".harness"
PROJECT_MARKER = Path(HARNESS_DIR) / "config.yaml"


class ProjectNotFoundError(RuntimeError):
    """Raised when no Jotta project contains the starting directory."""


@dataclass(frozen=True)
class ProjectPaths:
    """Paths of a project that has the harness installed."""

    root: Path

    @property
    def harness(self) -> Path:
        return self.root / HARNESS_DIR

    @property
    def planning(self) -> Path:
        return self.root / ".planning"

    @property
    def state(self) -> Path:
        return self.harness / "state"

    @property
    def runtime(self) -> Path:
        return self.harness / "runtime"

    @property
    def tasks(self) -> Path:
        return self.state / "tasks.json"

    @property
    def run(self) -> Path:
        return self.state / "current-run.json"

    @property
    def usage(self) -> Path:
        return self.state / "usage.json"

    @property
    def prd(self) -> Path:
        return self.planning / "PRD.md"

    @property
    def profiles(self) -> Path:
        return self.harness / "profiles"

    @property
    def skills(self) -> Path:
        return self.harness / "skills"

    @property
    def routing(self) -> Path:
        return self.harness / "models" / "routing.json"

    @property
    def budget_policy(self) -> Path:
        return self.harness / "budgets" / "policy.json"

    @property
    def budget_providers(self) -> Path:
        return self.harness / "budgets" / "providers.json"

    @property
    def gates(self) -> Path:
        return self.harness / "sensors" / "computational" / "gates.json"

    def required(self) -> list[Path]:
        """Files that must exist for the harness to operate."""
        harness = self.harness
        return [
            self.root / "AGENTS.md",
            harness / "README.md",
            harness / "AGENT-MANUAL.md",
            harness / "ARCHITECTURE.md",
            harness / "config.yaml",
            harness / "workflows" / "product.md",
            harness / "workflows" / "change.md",
            harness / "workflows" / "quality.md",
            harness / "adapters" / "orca.md",
            harness / "adapters" / "opencode" / "README.md",
            harness / "guides" / "operations" / "worktrees-and-agents.md",
            harness / "permissions" / "permissions.md",
            harness / "permissions" / "human-gates.md",
            self.profiles / "manual-classic.yaml",
            self.profiles / "lean.yaml",
            self.profiles / "strict.yaml",
            self.tasks,
            self.run,
            self.usage,
            self.prd,
        ]

    def relative(self, path: Path) -> str:
        """Return ``path`` relative to the project root with forward slashes."""
        return str(path.relative_to(self.root)).replace("\\", "/")


def find_root(start: Path) -> Path:
    """Return the closest directory at or above ``start`` that contains the harness."""
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / PROJECT_MARKER).is_file():
            return candidate
    raise ProjectNotFoundError(f"no Jotta project found at or above {current}; use --root to point to one")
