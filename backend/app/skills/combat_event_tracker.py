"""CombatEventTracker: transforma relatos passados em rascunhos auditáveis, sem aplicar dano implícito."""
import re
from .dice_roll_interpreter import DiceRollInterpreter, normalize
from .enemy_ability_discovery import EnemyAbilityDiscoverySkill
from .mega_brain import MegaBrainSkill
from ..catalog import load_catalog

PAST_EVENTS = re.compile(
    r"\b(?:usou|utilizou|atacou|tentei|esquivei|bloqueei|recebi|tomei|tirei|tirou|"
    r"rolou|rolei|gastei|gastou|acertou|falhou|atualizei|atualizou|"
    r"ficou|sofri|perdi|consumi|consumiu|aplicou|deu\s+\d+|"
    r"executou|queimou|defendeu|desviou|ativei|ativou)\b"
)
FUTURE_MARKERS = re.compile(r"\b(?:vou\s+usar|pretendo\s+usar|poderia\s+usar|usaria|tentaria|se\s+eu\s+usar)\b")
FINAL_RESOURCE = re.compile(
    r"\b(?:hp|ea)\s+(?:d[oa]\s+)?([\wÀ-ÿ \-']+?)\s+(?:ficou\s+em|para)\s+(\d{1,6})",
    re.IGNORECASE
)
SELF_RESOURCE = re.compile(
    r"\b(?:meu|minha)\s+(hp|ea)\s+(?:atual(?:izado|izada)?\s+)?"
    r"(?:ficou\s+em|para|em)\s+(\d{1,6})\b",
    re.IGNORECASE
)
NAMED_RESOURCE = re.compile(
    r"\b(hp|ea)\s+d[oa]\s+([\wÀ-ÿ \-']+?)\s+(?:ficou\s+em|para|em)\s+(\d{1,6})\b",
    re.IGNORECASE
)


