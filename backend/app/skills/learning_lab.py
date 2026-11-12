"""LearningLabSkill: avaliação de estratégias e cobertura, NÃO treinamento por vitórias inventadas."""
from collections import Counter
from ..lab_models import EnemyProfile, Scenario
from .tactical_decision import TacticalDecision

SCENARIOS: dict[Scenario, str] = {
    "opening": "Qual a melhor abertura contra esse inimigo?",
    "under_attack": "O inimigo me atacou. Vale bloquear, esquivar ou contra-atacar?",
    "close_combat": "O inimigo está próximo, em curta distância, corpo a corpo. Qual o melhor combo?",
    "long_range": "O inimigo está longe, em longa distância. Qual a melhor estratégia?",
    "area": "Estou diante de vários inimigos, em grupo, com ataques em área. Qual a melhor sequência?",
}

class LearningLabSkill:
    def __init__(self):
        self.decision = TacticalDecision()

    def evaluate(self, enemy: EnemyProfile, character: dict, scenario: Scenario) -> dict:
        """Executa um teste sem modificar a ficha do jogador e sem alegar resultado de combate."""
        if character["id"] != "akira":
            raise ValueError("O motor estratégico atual só possui catálogo específico para Akira.")
        summary = {
            "name": enemy.name, "team": "enemy", "hp": enemy.hp,
            "ea": enemy.ea, "spirit": enemy.spirit, "dexterity": enemy.dexterity
        }
        report = self.decision.analyze(character, [summary], SCENARIOS[scenario])
        candidates = report["alternatives"]
        unknown_techniques = sum(t.status == "placeholder" for t in enemy.techniques)
        warnings = [
            *report["warnings"],
            "Teste de decisão, NÃO simulação completa da vitória/derrota: oponente ainda não executa ações no motor.",
            "Nenhuma pontuação sintética será usada para atualizar pesos sem validação."
        ]
        if enemy.origin == "synthetic":
            warnings.append("Ficha e técnicas do inimigo são totalmente sintéticas; não representam regra oficial.")
        if unknown_techniques:
            warnings.append(f"{unknown_techniques} técnicas do inimigo ainda são placeholders sem mecânica informada.")
        return {
            "enemy_id": enemy.id, "scenario": scenario, "source": "synthetic_benchmark",
            "recommendation": candidates[0]["title"] if candidates else None,
            "candidates_considered": len(candidates),
            "score": candidates[0]["score"] if candidates else None,
            "warnings": warnings,
            "actual_result": None, "verified": False,
            "details": {
                "scenario_prompt": SCENARIOS[scenario],
                "enemy_name": enemy.name,
                "enemy_origin": enemy.origin,
                "skill_count": len(enemy.techniques),
                "skill_placeholders": unknown_techniques,
                "alternatives": candidates,
                "explanation": report["answer"],
                "metrics_note": "Pontuação relativa de avaliação. Não é taxa de vitória nem precisão comprovada."
            }
        }

    @staticmethod
    def benchmark_summary(runs: list[dict]) -> dict:
        recommendations = Counter(run["recommendation"] for run in runs if run["recommendation"])
        return {
            "tests": len(runs),
            "tests_with_recommendation": sum(bool(r["recommendation"]) for r in runs),
            "tests_without_recommendation": sum(not r["recommendation"] for r in runs),
            "unique_recommendations": len(recommendations),
            "most_frequent_recommendations": [
                {"name": name, "count": count} for name, count in recommendations.most_common(5)
            ],
            "scenarios": dict(Counter(run["scenario"] for run in runs)),
            "learning_status": "Resultados sintéticos guardados para análise e regressão; pesos estratégicos NÃO modificados.",
            "limitation": "Não calculamos vitória, derrota ou acurácia sem simular respostas adversárias e confirmar as mecânicas."
        }
