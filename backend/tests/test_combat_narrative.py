"""Contratos: narração não altera ficha; confirmação idempotente; dados reais != sintéticos."""
from app.skills.dice_roll_interpreter import DiceRollInterpreter
from app.skills.combat_event_tracker import CombatEventTracker
from app.models import Character


def test_dice_parser_distinguishes_formula_from_roll():
    rolls = DiceRollInterpreter().parse(
        "O inimigo tirou 24 no acerto. Eu tentei esquivar e tirei 19. "
        "O ataque usa 5d8 + 3d2, mas ainda não rolou o dano."
    )
    results = [x["total"] for x in rolls if x["total"] is not None]
    assert results == [24, 19]
    assert any(x["expression"] and "5d8" in x["expression"] and x["total"] is None for x in rolls)
    assert any(x["actor"] == "player" and x["total"] == 19 for x in rolls)


def test_narrative_extracts_absolute_hp_not_implicit_damage():
    actor = Character(id="akira", name="Akira Uchiha", team="player", hp=600, ea=731).model_dump()
    enemy = Character(id="foe", name="Maldição Grau 3", team="enemy", hp=300, ea=200).model_dump()
    report = CombatEventTracker().draft(
        "A maldição usou Ataque de Garras e tirou 24. Eu tentei esquivar e tirei 19. "
        "Recebi 35 de dano e atualizei meu HP para 565.",
        "akira", [actor, enemy]
    )
    assert report is not None
    assert report["damage_received"] == 35
    assert report["proposed_updates"]["akira"]["hp"] == 565
    assert report["sheet_snapshots"]["akira"]["hp"] == 600
    assert "reaction_available" not in report["proposed_updates"]["akira"]


def test_planned_action_not_recorded():
    actor = Character(id="akira", name="Akira Uchiha", team="player").model_dump()
    assert CombatEventTracker().draft("Vou usar Fangs depois da esquiva.", "akira", [actor]) is None


