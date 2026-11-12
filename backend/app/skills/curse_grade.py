"""Grau de maldições: números MENORES indicam ameaça MAIOR.

A escala de grau de maldição não é a dificuldade procedimental do laboratório:
- Grau Especial > Grau 1 > Grau 2 > Grau 3 > Grau 4.
- Dificuldade sintética de 1 a 5 continua crescendo normalmente, mas NÃO é grau.
- Grau não equivale a dano, HP ou chance de vitória conhecidos.
"""
import re
import unicodedata


_ORDER = {4: 1, 3: 2, 2: 3, 1: 4}
_LABELS = {1: "Grau 4", 2: "Grau 3", 3: "Grau 2", 4: "Grau 1", 5: "Grau Especial"}


def _normalize(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(c)
    ).strip()


class CurseGradeSkill:
    """Lê apenas graus explicitamente informados, sem supor estatísticas."""

    def priority(self, tier: str | None) -> int | None:
        """Retorna 1 (Grau 4) a 5 (Especial); None se o grau é desconhecido."""
        if not tier:
            return None
        normalized = _normalize(tier)
        match = re.search(r"\bgrau\s+(especial|[1-4])\b", normalized)
        if match:
            grade = match.group(1)
            return 5 if grade == "especial" else _ORDER[int(grade)]
        if normalized in ("especial", "maldição especial", "maldicao especial"):
            return 5
        return None

    def label(self, tier: str | None) -> str | None:
        priority = self.priority(tier)
        return _LABELS[priority] if priority is not None else None

    def compare(self, first: str | None, second: str | None) -> int | None:
        """1 se first é mais perigoso pelo GRAU, -1 se menos, 0 empate; None desconhecido."""
        a, b = self.priority(first), self.priority(second)
        if a is None or b is None:
            return None
        return (a > b) - (a < b)

    def enemy_grade(self, enemy: dict) -> str | None:
        # O grau é prioritariamente o campo tier; um nome "Maldição Grau 3" também é explícito.
        return self.label(enemy.get("tier")) or self.label(enemy.get("name"))

    def cautions(self, enemies: list[dict]) -> list[str]:
        warnings = []
        for enemy in enemies:
            grade = self.enemy_grade(enemy)
            if grade in ("Grau Especial", "Grau 1"):
                warnings.append(
                    f"{enemy['name']}: {grade} indica uma maldição de categoria elevada "
                    "na hierarquia (Especial > 1 > 2 > 3 > 4). "
                    "Considere defesa e preservação de recursos; o grau sozinho não confirma dano ou vitória."
                )
        return warnings
