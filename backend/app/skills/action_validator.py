"""Regras duras: nunca recomendar ações impossíveis como fatos."""
from .energy_optimizer import EnergyOptimizer

class ActionValidator:
    def __init__(self):
        self.energy = EnergyOptimizer()

    def check(self, character: dict, moves: list[dict]) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        if sum(m["main"] for m in moves) > character["main_actions"]:
            reasons.append("Ações principais insuficientes.")
        if sum(m["reaction"] for m in moves) > int(character["reaction_available"]):
            reasons.append("Reação indisponível.")
        if sum(m["offensive"] for m in moves) > 2:
            reasons.append("Limite de dois ataques ofensivos completos por turno.")
        for field, ability in (("fangs_used", "fangs"), ("maw_used", "maw"), ("amaterasu_used", "amaterasu")):
            uses = sum(m["id"] == ability for m in moves)
            limit = 1 if ability == "amaterasu" else 6
            if character[field] + uses > limit:
                reasons.append(f"Limite de uso de {ability} excedido.")
        if character.get("reinforcement_used", 0) + sum(m.get("buff") == "reinforcement" for m in moves) > 30:
            reasons.append("Limite de Reforço (30) excedido.")
        if character.get("output_used", 0) + sum(m.get("buff") == "output" for m in moves) > 30:
            reasons.append("Limite de Output (30) excedido.")
        costs = [self.energy.cost(m["id"]) for m in moves]
        confirmed_sum = sum(c.value or 0 for c in costs if c.status == "confirmed")
        # Custos originais podem cair com Votos/Eficiência; só rejeitamos
        # quando já faltar EA até para valores confirmados.
        if character["ea"] is not None and confirmed_sum > character["ea"]:
            reasons.append("EA insuficiente para os custos confirmados.")
        return len(reasons) == 0, reasons
