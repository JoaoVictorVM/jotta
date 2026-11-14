"""End-to-end checks of ``jotta install`` through the installed console script."""

from __future__ import annotations

import filecmp
import json
import os
import shutil
import subprocess
import sysconfig
from pathlib import Path

import pytest

from jotta.core.paths import templates_root
from jotta.install.installer import LOCAL_DIRECTORIES, template_files


def find_executable() -> str | None:
    name = "jotta.exe" if os.name == "nt" else "jotta"
    candidate = Path(sysconfig.get_path("scripts")) / name
    return str(candidate) if candidate.is_file() else shutil.which("jotta")


JOTTA = find_executable()
pytestmark = pytest.mark.skipif(JOTTA is None, reason="the jotta console script is not installed")


def jotta(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    assert JOTTA is not None
    return subprocess.run([JOTTA, *args], cwd=cwd, text=True, capture_output=True, check=False)


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=True)
    return result.stdout


def git_repository(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q")
    return path


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def assert_installed_tree(project: Path) -> None:
    templates = templates_root()
    expected = template_files(templates)
    for relative in expected:
        assert filecmp.cmp(templates / relative, project / relative, shallow=False), relative
    for directory in LOCAL_DIRECTORIES:
        assert (project / directory).is_dir(), directory
    assert (project / ".jotta" / ".gitignore").is_file()
    assert not any((project / ".jotta" / "runtime").rglob("*.*")), "runtime must start empty"
    installed = {path.relative_to(project) for path in project.rglob("*") if path.is_file()}
    assert installed - {Path(".git")} >= set(expected)


def test_install_into_a_git_repository_hides_the_harness_and_runs(tmp_path: Path) -> None:
    project = git_repository(tmp_path / "project")
    (project / "app.py").write_text("print('app')\n", encoding="utf-8")

    result = jotta("install", "--target", str(project))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "installed"
    assert_installed_tree(project)
    assert git(project, "status", "--porcelain", "--untracked-files=all").splitlines() == ["?? app.py"]

    for command in (["doctor"], ["models", "validate"], ["validate-prd"], ["sync-tasks"], ["budget", "status"]):
        run = jotta(*command, cwd=project / ".jotta")
        assert run.returncode == 0, (command, run.stdout, run.stderr)
    status = jotta("status", cwd=project)
    assert json.loads(status.stdout)["run"]["status"] == "idle"


def test_install_without_git_creates_the_target(tmp_path: Path) -> None:
    project = tmp_path / "new" / "project"
    result = jotta("install", "--target", str(project))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["git_exclude"] is None
    assert_installed_tree(project)
    assert not (project / ".git").exists()
    assert jotta("doctor", cwd=project).returncode == 0


def test_install_from_the_working_directory(tmp_path: Path) -> None:
    project = git_repository(tmp_path / "project")
    result = jotta("install", cwd=project)
    assert result.returncode == 0, result.stderr
    assert_installed_tree(project)


def test_install_into_a_subdirectory_of_a_repository_hides_the_harness(tmp_path: Path) -> None:
    repository = git_repository(tmp_path / "repository")
    project = repository / "services" / "api"
    result = jotta("install", "--target", str(project))
    assert result.returncode == 0, result.stderr
    assert_installed_tree(project)
    assert git(repository, "status", "--porcelain", "--untracked-files=all") == ""


def test_second_install_is_refused_and_changes_nothing(tmp_path: Path) -> None:
    project = git_repository(tmp_path / "project")
    assert jotta("install", "--target", str(project)).returncode == 0
    (project / "AGENTS.md").write_text("customized\n", encoding="utf-8")
    before = snapshot(project)

    result = jotta("install", "--target", str(project))
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report["status"] == "conflict"
    assert len(report["conflicts"]) == len(template_files(templates_root()))
    assert snapshot(project) == before


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    project = git_repository(tmp_path / "project")
    before = snapshot(project)
    result = jotta("install", "--target", str(project), "--dry-run")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "dry-run"
    assert snapshot(project) == before
    assert not (project / ".jotta").exists()


def test_force_overwrite_without_a_terminal_is_cancelled(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "CLAUDE.md").write_text("mine\n", encoding="utf-8")
    result = jotta("install", "--target", str(project), "--force-overwrite")
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "cancelled"
    assert (project / "CLAUDE.md").read_text(encoding="utf-8") == "mine\n"
