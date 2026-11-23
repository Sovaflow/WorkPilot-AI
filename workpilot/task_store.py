"""Local SQLite task ledger. No network calls or personal information required."""
import sqlite3
from pathlib import Path

FIELDS = ("id", "title", "due_date", "due_time", "preparation", "status", "source")


class TaskStore:
    def __init__(self, path="outputs/workpilot.db"):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            due_date TEXT NOT NULL,
            due_time TEXT NOT NULL DEFAULT '',
            preparation TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','done')),
            source TEXT NOT NULL DEFAULT 'manual',
            completed_at TEXT NOT NULL DEFAULT ''
        )""")
        self.db.commit()

    def seed(self, tasks):
        """Insert new tasks once; never reset a previously completed task."""
        for task in tasks:
            if task.get("status", "open") not in ("open", "done"):
                raise ValueError("Invalid task status")
            self.db.execute("""INSERT OR IGNORE INTO tasks
                (id, title, due_date, due_time, preparation, status, source, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (
                task["id"], task["title"], task["due_date"], task.get("due_time", ""),
                task.get("preparation", ""), task.get("status", "open"),
                task.get("source", "manual"), task.get("completed_at", "")
            ))
        self.db.commit()

    def list_tasks(self):
        return [dict(row) for row in self.db.execute(
            "SELECT * FROM tasks ORDER BY due_date, due_time, id")]

    def mark_done(self, task_id, timestamp):
        cursor = self.db.execute(
            "UPDATE tasks SET status='done', completed_at=? WHERE id=?",
            (timestamp, task_id))
        self.db.commit()
        if cursor.rowcount == 0:
            raise ValueError("Unknown task ID: " + task_id)

    def close(self):
        self.db.close()
