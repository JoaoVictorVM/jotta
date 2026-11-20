"""Parse the PRD feature table and locate feature planning artifacts."""

from __future__ import annotations

import re
from pathlib import Path

from jotta.core.state import JSONDict

FEATURE_ROW = re.compile(r"^\|\s*F\d+\s*\|", re.I)
WAVE_LINE = re.compile(r"\*\*Wave\s+(\d+)\*\*\s*:\s*(.*)", re.I)
FEATURE_ID = re.compile(r"F\d+")
NO_DEPENDENCY = {"none", "nenhuma", "-"}
HEADING = re.compile(r"^(#{1,6})\s")
LIST_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s")
TABLE_SEPARATOR = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


def parse_prd(prd: Path) -> tuple[list[JSONDict], list[str]]:
    if not prd.exists():
        return [], [f"PRD absent: {prd}"]
    features: list[JSONDict] = []
    errors: list[str] = []
    seen: set[str] = set()
    lines = prd.read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, 1):
        if not FEATURE_ROW.match(line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            errors.append(f"line {line_number}: incomplete feature table row")
            continue
        feature_id = cells[0].upper()
        if feature_id in seen:
            errors.append(f"line {line_number}: duplicate {feature_id}")
            continue
        seen.add(feature_id)
        dependencies = [] if cells[3].lower() in NO_DEPENDENCY else FEATURE_ID.findall(cells[3].upper())
        priority: int | None
        try:
            priority = int(cells[2])
        except ValueError:
            priority = None
            errors.append(f"invalid priority in {feature_id}")
        features.append({"id": feature_id, "name": cells[1], "priority": priority, "dependencies": dependencies})
    ids = {item["id"] for item in features}
    for item in features:
        for dependency in item["dependencies"]:
            if dependency not in ids:
                errors.append(f"{item['id']}: missing dependency {dependency}")
    waves: dict[str, int] = {}
    for line in lines:
        match = WAVE_LINE.search(line)
        if match:
            for feature_id in FEATURE_ID.findall(match.group(2).upper()):
                waves[feature_id] = int(match.group(1))
    for item in features:
        item["wave"] = waves.get(item["id"])
    return features, errors


def feature_for(prd: Path, reference: str) -> JSONDict | None:
    features, _ = parse_prd(prd)
    normalized = reference.strip().lower()
    for feature in features:
        if normalized in (feature["id"].lower(), feature["name"].lower()):
            return feature
    candidates = [feature for feature in features if normalized in feature["name"].lower()]
    return candidates[0] if len(candidates) == 1 else None


def feature_folder(planning: Path, feature: JSONDict | None) -> Path | None:
    if not feature:
        return None
    features_dir = planning / "features"
    matches = list(features_dir.glob(f"{feature['id']}-*")) if features_dir.exists() else []
    return matches[0] if len(matches) == 1 else None


def is_table(line: str) -> bool:
    return line.lstrip().startswith("|")


def table_row(lines: list[str], index: int) -> set[int]:
    """The matching row plus the header and separator of its table, never the other rows."""
    top = index
    while top > 0 and is_table(lines[top - 1]):
        top -= 1
    selected = {top, index}
    if top + 1 < len(lines) and TABLE_SEPARATOR.match(lines[top + 1]):
        selected.add(top + 1)
    return selected


def section(lines: list[str], index: int, level: int) -> set[int]:
    """A heading and everything until the next heading of the same or a higher level."""
    end = index + 1
    while end < len(lines):
        match = HEADING.match(lines[end])
        if match and len(match.group(1)) <= level:
            break
        end += 1
    return set(range(index, end))


def list_item(lines: list[str], index: int) -> set[int]:
    """A list item and its indented continuation lines, without the sibling items."""
    indent = len(lines[index]) - len(lines[index].lstrip())
    end = index + 1
    while end < len(lines):
        line = lines[end]
        if not line.strip() or len(line) - len(line.lstrip()) <= indent:
            break
        end += 1
    return set(range(index, end))


def paragraph(lines: list[str], index: int) -> set[int]:
    """The prose lines around ``index`` up to a blank line, heading, list item or table."""

    def prose(line: str) -> bool:
        return bool(line.strip()) and not (HEADING.match(line) or LIST_ITEM.match(line) or is_table(line))

    start, end = index, index + 1
    while start > 0 and prose(lines[start - 1]):
        start -= 1
    while end < len(lines) and prose(lines[end]):
        end += 1
    return set(range(start, end))


def prd_excerpt(prd: Path, feature: JSONDict | None) -> str:
    """The PRD lines about one feature: its table row, its own section, list items and paragraphs naming it.

    Lines about other features are left out, so their text neither enters the context packet nor the risk check.
    """
    if not prd.exists() or not feature:
        return ""
    lines = prd.read_text(encoding="utf-8").splitlines()
    needles = [rf"(?<![A-Za-z0-9]){re.escape(feature['id'])}(?!\d)"]
    if feature.get("name"):
        needles.append(rf"(?<!\w){re.escape(str(feature['name']))}(?!\w)")
    mention = re.compile("|".join(needles), re.I)
    selected: set[int] = set()
    for index, line in enumerate(lines):
        if not mention.search(line):
            continue
        heading = HEADING.match(line)
        if is_table(line):
            # A row belongs to the feature named in its first cell; a mention in another cell, such as a
            # dependency, belongs to another feature's row.
            if mention.search(line.strip().strip("|").split("|")[0]):
                selected |= table_row(lines, index)
        elif heading:
            selected |= section(lines, index, len(heading.group(1)))
        elif LIST_ITEM.match(line):
            selected |= list_item(lines, index)
        else:
            selected |= paragraph(lines, index)
    return "\n".join(lines[index] for index in sorted(selected))
