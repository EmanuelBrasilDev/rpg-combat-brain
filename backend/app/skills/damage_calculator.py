"""Estimativas de dano (médias de dados), nunca rolagens garantidas."""
from .dice_probability import expected_dice

class DamageCalculator:
    def evaluate(self, ability_id: str, character: dict) -> tuple[float | None, str]:
        spirit = character.get("spirit")
        form = character.get("form")
        if ability_id == "kenrykat":
            value = expected_dice("8d5") + expected_dice("5d2")
            text = "8d5 + 5d2 da Kenrykat"
            if form == "assault":
                value += expected_dice("8d2") + expected_dice("8d8") + expected_dice("8d3")
                text += " + Dragon Assault (8d2 + 8d8 + 8d3)"
            if form == "scales":
                value += expected_dice("8d8")
                text += " + Dragon Scales (8d8 em chamas)"
            return value, text + "; sem Reforço, crítico ou resistência do alvo"
        if ability_id in ("fangs", "maw"):
            if spirit is None:
                return None, "ESP não cadastrada: impossível estimar o dano de dados ESP."
            if ability_id == "fangs":
                normal = expected_dice(f"{spirit + 5}d10")
                burn = expected_dice("4d8")
                formula = f"({spirit}+5)d10 × 1,30; queimadura 4d8 separada"
            else:
                normal = expected_dice(f"{spirit}d10") + expected_dice("8d8")
                burn = expected_dice("12d4")
                formula = f"{spirit}d10 + 8d8, ×1,30; queimadura 12d4 separada"
            # O dano final +30% aplica-se ao dano normal segundo o voto.
            # Não somamos a queimadura como dano imediato sem confirmar sua periodicidade.
            return round(normal * 1.30, 2), formula + f" (queimadura média separada: {burn:g})"
        if ability_id == "flames_sho":
            value, formula = self.evaluate("kenrykat", character)
            return value, "Acerto garantido com arma: " + formula
        return None, "Dados insuficientes para quantificar o dano desta ação."
