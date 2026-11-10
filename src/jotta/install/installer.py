"""Copy the harness templates into a project without silently overwriting files."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from jotta.core.git import run_git
from jotta.core.paths import templates_root
from jotta.core.state import JSONDict

IGNORED_NAMES = {"runtime", "__pycache__"}
IGNORED_SUFFIXES = (".pyc", ".pyo")
LOCAL_DIRECTORIES = (
    Path(".planning") / "features",
    Path(".planning") / "changes",
    Path(".planning") / "decisions",
    Path(".planning") / "commit-plans",
    Path(".planning") / "archive",
    Path(".jotta") / "runtime" / "state",
)
GIT_EXCLUDES = ("/.jotta/", "/.planning/", "/AGENTS.md", "/CLAUDE.md", "/.claude/")
EXCLUDE_HEADER = "# jotta local"


class InstallRefusedError(RuntimeError):
    """Raised when the target must never receive an installation."""


@dataclass
class InstallPlan:
    """Everything an installation would do, computed before writing."""

    target: Path
    files: list[tuple[Path, Path]] = field(default_factory=list)
    conflicts: list[Path] = field(default_factory=list)
    directories: list[Path] = field(default_factory=list)
    exclude_path: Path | None = None
    exclude_entries: list[str] = field(default_factory=list)

    def relative(self, path: Path) -> str:
        return str(path.relative_to(self.target)).replace("\\", "/")

    def summary(self) -> JSONDict:
        return {
            "target": str(self.target),
            "files": len(self.files),
            "conflicts": [self.relative(path) for path in self.conflicts],
            "directories": [self.relative(path) for path in self.directories],
            "git_exclude": str(self.exclude_path) if self.exclude_path else None,
            "git_exclude_entries": self.exclude_entries,
        }


def template_files(templates: Path) -> list[Path]:
    """Template files relative to ``templates``, without generated content."""
    files: list[Path] = []
    for path in sorted(templates.rglob("*")):
        relative = path.relative_to(templates)
        if not path.is_file() or set(relative.parts) & IGNORED_NAMES or path.suffix in IGNORED_SUFFIXES:
            continue
        files.append(relative)
    return files


def git_exclude_path(target: Path) -> Path | None:
    """Return the ``info/exclude`` file of the repository containing ``target``, if any."""
    if not target.exists():
        return None
    result = run_git(target, "rev-parse", "--git-path", "info/exclude")
    if result.returncode != 0:
        return None
    path = Path(result.stdout.strip())
    return path if path.is_absolute() else target / path


def missing_excludes(exclude: Path) -> list[str]:
    current = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    lines = {line.strip() for line in current.splitlines()}
    return [entry for entry in GIT_EXCLUDES if entry not in lines]


def check_target(target: Path, templates: Path) -> None:
    resolved = templates.resolve()
    if target == resolved or resolved in target.parents:
        raise InstallRefusedError("target cannot be the Jotta templates or a directory inside them")
    if (target / "src" / "jotta" / "templates").is_dir():
        raise InstallRefusedError("target is the Jotta source repository")


def plan_install(target: Path, git_exclude: bool = True, templates: Path | None = None) -> InstallPlan:
    """Compute the installation of ``templates`` into ``target`` without touching the disk."""
    templates = templates or templates_root()
    target = target.expanduser().resolve()
    check_target(target, templates)
    plan = InstallPlan(target=target)
    for relative in template_files(templates):
        destination = target / relative
        plan.files.append((templates / relative, destination))
        if destination.exists():
            plan.conflicts.append(destination)
    plan.directories = [target / directory for directory in LOCAL_DIRECTORIES if not (target / directory).is_dir()]
    if git_exclude:
        plan.exclude_path = git_exclude_path(target)
        if plan.exclude_path is not None:
            plan.exclude_entries = missing_excludes(plan.exclude_path)
    return plan


def apply_install(plan: InstallPlan) -> None:
    """Write the planned files, local directories and Git exclusions."""
    for source, destination in plan.files:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    for directory in plan.directories:
        directory.mkdir(parents=True, exist_ok=True)
    if plan.exclude_path is not None and plan.exclude_entries:
        exclude = plan.exclude_path
        exclude.parent.mkdir(parents=True, exist_ok=True)
        current = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
        with exclude.open("a", encoding="utf-8", newline="\n") as handle:
            if current and not current.endswith("\n"):
                handle.write("\n")
            handle.write(f"\n{EXCLUDE_HEADER}\n")
            handle.write("\n".join(plan.exclude_entries) + "\n")
