"""Mega Brain — regras fornecidas pelo jogador, uso real e controle auditável."""
import json

from app import store
from app.models import Character
from app.skills.mega_brain import MegaBrainSkill, mega_brain_technique


def akira(client):
    return client.get("/api/characters").json()[0]


def test_catalog_and_sheet_register_mega_brain(client):
    a = akira(client)
    techniques = [t for t in a["techniques"] if t["name"] == "Mega Brain"]
    assert len(techniques) == 1
    ability = techniques[0]
    assert ability["category"] == "extra"
    assert ability["ea_cost"] == 0
    assert ability["cooldown"] == 2
    assert ability["duration_turns"] == 1
    assert ability["status"] == "user_provided"
    catalog = client.get("/api/catalog").json()
    mb = next(a for a in catalog["abilities"] if a["id"] == "mega_brain")
    assert mb["base_cost"] == 0
    assert mb["cooldown_turns"] == 2
    assert mb["duration_turns"] == 1
    assert mb["critical_threshold"] == 15
    assert mb["critical_die"] == "d20 natural"
    assert mb["interrupted_by_cc"] is True
    assert {"Stun", "Paralisia", "Fear"} <= set(mb["cc_examples"])


def test_export_includes_rules_but_not_pretend_state(client):
    content = client.get("/api/characters/akira/export").json()["content"]
    assert "# Habilidades Extras" in content
    assert "Mega Brain (0 EA; recarga base 2c; duração base 1t)" in content
    assert "inativa; CD restante 0t; duração restante 0t" in content
    assert "d20 NATURAL 15+" in content
    assert "CC encerra o estado" in content


def test_explicit_activation_consumes_all_bonus_not_ea(client):
    before = akira(client)
    assert before["bonus_actions"] == 2
    resp = client.post("/api/characters/akira/mega-brain/activate")
    assert resp.status_code == 200
    active = resp.json()
    assert active["mega_brain_active"] is True
    assert active["mega_brain_turns_remaining"] == 1
    assert active["mega_brain_cooldown_remaining"] == 2
    assert active["bonus_actions"] == 0
    assert active["ea"] == before["ea"]
    assert active["hp"] == before["hp"]
    assert "ATIVA" in client.get("/api/characters/akira/export").json()["content"]
    assert client.post("/api/characters/akira/mega-brain/activate").status_code == 409
    assert len(client.get("/api/events").json()) == 2


def test_extra_only_remaining_bonus_actions_are_consumed(client):
    client.patch("/api/characters/akira", json={"bonus_actions": 1})
    active = client.post("/api/characters/akira/mega-brain/activate").json()
    assert active["bonus_actions"] == 0
    assert active["main_actions"] == 2


def test_activation_requires_bonus_actions_and_no_cd(client):
    client.patch("/api/characters/akira", json={"bonus_actions": 0})
    assert client.post("/api/characters/akira/mega-brain/activate").status_code == 409
    client.patch("/api/characters/akira", json={"bonus_actions": 2, "mega_brain_cooldown_remaining": 1})
    assert client.post("/api/characters/akira/mega-brain/activate").status_code == 409
    assert akira(client)["mega_brain_active"] is False


def test_explicit_turn_progress_expires_and_decrements_cd(client):
    client.post("/api/characters/akira/mega-brain/activate")
    first = client.post("/api/turns/next", json={"character_id": "akira"}).json()["characters"][0]
    assert first["mega_brain_active"] is False
    assert first["mega_brain_turns_remaining"] == 0
    assert first["mega_brain_cooldown_remaining"] == 1
    assert first["bonus_actions"] == 2
    assert client.post("/api/characters/akira/mega-brain/activate").status_code == 409
    second = client.post("/api/turns/next", json={"character_id": "akira"}).json()["characters"][0]
    assert second["mega_brain_cooldown_remaining"] == 0
    assert client.post("/api/characters/akira/mega-brain/activate").status_code == 200


def test_cc_interrupt_keeps_existing_cooldown(client):
    client.post("/api/characters/akira/mega-brain/activate")
    after = client.post("/api/characters/akira/mega-brain/interrupt").json()
    assert after["mega_brain_active"] is False
    assert after["mega_brain_turns_remaining"] == 0
    assert after["mega_brain_cooldown_remaining"] == 2
    assert after["bonus_actions"] == 0
    assert client.post("/api/characters/akira/mega-brain/activate").status_code == 409


def test_only_natural_d20_while_active_counts_15_plus_critical(client):
    skill = MegaBrainSkill()
    inactive = akira(client)
    assert skill.is_critical(inactive, 20) is None
    client.post("/api/characters/akira/mega-brain/activate")
    active = akira(client)
    for number in range(1, 21):
        assert skill.is_critical(active, number) is (number >= 15)
    assert skill.is_critical(active, 21) is None
    assert skill.is_critical(active, None) is None
    client.post("/api/characters/akira/mega-brain/interrupt")
    assert skill.is_critical(akira(client), 17) is None


