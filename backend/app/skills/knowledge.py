"""Conhecimento: regras, perfil Akira e estado persistido."""
from ..catalog import ability, load_catalog
from ..store import list_characters, list_events
from ..combat_store import list_reports

class RulebookSkill:
    def turn_rules(self) -> str:
        rules = load_catalog()["turn"]
        return (
            f"Cada turno possui {rules['main_actions']} ações principais, "
            f"{rules['bonus_actions']} ações bônus e {rules['reactions']} reação. "
            f"Máximo de {rules['max_full_offensive_attacks']} ataques ofensivos completos. "
            + rules["note"]
        )

    def pending(self) -> list[str]:
        return load_catalog()["pending"]

class AkiraProfileSkill:
    def describe_ability(self, name: str) -> str | None:
        import unicodedata
        def norm(value: str) -> str:
            return ''.join(c for c in unicodedata.normalize("NFKD", value.casefold())
                           if not unicodedata.combining(c))
        target = norm(name)
        match = next((
            item for item in load_catalog()["abilities"]
            if norm(item["name"]) in target or item["id"].replace("_", " ") in target
        ), None)
        if not match:
            return None
        keys = ("base_cost", "confirmed_cost_with_fornalha", "damage", "burn",
                "hit_bonus", "range", "duration_turns", "defense", "durability", "notes")
        content = [f"**{match['name']}** — tipo: {match['kind']}"]
        for key in keys:
            if key in match:
                content.append(f"{key.replace('_', ' ').title()}: {match[key] if match[key] is not None else 'pendente'}")
        content.append("Fonte: fichas e esclarecimentos fornecidos. Dados faltantes não são inferidos.")
        return "\n".join(content)

class CombatMemorySkill:
    def snapshot(self) -> dict:
        return {"characters": list_characters(), "events": list_events(),
                "confirmed_reports": list_reports("confirmed", 30)}
