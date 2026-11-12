"""SQLite local: fichas base editáveis + eventos para auditoria e desfazer."""
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .catalog import load_catalog
from .models import Character
from .skills.attributes import AKIRA_ATTRIBUTES, ATTRIBUTE_FIELDS, ATTRIBUTE_MAX, migrate_attribute_keys

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "combat_brain.sqlite3"

def connect():
    path = Path(os.getenv("RPG_DB_PATH", str(DEFAULT_PATH)))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def initialize():
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS characters (
            id TEXT PRIMARY KEY, payload TEXT NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id TEXT NOT NULL, kind TEXT NOT NULL,
            before_json TEXT, after_json TEXT, created_at TEXT NOT NULL)""")
        existing = db.execute("SELECT COUNT(*) FROM characters").fetchone()[0]
        if existing == 0:
            catalog = load_catalog()["akira"]
            sheet = Character(
                id="akira", name=catalog["name"], team="player",
                level=catalog["level"], hp=catalog["hp_current"],
                ea=catalog["ea_current"], **AKIRA_ATTRIBUTES
            )
            db.execute("INSERT INTO characters VALUES(?,?)",
                       (sheet.id, sheet.model_dump_json()))
            _log(db, sheet.id, "created", None, sheet.model_dump())
        else:
            # Atualiza as fichas legadas sem apagar personalizações do jogador.
            for row in db.execute("SELECT id, payload FROM characters").fetchall():
                old = json.loads(row["payload"])
                upgraded = migrate_attribute_keys(old, seed_akira=row["id"] == "akira")
                # Antes desta versão não havia teto de 50. Preserve valores
                # legados acima de 50 na ficha em vez de perdê-los na migração.
                for field in ATTRIBUTE_FIELDS:
                    value = upgraded.get(field)
                    if isinstance(value, int) and value > ATTRIBUTE_MAX:
                        upgraded.setdefault("extra_metrics", {})[f"legacy_{field}_before_cap"] = value
                        upgraded[field] = ATTRIBUTE_MAX
                        note = f"Atributo {field} tinha {value} na versão antiga; original preservado em extra_metrics."
                        upgraded["notes"] = (upgraded.get("notes", "") + "\n" + note).strip()[:3000]
                new = Character.model_validate(upgraded).model_dump()
                if new != old:
                    db.execute("UPDATE characters SET payload=? WHERE id=?",
                               (json.dumps(new, ensure_ascii=False), row["id"]))
                    _log(db, row["id"], "attribute_migration", old, new)

def _log(db, character_id, kind, before, after):
    db.execute(
        """INSERT INTO events(character_id, kind, before_json, after_json, created_at)
           VALUES(?,?,?,?,?)""",
        (character_id, kind, json.dumps(before, ensure_ascii=False) if before is not None else None,
         json.dumps(after, ensure_ascii=False) if after is not None else None,
         datetime.now(timezone.utc).isoformat())
    )

def list_characters() -> list[dict]:
    with connect() as db:
        rows = db.execute("SELECT payload FROM characters ORDER BY CASE json_extract(payload,'$.team') WHEN 'player' THEN 0 WHEN 'ally' THEN 1 ELSE 2 END, id").fetchall()
    return [Character.model_validate(json.loads(row["payload"])).model_dump() for row in rows]

def get_character(id: str) -> dict | None:
    with connect() as db:
        row = db.execute("SELECT payload FROM characters WHERE id=?", (id,)).fetchone()
    return Character.model_validate(json.loads(row["payload"])).model_dump() if row else None

def create_character(name: str, team: str) -> dict:
    sheet = Character(id=str(uuid.uuid4())[:8], name=name, team=team).model_dump()
    with connect() as db:
        db.execute("INSERT INTO characters VALUES(?,?)",
                   (sheet["id"], json.dumps(sheet, ensure_ascii=False)))
        _log(db, sheet["id"], "created", None, sheet)
    return sheet

def create_from_enemy(profile) -> dict:
    """Só chamado após ação explícita do jogador: cópia editável, nunca mudança no adversário de teste."""
    origin_label = ("Ficha sintética: técnicas e capacidades precisam de validação do mestre."
                    if profile.origin == "synthetic" else
                    "Ficha de referência: valores do exemplo do jogador; técnicas ausentes permanecem pendentes.")
    sheet = Character(
        id=str(uuid.uuid4())[:8], name=profile.name, team="enemy",
        hp=profile.hp, ea=profile.ea, strength=profile.strength,
        speed=profile.speed, resistance=profile.resistance,
        intellect=profile.intellect, spirit=profile.spirit, tier=profile.tier,
        reinforcement_level=profile.reinforcement_level,
        output_level=profile.output_level, reverse_level=profile.reverse_level,
        domain_level=profile.domain_level, extra_metrics=profile.extra_metrics,
        techniques=[tech.model_dump() for tech in profile.techniques],
        sheet_origin=profile.origin, origin_warning=origin_label
    ).model_dump()
    with connect() as db:
        db.execute("INSERT INTO characters VALUES(?,?)",
                   (sheet["id"], json.dumps(sheet, ensure_ascii=False)))
        _log(db, sheet["id"], "created_from_enemy_forge", None, sheet)
    return sheet


def update_character(id: str, changes: dict, kind: str = "edited") -> dict | None:
    with connect() as db:
        row = db.execute("SELECT payload FROM characters WHERE id=?", (id,)).fetchone()
        if not row:
            return None
        before = Character.model_validate(json.loads(row["payload"])).model_dump()
        # Compatibilidade opcional com clientes antigos: DES/dexterity -> Velocidade.
        changes = dict(changes)
        if "dexterity" in changes:
            old_speed = changes.pop("dexterity")
            changes.setdefault("speed", old_speed)
        after = Character.model_validate({**before, **changes}).model_dump()
        if after == before:
            return after
        db.execute("UPDATE characters SET payload=? WHERE id=?",
                   (json.dumps(after, ensure_ascii=False), id))
        _log(db, id, kind, before, after)
        return after

def list_events(limit: int = 40) -> list[dict]:
    with connect() as db:
        rows = db.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (min(limit, 100),)).fetchall()
    return [{
        "id": row["id"], "character_id": row["character_id"],
        "kind": row["kind"],
        "before": json.loads(row["before_json"]) if row["before_json"] else None,
        "after": json.loads(row["after_json"]) if row["after_json"] else None,
        "created_at": row["created_at"]
    } for row in rows]

def undo_last() -> dict | None:
    """Desfaz apenas o último evento, sem apagar o histórico (event sourcing leve)."""
    with connect() as db:
        row = db.execute("SELECT * FROM events WHERE kind NOT IN ('undo','created','attribute_migration') ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return None
        # Impede desfazer um evento já desfeito.
        later_undo = db.execute(
            "SELECT id FROM events WHERE kind='undo' AND id>? LIMIT 1", (row["id"],)
        ).fetchone()
        if later_undo:
            return None
        before = json.loads(row["before_json"])
        after = json.loads(row["after_json"])
        current = db.execute("SELECT payload FROM characters WHERE id=?", (row["character_id"],)).fetchone()
        if not current or json.loads(current["payload"]) != after:
            return None
        db.execute("UPDATE characters SET payload=? WHERE id=?",
                   (json.dumps(before, ensure_ascii=False), row["character_id"]))
        _log(db, row["character_id"], "undo", after, before)
    return before

def new_turn(character_id: str | None = None) -> list[dict]:
    result = []
    for sheet in list_characters():
        if character_id is not None and sheet['id'] != character_id:
            continue
        result.append(update_character(sheet["id"], {
            "main_actions": 2, "bonus_actions": 2, "reaction_available": True
        }, kind="new_turn"))
    return result
