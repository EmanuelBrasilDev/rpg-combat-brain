"""CombatLearningSkill: aprendizado descritivo sobre eventos reais validados, sem ajustar pesos automaticamente."""
from collections import Counter

class CombatLearningSkill:
    def overview(self, reports: list[dict]) -> dict:
        confirmed = [r for r in reports if r.get("status") == "confirmed"]
        reviewed = [r for r in confirmed if r.get("feedback")]
        counts = Counter(r["feedback"]["rating"] for r in reviewed)
        techniques: Counter[str] = Counter()
        outcomes: Counter[str] = Counter()
        rolls_known = 0
        for item in confirmed:
            data = item["parsed"]
            techniques.update(data.get("techniques", []))
            outcomes[data.get("outcome", "unknown")] += 1
            rolls_known += sum(roll.get("total") is not None for roll in data.get("rolls", []))
        return {
            "confirmed_reports": len(confirmed),
            "feedback_count": len(reviewed),
            "feedback": {key: counts[key] for key in ("good", "neutral", "bad")},
            "reported_roll_results": rolls_known,
            "techniques_observed": [
                {"name": name, "count": count} for name, count in techniques.most_common(8)
            ],
            "reported_outcomes": dict(outcomes),
            "learning_status": "Memória de experiências reais disponível para consulta. "
                               "Ajuste automático de pesos ainda não implementado.",
            "note": "Feedback descreve a avaliação do jogador; não é taxa de acerto ou de vitória."
        }