def test_chat_creates_pending_and_no_subtraction(client):
    initial = client.get("/api/characters").json()[0]
    resp = client.post("/api/chat", json={
        "message": "A maldição usou garras, tirou 24. Eu tirei 19 e recebi 35 de dano. "
                   "Atualizei meu HP para 565."
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_id"] is not None
    assert client.get("/api/characters").json()[0] == initial
    reports = client.get("/api/combat/reports?status=pending").json()
    assert len(reports) == 1
    assert reports[0]["parsed"]["proposed_updates"]["akira"]["hp"] == 565
    reviewed = client.post("/api/combat/reports/" + str(data["report_id"]) + "/review",
                           json={"decision": "confirmed"})
    assert reviewed.status_code == 200
    assert client.get("/api/characters").json()[0]["hp"] == 565
    again = client.post("/api/combat/reports/" + str(data["report_id"]) + "/review",
                        json={"decision": "confirmed"})
    assert again.status_code == 200
    assert client.get("/api/characters").json()[0]["hp"] == 565


def test_sheet_edited_before_confirm_no_double_subtraction(client):
    report = client.post("/api/chat", json={
        "message": "Recebi 35 de dano, atualizei meu HP para 565."
    }).json()
    assert report["report_id"] is not None
    assert client.patch("/api/characters/akira", json={"hp": 565}).status_code == 200
    ok = client.post(f"/api/combat/reports/{report['report_id']}/review",
                     json={"decision": "confirmed"})
    assert ok.status_code == 200
    assert client.get("/api/characters").json()[0]["hp"] == 565


def test_stale_report_conflict_prevents_overwrite(client):
    report = client.post("/api/chat", json={
        "message": "Recebi 35 de dano e meu HP ficou em 565."
    }).json()
    client.patch("/api/characters/akira", json={"hp": 580})
    conflict = client.post(f"/api/combat/reports/{report['report_id']}/review",
                           json={"decision": "confirmed"})
    assert conflict.status_code == 409
    assert client.get("/api/characters").json()[0]["hp"] == 580
    assert client.get("/api/combat/reports?status=pending").json()


def test_discard_and_feedback_gate(client):
    pending = client.post("/api/chat", json={
        "message": "O inimigo me atacou. Eu bloqueei."
    }).json()["report_id"]
    bad = client.post(f"/api/combat/reports/{pending}/feedback",
                      json={"rating": "good", "note": "funcionou"})
    assert bad.status_code == 409
    assert client.post(f"/api/combat/reports/{pending}/review",
                       json={"decision": "discarded"}).status_code == 200
    assert len(client.get("/api/combat/reports?status=confirmed").json()) == 0


def test_learning_only_real_confirmed_and_human_feedback(client):
    draft = client.post("/api/chat", json={
        "message": "O inimigo atacou e eu tirei 19 na defesa."
    }).json()["report_id"]
    client.post(f"/api/combat/reports/{draft}/review", json={"decision": "confirmed"})
    feedback = client.post(f"/api/combat/reports/{draft}/feedback",
                           json={"rating": "good", "note": "boa decisão pelo risco"})
    assert feedback.status_code == 200
    overview = client.get("/api/learning/overview").json()
    assert overview["confirmed_reports"] == 1
    assert overview["feedback_count"] == 1
    assert overview["feedback"]["good"] == 1
    assert overview["reported_roll_results"] >= 1
    assert "NÃO" not in overview["learning_status"] or "ainda" in overview["learning_status"]


def test_explicit_adoption_of_generated_enemy(client):
    ref = client.post("/api/lab/enemies/generate", json={
        "template": "procedural", "archetype": "control",
        "difficulty": 4, "seed": 10
    }).json()
    before = client.get("/api/characters").json()
    assert len(before) == 1
    adopted = client.post("/api/lab/enemies/" + ref["id"] + "/adopt")
    assert adopted.status_code == 201
    enemy = adopted.json()
    assert enemy["team"] == "enemy"
    assert enemy["sheet_origin"] == "synthetic"
    assert enemy["techniques"] and enemy["domain_level"] is not None
    assert enemy["origin_warning"]
    assert len(client.get("/api/characters").json()) == 2
    assert client.get("/api/characters").json()[0]["hp"] == 600


def test_report_handles_snapshot_absolute_ea(client):
    report = client.post("/api/chat", json={
        "message": "Usei Fangs. Gastei 11 EA. Minha EA ficou em 720."
    }).json()
    assert report["report_id"] is not None
    assert client.get("/api/characters").json()[0]["ea"] == 731
    client.post(f"/api/combat/reports/{report['report_id']}/review",
                json={"decision": "confirmed"})
    assert client.get("/api/characters").json()[0]["ea"] == 720


def test_tactic_uses_only_confirmed_history(client):
    report = client.post("/api/chat", json={
        "message": "O inimigo atacou e eu tirei 19."
    }).json()
    assert report["report_id"] is not None
    advised = client.post("/api/chat", json={"message": "Qual a melhor jogada agora?"}).json()
    assert advised["intent"] == "tactics"
    assert any("aguardando" in x for x in advised["warnings"])
    client.post(f"/api/combat/reports/{report['report_id']}/review",
                json={"decision": "confirmed"})
    advised2 = client.post("/api/chat", json={"message": "Qual a melhor jogada agora?"}).json()
    assert advised2["intent"] == "tactics"
    assert not any("aguardando" in x for x in advised2["warnings"])


def test_ambiguous_hp_does_not_update_player(client):
    draft = client.post("/api/chat", json={
        "message": "O inimigo atacou. O HP ficou em 250."
    }).json()["report_id"]
    assert draft is not None
    pending = client.get("/api/combat/reports?status=pending").json()[0]
    assert pending["parsed"]["proposed_updates"] == {}
    confirmed = client.post(f"/api/combat/reports/{draft}/review",
                            json={"decision": "confirmed"})
    assert confirmed.status_code == 200
    assert client.get("/api/characters").json()[0]["hp"] == 600


def test_explicit_enemy_hp_target_does_not_touch_akira(client):
    enemy = client.post("/api/characters", json={
        "name": "Maldição Grau 3", "team": "enemy"
    }).json()
    client.patch("/api/characters/" + enemy["id"], json={"hp": 300})
    before = client.get("/api/characters").json()
    draft = client.post("/api/chat", json={
        "message": "O inimigo atacou e o HP da Maldição Grau 3 ficou em 250."
    }).json()["report_id"]
    pending = client.get("/api/combat/reports?status=pending").json()[0]
    assert pending["parsed"]["proposed_updates"][enemy["id"]]["hp"] == 250
    assert "akira" not in pending["parsed"]["proposed_updates"]
    confirmed = client.post(f"/api/combat/reports/{draft}/review",
                            json={"decision": "confirmed"})
    assert confirmed.status_code == 200
    sheets = client.get("/api/characters").json()
    assert sheets[0]["hp"] == 600
    assert next(c for c in sheets if c["id"] == enemy["id"])["hp"] == 250
