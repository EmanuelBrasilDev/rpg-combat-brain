"""Relatos narrativos pendentes e confirmados, isolados dos eventos de edição da ficha."""
import json
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field
from .models import Character
from .skills.enemy_ability_discovery import EnemyAbilityDiscoverySkill
from .store import connect, _log

class CombatReportConflict(Exception):
    """A ficha foi alterada desde o rascunho e não coincide com o estado relatado."""

class EnemyDiscoveryEdit(BaseModel):
    """O jogador corrige a extração antes de confirmar o acontecimento."""
    index: int = Field(ge=0)
    enemy_id: str | None = None
    name: str = Field(default="", max_length=100)
    cooldown: int | None = Field(default=None, ge=0, le=999)
    ea_cost: int | None = Field(default=None, ge=0)
    damage: str | None = Field(default=None, max_length=120)
    effect: str | None = Field(default=None, max_length=400)
    ignored: bool = False


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

def edit_discovery(report_id: int, edit: EnemyDiscoveryEdit) -> dict | None:
    """Alteração atômica no RASCUNHO, sem modificar ficha antes da confirmação."""
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM combat_reports WHERE id=?", (report_id,)).fetchone()
        if not row:
            return None
        if row["status"] != "pending":
            raise CombatReportConflict("Descobertas já revisadas não podem ser modificadas.")
        parsed = json.loads(row["payload"])
        discoveries = parsed.get("proposed_discoveries", [])
        if edit.index >= len(discoveries):
            raise CombatReportConflict("Descoberta não encontrada nesse relato.")
        if edit.enemy_id is not None:
            enemy = db.execute("SELECT payload FROM characters WHERE id=?", (edit.enemy_id,)).fetchone()
            if not enemy or Character.model_validate(json.loads(enemy["payload"])).team != "enemy":
                raise CombatReportConflict("Selecione uma ficha de inimigo válida.")
        old = discoveries[edit.index]
        discoveries[edit.index] = {
            **old,
            "enemy_id": edit.enemy_id,
            "name": edit.name.strip(),
            "cooldown": edit.cooldown,
            "ea_cost": edit.ea_cost,
            "damage": edit.damage.strip() if edit.damage else None,
            "effect": edit.effect.strip() if edit.effect else None,
            "ignored": edit.ignored
        }
        db.execute("UPDATE combat_reports SET payload=? WHERE id=?",
                   (json.dumps(parsed, ensure_ascii=False), report_id))
        return _to_report(db.execute("SELECT * FROM combat_reports WHERE id=?", (report_id,)).fetchone())


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
            discover = EnemyAbilityDiscoverySkill()
            for proposal in parsed.get("proposed_discoveries", []):
                if proposal.get("ignored"):
                    continue
                enemy_id = proposal.get("enemy_id")
                if not enemy_id:
                    raise CombatReportConflict(
                        "Selecione o inimigo responsável pela técnica antes de confirmar, "
                        "ou marque a descoberta como ignorada."
                    )
                row_enemy = db.execute("SELECT payload FROM characters WHERE id=?", (enemy_id,)).fetchone()
                if not row_enemy:
                    raise CombatReportConflict("O inimigo associado não está mais cadastrado.")
                previous = Character.model_validate(json.loads(row_enemy["payload"])).model_dump()
                if previous["team"] != "enemy":
                    raise CombatReportConflict("A técnica só pode ser vinculada a fichas de inimigos.")
                try:
                    techniques = discover.merged_techniques(previous, proposal)
                    revised = Character.model_validate({**previous, "techniques": techniques}).model_dump()
                except (ValueError, TypeError) as error:
                    raise CombatReportConflict(str(error))
                if previous != revised:
                    db.execute("UPDATE characters SET payload=? WHERE id=?",
                               (json.dumps(revised, ensure_ascii=False), enemy_id))
                    _log(db, enemy_id, "ability_discovered", previous, revised)
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
