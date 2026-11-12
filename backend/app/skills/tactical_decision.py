"""Busca e classificação heurística transparente, com alternativas e avisos."""
from .combo_forge import ComboForge
from .damage_calculator import DamageCalculator
from .energy_optimizer import EnergyOptimizer

class TacticalDecision:
    def __init__(self):
        self.forge = ComboForge()
        self.damage = DamageCalculator()
        self.energy = EnergyOptimizer()

    def analyze(self, character: dict, enemies: list[dict], message: str) -> dict:
        normalized = message.casefold()
        threat = any(x in normalized for x in
            ("me atac", "atacou", "vai atacar", "defend", "bloque", "esquiv", "reagir", "contra-atac", "ameaç"))
        close_range = any(x in normalized for x in
            ("corpo a corpo", "curta distancia", "curta distância", "perto", "proximo", "próximo", "adjacente"))
        far_range = any(x in normalized for x in ("longe", "longa distancia", "longa distância", "muito distante"))
        area = any(x in normalized for x in ("grupo", "varios", "vários", "muitos", "area", "área", "multiplos", "múltiplos"))
        low_hp = character["hp"] is not None and character["max_hp"] is not None and character["max_hp"] > 0 and character["hp"] / character["max_hp"] < 0.30
        sequences = self.forge.sequences(character, threat=threat, close_range=close_range, far_range=far_range)
        evaluations = []
        for seq in sequences:
            known_damage = 0.0
            missing_damage = False
            notes = []
            costs = []
            for move in seq:
                dmg, detail = self.damage.evaluate(move["id"], character)
                if dmg is None:
                    missing_damage = True
                else:
                    known_damage += dmg
                cost = self.energy.cost(move["id"])
                costs.append(cost)
                notes.append(detail)
            # Pontuação é apenas uma heurística do produto (não regra do RPG).
            defensive = any("defense" in x["tags"] for x in seq)
            guaranteed = any("guaranteed" in x["tags"] for x in seq)
            offensive_count = sum(m["offensive"] for m in seq)
            score = (min(known_damage, 180) / 5 + 5 * offensive_count
                     + (22 if defensive and (threat or low_hp) else 0)
                     + (12 if guaranteed else 0)
                     + (16 if area and any("area" in m["tags"] for m in seq) else 0)
                     - (20 if threat and not defensive else 0)
                     - (12 if low_hp and not defensive else 0)
                     - sum(c.value or 0 for c in costs) / 12)
            if missing_damage:
                score -= 4
            unknown_cost = any(c.status != "confirmed" for c in costs)
            evaluations.append({
                "title": " → ".join(m["label"] for m in seq),
                "ids": [m["id"] for m in seq],
                "score": round(score, 2),
                "main_actions": sum(m["main"] for m in seq),
                "reaction": sum(m["reaction"] for m in seq),
                "damage_expected": round(known_damage, 2) if not missing_damage else None,
                "cost_reference": sum(c.value or 0 for c in costs),
                "cost_verified": not unknown_cost,
                "notes": notes,
            })
        evaluations.sort(key=lambda x: x["score"], reverse=True)
        best = evaluations[0] if evaluations else None
        warnings = [
            "Classificação heurística inicial: não prevê as respostas do oponente nem substitui rolagens e decisões do mestre.",
            "Modificadores de bloqueio/esquiva, efeitos de queimadura e certas interações ainda não estão integralmente cadastrados."
        ]
        if character["spirit"] is None:
            warnings.append("ESP do Akira não cadastrada: dano das técnicas ESP dX não pode ser comparado numericamente.")
        if best and not best["cost_verified"]:
            warnings.append("A sequência utiliza ao menos um custo original/pendente; a EA final exata requer confirmação.")
        if not close_range and not far_range:
            warnings.append("Alcance narrativo ainda não foi informado: golpes corpo a corpo dependem de proximidade válida.")
        if not enemies:
            warnings.append("Nenhum inimigo cadastrado. A análise considera apenas o estado do personagem.")
        if not best:
            return {
                "answer": "Não encontrei uma sequência validada com os recursos atuais. Confira a ficha e as ações restantes.",
                "alternatives": [], "warnings": warnings
            }
        costs = ("custo de referência " + str(best["cost_reference"]) + " EA"
                 + (", confirmado para estes componentes" if best["cost_verified"] else ", ainda sujeito a descontos/regras pendentes"))
        answer = (
            "**Melhor opção provisória:** " + best["title"] + ".\n"
            + f"Ações principais: {best['main_actions']}; reações: {best['reaction']}; {costs}.\n"
            + ("Dano médio conhecido: " + str(best["damage_expected"]) + " (antes de resistência, acerto e efeitos separados).\n"
               if best["damage_expected"] is not None else "Dano não quantificável com os atributos disponíveis.\n")
            + "**Motivo:** opção de maior pontuação na busca local para este cenário; "
            + ("a ameaça imediata recebeu prioridade defensiva." if threat else "o sistema considerou custo, dano conhecido e ações disponíveis.")
            + "\nConfirme ações executadas antes de atualizar a ficha."
        )
        return {"answer": answer, "alternatives": evaluations[:3], "warnings": warnings}
