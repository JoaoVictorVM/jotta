from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from jotta.cli import main
from jotta.core.prd import feature_for, parse_prd, prd_excerpt
from jotta.core.risk import risk_for
from jotta.core.state import JSONDict
from jotta.evals.cases import CaseError, load_case, load_cases, parse, problems

REPO = Path(__file__).resolve().parents[1]
EVALS = REPO / "evals"
FIXTURE = EVALS / "fixtures" / "tasks-api"
IGNORED = shutil.ignore_patterns("__pycache__", ".pytest_cache")


@pytest.fixture(scope="module")
def cases() -> list[JSONDict]:
    return load_cases(EVALS / "cases")


def copy_fixture(target: Path) -> Path:
    shutil.copytree(FIXTURE, target, ignore=IGNORED)
    return target


def run_python(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args], cwd=project, capture_output=True, text=True, timeout=120, check=False
    )


def test_the_cases_cover_features_a_bug_a_refactor_and_a_risky_task(cases: list[JSONDict]) -> None:
    assert 5 <= len(cases) <= 10
    assert {case["kind"] for case in cases} == {"feature", "bug", "refactor"}
    assert [case["task"] for case in cases if case["risk"] == "high"] == ["F04"]
    assert all((EVALS / "fixtures" / case["fixture"]).is_dir() for case in cases)


def test_product_cases_match_the_fixture_prd(cases: list[JSONDict]) -> None:
    prd = FIXTURE / "PRD.md"
    features, errors = parse_prd(prd)
    assert errors == []
    by_task = {case["task"]: case for case in cases if case["workflow"] == "product"}
    assert sorted(by_task) == sorted(feature["id"] for feature in features)
    case_ids = {case["task"]: case["id"] for case in cases}
    for task, case in by_task.items():
        feature = feature_for(prd, task)
        assert feature is not None
        assert risk_for(prd_excerpt(prd, feature))["level"] == case["risk"], task
        assert sorted(case["depends_on"]) == sorted(case_ids[dep] for dep in feature["dependencies"]), task


def test_the_fixture_tests_pass_as_shipped(tmp_path: Path) -> None:
    project = copy_fixture(tmp_path / "tasks-api")
    result = run_python(project, "-m", "pytest", "-q", "-p", "no:cacheprovider")
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_reported_bug_reproduces_in_the_fixture(tmp_path: Path) -> None:
    project = copy_fixture(tmp_path / "tasks-api")
    script = """
from tasks_api.app import App
app = App()
for title in "abcde":
    app.handle("POST", "/tasks", body={"title": title})
app.handle("DELETE", "/tasks/2")
pages = [app.handle("GET", "/tasks", {"limit": "2", "offset": offset})[1]["items"] for offset in ("0", "2")]
print([[task["title"] for task in page] for page in pages])
"""
    result = run_python(project, "-c", f"import sys; sys.path.insert(0, 'src')\n{script}")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.replace("'", '"')) == [["a", "c"], ["c", "d"]]


def test_the_tasks_can_be_run_with_jotta_installed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = copy_fixture(tmp_path / "tasks-api")
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    assert main(["install", "--target", str(project)]) == 0
    shutil.copyfile(project / "PRD.md", project / ".planning" / "PRD.md")
    root = ["--root", str(project)]
    assert main([*root, "doctor"]) == 0
    assert main([*root, "validate-prd"]) == 0
    assert main([*root, "sync-tasks"]) == 0
    gates = json.loads((project / ".jotta" / "sensors" / "computational" / "gates.json").read_text(encoding="utf-8"))
    assert "python -m pytest -q" in gates["profiles"]["feature"]

    assert main([*root, "prepare", "F04"]) == 0
    packet = json.loads((project / ".jotta" / "runtime" / "context" / "f04-implementer.json").read_text("utf-8"))
    assert packet["risk"]["level"] == "high"
    assert packet["effective_profile"] == "strict"
    assert main([*root, "checkpoint", "--status", "completed"]) == 0
    assert main([*root, "prepare", "F05"]) == 1
    assert "F02" in capsys.readouterr().out
    assert main([*root, "prepare", "fix-pagination-offset", "--scope", "change"]) == 0
    packet = json.loads(
        (project / ".jotta" / "runtime" / "context" / "fix-pagination-offset-implementer.json").read_text("utf-8")
    )
    assert packet["effective_profile"] == "lean"


def test_load_case_fills_the_defaults(tmp_path: Path) -> None:
    path = tmp_path / "demo.yaml"
    path.write_text(
        "# a case\nid: demo\ntitle: 'Demo'\nfixture: tasks-api\nkind: bug\nworkflow: change\ntask: fix-demo\n"
        'risk: normal\nprompt: |\n  First line.\n\n    Indented.\nexpected:\n  - "It works."\n',
        encoding="utf-8",
    )
    case = load_case(path)
    assert case["title"] == "Demo"
    assert case["prompt"] == "First line.\n\n  Indented.\n"
    assert case["expected"] == ["It works."]
    assert case["human_gate"] is False
    assert case["depends_on"] == []


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("id: a\nid: b\n", "duplicate key"),
        ("not yaml\n", "expected 'key: value'"),
        ("expected:\nid: a\n", "has no value"),
    ],
)
def test_parse_rejects_what_it_cannot_read(text: str, message: str) -> None:
    with pytest.raises(CaseError, match=message):
        parse(text)


def test_problems_lists_every_schema_error() -> None:
    case: JSONDict = {
        "id": "Bad Id",
        "title": "",
        "fixture": "tasks-api",
        "kind": "chore",
        "workflow": "product",
        "task": "fix-it",
        "risk": "high",
        "prompt": "Do it.",
        "expected": "a string",
        "human_gate": "yes",
        "extra": 1,
    }
    errors = problems(case, "other")
    for expected in (
        "unknown key extra",
        "title must be a non-empty string",
        "expected must be a non-empty list",
        "kind must be one of feature, bug, refactor",
        "human_gate must be true or false",
        "id must be a lowercase slug",
        "does not match the file name",
        "a product case names a PRD feature",
        "a high-risk case must expect the human gate",
    ):
        assert any(expected in error for error in errors), expected
    change = {**case, "workflow": "change", "task": "Fix It"}
    assert "a change case names its change with a lowercase slug" in problems(change)
    assert problems({}) == [f"missing {key}" for key in ("id", "title", "fixture", "kind", "workflow", "task")] + [
        "missing risk",
        "missing prompt",
        "missing expected",
    ]


def test_load_cases_rejects_unknown_dependencies_and_bad_files(tmp_path: Path) -> None:
    good = (EVALS / "cases" / "tasks-api-f03-tags.yaml").read_text(encoding="utf-8")
    (tmp_path / "tasks-api-f03-tags.yaml").write_text(good, encoding="utf-8")
    with pytest.raises(CaseError, match="depends on unknown cases tasks-api-f01-status-filter"):
        load_cases(tmp_path)
    (tmp_path / "broken.yaml").write_text("id broken\n", encoding="utf-8")
    with pytest.raises(CaseError, match="broken.yaml"):
        load_cases(tmp_path)
    with pytest.raises(CaseError, match="missing.yaml"):
        load_case(tmp_path / "missing.yaml")
