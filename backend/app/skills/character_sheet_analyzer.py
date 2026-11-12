"""Consulta as fichas e sinaliza dados ausentes, sem inventar atributos."""
from ..catalog import load_catalog
from .curse_grade import CurseGradeSkill

class CharacterSheetAnalyzer:
    def summarize(self, character: dict) -> str:
        hp = character["hp"]
        ea = character["ea"]
        fields = [
            f"**{character['name']}** ({'jogador' if character['team']=='player' else 'aliado' if character['team']=='ally' else 'inimigo'})",
            f"HP: {hp if hp is not None else 'desconhecido'}" +
            (f"/{character['max_hp']}" if character["max_hp"] is not None else " (máximo não informado)"),
            f"EA: {ea if ea is not None else 'desconhecida'}" +
            (f"/{character['max_ea']}" if character["max_ea"] is not None else " (máximo não informado)"),
            f"Nível: {character['level'] or 'desconhecido'} | ESP: {character['spirit'] if character['spirit'] is not None else '?'} | DES: {character['dexterity'] if character['dexterity'] is not None else '?'}",
            f"Forma: {character['form']} | Principais: {character['main_actions']} | Bônus: {character['bonus_actions']} | Reação: {'livre' if character['reaction_available'] else 'gasta'}",
        ]
        if character["team"] == "enemy":
            label = CurseGradeSkill().enemy_grade(character)
            if label:
                fields.append(f"Classificação: {label} (Grau Especial > 1 > 2 > 3 > 4; menor número = mais forte).")
        if character['id'] == 'akira':
            fields.append(f"Fangs: {6-character['fangs_used']}/6 | Maw: {6-character['maw_used']}/6 | Críticos para Kokusen: {character['critical_count']}/3")
        levels = [(name, character.get(field)) for name, field in (
            ("Reforço", "reinforcement_level"), ("Output", "output_level"),
            ("Energia Reversa", "reverse_level"), ("Domínio", "domain_level")
        ) if character.get(field) is not None]
        if levels:
            fields.append("Proficiências: " + ", ".join(f"{name} Nv{value}" for name, value in levels))
        if character.get("techniques"):
            techniques = []
            for technique in character["techniques"][:15]:
                info = technique["name"]
                if technique.get("cooldown") is not None:
                    info += f" (recarga {technique['cooldown']} turnos)"
                if technique.get("ea_cost") is not None:
                    info += f" (EA {technique['ea_cost']})"
                if technique.get("damage"):
                    info += f" (dano {technique['damage']})"
                if technique.get("effect"):
                    info += f" — {technique['effect']}"
                if technique.get("status") == "synthetic":
                    info += " [mecânica sintética, não validada]"
                techniques.append(info)
            fields.append("Técnicas registradas:\n" + "\n".join("• " + info for info in techniques))
        if character.get("sheet_origin") == "synthetic":
            fields.append("Atenção: ficha sintética, não oficial; requer revisão.")
        if character["effects"]:
            fields.append("Efeitos: " + ", ".join(character["effects"]))
        return "\n".join(fields)

    def compare(self, characters: list[dict]) -> str:
        lines = ["**Fichas de combate cadastradas**"]
        for c in characters:
            role = {"player": "Jogador", "ally": "Aliado", "enemy": "Inimigo"}[c["team"]]
            lines.append(f"• {c['name']} ({role}) — HP {c['hp'] if c['hp'] is not None else '?'} | EA {c['ea'] if c['ea'] is not None else '?'}")
        return "\n".join(lines)

    def available_abilities(self, character: dict) -> list[dict]:
        if character["id"] != "akira":
            return []  # Não presumir que outros personagens tenham o kit do Akira.
        return load_catalog()["abilities"]
