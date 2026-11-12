"""EnemyAbilityDiscoverySkill — propõe técnicas observadas, não inventa regras.

Reconhece relatos de uso e alguns campos explícitos; após revisão humana,
vincula a técnica ao INIMIGO correto, sem atribuir cooldown/dano não relatado.
"""
import re

from .dice_roll_interpreter import normalize
from ..models import CombatTechnique


# Títulos após "usou" etc. Limites evitam engolir rolagens e outras ações.
_NAME = re.compile(
    r"\b(?:usou|utilizou|revelou|ativou|executou)\s+"
    r"(?:(?:a|o|uma|um)\s+)?"
    r"(?:(?:t[eé]cnica|habilidade|golpe|feiti[cç]o)\s+(?:chamad[oa]\s+)?)?"
    r"(?P<name>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9'’ -]{2,95}?)"
    r"(?=,|;|[.!?\n]|$|\s+(?:"
    r"e\s+(?:tirou|rolou|acertou|causou|gastou|aplicou|deu|revelou)|"
    r"que\s+(?:causa|deu|aplica|atingiu)|"
    r"com\s+(?:dano|um\s+total)|"
    r"causando|custando|custou|custa|"
    r"cooldown|recarga|cd\s*\d|"
    r"deixando|atingindo|"
    r"para\s+(?:acertar|atacar)"
    r")\b)",
    re.IGNORECASE,
)
# A forma explícita do chat é útil quando o nome possui "e", vírgulas etc:
# @tecnica Mahito | Transfiguração Ociosa | cd=2 | dano=4d8 | ea=30 | efeito=...
_COMMAND = re.compile(r"^@tecnica\s+(.+?)\s*\|\s*(.+?)(?:\s*\|\s*(.*))?$", re.IGNORECASE | re.DOTALL)
_COOLDOWN = re.compile(r"\b(?:cooldown|recarga|cd)\s*(?:de|:|=)?\s*(\d{1,3})\s*(?:c\b|turnos?\b)?", re.IGNORECASE)
_COOLDOWN_C = re.compile(r"\b(\d{1,3})c\b", re.IGNORECASE)
_EA = re.compile(r"\b(?:(?:custa|custou|gasta|gastou)\s*(\d{1,4})\s*ea|ea\s*(?:de|:|=)\s*(\d{1,4}))\b", re.IGNORECASE)
_DAMAGE = re.compile(r"\b(?:dano(?:\s+(?:de|foi))?\s*(?:de|:|=)?\s*)(\d{1,2}d\d{1,3}(?:\s*\+\s*(?:\d{1,2}d\d{1,3}|\d{1,4}))*)", re.IGNORECASE)
_EFFECT = re.compile(r"\befeito\s*(?::|=)\s*([^;\n.]{2,260})", re.IGNORECASE)
_UNNAMED = {"ataque", "uma tecnica", "tecnica", "um golpe", "habilidade", "um ataque", "seu golpe", "seu ataque"}


