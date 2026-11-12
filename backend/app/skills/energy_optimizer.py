"""Cálculos de EA: valores confirmados separados de estimativas."""
from dataclasses import dataclass
from math import ceil

from ..catalog import ability

@dataclass(frozen=True)
class EnergyCost:
    value: int | None
    status: str  # confirmed | base_only | unknown
    explanation: str

class EnergyOptimizer:
    @staticmethod
    def successive_discounts(base: int, rates: list[float]) -> int:
        """Aplica cada redução, arredondando para cima a cada etapa."""
        result = base
        for rate in rates:
            if not 0 <= rate <= 1:
                raise ValueError("Desconto fora do intervalo 0..1")
            result = ceil(result * (1 - rate))
        return result

    def cost(self, ability_id: str) -> EnergyCost:
        item = ability(ability_id)
        if not item:
            return EnergyCost(None, "unknown", "Habilidade não cadastrada.")
        if ability_id == "fangs":
            return EnergyCost(25, "confirmed",
                "25 EA é o custo padrão com Fornalha confirmado pelo jogador; outros descontos ainda dependem de validação.")
        if ability_id in ("block", "dodge"):
            return EnergyCost(0, "confirmed", "Reação básica; custo de EA não definido como obrigatório no sistema.")
        if ability_id == "kenrykat":
            return EnergyCost(0, "confirmed", "Golpe base com a arma; não inclui Reforço.")
        if ability_id == "amaterasu":
            return EnergyCost(70, "confirmed", "Custo fixo de Chama Única; uso único por combate.")
        if item.get("base_cost") is None:
            return EnergyCost(None, "unknown", "Custo de ativação ainda não informado.")
        return EnergyCost(item["base_cost"], "base_only",
            "Somente custo ORIGINAL informado; descontos efetivos ainda não foram validados.")

    def affordable(self, character: dict, skill_id: str) -> bool | None:
        cost = self.cost(skill_id)
        if cost.value is None or character["ea"] is None:
            return None
        # Custos base-only podem superestimar o gasto após descontos.
        return character["ea"] >= cost.value
