"""Hierarquia de graus de maldições, separada de dificuldade sintética."""
from app.skills.curse_grade import CurseGradeSkill
from app.skills.enemy_forge import EnemyForgeSkill
from app.lab_models import GenerateEnemyRequest


def test_grade_priority_is_inverted():
    grades = CurseGradeSkill()
    labels = ["Grau 4", "Grau 3", "Grau 2", "Grau 1", "Grau Especial"]
    assert [grades.priority(x) for x in labels] == [1, 2, 3, 4, 5]
    assert grades.compare("Grau 1", "Grau 3") == 1
    assert grades.compare("Grau 4", "Grau 2") == -1
    assert grades.compare("Grau Especial", "Grau 1") == 1
    assert grades.compare("Grau 3", "Grau 3") == 0


def test_unknown_tier_does_not_imply_strength():
    grade = CurseGradeSkill()
    assert grade.priority(None) is None
    assert grade.priority("Procedural (sem grau oficial)") is None
    assert grade.priority("Dificuldade 5") is None
    assert grade.priority("Grau 0") is None
    assert grade.compare("Grau 2", None) is None


def test_name_grade_parsing_and_case_insensitive():
    grade = CurseGradeSkill()
    assert grade.enemy_grade({"name": "MALDIÇÃO GRAU 3", "tier": None}) == "Grau 3"
    assert grade.enemy_grade({"name": "Mahito", "tier": "Grau Especial"}) == "Grau Especial"
    assert grade.enemy_grade({"name": "Maldição Grau 3", "tier": "Grau 1"}) == "Grau 1"


def test_high_grades_emit_caution_not_hardcoded_damage():
    grade = CurseGradeSkill()
    warnings = grade.cautions([
        {"name": "Maldição A", "tier": "Grau 1"},
        {"name": "Maldição B", "tier": "Grau 3"},
        {"name": "Maldição C", "tier": "Grau Especial"},
        {"name": "Maldição D", "tier": None},
    ])
    assert len(warnings) == 2
    assert "Maldição A" in warnings[0]
    assert "Maldição C" in warnings[1]
    assert "não confirma dano" in warnings[0]


def test_enemy_forge_procedural_difficulty_remains_independent():
    forge = EnemyForgeSkill()
    weak = forge.generate(GenerateEnemyRequest(template="procedural", difficulty=1, seed=8))
    strong = forge.generate(GenerateEnemyRequest(template="procedural", difficulty=5, seed=8))
    assert weak.hp < strong.hp
    assert weak.tier == strong.tier == "Procedural (sem grau oficial)"
    assert CurseGradeSkill().enemy_grade(weak.model_dump()) is None
    assert CurseGradeSkill().enemy_grade(strong.model_dump()) is None


def test_grade_1_advice_cautious_not_inverted(client):
    created = client.post("/api/characters", json={"name": "Maldição Arrasadora", "team": "enemy"}).json()
    assert client.patch(f"/api/characters/{created['id']}", json={"tier": "Grau 1"}).status_code == 200
    report = client.post("/api/chat", json={"message": "Qual a melhor abertura do Akira?"}).json()
    assert report["intent"] == "tactics"
    assert any("categoria elevada" in warning for warning in report["warnings"])
    grade3 = client.patch(f"/api/characters/{created['id']}", json={"tier": "Grau 3"})
    assert grade3.status_code == 200
    report3 = client.post("/api/chat", json={"message": "Qual a melhor abertura do Akira?"}).json()
    assert not any("categoria elevada" in warning for warning in report3["warnings"])
