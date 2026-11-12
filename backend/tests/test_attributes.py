"""Valores de atributos do Akira, modifiers e migração sem perda de dados."""
import json

import pytest
from pydantic import ValidationError

from app import store
from app.models import Character
from app.lab_models import EnemyProfile, GenerateEnemyRequest
from app.skills.attributes import ATTRIBUTE_FIELDS, AKIRA_ATTRIBUTES, attribute_modifier
from app.skills.enemy_forge import EnemyForgeSkill
from app.skills.damage_calculator import DamageCalculator


def test_akira_starts_with_confirmed_five_attributes(client):
    sheet = client.get("/api/characters").json()[0]
    assert {field: sheet[field] for field in ATTRIBUTE_FIELDS} == AKIRA_ATTRIBUTES
    assert sheet["strength"] == 26
    assert sheet["speed"] == 34
    assert sheet["resistance"] == 26
    assert sheet["intellect"] == 30
    assert sheet["spirit"] == 34
    assert "dexterity" not in sheet


@pytest.mark.parametrize("value, expected", [
    (None, None), (0, None), (9, None), (10, 0), (11, 0),
    (12, 1), (13, 1), (14, 2), (26, 8), (30, 10),
    (34, 12), (49, 19), (50, 20), (51, None)
])
def test_modifier_formula_and_unspecified_below_ten(value, expected):
    assert attribute_modifier(value) == expected


def test_attributes_reject_more_than_50_and_negative(client):
    for field in ATTRIBUTE_FIELDS:
        for illegal in (-1, 51):
            response = client.patch("/api/characters/akira", json={field: illegal})
            assert response.status_code == 422, (field, illegal)
        assert client.get("/api/characters").json()[0][field] == AKIRA_ATTRIBUTES[field]


def test_optional_enemy_attributes_and_patch(client):
    created = client.post("/api/characters", json={
        "name": "Maldição", "team": "enemy"
    }).json()
    assert all(created[field] is None for field in ATTRIBUTE_FIELDS)
    changed = client.patch(f"/api/characters/{created['id']}", json={
        "strength": 29, "speed": 24, "resistance": 18,
        "intellect": 16, "spirit": 38
    })
    assert changed.status_code == 200
    assert changed.json()["speed"] == 24
    assert changed.json()["spirit"] == 38


def test_legacy_dexterity_keys_migrate_without_erasing_player_edits(client):
    # Imita uma ficha gravada na versão antiga e previamente editada pelo usuário.
    with store.connect() as db:
        row = db.execute("SELECT payload FROM characters WHERE id='akira'").fetchone()
        old = json.loads(row["payload"])
        for field in ("strength", "speed", "resistance", "intellect"):
            old.pop(field, None)
        old["dexterity"] = 40
        old["spirit"] = 38  # Edição antiga deve ser preservada, não substituída por 34.
        db.execute("UPDATE characters SET payload=? WHERE id='akira'",
                   (json.dumps(old, ensure_ascii=False),))
    store.initialize()
    new = store.get_character("akira")
    assert new["speed"] == 40
    assert new["spirit"] == 38
    assert new["strength"] == 26
    assert new["resistance"] == 26
    assert new["intellect"] == 30
    assert "dexterity" not in new
    snapshot = store.list_events()
    assert any(e["kind"] == "attribute_migration" for e in snapshot)
    store.initialize()
    assert store.list_events() == snapshot  # A migração não repete.


def test_legacy_over_cap_value_is_archived_not_destroyed(client):
    with store.connect() as db:
        row = db.execute("SELECT payload FROM characters WHERE id='akira'").fetchone()
        old = json.loads(row["payload"])
        old["dexterity"] = 57
        old.pop("speed")
        db.execute("UPDATE characters SET payload=? WHERE id='akira'",
                   (json.dumps(old, ensure_ascii=False),))
    store.initialize()
    new = store.get_character("akira")
    assert new["speed"] == 50
    assert new["extra_metrics"]["legacy_speed_before_cap"] == 57


def test_legacy_enemy_profile_can_load():
    original = EnemyForgeSkill().generate(GenerateEnemyRequest(difficulty=3))
    payload = original.model_dump()
    payload["dexterity"] = payload.pop("speed")
    result = EnemyProfile.model_validate(payload)
    assert result.speed == original.speed
    assert result.strength == original.strength


def test_legacy_api_alias_works_with_present_canonical_key(client):
    response = client.patch("/api/characters/akira", json={"dexterity": 42})
    assert response.status_code == 200
    assert response.json()["speed"] == 42
    assert "dexterity" not in response.json()


def test_named_attribute_updates_by_chat(client):
    for message, field, value in [
        ("/set akira forca 28", "strength", 28),
        ("/set akira velocidade 36", "speed", 36),
        ("/set akira resistencia 30", "resistance", 30),
        ("/set akira intelecto 32", "intellect", 32),
        ("/set akira espirito 40", "spirit", 40),
        ("/set akira des 38", "speed", 38),  # alias histórico
    ]:
        response = client.post("/api/chat", json={"message": message})
        assert response.status_code == 200, response.text
        assert response.json()["intent"] == "update"
        assert client.get("/api/characters").json()[0][field] == value


def test_sheet_summarizes_canonical_modifiers(client):
    response = client.post("/api/chat", json={"message": "qual a ficha do Akira?"}).json()
    assert response["intent"] == "sheet"
    assert "Força: 26/50 (modificador +8)" in response["answer"]
    assert "Velocidade: 34/50 (modificador +12)" in response["answer"]
    assert "Resistência: 26/50 (modificador +8)" in response["answer"]
    assert "Intelecto: 30/50 (modificador +10)" in response["answer"]
    assert "Espírito: 34/50 (modificador +12)" in response["answer"]
    assert "Destreza" not in response["answer"]


def test_enemy_comparison_only_uses_known_values(client):
    enemy = client.post("/api/characters", json={"name": "Maldição Teste", "team": "enemy"}).json()
    client.patch(f"/api/characters/{enemy['id']}", json={"speed": 42, "spirit": 24})
    result = client.post("/api/chat", json={"message": "qual a melhor abertura?"}).json()
    warnings = "\n".join(result["warnings"])
    assert "Velocidade 34/42" in warnings
    assert "Espírito 34/24" in warnings
    assert "regra de testes/acerto/defesa" in warnings
    assert "Força 26/" not in warnings


def test_damage_uses_raw_spirit_not_attribute_modifier(client):
    # ESP d10 utiliza quantidade de dados igual ao VALOR do atributo,
    # não 12 dados nem soma genérica de +12.
    char = client.get("/api/characters").json()[0]
    damage, formula = DamageCalculator().evaluate("fangs", char)
    assert "(34+5)d10" in formula
    assert damage is not None and damage > 200


def test_synthetic_enemy_has_five_valid_bounded_values():
    profile = EnemyForgeSkill().generate(GenerateEnemyRequest(difficulty=5, seed=42))
    assert all(10 <= getattr(profile, field) <= 50 for field in ATTRIBUTE_FIELDS)
    assert "dexterity" not in profile.model_dump()


def test_invalid_model_not_silently_clamped():
    with pytest.raises(ValidationError):
        Character(id="x", name="Outro", strength=51, team="enemy")
