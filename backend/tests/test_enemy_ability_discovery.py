"""Descoberta progressiva de técnicas inimigas — identidade, revisão e segurança."""
from app.models import Character
from app.skills.enemy_ability_discovery import EnemyAbilityDiscoverySkill


def enemy(name="Maldição Grau 3", id="foe"):
    return Character(id=id, name=name, team="enemy").model_dump()


def test_extracts_named_ability_and_explicit_cooldown():
    entries = EnemyAbilityDiscoverySkill().extract(
        "A Maldição Grau 3 usou Ataque de Garras, dano 5d8 + 3d2, "
        "custa 20 EA, cooldown de 2 turnos.",
        [enemy()]
    )
    assert len(entries) == 1
    assert entries[0]["enemy_id"] == "foe"
    assert entries[0]["name"] == "Ataque de Garras"
    assert entries[0]["damage"] == "5d8 + 3d2"
    assert entries[0]["ea_cost"] == 20
    assert entries[0]["cooldown"] == 2


def test_unnamed_ability_does_not_get_invented():
    assert EnemyAbilityDiscoverySkill().extract(
        "O inimigo usou uma técnica e causou dano.", [enemy()]
    ) == []


def test_multiple_enemies_require_identity():
    entries = EnemyAbilityDiscoverySkill().extract(
        "O inimigo utilizou Corte das Sombras, cooldown 3 turnos.",
        [enemy("Maldição A", "a"), enemy("Maldição B", "b")]
    )
    assert len(entries) == 1
    assert entries[0]["enemy_id"] is None


def test_explicit_name_with_many_enemies():
    entries = EnemyAbilityDiscoverySkill().extract(
        "Mahito utilizou Transfiguração Ociosa, cooldown 0c.",
        [enemy("Mahito", "m"), enemy("Maldição B", "b")]
    )
    assert len(entries) == 1
    assert entries[0]["enemy_id"] == "m"
    assert entries[0]["cooldown"] == 0


def test_explicit_command_for_complex_name():
    entries = EnemyAbilityDiscoverySkill().extract(
        "@tecnica Mahito | Transfiguração Ociosa: toque mortal | cd=4 | dano=6d8+2d4 | ea=35 | efeito: altera o corpo",
        [enemy("Mahito", "m")]
    )
    assert len(entries) == 1
    assert entries[0]["name"] == "Transfiguração Ociosa: toque mortal"
    assert entries[0]["cooldown"] == 4
    assert entries[0]["ea_cost"] == 35
    assert entries[0]["damage"] == "6d8+2d4"
    assert entries[0]["effect"] == "altera o corpo"


def test_ability_revelation_pending_before_confirmation(client):
    created = client.post("/api/characters", json={
        "name": "Maldição Grau 3", "team": "enemy"
    }).json()
    resp = client.post("/api/chat", json={"message":
        "A Maldição Grau 3 usou Ataque de Garras, dano 5d8 + 3d2, cooldown 2 turnos."
    }).json()
    assert resp["report_id"] is not None
    before = next(c for c in client.get("/api/characters").json() if c["id"] == created["id"])
    assert before["techniques"] == []
    report = next(r for r in client.get("/api/combat/reports?status=pending").json()
                  if r["id"] == resp["report_id"])
    discovery = report["parsed"]["proposed_discoveries"][0]
    assert discovery["name"] == "Ataque de Garras"
    assert discovery["enemy_id"] == created["id"]
    assert discovery["cooldown"] == 2
    result = client.post(f"/api/combat/reports/{resp['report_id']}/review",
                         json={"decision": "confirmed"})
    assert result.status_code == 200
    after = next(c for c in client.get("/api/characters").json() if c["id"] == created["id"])
    assert len(after["techniques"]) == 1
    assert after["techniques"][0]["cooldown"] == 2
    assert after["techniques"][0]["damage"] == "5d8 + 3d2"
    assert after["techniques"][0]["status"] == "confirmed"
    assert client.post(f"/api/combat/reports/{resp['report_id']}/review",
                       json={"decision": "confirmed"}).status_code == 200
    assert len(next(c for c in client.get("/api/characters").json()
                    if c["id"] == created["id"])["techniques"]) == 1


