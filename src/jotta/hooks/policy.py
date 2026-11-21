"""Pin the configuration the hooks enforce, so editing it mid-session changes nothing until it is committed.

The hooks read the quality gates (``.jotta/sensors/computational/gates.json``): which commands run after an edit and
which receipt the agent needs before it stops. An agent that could weaken that file and see the effect at once
could switch its own checks off. So the hooks read each pinned file from the first source that applies:

1. ``HEAD``, when the project is a Git repository and the file is committed;
2. a snapshot taken by the first hook of the agent session, when the file is not committed (an installed harness is
   excluded from Git by default), so an edit takes effect in the next session;
3. the working tree, when there is neither a commit nor a session id.

A pinned file that differs on disk is reported once per session, and by ``jotta doctor``.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict, load_json, write_json_atomic

GIT_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class Pinned:
    """The text a hook enforces for a file, where it came from and whether the working tree differs."""

    text: str | None
    source: str
    diverges: bool


def pinned_files(paths: ProjectPaths) -> list[Path]:
    return [paths.gates]


def snapshot_path(paths: ProjectPaths) -> Path:
    return paths.state / "policy-snapshot.json"


def read_disk(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def committed(paths: ProjectPaths, path: Path) -> str | None:
    """The text of ``path`` at ``HEAD``, or ``None`` outside Git or when the file is not committed."""
    try:
        process = subprocess.run(
            ["git", "show", f"HEAD:{paths.relative(path)}"],
            cwd=paths.root,
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if process.returncode != 0:
        return None
    return process.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n")


def session_snapshot(paths: ProjectPaths, session_id: str) -> JSONDict:
    """The snapshot of the current session, taken from the working tree on the session's first hook."""
    snapshot = load_json(snapshot_path(paths), {}) if snapshot_path(paths).is_file() else {}
    if snapshot.get("session_id") == session_id and isinstance(snapshot.get("files"), dict):
        return snapshot
    files = {paths.relative(path): read_disk(path) for path in pinned_files(paths)}
    snapshot = {"session_id": session_id, "files": files, "reported": []}
    write_json_atomic(snapshot_path(paths), snapshot)
    return snapshot


def same(left: str | None, right: str | None) -> bool:
    if left is None or right is None:
        return left == right
    return left.replace("\r\n", "\n") == right.replace("\r\n", "\n")


def pin(paths: ProjectPaths, path: Path, session_id: str | None) -> Pinned:
    """The text the hooks enforce for ``path``."""
    disk = read_disk(path)
    head = committed(paths, path)
    if head is not None:
        return Pinned(head, "HEAD", not same(head, disk))
    if session_id:
        text = session_snapshot(paths, session_id)["files"].get(paths.relative(path))
        return Pinned(text, "session", not same(text, disk))
    return Pinned(disk, "working tree", False)


def load_gates(paths: ProjectPaths, session_id: str | None) -> JSONDict:
    """The pinned quality gates, or an empty configuration when they are missing or unreadable."""
    text = pin(paths, paths.gates, session_id).text
    try:
        data = json.loads(text) if text else {}
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def divergence_message(paths: ProjectPaths, path: Path, pinned: Pinned) -> str:
    until = "they are committed" if pinned.source == "HEAD" else "the next agent session"
    return (
        f"{paths.relative(path)} differs from the version the hooks enforce ({pinned.source}); "
        f"the hooks ignore the edits until {until}"
    )


def unreported_divergence(paths: ProjectPaths, session_id: str | None) -> list[str]:
    """Divergence messages not yet shown in this session; each is shown once per session."""
    messages = []
    for path in pinned_files(paths):
        pinned = pin(paths, path, session_id)
        if pinned.diverges:
            messages.append(divergence_message(paths, path, pinned))
    if not messages or not session_id:
        return messages
    snapshot = session_snapshot(paths, session_id)
    reported = [str(item) for item in snapshot.get("reported") or []]
    fresh = [message for message in messages if message not in reported]
    if fresh:
        write_json_atomic(snapshot_path(paths), {**snapshot, "reported": reported + fresh})
    return fresh


def doctor_warnings(paths: ProjectPaths) -> list[str]:
    """Committed pinned files whose working copy differs from ``HEAD``."""
    warnings = []
    for path in pinned_files(paths):
        pinned = pin(paths, path, None)
        if pinned.source == "HEAD" and pinned.diverges:
            warnings.append(divergence_message(paths, path, pinned))
    return warnings
