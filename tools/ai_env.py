#!/usr/bin/env python3
"""A dependency-free local project and task workbench."""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = Path(".ai-environment/workbench.sqlite3")
STATUSES = ("todo", "in_progress", "blocked", "done")
TRANSITIONS = {
    "todo": {"in_progress", "blocked"},
    "in_progress": {"todo", "blocked", "done"},
    "blocked": {"todo", "in_progress"},
    "done": {"in_progress"},
}

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    objective TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(id),
    title TEXT NOT NULL,
    acceptance TEXT NOT NULL,
    owner TEXT NOT NULL DEFAULT 'unassigned',
    status TEXT NOT NULL DEFAULT 'todo'
        CHECK (status IN ('todo','in_progress','blocked','done')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS tasks_project_status ON tasks(project_id, status, id);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(id),
    task_id INTEGER REFERENCES tasks(id),
    at TEXT NOT NULL,
    kind TEXT NOT NULL,
    detail TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.executescript(SCHEMA)
    try:
        db_path.chmod(0o600)
    except OSError:
        pass
    return connection


def project_id(name: str) -> str:
    slug = re.sub(r"[^\w]+", "-", name.strip().lower(), flags=re.UNICODE).strip("-_")
    if not slug:
        raise ValueError("project name must contain letters or numbers")
    return slug[:80]


def add_project(db: sqlite3.Connection, name: str, objective: str) -> str:
    name, objective = name.strip(), objective.strip()
    if not name or not objective:
        raise ValueError("project name and objective must not be empty")
    slug = project_id(name)
    with db:
        db.execute(
            "INSERT INTO projects(id,name,objective,created_at) VALUES(?,?,?,?)",
            (slug, name, objective, now()),
        )
        db.execute(
            "INSERT INTO events(project_id,at,kind,detail) VALUES(?,?,?,?)",
            (slug, now(), "project_created", name),
        )
    return slug


def project_or_error(db: sqlite3.Connection, slug: str) -> sqlite3.Row:
    row = db.execute("SELECT * FROM projects WHERE id=?", (slug,)).fetchone()
    if row is None:
        raise ValueError(f"unknown project: {slug}")
    return row


def add_task(
    db: sqlite3.Connection, slug: str, title: str, acceptance: str, owner: str
) -> int:
    project_or_error(db, slug)
    title, acceptance, owner = title.strip(), acceptance.strip(), owner.strip()
    if not title or not acceptance:
        raise ValueError("task title and acceptance condition must not be empty")
    stamp = now()
    with db:
        cursor = db.execute(
            """INSERT INTO tasks(project_id,title,acceptance,owner,created_at,updated_at)
               VALUES(?,?,?,?,?,?)""",
            (slug, title, acceptance, owner or "unassigned", stamp, stamp),
        )
        task_id = int(cursor.lastrowid)
        db.execute(
            "INSERT INTO events(project_id,task_id,at,kind,detail) VALUES(?,?,?,?,?)",
            (slug, task_id, stamp, "task_created", title),
        )
    return task_id


def change_status(db: sqlite3.Connection, slug: str, task_id: int, status: str) -> None:
    if status not in STATUSES:
        raise ValueError(f"status must be one of: {', '.join(STATUSES)}")
    row = db.execute(
        "SELECT status FROM tasks WHERE project_id=? AND id=?", (slug, task_id)
    ).fetchone()
    if row is None:
        raise ValueError(f"unknown task {task_id} in project {slug}")
    previous = row["status"]
    if status == previous:
        return
    if status not in TRANSITIONS[previous]:
        raise ValueError(f"cannot change task status from {previous} to {status}")
    stamp = now()
    with db:
        db.execute(
            "UPDATE tasks SET status=?,updated_at=? WHERE id=?",
            (status, stamp, task_id),
        )
        db.execute(
            """INSERT INTO events(project_id,task_id,at,kind,detail)
               VALUES(?,?,?,?,?)""",
            (slug, task_id, stamp, "status_changed", f"{previous} -> {status}"),
        )


def export_project(db: sqlite3.Connection, slug: str) -> str:
    project = project_or_error(db, slug)
    tasks = db.execute(
        """SELECT id,title,acceptance,owner,status FROM tasks
           WHERE project_id=? ORDER BY id""",
        (slug,),
    ).fetchall()
    counts = {status: 0 for status in STATUSES}
    for task in tasks:
        counts[task["status"]] += 1
    lines = [
        f"# {project['name']}",
        "",
        "## Objective",
        "",
        project["objective"],
        "",
        "## Progress",
        "",
        f"- Total tasks: {len(tasks)}",
        *[f"- {status.replace('_', ' ').title()}: {counts[status]}" for status in STATUSES],
        "",
        "## Tasks",
        "",
    ]
    if not tasks:
        lines.append("_No tasks yet._")
    for task in tasks:
        lines.extend(
            [
                f"### {task['id']}. {task['title']} [{task['status']}]",
                "",
                f"- Owner: {task['owner']}",
                f"- Acceptance: {task['acceptance']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-env",
        description="Local project planning and progress tracking; uses only Python's standard library.",
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite file (default: .ai-environment/workbench.sqlite3)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="create the local workbench database")

    project = commands.add_parser("project", help="manage projects")
    project_commands = project.add_subparsers(dest="project_command", required=True)
    create = project_commands.add_parser("add", help="create a project")
    create.add_argument("--name", required=True)
    create.add_argument("--objective", required=True)
    project_commands.add_parser("list", help="list projects")

    task = commands.add_parser("task", help="manage project tasks")
    task_commands = task.add_subparsers(dest="task_command", required=True)
    create_task = task_commands.add_parser("add", help="add a task")
    create_task.add_argument("--project", required=True)
    create_task.add_argument("--title", required=True)
    create_task.add_argument("--acceptance", required=True, help="observable completion condition")
    create_task.add_argument("--owner", default="unassigned")
    list_tasks = task_commands.add_parser("list", help="list tasks")
    list_tasks.add_argument("--project", required=True)
    status = task_commands.add_parser("status", help="change a task status")
    status.add_argument("--project", required=True)
    status.add_argument("--id", type=int, required=True)
    status.add_argument("--to", choices=STATUSES, required=True)

    export = commands.add_parser("export", help="print a project plan as Markdown")
    export.add_argument("--project", required=True)
    return parser


def run(args: argparse.Namespace) -> int:
    if args.command == "init":
        with closing(connect(args.db)):
            pass
        print(f"Workbench ready: {args.db}")
        return 0
    with closing(connect(args.db)) as db:
        if args.command == "project" and args.project_command == "add":
            slug = add_project(db, args.name, args.objective)
            print(f"Created project {slug}")
        elif args.command == "project":
            rows = db.execute("SELECT id,name,objective FROM projects ORDER BY id")
            for row in rows:
                print(f"{row['id']}\t{row['name']}\t{row['objective']}")
        elif args.command == "task" and args.task_command == "add":
            task_id = add_task(db, args.project, args.title, args.acceptance, args.owner)
            print(f"Created task {task_id} in {args.project}")
        elif args.command == "task" and args.task_command == "status":
            change_status(db, args.project, args.id, args.to)
            print(f"Updated task {args.id}: {args.to}")
        elif args.command == "task":
            project_or_error(db, args.project)
            rows = db.execute(
                "SELECT id,title,status,owner,acceptance FROM tasks WHERE project_id=? ORDER BY id",
                (args.project,),
            )
            for row in rows:
                print(f"{row['id']}\t{row['status']}\t{row['title']}\towner={row['owner']}\tacceptance={row['acceptance']}")
        elif args.command == "export":
            sys.stdout.write(export_project(db, args.project))
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return run(args)
    except (ValueError, sqlite3.Error, OSError) as exc:
        print(f"ai-env: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
