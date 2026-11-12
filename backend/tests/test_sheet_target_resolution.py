"""Regressões: Guardião de Pedra, citações ao Akira como estilo e Enemy Forge.

Exportações e consultas devem selecionar a ficha certa, sem criar uma cópia de
combate nem retornar dados de outro personagem se o alvo for desconhecido.
"""
from app import lab_store
from app.skills.sheet_target_resolver import SheetTargetResolverSkill


def guardiao(client, *, seed=42, difficulty=3):
    result = client.post("/api/lab/enemies/generate", json={
        "template": "procedural", "archetype": "defense",
        "difficulty": difficulty, "seed": seed,
    })
    assert result.status_code == 201, result.text
    return result.json()


def test_lab_guardian_renders_itself_not_akira(client):
    enemy = guardiao(client)
    assert enemy["name"].startswith("Guardião de Pedra")
    real_before = client.get("/api/characters").json()
    events_before = client.get("/api/events").json()
    response = client.get(f"/api/lab/enemies/{enemy['id']}/export")
    assert response.status_code == 200, response.text
    content = response.json()["content"]
    assert response.json()["character_name"] == enemy["name"]
    assert content.startswith(f"# {enemy['name']}\n")
    assert f"HP ({enemy['hp']})" in content
    assert f"EA ({enemy['ea']})" in content
    assert "# Atributos" in content
    assert f"* Força ({enemy['strength']}/50;" in content
    assert "# Técnicas" in content
    assert enemy["techniques"][0]["name"] in content
    assert "[SINTÉTICA, não confirmada]" in content
    assert "FICHA DE LABORATÓRIO" in content
    assert "Premissas da geração" in content
    assert "Akira Uchiha" not in content
    assert "Mangekyō" not in content
    assert "Kenrykat" not in content
    assert "Mega Brain" not in content
    assert client.get("/api/characters").json() == real_before
    assert client.get("/api/events").json() == events_before


def test_chat_target_with_akira_style_reference_uses_guardian(client):
    enemy = guardiao(client)
    messages = [
        "Transforme a ficha do Guardião de Pedra em texto no mesmo modelo do Akira",
        "Formate a ficha do Guardião de Pedra no estilo da ficha do Akira",
        "Quero a ficha do guardiao de pedra em texto como a do Akira",
        "exporte a ficha estilizada do Guardião de Pedra igual à do Akira",
    ]
    for message in messages:
        result = client.post("/api/chat", json={
            "message": message, "character_id": "akira"
        })
        assert result.status_code == 200, (message, result.text)
        output = result.json()
        assert output["intent"] in ("sheet_export", "sheet")
        assert output["answer"].startswith("# " + enemy["name"]), (message, output)
        assert "HP (" + str(enemy["hp"]) + ")" in output["answer"]
        assert "Kenrykat" not in output["answer"]
        assert output["report_id"] is None
    assert len(client.get("/api/characters").json()) == 1  # apenas Akira
    assert len(client.get("/api/combat/reports").json()) == 0


def test_plain_sheet_query_finds_lab_guardian(client):
    enemy = guardiao(client, seed=99)
    result = client.post("/api/chat", json={
        "message": "Qual a ficha do Guardião de Pedra?"
    }).json()
    assert result["intent"] == "sheet"
    assert result["answer"].startswith("# " + enemy["name"])
    assert "Mangekyō" not in result["answer"]


def test_two_lab_guardians_same_base_name_require_disambiguation(client):
    first = guardiao(client, difficulty=2, seed=11)
    second = guardiao(client, difficulty=4, seed=12)
    response = client.post("/api/chat", json={
        "message": "Formate a ficha do Guardião de Pedra no modelo do Akira"
    }).json()
    assert response["intent"] == "sheet_export"
    assert "mais de uma ficha" in response["answer"]
    assert first["id"] in response["answer"]
    assert second["id"] in response["answer"]
    assert "# Akira Uchiha" not in response["answer"]
    exact = client.post("/api/chat", json={
        "message": "/ficha-texto " + second["id"]
    }).json()
    assert exact["intent"] == "sheet_export"
    assert exact["answer"].startswith("# " + second["name"])
    assert f"HP ({second['hp']})" in exact["answer"]


def test_full_lab_name_with_suffix_resolves_uniquely(client):
    first = guardiao(client, seed=11, difficulty=2)
    second = guardiao(client, seed=12, difficulty=4)
    result = client.post("/api/chat", json={
        "message": f"Exportar ficha de {first['name']} em texto"
    }).json()
    assert result["intent"] == "sheet_export"
    assert result["answer"].startswith("# " + first["name"])
    assert f"HP ({first['hp']})" in result["answer"]
    assert f"HP ({second['hp']})" not in result["answer"]


def test_named_combat_guardian_uses_real_edited_sheet(client):
    lab = guardiao(client, seed=13, difficulty=3)
    adopted = client.post("/api/lab/enemies/" + lab["id"] + "/adopt").json()
    assert adopted["team"] == "enemy"
    changed = client.patch("/api/characters/" + adopted["id"], json={"hp": 123})
    assert changed.status_code == 200
    response = client.post("/api/chat", json={
        "message": "Transforme a ficha do Guardião de Pedra em texto no modelo do Akira"
    }).json()
    # Quando a mesma ficha existe no combate e no lab, vale a versão adotada
    assert response["answer"].startswith("# " + adopted["name"])
    assert "HP (123)" in response["answer"]
    assert f"HP ({lab['hp']})" not in response["answer"]


def test_unknown_named_target_returns_error_not_akira(client):
    result = client.post("/api/chat", json={
        "message": "Transforme a ficha do Dragão Obsidiano em texto no modelo do Akira",
        "character_id": "akira",
    }).json()
    assert result["intent"] == "sheet_export"
    assert "Não encontrei a ficha" in result["answer"]
    assert "# Akira Uchiha" not in result["answer"]
    assert "Kenrykat" not in result["answer"]


def test_export_command_selected_sheet_still_works(client):
    enemy = client.post("/api/characters", json={
        "name": "Guardião de Pedra", "team": "enemy"
    }).json()
    result = client.post("/api/chat", json={
        "message": "/ficha-texto", "character_id": enemy["id"]
    }).json()
    assert result["answer"].startswith("# Guardião de Pedra")
    result_by_name = client.post("/api/chat", json={
        "message": "/ficha-texto Guardião de Pedra"
    }).json()
    assert result_by_name["answer"].startswith("# Guardião de Pedra")


def test_export_absent_lab_reference_is_404(client):
    assert client.get("/api/lab/enemies/not-a-valid-id/export").status_code == 404


def test_resolver_pure_and_does_not_confuse_other_reference_names():
    target = {"id": "enemy", "name": "Guardião de Pedra", "team": "enemy"}
    akira = {"id": "akira", "name": "Akira Uchiha", "team": "player"}
    resolver = SheetTargetResolverSkill()
    result = resolver.resolve(
        "Transforme a ficha do Guardião de Pedra no mesmo modelo do Akira Uchiha",
        "akira", [akira, target], []
    )
    assert result.source == "combat"
    assert result.record["id"] == "enemy"
    # Ficha inexistente não cai no selecionado.
    missing = resolver.resolve(
        "Transforme a ficha da Maldição Rubra no estilo do Akira",
        "akira", [akira, target], []
    )
    assert missing.record is None
