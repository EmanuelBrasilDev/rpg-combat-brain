"""Reconhecimento determinístico de intenções e atualizações explícitas."""
import re
import unicodedata
from dataclasses import dataclass

@dataclass(frozen=True)
class Interpretation:
    intent: str
    update: tuple[str, str, int] | None = None

def normalize(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", text.casefold())
                   if not unicodedata.combining(ch))

def interpret(message: str, characters: list[dict]) -> Interpretation:
    raw = normalize(message).strip()
    # Alterações persistentes requerem verbo explícito ou /set.
    # /set akira ea 400
    match = re.fullmatch(r"/set\s+(.+?)\s+(hp|ea|esp|des)\s+(\d+)", raw)
    if match:
        name, field, number = match.groups()
        character = next((c for c in characters if normalize(c["name"]) == name or c["id"] == name), None)
        if character:
            return Interpretation("update", (character["id"], {"esp": "spirit", "des": "dexterity"}.get(field, field), int(number)))
        return Interpretation("unknown_character")
    match = re.fullmatch(r"(?:atualiz[ae]|confirm[oa])\s+(?:o\s+)?(hp|ea|esp|des)\s+d[oa]\s+(.+?)\s+(?:para|em)\s+(\d+)", raw)
    if match:
        field, name, number = match.groups()
        character = next((c for c in characters if normalize(c["name"]) == name), None)
        if character:
            return Interpretation("update", (character["id"], {"esp": "spirit", "des": "dexterity"}.get(field, field), int(number)))
        return Interpretation("unknown_character")
    if any(token in raw for token in ("desfaz", "desfazer", "undo", "voltar ultima")):
        return Interpretation("undo")
    if any(token in raw for token in ("proximo turno", "novo turno", "/turno")):
        return Interpretation("new_turn")
    if any(token in raw for token in ("melhor", "combo", "abertura", "estrateg", "defender", "bloquear",
                                      "esquivar", "reagir", "contra-atac", "o que faco", "o que posso fazer", "sequencia")):
        return Interpretation("tactics")
    if any(token in raw for token in ("regra", "turno funciona", "quantas acoes", "acoes principais")):
        return Interpretation("rules")
    if any(token in raw for token in ("fangs", "maw", "amaterasu", "dragon scales", "dragon assault", "kenrykat", "flame connection", "flames sho")):
        return Interpretation("ability")
    if any(token in raw for token in ("ficha", "status", "quanto", "habilidade", "energia", "hp", "ea", "critico")):
        return Interpretation("sheet")
    return Interpretation("help")
