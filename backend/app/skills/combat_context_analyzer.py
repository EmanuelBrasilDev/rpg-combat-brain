"""CombatContextAnalyzer: fatos confirmados + ficha atual; nunca infere ações consumidas."""
from .dice_roll_interpreter import normalize


class CombatContextAnalyzer:
    def summarize(self, character: dict, characters: list[dict],
                  confirmed_reports: list[dict], pending_reports: list[dict] | None = None) -> dict:
        recent = [r for r in confirmed_reports if r.get("character_id") == character["id"]][:5]
        enemies = [c for c in characters if c.get("team") == "enemy"]
        latest = recent[0] if recent else None
        summary = [
            f"Ficha ativa: {character['name']}; HP {character.get('hp')}; EA {character.get('ea')}.",
            f"Ações principais: {character.get('main_actions')}; bônus: {character.get('bonus_actions')}; "
            f"reação {'disponível' if character.get('reaction_available') else 'gasta'}.",
            f"Inimigos cadastrados: {len(enemies)}."
        ]
        warnings: list[str] = []
        if latest:
            data = latest["parsed"]
            summary.append(f"Último acontecimento confirmado: {data['message'][:240]}")
            if data.get("rolls"):
                known = [str(roll["total"]) for roll in data["rolls"] if roll["total"] is not None]
                if known:
                    summary.append("Totais de rolagem relatados: " + ", ".join(known) + ".")
            if data.get("outcome") != "unknown":
                summary.append("Resultado relatado: " + data["outcome"] + ".")
        if pending_reports:
            warnings.append(f"Há {len(pending_reports)} relato(s) aguardando confirmação; não entram como fatos.")
        if any(c.get("hp") is None for c in enemies):
            warnings.append("Alguns inimigos têm HP desconhecido.")
        return {"summary": "\n".join(summary), "latest": latest, "warnings": warnings}

    def tactical_prompt(self, message: str, context: dict) -> str:
        # Só usa fatos narrativos confirmados no cálculo, nunca relatos pendentes.
        latest = context.get("latest")
        if not latest:
            return message
        text = normalize(message)
        if any(word in text for word in ("atacou", "me atac", "corpo a corpo", "longe", "perto")):
            return message
        event = latest["parsed"]
        descriptions = []
        if event.get("enemy_attack_observed"):
            descriptions.append("o inimigo atacou")
        if event.get("outcome") == "miss_or_defense":
            descriptions.append("um teste de defesa foi relatado")
        # Não completa alcance ou gasto de reação por dedução.
        return message + (". Contexto confirmado: " + "; ".join(descriptions) if descriptions else "")
