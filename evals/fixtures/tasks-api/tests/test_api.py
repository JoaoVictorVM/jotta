from __future__ import annotations

import json
from pathlib import Path

from tasks_api.app import App
from tasks_api.store import TaskStore


def create(app: App, title: str, done: bool = False) -> dict:
    status, task = app.handle("POST", "/tasks", body={"title": title, "done": done})
    assert status == 201
    return task


def test_health() -> None:
    assert App().handle("GET", "/health") == (200, {"status": "ok"})


def test_create_and_read_a_task() -> None:
    app = App()
    task = create(app, "  Write the report  ")
    assert task == {"id": 1, "title": "Write the report", "done": False}
    assert app.handle("GET", "/tasks/1") == (200, task)


def test_create_rejects_invalid_bodies() -> None:
    app = App()
    invalid = ({"title": " "}, {"title": "x" * 201}, {"title": "a", "done": "yes"}, {"title": "a", "x": 1})
    for body in (None, [], {}, *invalid):
        status, payload = app.handle("POST", "/tasks", body=body)
        assert status == 400, body
        assert "error" in payload
    assert app.handle("GET", "/tasks")[1]["total"] == 0


def test_update_a_task() -> None:
    app = App()
    create(app, "Write the report")
    status, task = app.handle("PATCH", "/tasks/1", body={"done": True, "title": "Send the report"})
    assert status == 200
    assert task == {"id": 1, "title": "Send the report", "done": True}
    assert app.handle("PATCH", "/tasks/1", body={"done": 1})[0] == 400
    assert app.handle("PATCH", "/tasks/9", body={"done": True})[0] == 404


def test_delete_a_task() -> None:
    app = App()
    create(app, "Write the report")
    assert app.handle("DELETE", "/tasks/1") == (204, None)
    assert app.handle("GET", "/tasks/1")[0] == 404
    assert app.handle("DELETE", "/tasks/1")[0] == 404


def test_list_tasks_in_order() -> None:
    app = App()
    for title in ("a", "b", "c"):
        create(app, title)
    status, page = app.handle("GET", "/tasks", {"limit": "2"})
    assert status == 200
    assert [task["title"] for task in page["items"]] == ["a", "b"]
    assert page["total"] == 3


def test_list_rejects_invalid_pagination() -> None:
    app = App()
    for query in ({"limit": "0"}, {"limit": "101"}, {"limit": "x"}, {"offset": "-1"}):
        assert app.handle("GET", "/tasks", query)[0] == 400, query


def test_unknown_routes() -> None:
    app = App()
    assert app.handle("GET", "/nope")[0] == 404
    assert app.handle("PUT", "/tasks")[0] == 405
    assert app.handle("PUT", "/tasks/1")[0] == 405


def test_tasks_survive_a_restart(tmp_path: Path) -> None:
    path = tmp_path / "tasks.json"
    app = App(TaskStore(path))
    create(app, "Write the report")
    create(app, "Send the report")
    app.handle("DELETE", "/tasks/1")
    restarted = App(TaskStore(path))
    assert [task["title"] for task in restarted.handle("GET", "/tasks")[1]["items"]] == ["Send the report"]
    assert create(restarted, "Archive the report")["id"] == 3
    assert json.loads(path.read_text(encoding="utf-8"))["next_id"] == 4