def test_manual_assignment_cooldown_name_effect(client):
    first = client.post("/api/characters", json={"name": "Maldição A", "team": "enemy"}).json()
    client.post("/api/characters", json={"name": "Maldição B", "team": "enemy"})
    report_id = client.post("/api/chat", json={
        "message": "O inimigo usou Prisão Obscura. Rolou 18."
    }).json()["report_id"]
    pending = client.get("/api/combat/reports?status=pending").json()[0]
    assert pending["parsed"]["proposed_discoveries"][0]["enemy_id"] is None
    assert client.post(f"/api/combat/reports/{report_id}/review",
                       json={"decision": "confirmed"}).status_code == 409
    edited = client.patch(f"/api/combat/reports/{report_id}/discovery", json={
        "index": 0, "enemy_id": first["id"], "name": "Prisão Obscura",
        "cooldown": 3, "ea_cost": 25, "damage": None,
        "effect": "imobiliza o alvo por um turno", "ignored": False
    })
    assert edited.status_code == 200
    assert client.post(f"/api/combat/reports/{report_id}/review",
                       json={"decision": "confirmed"}).status_code == 200
    stored = next(c for c in client.get("/api/characters").json() if c["id"] == first["id"])
    assert stored["techniques"][0]["effect"] == "imobiliza o alvo por um turno"
    assert stored["techniques"][0]["cooldown"] == 3


def test_discard_does_not_register_ability(client):
    enemy_data = client.post("/api/characters", json={"name": "Maldição A", "team": "enemy"}).json()
    report_id = client.post("/api/chat", json={
        "message": "A Maldição A usou Distorção Ácida, cooldown 2 turnos."
    }).json()["report_id"]
    assert client.post(f"/api/combat/reports/{report_id}/review",
                       json={"decision": "discarded"}).status_code == 200
    saved = next(c for c in client.get("/api/characters").json() if c["id"] == enemy_data["id"])
    assert saved["techniques"] == []


def test_repeated_observation_no_duplicate(client):
    enemy_data = client.post("/api/characters", json={"name": "Maldição A", "team": "enemy"}).json()
    for report in (
        "A Maldição A usou Corte Sombrio.",
        "A Maldição A usou Corte Sombrio, cooldown 2 turnos."
    ):
        report_id = client.post("/api/chat", json={"message": report}).json()["report_id"]
        assert report_id is not None
        assert client.post(f"/api/combat/reports/{report_id}/review",
                           json={"decision": "confirmed"}).status_code == 200
    saved = next(c for c in client.get("/api/characters").json() if c["id"] == enemy_data["id"])
    assert len(saved["techniques"]) == 1
    assert saved["techniques"][0]["cooldown"] == 2


def test_conflicting_technique_does_not_overwrite_existing(client):
    target = client.post("/api/characters", json={"name": "Mahito", "team": "enemy"}).json()
    client.patch(f"/api/characters/{target['id']}", json={"techniques": [
        {"name": "Corte do Vazio", "cooldown": 2, "status": "confirmed"}
    ]})
    report_id = client.post("/api/chat", json={
        "message": "Mahito usou Corte do Vazio, cooldown 4 turnos."
    }).json()["report_id"]
    conflict = client.post(f"/api/combat/reports/{report_id}/review",
                           json={"decision": "confirmed"})
    assert conflict.status_code == 409
    stored = next(c for c in client.get("/api/characters").json() if c["id"] == target["id"])
    assert stored["techniques"][0]["cooldown"] == 2


def test_future_plans_cannot_reveal_enemy_abilities(client):
    target = client.post("/api/characters", json={"name": "Mahito", "team": "enemy"}).json()
    response = client.post("/api/chat", json={
        "message": "Mahito poderia usar Corte Sombrio."
    }).json()
    assert response["report_id"] is None
    assert next(c for c in client.get("/api/characters").json()
                if c["id"] == target["id"])["techniques"] == []
