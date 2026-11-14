from __future__ import annotations

import json
from pathlib import Path

import pytest

from jotta.commands.tasks import sync_tasks
from jotta.core.paths import ProjectPaths
from jotta.core.prd import feature_folder, feature_for, parse_prd, prd_excerpt
from jotta.core.state import load_json, write_json_atomic


def write_prd(tmp_path: Path, rows: str, waves: str = "") -> Path:
    prd = tmp_path / "PRD.md"
    header = "| ID | Feature | Priority | Dependencies |\n|---|---|---|---|\n"
    prd.write_text(f"# PRD\n\n{header}{rows}\n{waves}", encoding="utf-8")
    return prd


def test_parses_features_dependencies_and_waves(project: Path) -> None:
    features, errors = parse_prd(ProjectPaths(project).prd)
    assert errors == []
    assert [(f["id"], f["priority"], f["dependencies"], f["wave"]) for f in features] == [
        ("F01", 1, [], 1),
        ("F02", 2, ["F01"], 2),
        ("F03", 3, [], 1),
    ]


def test_missing_prd_is_an_error(tmp_path: Path) -> None:
    features, errors = parse_prd(tmp_path / "PRD.md")
    assert features == []
    assert errors and errors[0].startswith("PRD absent")


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        ("| F01 | A | 1 | none |\n| F01 | B | 2 | none |", "duplicate F01"),
        ("| F01 | A | high | none |", "invalid priority in F01"),
        ("| F01 | A | 1 | F09 |", "F01: missing dependency F09"),
        ("| F01 | A |", "incomplete feature table row"),
    ],
)
def test_reports_table_problems(tmp_path: Path, rows: str, expected: str) -> None:
    _, errors = parse_prd(write_prd(tmp_path, rows))
    assert any(expected in error for error in errors), errors


def test_accepts_every_spelling_of_no_dependency(tmp_path: Path) -> None:
    rows = "| F01 | A | 1 | none |\n| F02 | B | 1 | nenhuma |\n| F03 | C | 1 | - |"
    features, errors = parse_prd(write_prd(tmp_path, rows))
    assert errors == []
    assert all(feature["dependencies"] == [] for feature in features)


@pytest.mark.parametrize(("reference", "expected"), [("F02", "F02"), ("lista de tarefas", "F02"), ("tela", "F03")])
def test_feature_lookup_by_id_or_name(project: Path, reference: str, expected: str) -> None:
    feature = feature_for(ProjectPaths(project).prd, reference)
    assert feature is not None
    assert feature["id"] == expected


def test_ambiguous_or_unknown_reference_finds_nothing(project: Path) -> None:
    prd = ProjectPaths(project).prd
    assert feature_for(prd, "missing") is None
    assert feature_for(prd, "a") is None


def test_feature_folder_requires_a_single_match(project: Path) -> None:
    paths = ProjectPaths(project)
    feature = feature_for(paths.prd, "F01")
    assert feature_folder(paths.planning, feature) is None
    (paths.planning / "features" / "F01-login").mkdir(parents=True)
    assert feature_folder(paths.planning, feature) == paths.planning / "features" / "F01-login"
    (paths.planning / "features" / "F01-other").mkdir()
    assert feature_folder(paths.planning, feature) is None


def test_excerpt_keeps_lines_around_the_feature(project: Path) -> None:
    paths = ProjectPaths(project)
    excerpt = prd_excerpt(paths.prd, feature_for(paths.prd, "F02"))
    assert "Lista de tarefas" in excerpt
    assert prd_excerpt(paths.prd, None) == ""


def test_sync_marks_features_ready_by_dependencies(project: Path) -> None:
    paths = ProjectPaths(project)
    assert sync_tasks(paths) == 0
    status = {task["id"]: task["status"] for task in load_json(paths.tasks)["tasks"]}
    assert status == {"F01": "ready", "F02": "pending", "F03": "ready"}


def test_sync_reconciles_existing_tasks_by_id(project: Path) -> None:
    paths = ProjectPaths(project)
    sync_tasks(paths)
    data = load_json(paths.tasks)
    for task in data["tasks"]:
        if task["id"] == "F01":
            task.update(status="merged", merge_sha="abc123", evidence=["ci green"])
    data["tasks"].reverse()
    write_json_atomic(paths.tasks, data)
    paths.prd.write_text(paths.prd.read_text(encoding="utf-8").replace("Login com OAuth", "Login"), encoding="utf-8")

    assert sync_tasks(paths) == 0
    tasks = {task["id"]: task for task in load_json(paths.tasks)["tasks"]}
    assert (tasks["F01"]["name"], tasks["F01"]["status"], tasks["F01"]["merge_sha"]) == ("Login", "merged", "abc123")
    assert tasks["F01"]["evidence"] == ["ci green"]
    assert tasks["F02"]["status"] == "pending"


def test_sync_refuses_an_invalid_prd(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    paths = ProjectPaths(project)
    paths.prd.write_text("# PRD\n", encoding="utf-8")
    assert sync_tasks(paths) == 1
    assert "no feature found" in capsys.readouterr().out
    assert not paths.tasks.exists()


def test_sync_records_the_prd_hash(project: Path) -> None:
    paths = ProjectPaths(project)
    sync_tasks(paths)
    assert json.loads(paths.tasks.read_text(encoding="utf-8"))["prd_hash"].startswith("sha256:")
