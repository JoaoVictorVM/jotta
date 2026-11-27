"""The HTTP routes of the task API, as a plain function from a request to a status and a JSON body."""

from __future__ import annotations

import re
from typing import Any

from tasks_api.store import Task, TaskStore

MAX_TITLE = 200
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
TASK_PATH = re.compile(r"^/tasks/(\d+)$")

Response = tuple[int, Any]


def error(status: int, message: str) -> Response:
    return status, {"error": message}


class App:
    def __init__(self, store: TaskStore | None = None) -> None:
        self.store = store or TaskStore()

    def handle(
        self,
        method: str,
        path: str,
        query: dict[str, str] | None = None,
        body: Any = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        query = query or {}
        if path == "/health" and method == "GET":
            return 200, {"status": "ok"}
        if path == "/tasks":
            if method == "GET":
                return self.list_tasks(query)
            if method == "POST":
                return self.create_task(body)
            return error(405, "method not allowed")
        match = TASK_PATH.match(path)
        if match:
            task_id = int(match.group(1))
            if method == "GET":
                task = self.store.get(task_id)
                return (200, task) if task else error(404, "task not found")
            if method == "PATCH":
                return self.update_task(task_id, body)
            if method == "DELETE":
                return (204, None) if self.store.delete(task_id) else error(404, "task not found")
            return error(405, "method not allowed")
        return error(404, "not found")

    def list_tasks(self, query: dict[str, str]) -> Response:
        try:
            limit = int(query.get("limit", DEFAULT_LIMIT))
            offset = int(query.get("offset", 0))
        except ValueError:
            return error(400, "limit and offset must be integers")
        if not 1 <= limit <= MAX_LIMIT or offset < 0:
            return error(400, f"limit must be between 1 and {MAX_LIMIT} and offset must not be negative")
        tasks = self.store.all()
        page = [task for task in tasks if task["id"] > offset][:limit]
        return 200, {"items": page, "total": len(tasks), "limit": limit, "offset": offset}

    def create_task(self, body: Any) -> Response:
        if not isinstance(body, dict):
            return error(400, "body must be a JSON object")
        title = body.get("title")
        if not isinstance(title, str) or not title.strip():
            return error(400, "title is required")
        if len(title) > MAX_TITLE:
            return error(400, f"title must have at most {MAX_TITLE} characters")
        done = body.get("done", False)
        if not isinstance(done, bool):
            return error(400, "done must be a boolean")
        unknown = set(body) - {"title", "done"}
        if unknown:
            return error(400, f"unknown fields: {', '.join(sorted(unknown))}")
        task: Task = {"title": title.strip(), "done": done}
        return 201, self.store.add(task)

    def update_task(self, task_id: int, body: Any) -> Response:
        if self.store.get(task_id) is None:
            return error(404, "task not found")
        if not isinstance(body, dict):
            return error(400, "body must be a JSON object")
        fields: Task = {}
        if "title" in body:
            title = body["title"]
            if not isinstance(title, str) or not title.strip():
                return error(400, "title is required")
            if len(title) > MAX_TITLE:
                return error(400, f"title must have at most {MAX_TITLE} characters")
            fields["title"] = title.strip()
        if "done" in body:
            if not isinstance(body["done"], bool):
                return error(400, "done must be a boolean")
            fields["done"] = body["done"]
        unknown = set(body) - {"title", "done"}
        if unknown:
            return error(400, f"unknown fields: {', '.join(sorted(unknown))}")
        return 200, self.store.update(task_id, fields)
