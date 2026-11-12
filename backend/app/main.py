"""FastAPI local — a mesma API poderá ser hospedada separadamente no futuro."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .catalog import load_catalog
from .models import ChatRequest, ChatResponse, CreateCharacter
from . import store, chat_store, lab_store
from .lab_models import EnemyProfile, GenerateEnemyRequest, EvaluateRequest, BatchRequest
from .skills.enemy_forge import EnemyForgeSkill
from .skills.learning_lab import LearningLabSkill, SCENARIOS
from .skills.character_sheet_analyzer import CharacterSheetAnalyzer
from .skills.combat_interpreter import interpret
from .skills.tactical_decision import TacticalDecision
from .skills.tactical_response import TacticalResponse
from .skills.knowledge import RulebookSkill, AkiraProfileSkill
from .skills.battle_update import BattleUpdateSkill

@asynccontextmanager
async def lifespan(app: FastAPI):
    store.initialize()
    lab_store.initialize()
    yield

app = FastAPI(title="RPG Combat Brain", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)

analyzer = CharacterSheetAnalyzer()
decision = TacticalDecision()
response_skill = TacticalResponse()
rulebook_skill = RulebookSkill()
akira_skill = AkiraProfileSkill()
updates = BattleUpdateSkill()
enemy_forge = EnemyForgeSkill()
learning_lab = LearningLabSkill()

@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "local-first", "ai_api_required": False}

@app.get("/api/catalog")
def catalog():
    return load_catalog()

@app.get("/api/characters")
def characters():
    return store.list_characters()

@app.post("/api/characters", status_code=201)
def create_character(body: CreateCharacter):
    return store.create_character(body.name, body.team)

@app.patch("/api/characters/{id}")
def patch_character(id: str, changes: dict = Body(...)):
    if "id" in changes or "team" in changes:
        raise HTTPException(400, "ID e equipe não podem ser alterados por esta rota.")
    try:
        updated = store.update_character(id, changes)
    except ValidationError as error:
        raise HTTPException(422, error.errors(include_context=False))
    if updated is None:
        raise HTTPException(404, "Ficha não encontrada.")
    return updated

@app.get("/api/events")
def events():
    return store.list_events()

@app.post("/api/events/undo")
def undo():
    sheet = store.undo_last()
    if sheet is None:
        raise HTTPException(409, "Não há uma edição recente passível de desfazer.")
    return sheet

@app.post("/api/turns/next")
def next_turn(character_id: str = Body(embed=True)):
    if not store.get_character(character_id):
        raise HTTPException(404, "Ficha não encontrada.")
    return {"characters": updates.next_turn(character_id)}

@app.get("/api/messages")
def messages():
    return chat_store.list_messages()

@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    sheets = store.list_characters()
    character = next((c for c in sheets if c["id"] == body.character_id), None)
    if character is None:
        raise HTTPException(404, "Ficha ativa não encontrada.")
    parsed = interpret(body.message, sheets)
    warnings = []
    alternatives = []
    needs_confirmation = False

    if parsed.intent == "update" and parsed.update:
        character_id, field, value = parsed.update
        try:
            saved = store.update_character(character_id, {field: value}, kind="chat_update")
        except ValidationError as error:
            raise HTTPException(422, error.errors(include_context=False))
        answer = "Atualização confirmada e registrada.\n" + analyzer.summarize(saved)
    elif parsed.intent == "undo":
        undone = store.undo_last()
        answer = "Última edição desfeita.\n" + analyzer.summarize(undone) if undone else "Nenhuma edição recente disponível para desfazer."
    elif parsed.intent == "new_turn":
        updates.next_turn(character['id'])
        answer = "Novo turno de " + character['name'] + " registrado: ações principais e bônus restauradas, reação disponível. Efeitos e cooldowns não foram alterados automaticamente."
    elif parsed.intent == "unknown_character":
        answer = "Não encontrei essa ficha. Confira o nome exato no painel de personagens."
    elif parsed.intent == "rules":
        answer = rulebook_skill.turn_rules() + "\nHá também regras específicas e pendências listadas no arsenal do site."
    elif parsed.intent == "ability":
        answer = akira_skill.describe_ability(body.message) or "Não encontrei a técnica solicitada no catálogo. Confira o nome no Arsenal."
    elif parsed.intent == "sheet":
        named = next((c for c in sheets if c["name"].casefold() in body.message.casefold()), None)
        if any(word in body.message.casefold() for word in ("todos", "aliados", "inimigos", "equipe")):
            answer = analyzer.compare(sheets)
        else:
            answer = analyzer.summarize(named or character)
        warnings = ["Campos desconhecidos são mantidos como pendentes, não estimados."]
    elif parsed.intent == "tactics":
        enemies = [c for c in sheets if c["team"] == "enemy"]
        report = response_skill.format(decision.analyze(character, enemies, body.message))
        answer = report["answer"]
        alternatives = report["alternatives"]
        warnings = report["warnings"]
    else:
        answer = (
            "Sou o RPG Combat Brain, um assistente de regras e estratégia local.\n"
            "Você pode pedir 'analise uma abertura', 'melhor combo agora', 'devo bloquear?', "
            "'qual a ficha do Akira?' ou 'mostre os inimigos'.\n"
            "Para atualizar uma ficha por chat, use '/set akira ea 400' ou "
            "'atualiza o HP do Akira Uchiha para 550'.\n"
            "Ações planejadas NÃO alteram recursos até serem confirmadas."
        )
        needs_confirmation = True
    chat_store.add_message("user", body.message)
    chat_store.add_message("assistant", answer, {"alternatives": alternatives, "warnings": warnings})
    return ChatResponse(intent=parsed.intent, answer=answer,
                        alternatives=alternatives, warnings=warnings,
                        requires_confirmation=needs_confirmation)


# LABORATÓRIO DE APRENDIZADO — dados simulados NUNCA alteram a batalha real.
@app.get("/api/lab/enemies")
def lab_enemies():
    return lab_store.list_enemies()

@app.post("/api/lab/enemies/generate", status_code=201)
def generate_lab_enemy(body: GenerateEnemyRequest):
    profile = enemy_forge.generate(body)
    return lab_store.add_enemy(profile)

@app.get("/api/lab/runs")
def lab_runs():
    return lab_store.list_runs()

@app.post("/api/lab/evaluate")
def evaluate_lab(body: EvaluateRequest):
    opponent = lab_store.get_enemy(body.enemy_id)
    if opponent is None:
        raise HTTPException(404, "Adversário de teste não encontrado.")
    character = store.get_character(body.character_id)
    if character is None:
        raise HTTPException(404, "Ficha ativa não encontrada.")
    try:
        run = learning_lab.evaluate(EnemyProfile.model_validate(opponent), character, body.scenario)
    except ValueError as error:
        raise HTTPException(422, str(error))
    return lab_store.add_run(run)

@app.post("/api/lab/benchmarks")
def benchmark_lab(body: BatchRequest):
    character = store.get_character(body.character_id)
    if character is None:
        raise HTTPException(404, "Ficha ativa não encontrada.")
    if body.start_seed + body.samples > 1_000_000:
        raise HTTPException(422, "Sementes ultrapassam o limite configurado.")
    if character["id"] != "akira":
        raise HTTPException(422, "O motor de recomendações atual suporta apenas Akira.")
    scenarios = list(SCENARIOS)
    result = []
    for index in range(body.samples):
        profile = enemy_forge.generate(GenerateEnemyRequest(
            template="procedural", archetype=body.archetype,
            difficulty=body.difficulty, seed=body.start_seed + index
        ))
        lab_store.add_enemy(profile)
        run = learning_lab.evaluate(profile, character, scenarios[index % len(scenarios)])
        result.append(lab_store.add_run(run))
    return {"summary": learning_lab.benchmark_summary(result), "runs": result}
