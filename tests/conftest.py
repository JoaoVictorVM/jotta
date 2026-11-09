from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

PRD = """# PRD

| ID | Feature | Priority | Dependencies |
|---|---|---|---|
| F01 | Login com OAuth | 1 | none |
| F02 | Lista de tarefas | 2 | F01 |
| F03 | Tela inicial | 3 | - |

**Wave 1**: F01, F03
**Wave 2**: F02
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A consumer project with the harness template and a small PRD."""
    root = tmp_path / "project"
    root.mkdir()
    shutil.copytree(REPO / ".harness", root / ".harness", ignore=shutil.ignore_patterns("runtime", "__pycache__"))
    shutil.copytree(REPO / ".planning", root / ".planning")
    shutil.copy(REPO / "AGENTS.md", root / "AGENTS.md")
    (root / ".planning" / "PRD.md").write_text(PRD, encoding="utf-8")
    return root
