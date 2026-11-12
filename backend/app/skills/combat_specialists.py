"""Especialistas com responsabilidades específicas para exploração estratégica."""
from .energy_optimizer import EnergyOptimizer

class OpeningArchitectSkill:
    def choose(self, candidates: list[dict]) -> list[dict]:
        """Abertura: considerar opções que não gastem a reação antecipadamente."""
        return sorted(candidates, key=lambda x: (
            x["reaction"] > 0, not x["cost_verified"], -x["score"]
        ))

class ReactionMasterSkill:
    def viable(self, character: dict, close_range: bool) -> list[str]:
        if not character.get("reaction_available"):
            return []
        result = ["Bloquear", "Esquivar"]
        if character.get("form") == "scales":
            result.append("Aproveitar Dragon Scales (8d8 defesa; punição corpo a corpo 8d5)")
        cost = EnergyOptimizer().cost("flames_sho")
        if close_range and character.get("ea") is not None and character["ea"] >= (cost.value or 0):
            result.append("Flames Shō: ataque garantido com arma como reação (custo original 45 EA)")
        return result

class EnemyAnalysisSkill:
    def missing_information(self, enemies: list[dict]) -> list[str]:
        if not enemies:
            return ["Sem fichas de inimigos para comparação."]
        notes = []
        for enemy in enemies:
            missing = [field for field in ("hp", "ea", "spirit", "dexterity")
                       if enemy.get(field) is None]
            if missing:
                notes.append(f"{enemy['name']}: {', '.join(missing)} não informados.")
        return notes
