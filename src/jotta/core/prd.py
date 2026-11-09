"""Parse the PRD feature table and locate feature planning artifacts."""

from __future__ import annotations

import re
from pathlib import Path

from jotta.core.state import JSONDict

FEATURE_ROW = re.compile(r"^\|\s*F\d+\s*\|", re.I)
WAVE_LINE = re.compile(r"\*\*Wave\s+(\d+)\*\*\s*:\s*(.*)", re.I)
FEATURE_ID = re.compile(r"F\d+")
NO_DEPENDENCY = {"none", "nenhuma", "-"}


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


def prd_excerpt(prd: Path, feature: JSONDict | None) -> str:
    if not prd.exists() or not feature:
        return ""
    lines = prd.read_text(encoding="utf-8").splitlines()
    needles = [feature["id"].lower(), feature["name"].lower()]
    selected: set[int] = set()
    for index, line in enumerate(lines):
        lowered = line.lower()
        if any(needle and needle in lowered for needle in needles):
            selected.update(range(max(0, index - 2), min(len(lines), index + 4)))
    return "\n".join(lines[index] for index in sorted(selected))
