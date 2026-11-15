from __future__ import annotations

from pathlib import Path

import pytest

from jotta.hooks.guard import evaluate, is_secret, split_commands


def bash(command: str, cwd: Path) -> dict[str, object]:
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}


@pytest.mark.parametrize(
    ("command", "rule"),
    [
        ("git push --force", "force-push"),
        ("git push -f origin main", "force-push"),
        ("git push -uf origin main", "force-push"),
        ("git push --force-with-lease origin feat/x", "force-push"),
        ("git push origin +main", "force-push"),
        ("git push origin :old-branch", "force-push"),
        ("git push origin --delete old-branch", "force-push"),
        ("git -C repo push --force", "force-push"),
        ("npm test && git push --force", "force-push"),
        ("echo ok; sudo git push -f", "force-push"),
        ("GIT_TRACE=1 git push --force", "force-push"),
        ("git reset --hard HEAD~1", "hard-reset"),
        ("git commit --no-verify -m 'feat: x'", "bypass-branch-protection"),
        ("git commit -nm 'feat: x'", "bypass-branch-protection"),
        ("git push --no-verify origin feat/x", "bypass-branch-protection"),
        ("gh pr merge 12 --merge --admin", "bypass-branch-protection"),
        ("gh api -X DELETE repos/o/r/branches/main/protection", "bypass-branch-protection"),
        ("gh api --method=PUT repos/o/r/branches/main/protection", "bypass-branch-protection"),
        ("gh api repos/o/r/rulesets -f name=open", "bypass-branch-protection"),
        ("cat .env", "read-secrets"),
        ("grep TOKEN config/.env.production", "read-secrets"),
        ("cp ~/.ssh/id_rsa /tmp/key", "read-secrets"),
        ("python load.py --config=secrets.json", "read-secrets"),
        ("rm -rf /", "delete-outside-project"),
        ("rm -rf ..", "delete-outside-project"),
        ("rm -rf .", "delete-outside-project"),
        ("rm -r -f ../other-project", "delete-outside-project"),
        ("rm --recursive --force /tmp/cache", "delete-outside-project"),
        ("rm -rf $BUILD_DIR", "delete-outside-project"),
        ("rm -rf ~/projects", "delete-outside-project"),
        ("rm -rf build/*", "delete-outside-project"),
    ],
)
def test_dangerous_commands_are_blocked(tmp_path: Path, command: str, rule: str) -> None:
    decision = evaluate(bash(command, tmp_path), tmp_path)
    assert not decision.allowed
    assert decision.rule == rule
    assert decision.reason


@pytest.mark.parametrize(
    "command",
    [
        "git push -u origin feat/hooks",
        "git push origin feat/hooks",
        "git commit -m 'feat(hooks): adiciona guard'",
        "git reset --soft HEAD~1",
        "git status && git diff",
        "gh pr merge 12 --merge --delete-branch",
        "gh api repos/o/r/branches/main/protection",
        "rm -rf build dist",
        "rm -rf ./node_modules",
        "rm notes.txt",
        "cp .env.example .env.example.bak",
        "echo 'keep .env out of commits'",
        "python -m pytest",
        "",
    ],
)
def test_safe_commands_are_allowed(tmp_path: Path, command: str) -> None:
    assert evaluate(bash(command, tmp_path), tmp_path).allowed


def test_deletion_is_resolved_from_the_working_directory(tmp_path: Path) -> None:
    nested = tmp_path / "src" / "app"
    assert evaluate(bash("rm -rf ../legacy", nested), tmp_path).allowed
    assert not evaluate(bash("rm -rf ../../..", nested), tmp_path).allowed


@pytest.mark.parametrize(
    ("tool", "field", "path"),
    [
        ("Read", "file_path", "/work/app/.env"),
        ("Read", "file_path", "C:\\work\\app\\.env.local"),
        ("Edit", "file_path", "deploy/server.pem"),
        ("Read", "file_path", "/opt/ci/.aws/config"),
        ("NotebookEdit", "notebook_path", "keys/id_ed25519"),
        ("Grep", "path", ".env"),
    ],
)
def test_reading_credentials_is_blocked(tool: str, field: str, path: str, tmp_path: Path) -> None:
    decision = evaluate({"tool_name": tool, "tool_input": {field: path}}, tmp_path)
    assert (decision.allowed, decision.rule) == (False, "read-secrets")


@pytest.mark.parametrize(
    ("tool", "path"),
    [("Read", ".env.example"), ("Read", "src/env.py"), ("Write", ".env"), ("Read", "keys/id_rsa.pub")],
)
def test_ordinary_files_and_new_secrets_are_allowed(tool: str, path: str, tmp_path: Path) -> None:
    assert evaluate({"tool_name": tool, "tool_input": {"file_path": path}}, tmp_path).allowed


def test_unknown_tools_and_malformed_input_are_allowed(tmp_path: Path) -> None:
    assert evaluate({"tool_name": "WebFetch", "tool_input": {"url": "https://example.com"}}, tmp_path).allowed
    assert evaluate({"tool_name": "Bash", "tool_input": "git push --force"}, tmp_path).allowed
    assert evaluate({}, tmp_path).allowed


@pytest.mark.parametrize(
    ("path", "secret"),
    [
        (".env", True),
        (".env.production", True),
        ("config/credentials.json", True),
        ("certs/tls.key", True),
        (".env.sample", False),
        ("environment.md", False),
        ("README.md", False),
        ("", False),
    ],
)
def test_secret_detection(path: str, secret: bool) -> None:
    assert is_secret(path) is secret


def test_commands_are_split_on_shell_operators() -> None:
    line = "FOO=1 sudo git push -f; ls | wc -l && (cd sub || exit)\nrm -rf x"
    assert split_commands(line) == [
        ["git", "push", "-f"],
        ["ls"],
        ["wc", "-l"],
        ["cd", "sub"],
        ["exit"],
        ["rm", "-rf", "x"],
    ]


def test_unbalanced_quotes_fall_back_to_whitespace(tmp_path: Path) -> None:
    assert not evaluate(bash("git push --force 'unterminated", tmp_path), tmp_path).allowed
