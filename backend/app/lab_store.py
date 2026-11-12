"""SQLite para adversários de laboratório e avaliações sintéticas (não misturar com batalhas reais)."""
import json
from datetime import datetime, timezone
from .store import connect
from .lab_models import EnemyProfile

def initialize():
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS lab_enemies(
            id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS learning_runs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enemy_id TEXT NOT NULL,
            scenario TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")

def add_enemy(profile: EnemyProfile) -> dict:
    payload = profile.model_dump()
    with connect() as db:
        db.execute("INSERT INTO lab_enemies(id, payload, created_at) VALUES(?,?,?)",
                   (profile.id, json.dumps(payload, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))
    return payload

def list_enemies(limit: int = 100) -> list[dict]:
    with connect() as db:
        rows = db.execute("SELECT payload FROM lab_enemies ORDER BY created_at DESC, rowid DESC LIMIT ?",
                          (min(100, max(1, limit)),)).fetchall()
    return [EnemyProfile.model_validate(json.loads(r["payload"])).model_dump() for r in rows]

def get_enemy(enemy_id: str) -> dict | None:
    with connect() as db:
        row = db.execute("SELECT payload FROM lab_enemies WHERE id=?", (enemy_id,)).fetchone()
    return EnemyProfile.model_validate(json.loads(row["payload"])).model_dump() if row else None

def add_run(data: dict) -> dict:
    with connect() as db:
        stamp = datetime.now(timezone.utc).isoformat()
        cursor = db.execute(
            "INSERT INTO learning_runs(enemy_id, scenario, result_json, created_at) VALUES(?,?,?,?)",
            (data["enemy_id"], data["scenario"], json.dumps(data, ensure_ascii=False), stamp)
        )
        run_id = cursor.lastrowid
    return {**data, "id": run_id, "created_at": stamp}

def list_runs(limit: int = 80) -> list[dict]:
    with connect() as db:
        rows = db.execute("SELECT * FROM learning_runs ORDER BY id DESC LIMIT ?",
                          (min(200, max(1, limit)),)).fetchall()
    return [
        {**json.loads(row["result_json"]), "id": row["id"], "created_at": row["created_at"]}
        for row in rows
    ]
