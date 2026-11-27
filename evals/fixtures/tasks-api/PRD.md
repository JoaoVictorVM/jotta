# Tasks API: Product Requirements Document

## Overview

Tasks API is a small JSON service for a personal to-do list. It already creates, reads, updates, deletes and lists tasks with `limit` and `offset` pagination, and it can keep the tasks in a JSON file between restarts. This document describes the next features.

Every response is JSON, every error has the shape `{"error": "<message>"}`, and invalid input returns status 400 without changing any task.

## Features

### F01: Filter by status

`GET /tasks?done=true` lists only completed tasks and `GET /tasks?done=false` only open ones. Any other value of `done` returns 400. The filter combines with pagination, and `total` counts the filtered tasks.

### F02: Due dates

A task may have a `due` date in the `YYYY-MM-DD` format, set on creation or update and removed by sending `null`. An invalid date returns 400. `GET /tasks/overdue` lists the open tasks whose due date is before today, ordered by due date and then by id. The service reads today's date from a clock that tests can replace.

### F03: Tags

A task may have `tags`: a list of up to 10 distinct lowercase words of 1 to 30 letters, digits or hyphens. Tags are normalized to lowercase. `GET /tasks?tag=<tag>` lists the tasks that have that tag, and combines with the `done` filter and with pagination.

### F04: Token authentication for changes

Creating, updating and deleting tasks requires authentication: the request must send the token from the `TASKS_API_TOKEN` environment variable in the `Authorization` header, with the `Bearer` scheme. A missing or wrong token returns 401 and changes nothing. When the variable is not set, every change is refused. Reading tasks and `GET /health` stay open. The token is compared in constant time and never appears in responses or logs.

### F05: Statistics

`GET /tasks/stats` returns the number of tasks in total, completed, open and overdue, as `{"total": 0, "done": 0, "open": 0, "overdue": 0}`. Overdue follows the rule of F02.

## Dependency Graph

| # | Feature | Priority | Dependencies |
|---|---|---|---|
| F01 | Filter by status | 1 | None |
| F02 | Due dates | 1 | None |
| F03 | Tags | 2 | F01 |
| F04 | Token authentication for changes | 1 | None |
| F05 | Statistics | 3 | F02 |

## Execution Waves

- **Wave 1**: F01, F02, F04
- **Wave 2**: F03, F05

## Out of scope

User accounts, sharing tasks between people, and any storage other than memory and the JSON file.
