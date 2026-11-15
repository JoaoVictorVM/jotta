"""The files a task may edit: extracted from its spec, declared on the command line or widened by a person."""

from __future__ import annotations

import fnmatch
import re
from pathlib import PurePosixPath

ALWAYS_ALLOWED = (".planning/",)
ENFORCEMENT = {"strict": "block", "lean": "warn", "manual-classic": "off"}
TABLE_PATH = re.compile(r"^\|\s*`([^`\s]+)`\s*\|")


def normalize(entry: str) -> str:
    """A project-relative path in slash form; a trailing slash marks a directory."""
    value = entry.strip().replace("\\", "/")
    directory = value.endswith("/")
    value = re.sub(r":\d+(?::\d+)?$", "", value)
    parts = [part for part in PurePosixPath(value).parts if part not in {".", "/"}]
    normalized = "/".join(parts)
    return f"{normalized}/" if directory and normalized else normalized


def paths_from_spec(text: str) -> list[str]:
    """Paths listed in the first column of the spec's tables, such as the component and test file tables."""
    found: list[str] = []
    for line in text.splitlines():
        match = TABLE_PATH.match(line.strip())
        if not match:
            continue
        candidate = match.group(1)
        if ("/" in candidate or "." in candidate) and not candidate.startswith(("http", "/api")):
            found.append(normalize(candidate))
    return unique(found)


def unique(paths: list[str]) -> list[str]:
    return list(dict.fromkeys(path for path in paths if path))


def in_scope(relative: str, allowed: list[str]) -> bool:
    """Whether the project-relative ``relative`` path is covered by an allowed file, directory or glob."""
    target = normalize(relative)
    for entry in [*ALWAYS_ALLOWED, *allowed]:
        pattern = normalize(entry)
        if not pattern:
            continue
        if pattern.endswith("/"):
            if target.startswith(pattern):
                return True
        elif target == pattern or target.startswith(f"{pattern}/") or fnmatch.fnmatchcase(target, pattern):
            return True
    return False


def enforcement_for(profile: str | None) -> str:
    return ENFORCEMENT.get(profile or "", "off")
