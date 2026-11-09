"""JSON state helpers with atomic writes."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

JSONDict = dict[str, Any]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: JSONDict | None = None) -> JSONDict:
    if not path.exists() and default is not None:
        return default
    data: JSONDict = json.loads(path.read_text(encoding="utf-8"))
    return data


def write_json_atomic(path: Path, data: JSONDict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def print_json(data: JSONDict, indent: int | None = 2) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=indent))
