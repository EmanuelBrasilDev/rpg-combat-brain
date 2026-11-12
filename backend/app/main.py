"""FastAPI local — a mesma API poderá ser hospedada separadamente no futuro."""
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .catalog import load_catalog
from .models import ChatRequest, ChatResponse, CreateCharacter
from . import store, chat_store, lab_store, combat_store
from .combat_store import CombatFeedback, CombatReportConflict, EnemyDiscoveryEdit
from .skills.combat_event_tracker import CombatEventTracker
from .skills.combat_context_analyzer import CombatContextAnalyzer
from .skills.combat_learning import CombatLearningSkill
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
    combat_store.initialize()
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
tracker = CombatEventTracker()
context_skill = CombatContextAnalyzer()
combat_learning = CombatLearningSkill()

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
    report_id = None
    draft = tracker.draft(body.message, character["id"], sheets)
    # Um relato é uma proposta, não um evento aplicado à ficha.
    if draft and parsed.intent not in ("update", "undo", "new_turn", "rules"):
        report_id = combat_store.add_draft(draft)["id"]
        needs_confirmation = True
    context = context_skill.summarize(
        character, sheets,
        combat_store.list_reports("confirmed", 30),
        combat_store.list_reports("pending", 30)
    )

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
    elif parsed.intent == "combat_report":
        if report_id is not None:
            rolls = draft.get("rolls", []) if draft else []
            results = [
                f"{item['actor']}: {item['total']}" + (
                    f" ({item['expression']})" if item.get("expression") else ""
                ) for item in rolls if item.get("total") is not None
            ]
            changes = draft.get("proposed_updates", {}) if draft else {}
            summary = [
                f"**Relato #{report_id} preparado para revisão.**",
                f"Técnicas reconhecidas: {', '.join(draft['techniques']) or 'nenhuma identificada'}.",
                f"Novas habilidades inimigas propostas: {', '.join(x['name'] for x in draft.get('proposed_discoveries', [])) or 'nenhuma'}.",
                f"Rolagens informadas: {', '.join(results) or 'nenhum total explícito'}.",
                f"Resultado narrado: {draft['outcome']}.",
                f"Estados finais candidatos: {changes or 'nenhum'}",
                "Revise as habilidades descobertas (inimigo, nome, efeito e cooldown) no painel antes de confirmar. "
                "HP/EA só serão alterados por valores FINAIS explícitos; não há descontos automáticos."
            ]
            answer = "\n".join(summary)
            warnings.extend(draft["warnings"])
        else:
            answer = "Não identifiquei um acontecimento concluído com confiança. "
            answer += "Descreva o que foi executado e as rolagens, ou atualize a ficha diretamente."
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
        prompt = context_skill.tactical_prompt(body.message, context)
        report = response_skill.format(decision.analyze(character, enemies, prompt))
        answer = report["answer"]
        alternatives = report["alternatives"]
        warnings = report["warnings"] + context["warnings"]
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
    if report_id is not None and parsed.intent != "combat_report":
        answer += f"\n\n**Relato #{report_id} aguardando confirmação.** "
        answer += "A estratégia acima não considera o relato pendente como fato. Revise no painel de eventos."
        warnings.extend(draft["warnings"])
    chat_store.add_message("user", body.message)
    chat_store.add_message("assistant", answer, {"alternatives": alternatives, "warnings": warnings, "report_id": report_id})
    return ChatResponse(intent=parsed.intent, answer=answer,
                        alternatives=alternatives, warnings=warnings,
                        requires_confirmation=needs_confirmation, report_id=report_id)


# RELATOS DE COMBATE REAIS — confirmação humana, sem subtração automática.
@app.get("/api/combat/reports")
def reports(status: Literal["pending", "confirmed", "discarded"] | None = None):
    return combat_store.list_reports(status)

@app.patch("/api/combat/reports/{report_id}/discovery")
def edit_report_discovery(report_id: int, body: EnemyDiscoveryEdit):
    try:
        report = combat_store.edit_discovery(report_id, body)
    except CombatReportConflict as error:
        raise HTTPException(409, str(error))
    if report is None:
        raise HTTPException(404, "Relato não encontrado.")
    return report

@app.post("/api/combat/reports/{report_id}/review")
def review_report(report_id: int, decision: Literal["confirmed", "discarded"] = Body(embed=True)):
    try:
        report = combat_store.review(report_id, decision)
    except CombatReportConflict as error:
        raise HTTPException(409, str(error))
    if report is None:
        raise HTTPException(404, "Relato não encontrado.")
    return report

@app.post("/api/combat/reports/{report_id}/feedback")
def feedback_report(report_id: int, body: CombatFeedback):
    try:
        report = combat_store.set_feedback(report_id, body)
    except CombatReportConflict as error:
        raise HTTPException(409, str(error))
    if report is None:
        raise HTTPException(404, "Relato não encontrado.")
    return report

@app.get("/api/learning/overview")
def learning_overview():
    return combat_learning.overview(combat_store.list_reports("confirmed", 150))


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


@app.post("/api/lab/enemies/{enemy_id}/adopt", status_code=201)
def adopt_lab_enemy(enemy_id: str):
    """Usuário escolhe explicitamente copiar uma ficha do laboratório para o combate."""
    enemy = lab_store.get_enemy(enemy_id)
    if enemy is None:
        raise HTTPException(404, "Ficha de laboratório não encontrada.")
    return store.create_from_enemy(EnemyProfile.model_validate(enemy))
