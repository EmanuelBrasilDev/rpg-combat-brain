"""Comparações informativas dos atributos conhecidos, sem inventar fórmulas de combate."""
from .attributes import ATTRIBUTE_FIELDS, ATTRIBUTE_LABELS, attribute_modifier


class AttributeComparisonSkill:
    def compare(self, character: dict, enemies: list[dict]) -> list[str]:
        notes = []
        for enemy in enemies[:5]:
            comparisons = []
            for field in ATTRIBUTE_FIELDS:
                ally_value = character.get(field)
                enemy_value = enemy.get(field)
                if ally_value is None or enemy_value is None:
                    continue
                ally_mod = attribute_modifier(ally_value)
                enemy_mod = attribute_modifier(enemy_value)
                delta = enemy_value - ally_value
                relation = "inimigo superior" if delta > 0 else "Akira superior" if delta < 0 else "empate"
                mods = (
                    f"; mods {ally_mod:+d}/{enemy_mod:+d}"
                    if ally_mod is not None and enemy_mod is not None else ""
                )
                comparisons.append(
                    f"{ATTRIBUTE_LABELS[field]} {ally_value}/{enemy_value} "
                    f"({relation}{mods})"
                )
            if comparisons:
                notes.append(
                    f"Atributos {character['name']} / {enemy['name']}: "
                    + "; ".join(comparisons)
                    + ". Comparação informativa; a regra de testes/acerto/defesa "
                    "precisa ser informada antes de converter diferenças em bônus."
                )
        return notes