class CombatEventTracker:
    def __init__(self):
        self.rolls = DiceRollInterpreter()
        self.discovery = EnemyAbilityDiscoverySkill()

    def draft(self, message: str, character_id: str, characters: list[dict]) -> dict | None:
        text = normalize(message)
        discoveries = self.discovery.extract(message, characters)
        if (not PAST_EVENTS.search(text) and not discoveries) or FUTURE_MARKERS.search(text):
            return None
        rolls = self.rolls.parse(message)
        actor = next((c for c in characters if c["id"] == character_id), None)
        if actor is None:
            return None
        # Somente um resultado explicitamente NATURAL de d20 pode ser
        # associado ao limiar crítico. Totais somados a bônus não qualificam.
        if actor["id"] == "akira" and actor.get("mega_brain_active"):
            for roll in rolls:
                context = normalize(roll.get("context") or "")
                if (roll["actor"] == "player" and roll["total"] is not None
                    and re.search(r"\bd20\b", context)
                    and re.search(r"\b(?:natural|puro|sem modificador|sem bonus)\b", context)):
                    roll["mega_brain_critical"] = MegaBrainSkill.is_critical(
                        actor, roll["total"]
                    )
        detected = []
        for item in load_catalog()["abilities"]:
            if normalize(item["name"]) in text:
                detected.append(item["name"])
        for participant in characters:
            for technique in participant.get("techniques", []):
                if normalize(technique["name"]) in text:
                    detected.append(technique["name"])
        # Em uma cena simples, o nome do golpe pode estar em uma ficha de inimigo.
        # Não presume quem executou a técnica se o texto não identifica o autor.
        enemy_attack = bool(re.search(r"\b(?:inimigo|maldicao|mahito|adversario|ele)\b.{0,90}"
                                      r"\b(?:atacou|usou|utilizou|acertou)\b", text))
        outcome = "unknown"
        if re.search(r"\b(?:falhou|errou|nao acertou|nao conseguiu|esquivei)\b", text):
            outcome = "miss_or_defense"
        elif re.search(r"\b(?:acertou|atingiu|recebi|sofri)\b", text):
            outcome = "hit_reported"
        damage_match = re.search(r"\b(?:recebi|sofri|tomei)\s+(\d{1,5})\s+(?:de\s+)?dano\b", text)
        ea_spent = re.search(r"\b(?:gastei|consumi)\s+(\d{1,5})\s*ea\b", text)
        # Somente estados ABSOLUTOS poderão ser escritos ao confirmar o relato.
        # Quantidade de dano/EA consumida nunca é subtraída automaticamente.
        updates: dict[str, dict] = {}
        mega_warnings = []
        for match in NAMED_RESOURCE.finditer(message):
            field, name, value = match.groups()
            possible = self._character(name.strip(), characters)
            if possible is not None:
                updates.setdefault(possible["id"], {})[field.lower()] = int(value)
        for match in SELF_RESOURCE.finditer(message):
            # Exige possessivo explícito (meu/minha); "o HP" sozinho é ambíguo.
            field, value = match.groups()
            updates.setdefault(actor["id"], {})[field.lower()] = int(value)
        # "atualizei meu HP para 565" é capturado pelo padrão acima.
        explicit_reaction = bool(re.search(
            r"\b(?:gastei|consumi|usei)\s+(?:a\s+)?(?:minha\s+)?reacao\b|"
            r"\b(?:minha\s+)?reacao\s+(?:foi\s+)?(?:consumida|gasta)\b", text
        ))
        if explicit_reaction:
            updates.setdefault(actor["id"], {})["reaction_available"] = False
        if actor["id"] == "akira":
            activated = bool(re.search(r"\b(?:ativei|akira\s+ativou)\s+(?:a\s+|o\s+)?mega\s+brain\b", text))
            suffered_cc = bool(re.search(
                r"\b(?:sofri|fiquei|fui|akira\s+sofreu|akira\s+ficou)\b"
                r".{0,60}\b(?:stun|paralisi[a-z]*|paralisad[a-z]*|fear|"
                r"atordoad[a-z]*|amedrontad[a-z]*|cc)\b", text
            ))
            skill = MegaBrainSkill()
            if activated and suffered_cc:
                mega_warnings.append(
                    "Ativação de Mega Brain e CC no mesmo relato: revise separadamente a ordem dos fatos."
                )
            elif activated:
                try:
                    updates.setdefault("akira", {}).update(skill.activate_changes(actor))
                    mega_warnings.append(
                        "Ativação relatada: após confirmar, serão consumidas TODAS as ações bônus "
                        "do turno, sem gastar EA. Duração 1 turno e cooldown de 2 turnos."
                    )
                except ValueError as error:
                    mega_warnings.append(f"Mega Brain não foi aplicada: {error}")
            elif suffered_cc and actor.get("mega_brain_active"):
                updates.setdefault("akira", {}).update(skill.interrupt_changes(actor))
                mega_warnings.append(
                    "CC sofrido por Akira: confirmar encerrará Mega Brain, preservando o cooldown."
                )
        snapshots = {
            c["id"]: {"hp": c.get("hp"), "ea": c.get("ea"),
                      "reaction_available": c.get("reaction_available"),
                      "bonus_actions": c.get("bonus_actions"),
                      "mega_brain_active": c.get("mega_brain_active"),
                      "mega_brain_turns_remaining": c.get("mega_brain_turns_remaining"),
                      "mega_brain_cooldown_remaining": c.get("mega_brain_cooldown_remaining")}
            for c in characters if c["id"] in updates
        }
        warnings = list(mega_warnings)
        if damage_match:
            warnings.append("O dano informado é registrado como observação; sem HP final, não será descontado automaticamente.")
        if ea_spent:
            warnings.append("EA gasta é observação; sem EA final confirmada, não será subtraída automaticamente.")
        if discoveries:
            warnings.append("Técnicas reveladas ficam pendentes até você confirmar nome, inimigo e cooldown. Dados não informados não serão inventados.")
        if not updates and not discoveries:
            warnings.append("Nenhuma atualização automática de ficha identificada; o relato será apenas lembrado.")
        if any(roll.get("mega_brain_critical") is True for roll in rolls):
            warnings.append(
                "Mega Brain: rolagem NATURAL de d20 15+ identificada como crítico; "
                "isso não altera automaticamente o contador de Kokusen."
            )
        if rolls and any(roll["total"] is None for roll in rolls):
            warnings.append("Expressões de dados sem resultado foram mantidas como fórmulas, não como rolagens executadas.")
        return {
            "message": message, "character_id": character_id, "rolls": rolls,
            "techniques": list(dict.fromkeys(detected)),
            "outcome": outcome, "enemy_attack_observed": enemy_attack,
            "damage_received": int(damage_match.group(1)) if damage_match else None,
            "ea_spent": int(ea_spent.group(1)) if ea_spent else None,
            "proposed_updates": updates, "sheet_snapshots": snapshots,
            "proposed_discoveries": discoveries,
            "warnings": warnings, "kind": "reported_observation",
        }

    @staticmethod
    def _character(text: str, characters: list[dict]) -> dict | None:
        norm = normalize(text).strip()
        if norm in ("akira", "akira uchiha"):
            return next((c for c in characters if c["id"] == "akira"), None)
        return next(
            (c for c in characters if normalize(c["name"]) == norm or c["id"] == norm),
            None,
        )
