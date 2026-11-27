"""Task storage: kept in memory and, when a path is given, saved to a JSON file after every change."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

Task = dict[str, Any]


class TaskStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.tasks: dict[int, Task] = {}
        self.next_id = 1
        if path is not None and path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            self.tasks = {int(task["id"]): task for task in data["tasks"]}
            self.next_id = int(data["next_id"])

    def all(self) -> list[Task]:
        return [dict(self.tasks[key]) for key in sorted(self.tasks)]

    def get(self, task_id: int) -> Task | None:
        task = self.tasks.get(task_id)
        return dict(task) if task is not None else None

    def add(self, fields: Task) -> Task:
        task = {"id": self.next_id, **fields}
        self.tasks[self.next_id] = task
        self.next_id += 1
        self.save()
        return dict(task)

    def update(self, task_id: int, fields: Task) -> Task | None:
        task = self.tasks.get(task_id)
        if task is None:
            return None
        task.update(fields)
        self.save()
        return dict(task)

    def delete(self, task_id: int) -> bool:
        if self.tasks.pop(task_id, None) is None:
            return False
        self.save()
        return True

    def save(self) -> None:
        if self.path is None:
            return
        data = {"next_id": self.next_id, "tasks": self.all()}
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
