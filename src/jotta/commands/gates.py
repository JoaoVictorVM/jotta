"""Deterministic gates for text, staged files, branch names and commit messages."""

from __future__ import annotations

import re
from pathlib import Path

from jotta.core.git import in_git, run_git
from jotta.core.paths import ProjectPaths

LOCAL_PATHS = (".jotta/", ".planning/", ".claude/", ".opencode/", "AGENTS.md", "CLAUDE.md")
TEXT_EXTS = {".md", ".txt", ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".yaml", ".yml"}
COMMIT_TYPES = "feat|fix|refactor|test|docs|style|perf|build|ci|chore"
BRANCH_RE = re.compile(rf"^({COMMIT_TYPES})/[a-z0-9]+(?:-[a-z0-9]+)*$")
COMMIT_RE = re.compile(rf"^({COMMIT_TYPES})\([a-z0-9_-]+\): [a-z0-9].+$")
FORBIDDEN_DASHES = ("\u2013", "\u2014")
FORBIDDEN_META = [
    re.compile(r"[\u2013\u2014]"),
    re.compile(r"co-authored-by", re.I),
    re.compile(r"generated with", re.I),
    re.compile(r"\b(?:claude|anthropic)\b", re.I),
    re.compile(r"\b(?:PRD|spec\.md|plan\.md)\b", re.I),
    re.compile(r"\b(?:F|RF|US)\d+\b", re.I),
]


def tracked_files(paths: ProjectPaths) -> list[Path]:
    root = paths.root
    if in_git(root):
        return [root / value for value in run_git(root, "ls-files", "-z").stdout.split("\0") if value]
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and ".jotta" not in path.parts and ".planning" not in path.parts
    ]


def gate_text(paths: ProjectPaths) -> int:
    errors: list[str] = []
    for path in tracked_files(paths):
        if path.suffix.lower() not in TEXT_EXTS:
            continue
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line_number, line in enumerate(lines, 1):
            if any(dash in line for dash in FORBIDDEN_DASHES):
                errors.append(f"{path.relative_to(paths.root)}:{line_number}: forbidden dash")
    for error in errors:
        print(error)
    print("TEXT OK" if not errors else "TEXT FAILED")
    return 1 if errors else 0


def gate_staged(paths: ProjectPaths) -> int:
    root = paths.root
    if not in_git(root):
        print("STAGED SKIPPED: no Git")
        return 0
    staged = run_git(root, "diff", "--cached", "--name-only", "-z").stdout.split("\0")
    errors: list[str] = []
    for value in (item.replace("\\", "/") for item in staged if item):
        if value == ".gitkeep" or value.endswith("/.gitkeep"):
            errors.append(f"forbidden .gitkeep: {value}")
        if value in LOCAL_PATHS or any(value.startswith(prefix) for prefix in LOCAL_PATHS if prefix.endswith("/")):
            errors.append(f"local file staged: {value}")
    for error in errors:
        print(error)
    print("STAGED OK" if not errors else "STAGED FAILED")
    return 1 if errors else 0


def gate_branch(paths: ProjectPaths, name: str | None) -> int:
    root = paths.root
    name = name or (run_git(root, "branch", "--show-current").stdout.strip() if in_git(root) else "")
    valid = BRANCH_RE.fullmatch(name) is not None
    print("BRANCH OK" if valid else f"BRANCH FAILED: {name}")
    return 0 if valid else 1


def gate_commit(message: str) -> int:
    errors = [] if COMMIT_RE.fullmatch(message) and not message.endswith(".") else ["invalid format"]
    errors.extend(f"forbidden text: {pattern.pattern}" for pattern in FORBIDDEN_META if pattern.search(message))
    for error in errors:
        print(f"COMMIT FAILED: {error}")
    print("COMMIT OK" if not errors else "COMMIT FAILED")
    return 1 if errors else 0
