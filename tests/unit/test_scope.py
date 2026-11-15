from __future__ import annotations

import pytest

from jotta.core.scope import enforcement_for, in_scope, normalize, paths_from_spec

SPEC = """# Spec

### Section 4: Component Overview

| File Path | New/Modified | Purpose | Key Responsibilities |
|---|---|---|---|
| `src/screens/Home.tsx` | New | Screen | Render |
| `src/api/` | Modified | Client | Calls |
| `./src/utils/format.ts:12` | Modified | Helper | Format |
| `src/screens/Home.tsx` | New | Duplicate | Ignored |

| Test File | Test Type | Target | Coverage Goal |
|---|---|---|---|
| `tests/home.test.tsx` | Unit | Home | 90% |

| Method | Path |
|---|---|
| `GET` | `/api/v1/home` |

The file `src/elsewhere.ts` is only mentioned in prose.
"""


def test_paths_come_from_the_first_column_of_spec_tables() -> None:
    assert paths_from_spec(SPEC) == ["src/screens/Home.tsx", "src/api/", "src/utils/format.ts", "tests/home.test.tsx"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("src/app.py", "src/app.py"),
        ("./src/app.py", "src/app.py"),
        ("src\\app.py", "src/app.py"),
        ("src/app/", "src/app/"),
        ("src/app.py:10:2", "src/app.py"),
        ("", ""),
    ],
)
def test_normalize(raw: str, expected: str) -> None:
    assert normalize(raw) == expected


@pytest.mark.parametrize(
    ("path", "covered"),
    [
        ("src/screens/Home.tsx", True),
        ("src/api/client.ts", True),
        ("src/api", False),
        ("src/screens/Other.tsx", False),
        ("src/application/x.ts", False),
        ("tests/unit/a_test.py", True),
        ("lib/b.py", True),
        ("lib/sub/c.py", True),
        ("docs/notes.md", True),
        (".planning/features/F01/progress.md", True),
        ("README.md", False),
    ],
)
def test_in_scope(path: str, covered: bool) -> None:
    allowed = ["src/screens/Home.tsx", "src/api/", "tests/unit/*_test.py", "lib", "docs/*.md"]
    assert in_scope(path, allowed) is covered


def test_enforcement_follows_the_profile() -> None:
    assert [enforcement_for(name) for name in ("strict", "lean", "manual-classic", None)] == [
        "block",
        "warn",
        "off",
        "off",
    ]