class EnemyAbilityDiscoverySkill:
    """Propõe descobertas; alterações só são aplicadas após confirmar relato."""

    @staticmethod
    def _enemy(name: str, characters: list[dict]) -> dict | None:
        needle = normalize(name).strip()
        matches = [c for c in characters if c["team"] == "enemy" and (
            normalize(c["name"]) == needle or c["id"] == needle
        )]
        return matches[0] if len(matches) == 1 else None

    def _target(self, message: str, characters: list[dict]) -> str | None:
        enemies = [c for c in characters if c["team"] == "enemy"]
        explicitly_named = [
            enemy for enemy in enemies
            if re.search(r"(?<!\w)" + re.escape(normalize(enemy["name"])) + r"(?!\w)",
                         normalize(message))
        ]
        if len(explicitly_named) == 1:
            return explicitly_named[0]["id"]
        if len(explicitly_named) > 1:
            return None
        # Nunca escolhe arbitrariamente entre múltiplos inimigos.
        return enemies[0]["id"] if len(enemies) == 1 else None

    @staticmethod
    def _fields(text: str) -> dict:
        cooldown = _COOLDOWN.search(text) or _COOLDOWN_C.search(text)
        ea = _EA.search(text)
        damage = _DAMAGE.search(text)
        effect = _EFFECT.search(text)
        return {
            "cooldown": int(cooldown.group(1)) if cooldown else None,
            "ea_cost": int(next(g for g in ea.groups() if g is not None)) if ea else None,
            "damage": re.sub(r"\s+", " ", damage.group(1)).strip() if damage else None,
            "effect": effect.group(1).strip() if effect else None,
        }

    def extract(self, message: str, characters: list[dict]) -> list[dict]:
        command = _COMMAND.match(message.strip())
        if command:
            target_label, name, extra = command.groups()
            target = self._enemy(target_label, characters)
            fields = self._fields(extra or "")
            return [{
                "enemy_id": target["id"] if target else None,
                "name": name.strip()[:100],
                **fields,
                "evidence": message[:500],
                "ignored": False
            }] if name.strip() else []
        discoveries: list[dict] = []
        # Don't interpret "vou usar" or ability proposals as an observed use.
        plain = normalize(message)
        if re.search(r"\b(?:vou|pretendo|poderia|deveria)\s+(?:usar|utilizar)\b", plain):
            return []
        target_id = self._target(message, characters)
        for match in list(_NAME.finditer(message))[:5]:
            name = re.sub(r"\s+", " ", match.group("name")).strip(" .,-:;")
            if len(name) < 3 or normalize(name) in _UNNAMED:
                continue
            # If speaker says "Akira usou" this is not an enemy technique.
            prefix = normalize(message[max(0, match.start() - 85):match.start()])
            if re.search(r"\b(?:eu|akira|aliado)\b[^.!?\n]{0,60}$", prefix):
                continue
            # Avoid treating a generic attack by the player as enemy ability.
            if not re.search(r"\b(?:inimigo|maldicao|adversario|mahito|ele|ela)\b", prefix) and not any(
                normalize(c["name"]) in prefix for c in characters if c["team"] == "enemy"
            ):
                continue
            # Remainder of THIS clause, not the whole battle text; don't attach the
            # cooldown of a second technique to the first one.
            clause_end = re.search(r"[.;\n]", message[match.end():])
            end = match.end() + (clause_end.start() if clause_end else len(message) - match.end())
            fields = self._fields(message[match.end():end])
            discoveries.append({
                "enemy_id": target_id,
                "name": name[:100],
                **fields,
                "evidence": message[max(0, match.start()-65):end][:500],
                "ignored": False
            })
        # Same name in one message is only one proposal.
        unique = {}
        for entry in discoveries:
            unique.setdefault(normalize(entry["name"]), entry)
        return list(unique.values())

    def merged_techniques(self, character: dict, proposal: dict) -> list[dict]:
        """Idempotente e conservador: só preenche lacunas, detecta divergências."""
        name = str(proposal["name"]).strip()
        if not 1 <= len(name) <= 100:
            raise ValueError("Informe um nome de técnica (até 100 caracteres).")
        candidate = CombatTechnique.model_validate({
            "name": name,
            "damage": proposal.get("damage"),
            "ea_cost": proposal.get("ea_cost"),
            "cooldown": proposal.get("cooldown"),
            "effect": proposal.get("effect"),
            "status": "confirmed",  # confirmado pelo jogador; não implica cânone
        })
        existing = [CombatTechnique.model_validate(t).model_dump()
                    for t in character.get("techniques", [])]
        matched = next((i for i, t in enumerate(existing)
                        if normalize(t["name"]) == normalize(candidate.name)), None)
        if matched is None:
            return existing + [candidate.model_dump()]
        current = existing[matched]
        for field in ("damage", "ea_cost", "cooldown", "effect"):
            proposed_value = getattr(candidate, field)
            if proposed_value is None:
                continue
            if current.get(field) is not None and current[field] != proposed_value:
                raise ValueError(
                    f"{candidate.name}: {field} já está registrado como {current[field]!r}; "
                    "revise a ficha antes de substituir um dado confirmado."
                )
            current[field] = proposed_value
        # Manual/user-provided values become observed once a report is confirmed.
        current["status"] = "confirmed"
        return existing
