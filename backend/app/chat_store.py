"""Persistência do histórico conversacional por SQLite."""
import json
from .store import connect

def _table(db):
    db.execute("""CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        extras TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")

def list_messages(limit: int = 100) -> list[dict]:
    with connect() as db:
        _table(db)
        rows = db.execute(
            "SELECT * FROM (SELECT * FROM messages ORDER BY id DESC LIMIT ?) ORDER BY id ASC",
            (min(limit, 200),)
        ).fetchall()
    return [{**dict(row), **json.loads(row["extras"])} for row in rows]

def add_message(role: str, content: str, extras: dict | None = None):
    with connect() as db:
        _table(db)
        db.execute("INSERT INTO messages(role, content, extras) VALUES(?,?,?)",
                   (role, content, json.dumps(extras or {}, ensure_ascii=False)))
