def test_seeded_akira(client):
    response = client.get("/api/characters")
    assert response.status_code == 200
    akira = response.json()[0]
    assert akira["name"] == "Akira Uchiha"
    assert akira["hp"] == 600 and akira["ea"] == 731
    assert akira["max_hp"] is None

def test_edit_and_undo(client):
    client.patch("/api/characters/akira", json={"ea": 400})
    assert client.get("/api/characters").json()[0]["ea"] == 400
    assert client.post("/api/events/undo").status_code == 200
    assert client.get("/api/characters").json()[0]["ea"] == 731

def test_chat_reads_and_writes(client):
    lookup = client.post("/api/chat", json={"message": "qual a ficha do Akira?"}).json()
    assert "731" in lookup["answer"]
    update = client.post("/api/chat", json={"message": "/set akira ea 500"}).json()
    assert update["intent"] == "update"
    assert client.get("/api/characters").json()[0]["ea"] == 500

def test_ambiguous_message_never_changes_sheet(client):
    client.post("/api/chat", json={"message": "Vou usar Fangs com 100 EA."})
    assert client.get("/api/characters").json()[0]["ea"] == 731

def test_create_enemy_and_analyze(client):
    enemy = client.post("/api/characters", json={"name": "Maldição de teste", "team": "enemy"})
    assert enemy.status_code == 201
    analysis = client.post("/api/chat", json={"message": "qual minha melhor abertura?"}).json()
    assert analysis["intent"] == "tactics"
    assert analysis["alternatives"]

def test_unknown_fields_rejected(client):
    response = client.patch("/api/characters/akira", json={"invented_field": 123})
    assert response.status_code == 422
