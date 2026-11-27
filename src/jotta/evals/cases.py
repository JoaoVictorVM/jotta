"""Load and check the eval cases in ``evals/cases/*.yaml``.

A case is a task an agent performs on a fixture app with Jotta installed. It is written in a small subset of YAML
that the standard library can read: ``key: value`` scalars, ``key: |`` blocks of text and ``key:`` lists of
``- item`` strings. Each case names its fixture under ``evals/fixtures/``, its workflow, the PRD feature or change
it covers, the risk the harness must find and the behavior the result must show.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

from jotta.core.state import JSONDict

KINDS = ("feature", "bug", "refactor")
WORKFLOWS = ("product", "change")
RISKS = ("normal", "high")
REQUIRED = ("id", "title", "fixture", "kind", "workflow", "task", "risk", "prompt", "expected")
LISTS = ("expected", "depends_on")
OPTIONAL = ("human_gate", "depends_on")
KEY = re.compile(r"^([a-z_]+):(?:\s+(.*?))?\s*$")
ITEM = re.compile(r"^\s+-\s+(.*?)\s*$")
FEATURE = re.compile(r"^F\d+$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class CaseError(ValueError):
    """A case file that cannot be read or breaks the case schema."""


def scalar(value: str) -> object:
    if value in ("true", "false"):
        return value == "true"
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse(text: str) -> JSONDict:
    """The mapping of a case file; raises ``CaseError`` on anything outside the supported subset."""
    data: JSONDict = {}
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line.strip() or line.startswith("#"):
            continue
        match = KEY.match(line)
        if match is None:
            raise CaseError(f"line {index}: expected 'key: value', got {line!r}")
        key, value = match.group(1), match.group(2) or ""
        if key in data:
            raise CaseError(f"line {index}: duplicate key {key!r}")
        if value == "|":
            block = []
            while index < len(lines) and (not lines[index].strip() or lines[index].startswith(" ")):
                block.append(lines[index])
                index += 1
            data[key] = textwrap.dedent("\n".join(block)).strip() + "\n"
        elif value:
            data[key] = scalar(value)
        else:
            items = []
            while index < len(lines) and (item := ITEM.match(lines[index])):
                items.append(str(scalar(item.group(1))))
                index += 1
            if not items:
                raise CaseError(f"line {index}: {key!r} has no value")
            data[key] = items
    return data


def problems(case: JSONDict, name: str | None = None) -> list[str]:
    """Every way ``case`` breaks the schema; ``name`` is the file stem, which must equal the id."""
    errors = [f"missing {key}" for key in REQUIRED if key not in case]
    errors += [f"unknown key {key}" for key in case if key not in REQUIRED and key not in OPTIONAL]
    for key in REQUIRED:
        if key in case and key not in LISTS and not (isinstance(case[key], str) and case[key].strip()):
            errors.append(f"{key} must be a non-empty string")
    for key in LISTS:
        if key in case and not (isinstance(case[key], list) and case[key]):
            errors.append(f"{key} must be a non-empty list")
    choices = {"kind": KINDS, "workflow": WORKFLOWS, "risk": RISKS}
    errors += [
        f"{key} must be one of {', '.join(values)}"
        for key, values in choices.items()
        if key in case and case[key] not in values
    ]
    if "human_gate" in case and not isinstance(case["human_gate"], bool):
        errors.append("human_gate must be true or false")
    case_id = case.get("id")
    if isinstance(case_id, str) and not SLUG.match(case_id):
        errors.append("id must be a lowercase slug")
    if name is not None and case_id != name:
        errors.append(f"id {case_id!r} does not match the file name {name!r}")
    task = case.get("task")
    if case.get("workflow") == "product" and isinstance(task, str) and not FEATURE.match(task):
        errors.append("a product case names a PRD feature such as F01")
    if case.get("workflow") == "change" and isinstance(task, str) and not SLUG.match(task):
        errors.append("a change case names its change with a lowercase slug")
    if case.get("risk") == "high" and case.get("human_gate") is not True:
        errors.append("a high-risk case must expect the human gate")
    return errors


def load_case(path: Path) -> JSONDict:
    """A valid case, with ``human_gate`` and ``depends_on`` filled in."""
    try:
        case = parse(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CaseError(f"{path.name}: {exc}") from exc
    except CaseError as exc:
        raise CaseError(f"{path.name}: {exc}") from exc
    errors = problems(case, path.stem)
    if errors:
        raise CaseError(f"{path.name}: {'; '.join(errors)}")
    return {"human_gate": False, "depends_on": [], **case}


def load_cases(directory: Path) -> list[JSONDict]:
    """Every case in ``directory``, ordered by id; raises ``CaseError`` on the first invalid one."""
    cases = [load_case(path) for path in sorted(directory.glob("*.yaml"))]
    ids = {case["id"] for case in cases}
    for case in cases:
        missing = [name for name in case["depends_on"] if name not in ids]
        if missing:
            raise CaseError(f"{case['id']}.yaml: depends on unknown cases {', '.join(missing)}")
    return cases
