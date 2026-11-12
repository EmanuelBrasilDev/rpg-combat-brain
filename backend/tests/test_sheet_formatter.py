"""Exportação estilizada de fichas, sem inventar cooldowns ou alterar estado."""
from copy import deepcopy

from app.models import Character
from app.skills.character_sheet_formatter import CharacterSheetFormatterSkill


def test_akira_export_preserves_style_and_confirmed_values(client):
    resp = client.get("/api/characters/akira/export")
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "markdown"
    assert data["character_name"] == "Akira Uchiha"
    output = data["content"]
    for line in (
        "# Akira Uchiha",
        "HP (600)",
        "EA (731)",
        "# Atributos",
        "* Força (26/50; mod. +8)",
        "* Velocidade (34/50; mod. +12)",
        "* Resistência (26/50; mod. +8)",
        "* Intelecto (30/50; mod. +10)",
        "* Espírito (34/50; mod. +12)",
        "# Dragon Scales (?t restantes)",
        "* Durabilidade (100)",
        "* Defesa (8d8)",
        "* Chamas (8d8)",
        "# Dragon Assault (?t restantes)",
        "* Velocidade (8d2)",
        "* Boost (8d2)",
        "* Dano (8d8)",
        "* Chamas (8d3)",
        "# Mangekyō Sharingan",
        "* Amaterasu (0/1 uso)",
        "# Habilidades Extras",
        "# Técnicas",
        "* Crimson Dragon's Fangs (0/6 usos) — cooldown ?c",
        "* Crimson Dragon's Maw (0/6 usos) — cooldown ?c",
        "# Itens",
        "* Kenrykat (8d5 + 5d2) — Kokusen (0/3 críticos)",
    ):
        assert line in output, line
    assert "Mega Brain" not in output  # não existe na ficha!
    assert "Destreza" not in output
    assert "0c" not in output  # nenhum cooldown foi confirmado
    assert "0t" not in output  # turnos restantes não são rastreados
    assert data["content"].endswith("\n")


def test_export_uses_current_sheet_after_changes_and_is_read_only(client):
    initial_events = len(client.get("/api/events").json())
    before = client.get("/api/characters").json()
    initial = client.get("/api/characters/akira/export").json()["content"]
    assert len(client.get("/api/events").json()) == initial_events
    assert client.get("/api/characters").json() == before
    changes = client.patch("/api/characters/akira", json={
        "hp": 565, "ea": 600, "form": "scales",
        "fangs_used": 2, "maw_used": 1, "amaterasu_used": 1,
        "critical_count": 2, "speed": 36
    })
    assert changes.status_code == 200
    updated = client.get("/api/characters/akira/export").json()["content"]
    assert updated != initial
    for line in (
        "HP (565)", "EA (600)", "* Velocidade (36/50; mod. +13)",
        "* Estado (ativa)", "* Crimson Dragon's Fangs (2/6 usos)",
        "* Crimson Dragon's Maw (1/6 usos)", "* Amaterasu (1/1 uso)",
        "Kokusen (2/3 críticos)"
    ):
        assert line in updated
    latest_count = len(client.get("/api/events").json())
    client.get("/api/characters/akira/export")
    assert len(client.get("/api/events").json()) == latest_count


def test_generic_enemy_export_respects_unknowns_and_custom_fields(client):
    created = client.post("/api/characters", json={
        "name": "Maldição Grau 2", "team": "enemy"
    }).json()
    updated = client.patch(f"/api/characters/{created['id']}", json={
        "hp": 300, "tier": "Grau 2",
        "speed": 38, "spirit": 24,
        "techniques": [
            {
                "name": "Rajada Oculta", "cooldown": 3, "ea_cost": 20,
                "damage": "4d8+2d2", "effect": "causa lentidão",
                "status": "confirmed", "category": "technique"
            },
            {
                "name": "Visão Ampliada", "cooldown": 0,
                "status": "confirmed", "category": "extra"
            }
        ],
        "items": [{"name": "Amuleto", "effect": "proteção"}],
    })
    assert updated.status_code == 200, updated.text
    output = client.get(f"/api/characters/{created['id']}/export").json()["content"]
    assert "# Maldição Grau 2" in output
    assert "HP (300)" in output
    assert "EA (?)" in output
    assert "Grau (Grau 2)" in output
    assert "* Força (?/50)" in output
    assert "* Velocidade (38/50; mod. +14)" in output
    assert "* Espírito (24/50; mod. +7)" in output
    assert "* Visão Ampliada (0c)" in output
    assert "* Rajada Oculta (3c; EA 20; dano 4d8+2d2) — causa lentidão" in output
    assert "* Amuleto — proteção" in output
    assert "Kenrykat" not in output
    assert "Amaterasu" not in output
    assert "Dragon Scales" not in output


