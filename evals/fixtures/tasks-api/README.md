# Tasks API

A small JSON service for a personal to-do list, written with the Python standard library.

## Run

```bash
python -m pip install -e ".[dev]"
python -m pytest
PYTHONPATH=src python -m tasks_api --port 8000 --data tasks.json
```

## Routes

| Method | Path | Result |
|---|---|---|
| `GET` | `/health` | `{"status": "ok"}` |
| `GET` | `/tasks?limit=20&offset=0` | A page of tasks: `items`, `total`, `limit` and `offset` |
| `POST` | `/tasks` | Creates a task from `{"title": "...", "done": false}` |
| `GET` | `/tasks/<id>` | One task |
| `PATCH` | `/tasks/<id>` | Changes `title` or `done` |
| `DELETE` | `/tasks/<id>` | Deletes a task |

The next features are described in [PRD.md](./PRD.md).
