"""CombatEventTracker: transforma relatos passados em rascunhos auditáveis, sem aplicar dano implícito."""
import re
from .dice_roll_interpreter import DiceRollInterpreter, normalize
from ..catalog import load_catalog

PAST_EVENTS = re.compile(
    r"\b(?:usou|utilizou|atacou|tentei|esquivei|bloqueei|recebi|tomei|tirei|tirou|"
    r"rolou|rolei|gastei|gastou|acertou|falhou|atualizei|atualizou|"
    r"ficou|sofri|perdi|consumi|consumiu|aplicou|deu\s+\d+|"
    r"executou|queimou|defendeu|desviou)\b"
)
FUTURE_MARKERS = re.compile(r"\b(?:vou\s+usar|pretendo\s+usar|poderia\s+usar|usaria|tentaria|se\s+eu\s+usar)\b")
FINAL_RESOURCE = re.compile(
    r"\b(?:hp|ea)\s+(?:d[oa]\s+)?([\wÀ-ÿ \-']+?)\s+(?:ficou\s+em|para)\s+(\d{1,6})",
    re.IGNORECASE
)
SELF_RESOURCE = re.compile(
    r"\b(?:(?:meu|minha|o)\s+)?(hp|ea)\s+(?:atual(?:izado|izada)?\s+)?"
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

    def draft(self, message: str, character_id: str, characters: list[dict]) -> dict | None:
        text = normalize(message)
        if not PAST_EVENTS.search(text) or FUTURE_MARKERS.search(text):
            return None
        rolls = self.rolls.parse(message)
        actor = next((c for c in characters if c["id"] == character_id), None)
        if actor is None:
            return None
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
        updates: dict[str, dict[str, int]] = {}
        for match in NAMED_RESOURCE.finditer(message):
            field, name, value = match.groups()
            possible = self._character(name.strip(), characters)
            if possible is not None:
                updates.setdefault(possible["id"], {})[field.lower()] = int(value)
        for match in SELF_RESOURCE.finditer(message):
            # Não interpretar "HP do inimigo para X" como HP do Akira.
            pre = normalize(message[max(0, match.start()-10):match.start()])
            after = normalize(message[match.start():min(len(message), match.end()+70)])
            if " do " in after[:26] or " da " in after[:26]:
                continue
            field, value = match.groups()
            updates.setdefault(actor["id"], {})[field.lower()] = int(value)
        # "atualizei meu HP para 565" é capturado pelo padrão acima.
        explicit_reaction = bool(re.search(
            r"\b(?:gastei|consumi|usei)\s+(?:a\s+)?(?:minha\s+)?reacao\b|"
            r"\b(?:minha\s+)?reacao\s+(?:foi\s+)?(?:consumida|gasta)\b", text
        ))
        if explicit_reaction:
            updates.setdefault(actor["id"], {})["reaction_available"] = False
        snapshots = {
            c["id"]: {"hp": c.get("hp"), "ea": c.get("ea"),
                      "reaction_available": c.get("reaction_available")}
            for c in characters if c["id"] in updates
        }
        warnings = []
        if damage_match:
            warnings.append("O dano informado é registrado como observação; sem HP final, não será descontado automaticamente.")
        if ea_spent:
            warnings.append("EA gasta é observação; sem EA final confirmada, não será subtraída automaticamente.")
        if not updates:
            warnings.append("Nenhuma mudança absoluta de ficha identificada. Confirmar o relato não alterará HP/EA.")
        if rolls and any(roll["total"] is None for roll in rolls):
            warnings.append("Expressões de dados sem resultado foram mantidas como fórmulas, não como rolagens executadas.")
        return {
            "message": message, "character_id": character_id, "rolls": rolls,
            "techniques": list(dict.fromkeys(detected)),
            "outcome": outcome, "enemy_attack_observed": enemy_attack,
            "damage_received": int(damage_match.group(1)) if damage_match else None,
            "ea_spent": int(ea_spent.group(1)) if ea_spent else None,
            "proposed_updates": updates, "sheet_snapshots": snapshots,
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
