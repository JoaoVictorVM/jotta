from __future__ import annotations

import pytest

from jotta.hooks.payload import expand, patch_files, patch_text, shell_command

PATCH = """*** Begin Patch
*** Add File: src/new.py
+print(1)
*** Update File: src/app.py
@@
-a
+b
*** Move to: src/renamed.py
*** Delete File: old/legacy.py
*** End Patch
"""


def test_patch_files_lists_every_touched_path_with_its_tool() -> None:
    assert patch_files(PATCH) == [
        ("Write", "src/new.py"),
        ("Edit", "src/app.py"),
        ("Write", "src/renamed.py"),
        ("Edit", "old/legacy.py"),
    ]


@pytest.mark.parametrize(
    "tool_input", [PATCH, {"input": PATCH}, {"command": ["apply_patch", PATCH]}, {"x": {"y": PATCH}}]
)
def test_the_patch_is_found_wherever_the_agent_put_it(tool_input: object) -> None:
    assert patch_text(tool_input) == PATCH


def test_input_without_a_patch_has_no_files() -> None:
    assert patch_text({"input": "hello"}) == ""
    assert patch_text(42) == ""
    assert expand({"tool_name": "apply_patch", "tool_input": {"input": "hello"}}) == []


def test_an_apply_patch_event_becomes_one_event_per_file() -> None:
    events = expand({"tool_name": "apply_patch", "tool_input": {"input": PATCH}, "cwd": "/p"})
    assert [(item["tool_name"], item["tool_input"]["file_path"]) for item in events] == patch_files(PATCH)
    assert all(item["cwd"] == "/p" for item in events)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("git status", "git status"),
        (["bash", "-lc", "git push --force"], "git push --force"),
        (["powershell", "-Command", "rm -r x"], "rm -r x"),
        (["git", "push", "origin main"], "git push 'origin main'"),
        (None, ""),
    ],
)
def test_shell_command(value: object, expected: str) -> None:
    assert shell_command(value) == expected


def test_codex_shell_inputs_get_a_command_string() -> None:
    [listed] = expand({"tool_name": "Bash", "tool_input": {"command": ["bash", "-lc", "ls"]}})
    [cmd] = expand({"tool_name": "Bash", "tool_input": {"cmd": "ls -la"}})
    assert (listed["tool_input"]["command"], cmd["tool_input"]["command"]) == ("ls", "ls -la")


def test_claude_events_pass_through_unchanged() -> None:
    event = {"tool_name": "Edit", "tool_input": {"file_path": "src/app.py"}}
    assert expand(event) == [event]