def test_custom_items_abilities_and_effects_on_akira(client):
    response = client.patch("/api/characters/akira", json={
        "techniques": [
            {"name": "Mega Brain", "category": "extra", "cooldown": 0},
            {"name": "Lança Flamejante", "category": "technique",
             "cooldown": 2, "damage": "3d8", "ea_cost": 11}
        ],
        "items": [{"name": "Patuá", "damage": "1d6", "effect": "defesa extra"}],
        "effects": ["Reforço ativo", "Escudo espiritual"],
        "notes": "Combate durante tempestade."
    })
    assert response.status_code == 200
    content = client.get("/api/characters/akira/export").json()["content"]
    assert "# Habilidades Extras\n* Mega Brain (0c)" in content
    assert "# Técnicas" in content
    assert "* Lança Flamejante (2c; EA 11; dano 3d8)" in content
    assert "* Patuá (1d6) — defesa extra" in content
    assert "# Efeitos ativos" in content
    assert "* Reforço ativo" in content
    assert "Combate durante tempestade." in content


def test_synthetic_abilities_are_labeled(client):
    created = client.post("/api/characters", json={
        "name": "Maldição Sintética", "team": "enemy"
    }).json()
    assert client.patch(f"/api/characters/{created['id']}", json={
        "techniques": [{"name": "Corte Inventado", "status": "synthetic"}],
        "sheet_origin": "synthetic"
    }).status_code == 200
    text = client.get(f"/api/characters/{created['id']}/export").json()["content"]
    assert "Corte Inventado (?c) [SINTÉTICA, não confirmada]" in text
    assert "ATENÇÃO: ficha sintética, não oficial." in text


def test_chat_can_export_selected_or_named_character(client):
    foe = client.post("/api/characters", json={
        "name": "Maldição Anciã", "team": "enemy"
    }).json()
    response = client.post("/api/chat", json={"message": "Transforme a ficha do Akira em texto"}).json()
    assert response["intent"] == "sheet_export"
    assert response["report_id"] is None
    assert "# Akira Uchiha" in response["answer"]

    other = client.post("/api/chat", json={
        "message": "Exporte a ficha estilizada da Maldição Anciã"
    }).json()
    assert other["intent"] == "sheet_export"
    assert "# Maldição Anciã" in other["answer"]
    assert "Kenrykat" not in other["answer"]

    chosen = client.post("/api/chat", json={
        "message": "/ficha-texto", "character_id": foe["id"]
    }).json()
    assert chosen["intent"] == "sheet_export"
    assert "# Maldição Anciã" in chosen["answer"]


def test_export_missing_sheet_is_404(client):
    response = client.get("/api/characters/nao-existe/export")
    assert response.status_code == 404


def test_formatter_never_mutates_input_and_escapes_newlines():
    sheet = Character(id="x", name="Maldição\nCom Nome", team="enemy",
                      techniques=[{"name": "Técnica\nSombria"}]).model_dump()
    before = deepcopy(sheet)
    output = CharacterSheetFormatterSkill().format(sheet)
    assert sheet == before
    assert "# Maldição Com Nome" in output
    assert "* Técnica Sombria (?c)" in output


def test_registered_canonical_technique_data_are_not_lost(client):
    patch = client.patch("/api/characters/akira", json={
        "max_hp": 700,
        "max_ea": 800,
        "techniques": [
            {"name": "Crimson Dragon's Fangs", "cooldown": 2, "ea_cost": 25,
             "damage": "39d10", "status": "confirmed"},
            {"name": "Amaterasu", "cooldown": 4, "status": "confirmed"},
        ],
        "items": [
            {"name": "Kenrykat", "damage": "9d5", "effect": "lâmina modificada"}
        ]
    })
    assert patch.status_code == 200, patch.text
    content = client.get("/api/characters/akira/export").json()["content"]
    assert "HP (600/700)" in content
    assert "EA (731/800)" in content
    assert "Crimson Dragon's Fangs (0/6 usos) — cooldown 2c — EA 25; dano 39d10" in content
    assert content.count("Crimson Dragon's Fangs") == 1
    assert "* Cooldown de Amaterasu (4c)" in content
    assert "* Kenrykat (9d5) — Kokusen (0/3 críticos); lâmina modificada" in content
    assert content.count("Kenrykat") == 1
