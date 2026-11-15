from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from jotta.cli import main
from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict
from jotta.quality.detect import detect, suggest

NODE_SCRIPTS = {"lint": "eslint .", "typecheck": "tsc --noEmit", "test": "vitest run", "build": "vite build"}
PYPROJECT = """[project]
name = "app"

[dependency-groups]
dev = ["pytest>=8", "mypy>=1.10"]

[tool.ruff]
line-length = 100
"""


def write(root: Path, files: dict[str, str]) -> Path:
    for name, content in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(content, encoding="utf-8")
    return root


def package(**fields: object) -> str:
    return json.dumps({"name": "app", **fields})


def gates(project: Path) -> JSONDict:
    data: JSONDict = json.loads(
        (project / ".jotta" / "sensors" / "computational" / "gates.json").read_text(encoding="utf-8")
    )
    return data


def set_profiles(project: Path, **profiles: list[str]) -> None:
    path = project / ".jotta" / "sensors" / "computational" / "gates.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["profiles"].update(profiles)
    path.write_text(json.dumps(data), encoding="utf-8")


def detect_stack(project: Path, capsys: pytest.CaptureFixture[str], *extra: str) -> JSONDict:
    assert main(["--root", str(project), "detect-stack", *extra]) == 0
    data: JSONDict = json.loads(capsys.readouterr().out)
    return data


def test_node_with_npm_uses_the_package_scripts(tmp_path: Path) -> None:
    write(tmp_path, {"package.json": package(scripts=NODE_SCRIPTS), "package-lock.json": "{}"})
    [stack] = detect(tmp_path)
    assert (stack.name, stack.manager) == ("node", "npm")
    assert stack.profiles == {
        "smoke": ["npm run lint", "npm run typecheck"],
        "feature": ["npm run lint", "npm run typecheck", "npm test"],
        "full": ["npm run lint", "npm run typecheck", "npm test", "npm run build"],
    }


@pytest.mark.parametrize(
    ("files", "manager", "lint", "test"),
    [
        ({"pnpm-lock.yaml": ""}, "pnpm", "pnpm run lint", "pnpm test"),
        ({"yarn.lock": ""}, "yarn", "yarn lint", "yarn test"),
        ({}, "npm", "npm run lint", "npm test"),
    ],
)
def test_node_manager_comes_from_the_lock_file(
    tmp_path: Path, files: dict[str, str], manager: str, lint: str, test: str
) -> None:
    write(tmp_path, {"package.json": package(scripts={"lint": "eslint .", "test": "jest"}), **files})
    [stack] = detect(tmp_path)
    assert stack.manager == manager
    assert stack.profiles["feature"] == [lint, test]


def test_the_package_manager_field_wins_over_lock_files(tmp_path: Path) -> None:
    write(tmp_path, {"package.json": package(packageManager="pnpm@9.1.0"), "yarn.lock": ""})
    assert detect(tmp_path)[0].manager == "pnpm"


def test_typescript_without_a_typecheck_script_runs_tsc(tmp_path: Path) -> None:
    manifest = package(
        devDependencies={"typescript": "^5"}, scripts={"test": 'echo "Error: no test specified" && exit 1'}
    )
    write(tmp_path, {"package.json": manifest, "tsconfig.json": "{}", "pnpm-lock.yaml": ""})
    [stack] = detect(tmp_path)
    assert stack.profiles["smoke"] == ["pnpm exec tsc --noEmit"]
    assert stack.profiles["feature"] == ["pnpm exec tsc --noEmit"], "the npm placeholder test is not a test"


def test_python_with_uv_uses_the_configured_tools(tmp_path: Path) -> None:
    write(tmp_path, {"pyproject.toml": PYPROJECT, "uv.lock": ""})
    [stack] = detect(tmp_path)
    assert (stack.name, stack.manager) == ("python", "uv")
    assert stack.profiles == {
        "smoke": ["uv run ruff check .", "uv run mypy ."],
        "feature": ["uv run ruff check .", "uv run mypy .", "uv run pytest -q"],
        "full": ["uv run ruff check .", "uv run mypy .", "uv run pytest -q", "uv run ruff format --check ."],
    }


def test_python_with_poetry(tmp_path: Path) -> None:
    write(tmp_path, {"pyproject.toml": '[tool.poetry]\nname = "app"\n\n[tool.pytest.ini_options]\n', "poetry.lock": ""})
    [stack] = detect(tmp_path)
    assert stack.manager == "poetry"
    assert stack.profiles["feature"][-1] == "poetry run pytest -q"


def test_python_with_pip_and_no_tools_falls_back_to_compileall(tmp_path: Path) -> None:
    write(tmp_path, {"requirements.txt": "requests==2.32.0\npytest-ruffish==1.0\n"})
    [stack] = detect(tmp_path)
    assert stack.manager == "pip"
    assert stack.profiles["smoke"][0].startswith("python -m compileall -q -x")
    assert stack.profiles["feature"] == stack.profiles["smoke"], "pytest-ruffish is neither pytest nor ruff"


