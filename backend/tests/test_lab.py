"""Testes de geração e avaliação sintética: isolamento e procedência são invariantes."""
from app.lab_models import GenerateEnemyRequest
from app.skills.enemy_forge import EnemyForgeSkill
from app.skills.learning_lab import LearningLabSkill

def test_exact_grade3_reference():
    generated = EnemyForgeSkill().generate(GenerateEnemyRequest(template="curse_grade_3"))
    assert generated.origin == "user_example"
    assert generated.hp == 300 and generated.ea == 200
    assert generated.techniques[0].name == "Ataque de Garras"
    assert generated.techniques[0].damage == "5d8 + 3d2"
    assert generated.output_level is None
    assert generated.reinforcement_level is None
    assert not generated.approved_for_real_combat

def test_mahito_reference_does_not_invent_techniques():
    generated = EnemyForgeSkill().generate(GenerateEnemyRequest(template="mahito_reference"))
    assert generated.hp == 1000 and generated.ea == 1200
    assert len(generated.techniques) == 6
    assert all(t.status == "placeholder" and t.damage is None and t.ea_cost is None
               for t in generated.techniques)
    assert generated.domain_level is None

def test_procedural_reproducible_and_labeled_synthetic():
    forge = EnemyForgeSkill()
    req = GenerateEnemyRequest(template="procedural", archetype="control", difficulty=4, seed=99)
    a = forge.generate(req).model_dump(exclude={"id"})
    b = forge.generate(req).model_dump(exclude={"id"})
    assert a == b
    assert a["origin"] == "synthetic"
    assert a["approved_for_real_combat"] is False
    assert all(t["status"] == "synthetic" for t in a["techniques"])
    assert a["output_level"] is not None

def test_learning_lab_refuses_to_treat_test_as_result():
    forge = EnemyForgeSkill()
    enemy = forge.generate(GenerateEnemyRequest())
    akira = {
        "id": "akira", "name": "Akira Uchiha", "hp": 600, "ea": 731,
        "max_hp": None, "spirit": None, "form": "none", "main_actions": 2,
        "reaction_available": True, "fangs_used": 0, "maw_used": 0, "amaterasu_used": 0
    }
    report = LearningLabSkill().evaluate(enemy, akira.copy(), "opening")
    assert report["actual_result"] is None
    assert report["verified"] is False
    assert report["source"] == "synthetic_benchmark"
    assert akira["ea"] == 731
    assert report["candidates_considered"] >= 1

def test_enemy_generate_and_evaluate_api_does_not_change_akira(client):
    before = client.get("/api/characters").json()[0]
    enemy_response = client.post("/api/lab/enemies/generate", json={
        "template": "procedural", "archetype": "assault", "difficulty": 3, "seed": 7
    })
    assert enemy_response.status_code == 201
    enemy = enemy_response.json()
    assert enemy["origin"] == "synthetic"
    assert len(client.get("/api/lab/enemies").json()) == 1
    run_response = client.post("/api/lab/evaluate", json={
        "enemy_id": enemy["id"], "character_id": "akira", "scenario": "close_combat"
    })
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["verified"] is False
    assert run["actual_result"] is None
    assert run["candidates_considered"] >= 1
    after = client.get("/api/characters").json()[0]
    assert after == before
    assert len(client.get("/api/lab/runs").json()) == 1

def test_batch_creates_only_synthetic_benchmarks(client):
    before = client.get("/api/characters").json()
    result = client.post("/api/lab/benchmarks", json={
        "archetype": "balanced", "difficulty": 2, "start_seed": 30,
        "samples": 5, "character_id": "akira"
    })
    assert result.status_code == 200
    data = result.json()
    assert data["summary"]["tests"] == 5
    assert len(data["runs"]) == 5
    assert set(run["source"] for run in data["runs"]) == {"synthetic_benchmark"}
    assert all(not run["verified"] and run["actual_result"] is None for run in data["runs"])
    assert client.get("/api/characters").json() == before
    assert len(client.get("/api/events").json()) == 1  # só o Akira inicial

def test_batch_limits_and_missing_enemy(client):
    result = client.post("/api/lab/benchmarks", json={
        "samples": 30, "start_seed": 0
    })
    assert result.status_code == 422
    missing = client.post("/api/lab/evaluate", json={
        "enemy_id": "inexistente", "character_id": "akira", "scenario": "opening"
    })
    assert missing.status_code == 404
