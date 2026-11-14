from __future__ import annotations

import argparse
import io
import json
import subprocess
from pathlib import Path

import pytest

from jotta.cli import main
from jotta.commands import install
from jotta.core.paths import templates_root
from jotta.core.state import JSONDict
from jotta.install.installer import GIT_EXCLUDES, template_files

REPO = Path(__file__).resolve().parents[1]


def git_init(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def output(capsys: pytest.CaptureFixture[str]) -> JSONDict:
    data: JSONDict = json.loads(capsys.readouterr().out)
    return data


def exclude_lines(project: Path) -> list[str]:
    return (project / ".git" / "info" / "exclude").read_text(encoding="utf-8").splitlines()


def test_install_copies_every_template_file_and_passes_doctor(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = git_init(tmp_path / "project")
    assert main(["install", "--target", str(project)]) == 0
    result = output(capsys)
    assert result["status"] == "installed"
    for relative in template_files(templates_root()):
        assert (project / relative).is_file(), relative
    assert (project / ".planning" / "features").is_dir()
    assert (project / ".jotta" / "runtime" / "state").is_dir()
    assert all(entry in exclude_lines(project) for entry in GIT_EXCLUDES)
    assert main(["--root", str(project), "doctor"]) == 0


def test_install_defaults_to_the_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    assert main(["install"]) == 0
    assert output(capsys)["git_exclude"] is None, "a project without Git has no exclude file"
    assert (project / ".jotta" / "config.yaml").is_file()


def test_install_does_not_repeat_git_exclusions(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = git_init(tmp_path / "project")
    assert main(["install", "--target", str(project)]) == 0
    assert main(["install", "--target", str(project), "--force-overwrite", "--yes"]) == 0
    capsys.readouterr()
    lines = exclude_lines(project)
    assert all(lines.count(entry) == 1 for entry in GIT_EXCLUDES)


def test_no_git_exclude_leaves_the_exclude_file_untouched(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = git_init(tmp_path / "project")
    before = exclude_lines(project)
    assert main(["install", "--target", str(project), "--no-git-exclude"]) == 0
    assert output(capsys)["git_exclude"] is None
    assert exclude_lines(project) == before


def test_conflicts_block_the_installation_without_writing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "AGENTS.md").write_text("mine\n", encoding="utf-8")
    assert main(["install", "--target", str(project)]) == 2
    result = output(capsys)
    assert result["status"] == "conflict"
    assert result["conflicts"] == ["AGENTS.md"]
    assert not (project / ".jotta").exists()
    assert (project / "AGENTS.md").read_text(encoding="utf-8") == "mine\n"


def test_dry_run_reports_without_writing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = git_init(tmp_path / "project")
    assert main(["install", "--target", str(project), "--dry-run"]) == 0
    result = output(capsys)
    assert result["status"] == "dry-run"
    assert result["files"] == len(template_files(templates_root()))
    assert result["git_exclude_entries"] == list(GIT_EXCLUDES)
    assert not (project / ".jotta").exists()
    assert "/.jotta/" not in exclude_lines(project)


def test_force_overwrite_with_yes_replaces_conflicting_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "AGENTS.md").write_text("mine\n", encoding="utf-8")
    assert main(["install", "--target", str(project), "--force-overwrite", "--yes"]) == 0
    assert output(capsys)["overwritten"] == ["AGENTS.md"]
    expected = (templates_root() / "AGENTS.md").read_text(encoding="utf-8")
    assert (project / "AGENTS.md").read_text(encoding="utf-8") == expected


@pytest.mark.parametrize(("answer", "code"), [(True, 0), (False, 2)])
def test_force_overwrite_asks_for_confirmation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], answer: bool, code: int
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "AGENTS.md").write_text("mine\n", encoding="utf-8")
    questions: list[str] = []

    def confirm(question: str) -> bool:
        questions.append(question)
        return answer

    args = argparse.Namespace(target=str(project), dry_run=False, force_overwrite=True, yes=False, no_git_exclude=False)
    assert install.run(args, confirm=confirm) == code
    assert len(questions) == 1
    capsys.readouterr()
    changed = (project / "AGENTS.md").read_text(encoding="utf-8") != "mine\n"
    assert changed is answer


def test_force_overwrite_without_a_terminal_is_cancelled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "AGENTS.md").write_text("mine\n", encoding="utf-8")
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert main(["install", "--target", str(project), "--force-overwrite"]) == 2
    assert output(capsys)["status"] == "cancelled"


@pytest.mark.parametrize("target", [REPO, templates_root(), templates_root() / ".jotta"])
def test_install_refuses_the_source_repository_and_the_templates(
    target: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["install", "--target", str(target), "--dry-run"]) == 2
    assert output(capsys)["status"] == "refused"


def test_install_in_a_subdirectory_anchors_exclusions_to_it(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repository = git_init(tmp_path / "repository")
    project = repository / "services" / "api"
    assert main(["install", "--target", str(project)]) == 0
    capsys.readouterr()
    lines = exclude_lines(repository)
    assert "/services/api/.jotta/" in lines
    assert "/.jotta/" not in lines


def test_confirmation_at_end_of_input_is_a_no(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "AGENTS.md").write_text("mine\n", encoding="utf-8")
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    assert main(["install", "--target", str(project), "--force-overwrite"]) == 2
    assert output(capsys)["status"] == "cancelled"
    assert (project / "AGENTS.md").read_text(encoding="utf-8") == "mine\n"
