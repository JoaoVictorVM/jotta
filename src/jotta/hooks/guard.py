"""Decide whether a tool call may run, before the agent executes it.

The rules mirror the ``deny`` list of ``.jotta/policy/permissions.md``. They are deliberately conservative: a
command the guard cannot understand with certainty, such as a deletion target built from a variable, is blocked
rather than allowed.
"""

from __future__ import annotations

import fnmatch
import re
import shlex
from dataclasses import dataclass
from pathlib import Path, PurePath

from jotta.core.state import JSONDict

SHELL_TOOLS = {"Bash"}
FILE_TOOLS = {"Read", "Edit", "MultiEdit", "Write", "NotebookEdit", "NotebookRead"}
SEARCH_TOOLS = {"Grep", "Glob"}

SECRET_PATTERNS = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.keystore",
    "id_rsa*",
    "id_dsa*",
    "id_ecdsa*",
    "id_ed25519*",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "credentials",
    "credentials.json",
    "secrets.json",
    "secrets.yaml",
    "secrets.yml",
)
SAFE_SEGMENTS = {"example", "sample", "template", "dist"}
SECRET_DIRECTORIES = (".aws", ".ssh", ".gnupg")

OPERATOR_CHARACTERS = set(";&|()")
COMMAND_PREFIXES = {"sudo", "env", "command", "exec", "nohup", "time", "xargs"}
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
UNRESOLVED = re.compile(r"[$`*?~{]")
PROTECTION_ENDPOINT = re.compile(r"/branches/[^/\s]+/protection|/rulesets")
API_FIELD_FLAGS = {"-f", "-F", "--field", "--raw-field", "--input"}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    rule: str | None = None
    reason: str | None = None


ALLOW = Decision(allowed=True)


def deny(rule: str, reason: str) -> Decision:
    return Decision(allowed=False, rule=rule, reason=reason)


def is_secret(path: str) -> bool:
    """Whether ``path`` names a credential file the agent must not read."""
    pure = PurePath(path.replace("\\", "/"))
    name = pure.name.lower()
    if not name:
        return False
    if any(part.lower() in SECRET_DIRECTORIES for part in pure.parts[:-1]):
        return True
    if SAFE_SEGMENTS & set(name.split(".")[1:]) or name.endswith(".pub"):
        return False
    return any(fnmatch.fnmatch(name, pattern) for pattern in SECRET_PATTERNS)


def split_commands(command: str) -> list[list[str]]:
    """Split a shell command line into simple commands, each as a list of words."""
    lexer = shlex.shlex(command.replace("\n", ";"), posix=True, punctuation_chars=";&|()")
    lexer.whitespace_split = True
    commands: list[list[str]] = [[]]
    try:
        for token in lexer:
            if set(token) <= OPERATOR_CHARACTERS:
                commands.append([])
            else:
                commands[-1].append(token)
    except ValueError:
        return [strip_prefixes(command.split())]
    return [strip_prefixes(words) for words in commands if words]


def strip_prefixes(words: list[str]) -> list[str]:
    """Drop environment assignments and wrappers such as ``sudo`` that precede the real program."""
    index = 0
    while index < len(words):
        word = words[index]
        wrapper_option = index > 0 and words[index - 1] in COMMAND_PREFIXES and word.startswith("-")
        if not (ASSIGNMENT.match(word) or word in COMMAND_PREFIXES or wrapper_option):
            break
        index += 1
    return [word for word in words[index:] if word]


def program(words: list[str]) -> str:
    return PurePath(words[0].replace("\\", "/")).name.lower() if words else ""


def git_subcommand(words: list[str]) -> tuple[str, list[str]]:
    """Return the git subcommand and its arguments, skipping global options such as ``-C path``."""
    index = 1
    while index < len(words) and words[index].startswith("-"):
        index += 2 if words[index] in {"-C", "-c", "--git-dir", "--work-tree", "--namespace"} else 1
    if index >= len(words):
        return "", []
    return words[index], words[index + 1 :]


def short_flags(arguments: list[str]) -> set[str]:
    return {char for word in arguments if re.fullmatch(r"-[A-Za-z]+", word) for char in word[1:]}


