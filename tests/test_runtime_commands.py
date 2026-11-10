from __future__ import annotations

import json
from pathlib import Path

import pytest

from jotta.cli import main
from jotta.core.paths import ProjectNotFoundError, find_root, templates_root


def run_json(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, dict[str, object]]:
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_find_root_walks_up_from_a_nested_directory(project: Path) -> None:
    nested = project / "src" / "deep"
    nested.mkdir(parents=True)
    assert find_root(nested) == project.resolve()


def test_find_root_fails_outside_a_project(tmp_path: Path) -> None:
    with pytest.raises(ProjectNotFoundError):
        find_root(tmp_path)


def test_packaged_templates_are_a_valid_project(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--root", str(templates_root()), "doctor"]) == 0
    assert "DOCTOR OK" in capsys.readouterr().out


def test_doctor_accepts_the_template(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--root", str(project), "doctor"]) == 0
    assert "DOCTOR OK" in capsys.readouterr().out


def test_root_is_discovered_from_the_working_directory(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(project / ".planning")
    assert main(["validate-prd"]) == 0
    assert "PRD OK: 3 features" in capsys.readouterr().out


def test_lifecycle_from_sync_to_finish(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = str(project)
    assert main(["--root", root, "sync-tasks"]) == 0
    capsys.readouterr()

    code, blocked = run_json(capsys, "--root", root, "prepare", "F02")
    assert code == 1
    assert blocked["missing_dependencies"] == ["F01"]

    code, prepared = run_json(capsys, "--root", root, "prepare", "F01")
    assert code == 0
    assert prepared["profile"] == "strict", "a high-risk lean task must be elevated to strict"
    packet = json.loads((project / str(prepared["context_packet"])).read_text(encoding="utf-8"))
    assert packet["effective_profile"] == "strict"

    code, checkpoint = run_json(
        capsys, "--root", root, "checkpoint", "--evidence", "ok", "--stage", "implementation", "--input-tokens", "10"
    )
    assert code == 0
    assert checkpoint["task_status"] == "completed"

    code, finished = run_json(capsys, "--root", root, "finish", "--status", "completed-local", "--evidence", "done")
    assert code == 0
    tasks = json.loads((project / ".jotta" / "runtime" / "state" / "tasks.json").read_text(encoding="utf-8"))
    statuses = {task["id"]: task["status"] for task in tasks["tasks"]}
    assert statuses["F01"] == "completed-local"
    usage = json.loads((project / ".jotta" / "runtime" / "state" / "usage.json").read_text(encoding="utf-8"))
    assert usage["by_stage"]["implementation"]["input_tokens"] == 10


def test_budget_gate_blocks_prepare_above_the_human_gate(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = str(project)
    assert main(["--root", root, "budget", "record", "--provider-usage-percent", "90"]) == 0
    capsys.readouterr()
    code, blocked = run_json(capsys, "--root", root, "prepare", "F03")
    assert code == 2
    assert blocked["status"] == "blocked"


def test_models_resolve_inherits_when_no_model_is_configured(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, route = run_json(capsys, "--root", str(project), "models", "resolve", "--task", "final-qa")
    assert code == 0
    assert route["status"] == "inherit"


def test_quality_skips_an_empty_profile(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, receipt = run_json(capsys, "--root", str(project), "quality", "smoke")
    assert code == 0
    assert receipt["status"] == "skipped"


@pytest.mark.parametrize(
    ("message", "expected"),
    [("feat(cli): adiciona comando", 0), ("Feat: invalid", 1), ("feat(cli): adiciona comando \u2014 claude", 1)],
)
def test_commit_gate_does_not_need_a_project(
    message: str, expected: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["gate", "commit", "--message", message]) == expected


def test_a_fresh_project_starts_without_state_files(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = project / ".jotta" / "runtime" / "state"
    assert not state.exists()
    code, status = run_json(capsys, "--root", str(project), "status")
    assert code == 0
    assert status["run"]["status"] == "idle"
    code, budget = run_json(capsys, "--root", str(project), "budget", "status")
    assert code == 0
    assert budget["status"] == "continue"
    assert main(["--root", str(project), "progress"]) == 0
    assert (state / "progress.md").is_file()


def test_runtime_is_ignored_inside_the_installed_harness() -> None:
    ignore = templates_root() / ".jotta" / ".gitignore"
    assert "runtime/" in ignore.read_text(encoding="utf-8").splitlines()
