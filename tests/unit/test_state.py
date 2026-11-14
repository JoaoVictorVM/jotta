from __future__ import annotations

import hashlib
from pathlib import Path

from jotta.core.state import default_usage, load_json, sha256, write_json_atomic


def test_atomic_write_creates_parents_and_leaves_no_temp_file(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "state.json"
    write_json_atomic(target, {"name": "café"})
    assert load_json(target) == {"name": "café"}
    assert [path.name for path in target.parent.iterdir()] == ["state.json"]
    assert target.read_text(encoding="utf-8").endswith("\n")


def test_atomic_write_replaces_existing_content(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    write_json_atomic(target, {"version": 1})
    write_json_atomic(target, {"version": 2})
    assert load_json(target) == {"version": 2}


def test_missing_file_returns_the_default(tmp_path: Path) -> None:
    usage = default_usage()
    assert load_json(tmp_path / "missing.json", usage) is usage


def test_defaults_are_fresh_copies() -> None:
    first = default_usage()
    first["reservations"].append({"id": "agents"})
    assert default_usage()["reservations"] == []


def test_sha256_hashes_the_file_bytes(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    target.write_bytes(b"jotta")
    assert sha256(target) == hashlib.sha256(b"jotta").hexdigest()