def test_narrated_activation_is_pending_until_confirmed(client):
    before = akira(client)
    response = client.post("/api/chat", json={"message": "Ativei Mega Brain."}).json()
    assert response["intent"] == "combat_report"
    assert response["report_id"] is not None
    assert akira(client) == before
    pending = client.get("/api/combat/reports?status=pending").json()
    draft = pending[0]["parsed"]
    assert draft["proposed_updates"]["akira"]["bonus_actions"] == 0
    assert draft["proposed_updates"]["akira"]["mega_brain_active"] is True
    resp = client.post(f"/api/combat/reports/{response['report_id']}/review",
                       json={"decision": "confirmed"})
    assert resp.status_code == 200, resp.text
    assert akira(client)["mega_brain_active"] is True
    assert client.post(f"/api/combat/reports/{response['report_id']}/review",
                       json={"decision": "confirmed"}).status_code == 200


def test_discard_narrative_activation_does_not_mutate(client):
    before = akira(client)
    report = client.post("/api/chat", json={"message": "Ativei a Mega Brain."}).json()
    assert report["report_id"] is not None
    assert client.post(f"/api/combat/reports/{report['report_id']}/review",
                       json={"decision": "discarded"}).status_code == 200
    assert akira(client) == before


def test_narrated_cc_requires_confirmation_and_does_not_clear_cd(client):
    client.post("/api/characters/akira/mega-brain/activate")
    before = akira(client)
    draft = client.post("/api/chat", json={"message": "Sofri Stun e fiquei paralisado."}).json()
    assert draft["intent"] == "combat_report"
    assert draft["report_id"] is not None
    assert akira(client) == before
    response = client.post(f"/api/combat/reports/{draft['report_id']}/review",
                           json={"decision": "confirmed"})
    assert response.status_code == 200, response.text
    saved = akira(client)
    assert saved["mega_brain_active"] is False
    assert saved["mega_brain_turns_remaining"] == 0
    assert saved["mega_brain_cooldown_remaining"] == 2


def test_enemy_cc_does_not_interrupt_akira(client):
    client.post("/api/characters/akira/mega-brain/activate")
    draft = client.post("/api/chat", json={"message": "O inimigo sofreu Stun."}).json()
    assert draft["report_id"] is not None
    assert client.post(f"/api/combat/reports/{draft['report_id']}/review",
                       json={"decision": "confirmed"}).status_code == 200
    assert akira(client)["mega_brain_active"] is True


def test_disallow_activating_from_stale_narrative(client):
    draft = client.post("/api/chat", json={"message": "Ativei Mega Brain."}).json()
    assert draft["report_id"] is not None
    client.patch("/api/characters/akira", json={"bonus_actions": 1})
    conflict = client.post(f"/api/combat/reports/{draft['report_id']}/review",
                           json={"decision": "confirmed"})
    assert conflict.status_code == 409
    assert akira(client)["mega_brain_active"] is False


def test_report_natural_d20_flagged_only_with_explicit_natural_result(client):
    client.post("/api/characters/akira/mega-brain/activate")
    draft = client.post("/api/chat", json={
        "message": "Tirei 16 no d20 natural no meu ataque. Tirei 14 no d20 natural depois. Tirei 19 no acerto."
    }).json()
    assert draft["report_id"] is not None
    rolls = client.get("/api/combat/reports?status=pending").json()[0]["parsed"]["rolls"]
    assert [r.get("mega_brain_critical") for r in rolls if r["total"] is not None] == [True, False, None]
    assert akira(client)["critical_count"] == 0


def test_seed_upgrade_is_idempotent_and_preserves_custom_mega_brain(client):
    initial = akira(client)
    with store.connect() as db:
        old = dict(initial)
        old["techniques"] = [{
            "name": "Mega Brain", "ea_cost": 0, "cooldown": 2,
            "effect": "Editar pelo jogador", "category": "extra"
        }]
        db.execute("UPDATE characters SET payload=? WHERE id='akira'",
                   (json.dumps(old, ensure_ascii=False),))
    store.initialize()
    store.initialize()
    sheet = akira(client)
    assert len([t for t in sheet["techniques"] if t["name"] == "Mega Brain"]) == 1
    assert sheet["techniques"][0]["effect"] == "Editar pelo jogador"


def test_mega_brain_not_added_to_enemy(client):
    enemy = client.post("/api/characters", json={"name": "Maldição", "team": "enemy"}).json()
    assert enemy["techniques"] == []
    assert client.post(f"/api/characters/{enemy['id']}/mega-brain/activate").status_code == 409
