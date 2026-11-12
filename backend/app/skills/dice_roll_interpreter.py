"""DiceRollInterpreter — extrai dados efetivamente relatados, sem rolar nem inventar modificadores."""
import re
import unicodedata

DICE_FORMULA = re.compile(
    r"\b\d{1,2}d\d{1,3}(?:\s*[+-]\s*(?:\d{1,2}d\d{1,3}|\d{1,3}|ESP|DES))*\b",
    re.IGNORECASE,
)
# "tirei 19", "o inimigo tirou 24", "rolou 17", "resultado 22".
ROLL_RESULT = re.compile(
    r"\b(?P<verb>tirei|tirou|rolou|rolei|resultado(?:\s+de)?|deu)\s+(?P<number>\d{1,4})\b",
    re.IGNORECASE,
)
EXPLICIT_TOTAL = re.compile(
    r"\b(?P<formula>\d{1,2}d\d{1,3}(?:\s*[+]\s*(?:ESP|DES|\d{1,3}|\d{1,2}d\d{1,3}))*)"
    r"\s*(?:=|total(?:\s+de)?|resultou\s+em)\s*(?P<number>\d{1,4})\b",
    re.IGNORECASE,
)


def normalize(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(c)
    )


class DiceRollInterpreter:
    def parse(self, message: str) -> list[dict]:
        rolls: list[dict] = []
        seen: set[tuple[int, int]] = set()
        for match in EXPLICIT_TOTAL.finditer(message):
            begin, end = match.span()
            seen.add((begin, end))
            rolls.append(self._roll(
                message, begin, end, match.group("formula").strip(),
                int(match.group("number")), "explicit_total"
            ))
        for match in ROLL_RESULT.finditer(message):
            begin, end = match.span()
            if any(a <= begin < b for a, b in seen):
                continue
            rolls.append(self._roll(
                message, begin, end, None, int(match.group("number")), "reported_result"
            ))
        # Expressões "5d8 + 3d2" sem total são fórmulas, NÃO rolagens observadas.
        for match in DICE_FORMULA.finditer(message):
            begin, end = match.span()
            if any(a <= begin < b or (begin <= a < end) for a, b in seen):
                continue
            if any(roll["expression"] and
                   normalize(match.group()) in normalize(roll["expression"])
                   for roll in rolls):
                continue
            rolls.append(self._roll(message, begin, end, match.group().strip(), None, "formula_only"))
        rolls.sort(key=lambda item: item["position"])
        return [{k: v for k, v in roll.items() if k != "position"} for roll in rolls[:24]]

    def _roll(self, message: str, begin: int, end: int, formula: str | None,
              total: int | None, source: str) -> dict:
        prefix = normalize(message[max(0, begin - 95):begin])
        after = normalize(message[end:end + 45])
        # A atribuição de autor deve permanecer conservadora quando faltar contexto.
        if (re.search(r"\b(?:eu|meu|minha|akira)\b[^.!?\n]{0,40}$", prefix) or
                re.search(r"\b(?:tirei|rolei)\b", normalize(message[begin:end]))):
            actor = "player"
        elif re.search(r"\b(?:inimigo|maldicao|mahito|adversario|ele)\b[^.!?\n]{0,55}$", prefix):
            actor = "enemy"
        elif re.search(r"\b(?:aliado|companheiro|ela)\b[^.!?\n]{0,55}$", prefix):
            actor = "ally"
        else:
            actor = "unknown"
        context = normalize(message[max(0, begin - 65):min(len(message), end + 50)])
        if any(x in context for x in ("esquiv", "defes", "bloque")):
            kind = "defense"
        elif any(x in context for x in ("acert", "ataqu", "garr", "golpe")):
            kind = "attack"
        elif "dano" in context:
            kind = "damage"
        else:
            kind = "unknown"
        return {
            "position": begin, "actor": actor, "kind": kind, "expression": formula,
            "total": total, "source": source,
            "context": message[max(0, begin - 45):min(len(message), end + 50)].strip()
        }
