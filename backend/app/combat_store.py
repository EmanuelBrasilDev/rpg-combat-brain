"""Relatos narrativos pendentes e confirmados, isolados dos eventos de edição da ficha."""
import json
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field
from .models import Character
from .store import connect, _log

class CombatReportConflict(Exception):
    """A ficha foi alterada desde o rascunho e não coincide com o estado relatado."""

class CombatFeedback(BaseModel):
    rating: Literal["good", "neutral", "bad"]
    note: str = Field(default="", max_length=1200)

def initialize():
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS combat_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending', 'confirmed', 'discarded')),
            payload TEXT NOT NULL,
            feedback TEXT,
            created_at TEXT NOT NULL,
            reviewed_at TEXT
        )""")

def _to_report(row) -> dict:
    payload = json.loads(row["payload"])
    return {
        "id": row["id"],
        "character_id": row["character_id"],
        "status": row["status"],
        "parsed": payload,
        "feedback": json.loads(row["feedback"]) if row["feedback"] else None,
        "created_at": row["created_at"],
        "reviewed_at": row["reviewed_at"]
    }

def add_draft(parsed: dict) -> dict:
    with connect() as db:
        stamp = datetime.now(timezone.utc).isoformat()
        result = db.execute(
            "INSERT INTO combat_reports(character_id,status,payload,created_at) VALUES(?,?,?,?)",
            (parsed["character_id"], "pending", json.dumps(parsed, ensure_ascii=False), stamp)
        )
        row = db.execute("SELECT * FROM combat_reports WHERE id=?", (result.lastrowid,)).fetchone()
        return _to_report(row)

def list_reports(status: str | None = None, limit: int = 60) -> list[dict]:
    if status is not None and status not in ("pending", "confirmed", "discarded"):
        raise ValueError("Filtro inválido.")
    with connect() as db:
        if status:
            rows = db.execute("SELECT * FROM combat_reports WHERE status=? ORDER BY id DESC LIMIT ?",
                              (status, min(150, max(1, limit)))).fetchall()
        else:
            rows = db.execute("SELECT * FROM combat_reports ORDER BY id DESC LIMIT ?",
                              (min(150, max(1, limit)),)).fetchall()
        return [_to_report(row) for row in rows]

def get_report(report_id: int) -> dict | None:
    with connect() as db:
        row = db.execute("SELECT * FROM combat_reports WHERE id=?", (report_id,)).fetchone()
    return _to_report(row) if row else None

def review(report_id: int, decision: Literal["confirmed", "discarded"]) -> dict | None:
    """Confirma estados finais absolutos; não subtrai dano nem energia por dedução."""
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM combat_reports WHERE id=?", (report_id,)).fetchone()
        if not row:
            return None
        if row["status"] == decision:
            return _to_report(row)  # Reenvios são idempotentes.
        if row["status"] != "pending":
            raise CombatReportConflict("O relato já foi revisado com outra decisão.")
        parsed = json.loads(row["payload"])
        if decision == "confirmed":
            for char_id, changes in parsed["proposed_updates"].items():
                current_row = db.execute("SELECT payload FROM characters WHERE id=?", (char_id,)).fetchone()
                if not current_row:
                    raise CombatReportConflict(f"Ficha {char_id} indisponível.")
                before_raw = json.loads(current_row["payload"])
                before = Character.model_validate(before_raw).model_dump()
                snapshot = parsed["sheet_snapshots"].get(char_id, {})
                for field, target in changes.items():
                    if field not in ("hp", "ea", "reaction_available"):
                        raise CombatReportConflict("Campo não permitido na atualização narrativa.")
                    current = before.get(field)
                    if current != target and current != snapshot.get(field):
                        raise CombatReportConflict(
                            f"{char_id}.{field} mudou desde a narração ({snapshot.get(field)} → {current}); "
                            "revise a ficha e descarte este relato antes de reenviá-lo."
                        )
                after = Character.model_validate({**before, **changes}).model_dump()
                if after != before:
                    db.execute("UPDATE characters SET payload=? WHERE id=?",
                               (json.dumps(after, ensure_ascii=False), char_id))
                    _log(db, char_id, "report_confirmed_update", before, after)
        stamp = datetime.now(timezone.utc).isoformat()
        db.execute("UPDATE combat_reports SET status=?, reviewed_at=? WHERE id=?",
                   (decision, stamp, report_id))
        return _to_report(db.execute("SELECT * FROM combat_reports WHERE id=?", (report_id,)).fetchone())

def set_feedback(report_id: int, feedback: CombatFeedback) -> dict | None:
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM combat_reports WHERE id=?", (report_id,)).fetchone()
        if not row:
            return None
        if row["status"] != "confirmed":
            raise CombatReportConflict("Somente relatos confirmados podem treinar a memória de experiências.")
        db.execute("UPDATE combat_reports SET feedback=? WHERE id=?",
                   (feedback.model_dump_json(), report_id))
        return _to_report(db.execute("SELECT * FROM combat_reports WHERE id=?", (report_id,)).fetchone())