def test_python_with_pip_runs_tools_as_modules(tmp_path: Path) -> None:
    write(tmp_path, {"requirements-dev.txt": "ruff\npytest\n", "setup.py": ""})
    assert detect(tmp_path)[0].profiles["full"] == [
        "python -m ruff check .",
        "python -m pytest -q",
        "python -m ruff format --check .",
    ]


def test_go_and_rust(tmp_path: Path) -> None:
    write(tmp_path, {"go.mod": "module app\n", "Cargo.toml": "[package]\n"})
    stacks = detect(tmp_path)
    assert [(stack.name, stack.manager) for stack in stacks] == [("go", "go"), ("rust", "cargo")]
    assert stacks[0].profiles["feature"] == ["go vet ./...", "go test ./..."]
    assert stacks[1].profiles["smoke"] == ["cargo check --all-targets"]
    assert suggest(stacks)["smoke"] == ["go vet ./...", "cargo check --all-targets"]


def test_nothing_is_detected_in_an_empty_project(tmp_path: Path) -> None:
    assert detect(tmp_path) == []
    assert suggest([]) == {"smoke": [], "feature": [], "full": []}


def test_a_broken_package_json_still_counts_as_node(tmp_path: Path) -> None:
    write(tmp_path, {"package.json": "{not json"})
    [stack] = detect(tmp_path)
    assert stack.profiles == {"smoke": [], "feature": [], "full": []}


def test_detection_fills_only_the_free_profiles(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(project, {"go.mod": "module app\n"})
    set_profiles(project, feature=["make check"])
    result = detect_stack(project, capsys)
    assert (result["filled"], result["kept"]) == (["smoke", "full"], ["feature"])
    data = gates(project)
    assert data["profiles"] == {
        "smoke": ["go vet ./..."],
        "feature": ["make check"],
        "full": ["go vet ./...", "go test ./...", "go build ./..."],
    }
    assert data["detected"]["stacks"] == [{"name": "go", "manager": "go", "evidence": ["go.mod"]}]
    assert data["post_edit"]["profile"] == "smoke", "other sections are kept"


def test_an_untouched_suggestion_follows_the_project(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(project, {"package.json": package(scripts={"test": "jest"})})
    detect_stack(project, capsys)
    assert gates(project)["profiles"]["smoke"] == []
    write(project, {"package.json": package(scripts={"test": "jest", "lint": "eslint ."})})
    result = detect_stack(project, capsys)
    assert result["filled"] == ["smoke", "feature", "full"]
    assert gates(project)["profiles"]["feature"] == ["npm run lint", "npm test"]


def test_an_edited_suggestion_is_never_overwritten(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(project, {"go.mod": "module app\n"})
    detect_stack(project, capsys)
    set_profiles(project, smoke=["go vet ./...", "staticcheck ./..."])
    write(project, {"Cargo.toml": "[package]\n"})
    result = detect_stack(project, capsys)
    assert "smoke" in result["kept"]
    assert gates(project)["profiles"]["smoke"] == ["go vet ./...", "staticcheck ./..."]


def test_dry_run_writes_nothing(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(project, {"go.mod": "module app\n"})
    result = detect_stack(project, capsys, "--dry-run")
    assert (result["status"], result["filled"]) == ("dry-run", ["smoke", "feature", "full"])
    assert result["profiles"]["smoke"] == ["go vet ./..."]
    assert "detected" not in gates(project)


def test_doctor_reports_the_quality_profiles(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--root", str(project), "doctor"]) == 0
    assert "quality profiles smoke, feature, full have no commands" in capsys.readouterr().out
    write(project, {"go.mod": "module app\n"})
    assert main(["--root", str(project), "doctor"]) == 0
    assert "can be filled for go (go); run `jotta detect-stack`" in capsys.readouterr().out
    detect_stack(project, capsys)
    assert main(["--root", str(project), "doctor"]) == 0
    assert "quality profiles" not in capsys.readouterr().out


@pytest.mark.parametrize(
    ("files", "stack"),
    [
        ({"package.json": package(scripts=NODE_SCRIPTS), "package-lock.json": "{}"}, "node"),
        ({"pyproject.toml": PYPROJECT, "uv.lock": ""}, "python"),
    ],
)
def test_install_fills_the_three_profiles(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], files: dict[str, str], stack: str
) -> None:
    project = write(tmp_path / "project", files)
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    assert main(["install", "--target", str(project)]) == 0
    quality = json.loads(capsys.readouterr().out)["quality"]
    assert quality["stacks"][0]["name"] == stack
    assert quality["filled"] == ["smoke", "feature", "full"]
    profiles = gates(project)["profiles"]
    assert all(profiles[name] for name in ("smoke", "feature", "full"))
    assert ProjectPaths(project).gates.is_file()
