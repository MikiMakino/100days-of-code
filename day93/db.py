import sqlite3
from datetime import datetime
from pathlib import Path

from task import Task

DB_PATH = Path(__file__).parent / "todo.db"


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                title     TEXT    NOT NULL,
                memo      TEXT    DEFAULT '',
                due_date  TEXT,
                priority  TEXT    DEFAULT '中',
                done      INTEGER DEFAULT 0
            )
        """)
        conn.commit()


def _row_to_task(row: tuple) -> Task:
    id_, title, memo, due_date_str, priority, done = row
    due_date = datetime.fromisoformat(due_date_str) if due_date_str else None
    return Task(id=id_, title=title, memo=memo, due_date=due_date, priority=priority, done=bool(done))


def get_all_tasks() -> list[Task]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, title, memo, due_date, priority, done FROM tasks ORDER BY id"
        ).fetchall()
    return [_row_to_task(row) for row in rows]


def add_task(task: Task) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, memo, due_date, priority, done) VALUES (?, ?, ?, ?, ?)",
            (task.title, task.memo, str(task.due_date) if task.due_date else None, task.priority, int(task.done)),
        )
        conn.commit()
        return cur.lastrowid


def update_task(task: Task) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE tasks SET title=?, memo=?, due_date=?, priority=?, done=? WHERE id=?",
            (task.title, task.memo, str(task.due_date) if task.due_date else None, task.priority, int(task.done), task.id),
        )
        conn.commit()


def delete_task(task_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        conn.commit()


def delete_completed_tasks() -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM tasks WHERE done=1")
        conn.commit()


def toggle_done(task_id: int) -> None:
    with _connect() as conn:
        conn.execute("UPDATE tasks SET done = 1 - done WHERE id=?", (task_id,))
        conn.commit()
