"""Recognize the project's stack and suggest commands for the ``smoke``, ``feature`` and ``full`` quality profiles.

Detection reads only files at the project root: manifests, lock files and tool configuration. It never runs the
project's tools. A command is suggested only when the project shows it uses the tool, such as a ``lint`` script in
``package.json`` or a ``[tool.ruff]`` table in ``pyproject.toml``.

The suggestion fills a profile only when the profile is empty or still equal to the previous suggestion, which is
recorded in the ``detected`` section of ``gates.json``. A profile the user edited is never overwritten.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict, load_json, print_json, write_json_atomic

PROFILES = ("smoke", "feature", "full")
NPM_PLACEHOLDER_TEST = "no test specified"
SKIPPED_DIRECTORIES = r"(\.git|\.venv|venv|node_modules|\.jotta|\.planning)"
TYPECHECK_SCRIPTS = ("typecheck", "type-check", "check-types", "tsc")


@dataclass
class Stack:
    """A recognized stack and the commands it suggests for each profile."""

    name: str
    manager: str
    evidence: list[str]
    profiles: dict[str, list[str]] = field(default_factory=dict)

    def summary(self) -> JSONDict:
        return {"name": self.name, "manager": self.manager, "evidence": self.evidence}


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def node_manager(root: Path, package: JSONDict) -> str:
    declared = str(package.get("packageManager") or "").split("@")[0]
    if declared in {"npm", "pnpm", "yarn"}:
        return declared
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    return "npm"


def detect_node(root: Path) -> Stack | None:
    manifest = root / "package.json"
    if not manifest.is_file():
        return None
    try:
        package = json.loads(read(manifest))
    except json.JSONDecodeError:
        package = {}
    if not isinstance(package, dict):
        package = {}
    manager = node_manager(root, package)
    raw_scripts = package.get("scripts")
    scripts: JSONDict = raw_scripts if isinstance(raw_scripts, dict) else {}
    dependencies = {
        name
        for key in ("dependencies", "devDependencies")
        if isinstance(package.get(key), dict)
        for name in package[key]
    }

    def script(name: str) -> str:
        return f"yarn {name}" if manager == "yarn" else f"{manager} run {name}"

    smoke: list[str] = []
    if "lint" in scripts:
        smoke.append(script("lint"))
    typecheck = next((name for name in TYPECHECK_SCRIPTS if name in scripts), None)
    if typecheck:
        smoke.append(script(typecheck))
    elif "typescript" in dependencies and (root / "tsconfig.json").exists():
        runner = {"npm": "npx", "pnpm": "pnpm exec", "yarn": "yarn"}[manager]
        smoke.append(f"{runner} tsc --noEmit")
    tests = []
    if "test" in scripts and NPM_PLACEHOLDER_TEST not in str(scripts["test"]):
        tests.append("yarn test" if manager == "yarn" else f"{manager} test")
    build = [script("build")] if "build" in scripts else []
    evidence = [
        "package.json",
        *[name for name in ("pnpm-lock.yaml", "yarn.lock", "package-lock.json") if (root / name).exists()],
    ]
    return Stack("node", manager, evidence, profiles_from(smoke, tests, build))


def python_manager(root: Path, pyproject: str) -> str:
    if (root / "uv.lock").exists():
        return "uv"
    if (root / "poetry.lock").exists() or "[tool.poetry" in pyproject:
        return "poetry"
    return "pip"


def uses(tool: str, text: str, *config_files: Path) -> bool:
    return any(path.exists() for path in config_files) or re.search(rf"(?<![\w-]){tool}(?![\w-])", text) is not None


def detect_python(root: Path) -> Stack | None:
    manifests = [
        name for name in ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt") if (root / name).is_file()
    ]
    if not manifests:
        return None
    pyproject = read(root / "pyproject.toml")
    text = "\n".join(
        read(path) for path in [root / "pyproject.toml", root / "setup.cfg", *root.glob("requirements*.txt")]
    )
    manager = python_manager(root, pyproject)
    prefix = {"uv": "uv run ", "poetry": "poetry run ", "pip": "python -m "}[manager]

    ruff = uses("ruff", text, root / "ruff.toml", root / ".ruff.toml")
    smoke: list[str] = []
    if ruff:
        smoke.append(f"{prefix}ruff check .")
    if uses("mypy", text, root / "mypy.ini", root / ".mypy.ini"):
        smoke.append(f"{prefix}mypy .")
    if not smoke:
        smoke.append(f'python -m compileall -q -x "{SKIPPED_DIRECTORIES}" .')
    tests = [f"{prefix}pytest -q"] if uses("pytest", text, root / "pytest.ini", root / "conftest.py") else []
    extra = [f"{prefix}ruff format --check ."] if ruff else []
    evidence = [*manifests, *[name for name in ("uv.lock", "poetry.lock") if (root / name).exists()]]
    return Stack("python", manager, evidence, profiles_from(smoke, tests, extra))


def detect_go(root: Path) -> Stack | None:
    if not (root / "go.mod").is_file():
        return None
    return Stack("go", "go", ["go.mod"], profiles_from(["go vet ./..."], ["go test ./..."], ["go build ./..."]))


def detect_rust(root: Path) -> Stack | None:
    if not (root / "Cargo.toml").is_file():
        return None
    return Stack(
        "rust",
        "cargo",
        ["Cargo.toml"],
        profiles_from(["cargo check --all-targets"], ["cargo test"], ["cargo fmt --check", "cargo build"]),
    )


def profiles_from(smoke: list[str], tests: list[str], full_extra: list[str]) -> dict[str, list[str]]:
    """``smoke`` is the fast check, ``feature`` adds the tests and ``full`` adds the slower checks."""
    feature = [*smoke, *tests]
    return {"smoke": smoke, "feature": feature, "full": [*feature, *full_extra]}


DETECTORS = (detect_node, detect_python, detect_go, detect_rust)


def detect(root: Path) -> list[Stack]:
    """Every stack recognized at ``root``, in a stable order."""
    return [stack for detector in DETECTORS if (stack := detector(root)) is not None]


def suggest(stacks: list[Stack]) -> dict[str, list[str]]:
    """The commands of every stack, profile by profile, without duplicates."""
    merged: dict[str, list[str]] = {profile: [] for profile in PROFILES}
    for stack in stacks:
        for profile in PROFILES:
            merged[profile].extend(
                command for command in stack.profiles.get(profile, []) if command not in merged[profile]
            )
    return merged


@dataclass
class DetectionPlan:
    """What applying the detection would change in ``gates.json``."""

    stacks: list[Stack]
    suggested: dict[str, list[str]]
    filled: list[str]
    kept: list[str]

    def summary(self) -> JSONDict:
        return {
            "stacks": [stack.summary() for stack in self.stacks],
            "filled": self.filled,
            "kept": self.kept,
            "profiles": {profile: self.suggested[profile] for profile in self.filled},
        }


def plan_detection(paths: ProjectPaths) -> DetectionPlan:
    """Compare the suggestion with the current profiles without writing anything."""
    stacks = detect(paths.root)
    suggested = suggest(stacks)
    gates = load_json(paths.gates, {})
    current = gates.get("profiles") or {}
    previous = (gates.get("detected") or {}).get("profiles") or {}
    filled: list[str] = []
    kept: list[str] = []
    for profile in PROFILES:
        commands = current.get(profile) or []
        if not suggested[profile] or commands == suggested[profile]:
            continue
        if not commands or commands == previous.get(profile):
            filled.append(profile)
        else:
            kept.append(profile)
    return DetectionPlan(stacks, suggested, filled, kept)


def apply_detection(paths: ProjectPaths, plan: DetectionPlan) -> None:
    """Write the filled profiles and record the suggestion so later runs can tell user edits apart."""
    if not plan.stacks:
        return
    gates = load_json(paths.gates, {})
    profiles = dict(gates.get("profiles") or {})
    for profile in plan.filled:
        profiles[profile] = plan.suggested[profile]
    gates["profiles"] = profiles
    gates["detected"] = {"stacks": [stack.summary() for stack in plan.stacks], "profiles": plan.suggested}
    write_json_atomic(paths.gates, gates)


def run(paths: ProjectPaths, dry_run: bool = False) -> int:
    """Detect the stack, fill the quality profiles that are still free and print what changed."""
    plan = plan_detection(paths)
    if not dry_run:
        apply_detection(paths, plan)
    print_json({"status": "dry-run" if dry_run else "detected", **plan.summary()})
    return 0


def doctor_warnings(paths: ProjectPaths) -> list[str]:
    """What ``jotta doctor`` reports about the quality profiles."""
    plan = plan_detection(paths)
    profiles = load_json(paths.gates, {}).get("profiles") or {}
    if plan.filled:
        stacks = ", ".join(f"{stack.name} ({stack.manager})" for stack in plan.stacks)
        return [f"quality profiles {', '.join(plan.filled)} can be filled for {stacks}; run `jotta detect-stack`"]
    empty = [profile for profile in PROFILES if not profiles.get(profile)]
    if empty:
        return [f"quality profiles {', '.join(empty)} have no commands; set them in {paths.relative(paths.gates)}"]
    return []