def check_git(words: list[str]) -> Decision:
    subcommand, arguments = git_subcommand(words)
    if subcommand == "push":
        forced = {"--force", "--force-with-lease", "--force-if-includes", "--mirror", "--delete"}
        if forced & {word.split("=")[0] for word in arguments} or "f" in short_flags(arguments):
            return deny("force-push", "force pushes and remote deletions rewrite shared history")
        if any(word.startswith(("+", ":")) for word in arguments):
            return deny("force-push", "a '+' or ':' refspec forces or deletes a remote branch")
        if "--no-verify" in arguments:
            return deny("bypass-branch-protection", "--no-verify skips the repository's push hooks")
    if subcommand == "reset" and "--hard" in arguments:
        return deny("hard-reset", "git reset --hard discards uncommitted work")
    if subcommand == "commit" and ("--no-verify" in arguments or "n" in short_flags(arguments)):
        return deny("bypass-branch-protection", "--no-verify skips the repository's commit hooks")
    return ALLOW


def api_method(arguments: list[str]) -> str:
    """The HTTP method of a ``gh api`` call; like gh, sending fields without a method means POST."""
    for index, word in enumerate(arguments):
        if word in {"-X", "--method"} and index + 1 < len(arguments):
            return arguments[index + 1].upper()
        if word.startswith("--method="):
            return word.split("=", 1)[1].upper()
    sends_fields = any(word.split("=")[0] in API_FIELD_FLAGS for word in arguments)
    return "POST" if sends_fields else "GET"


def check_gh(words: list[str]) -> Decision:
    arguments = words[1:]
    if arguments[:2] == ["pr", "merge"] and "--admin" in arguments:
        return deny("bypass-branch-protection", "gh pr merge --admin bypasses required reviews and checks")
    protection = arguments[:1] == ["api"] and any(PROTECTION_ENDPOINT.search(word) for word in arguments)
    if protection and api_method(arguments) != "GET":
        return deny("bypass-branch-protection", "changing branch protection or rulesets requires a human")
    return ALLOW


def inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def check_rm(words: list[str], cwd: Path, root: Path) -> Decision:
    arguments = words[1:]
    flags = short_flags(arguments) | {word for word in arguments if word.startswith("--")}
    recursive = bool({"r", "R"} & flags or "--recursive" in flags)
    if not recursive:
        return ALLOW
    targets = [word for word in arguments if not word.startswith("-")]
    for target in targets:
        if UNRESOLVED.search(target):
            return deny("delete-outside-project", f"cannot verify the deletion target {target!r}")
        resolved = (cwd / target).resolve()
        if resolved == root or not inside(resolved, root):
            return deny("delete-outside-project", f"recursive deletion of {target!r} leaves the project")
    return ALLOW


def check_shell(command: str, cwd: Path, root: Path) -> Decision:
    for words in split_commands(command):
        name = program(words)
        if name == "git":
            decision = check_git(words)
        elif name == "gh":
            decision = check_gh(words)
        elif name == "rm":
            decision = check_rm(words, cwd, root)
        else:
            decision = ALLOW
        if decision.allowed:
            secret = next((word for word in words[1:] if is_secret(word.split("=")[-1])), None)
            if secret is not None:
                decision = deny("read-secrets", f"{secret!r} may hold credentials")
        if not decision.allowed:
            return decision
    return ALLOW


def evaluate(payload: JSONDict, root: Path) -> Decision:
    """Decide a ``PreToolUse`` event for a project rooted at ``root``."""
    tool = str(payload.get("tool_name", ""))
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return ALLOW
    cwd = Path(str(payload.get("cwd") or root)).resolve()
    if tool in SHELL_TOOLS:
        return check_shell(str(tool_input.get("command", "")), cwd, root)
    if tool in FILE_TOOLS:
        path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        if path and is_secret(path) and tool != "Write":
            return deny("read-secrets", f"{path!r} may hold credentials")
    if tool in SEARCH_TOOLS:
        path = str(tool_input.get("path") or "")
        if path and is_secret(path):
            return deny("read-secrets", f"{path!r} may hold credentials")
    return ALLOW
