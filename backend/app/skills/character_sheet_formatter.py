"""CharacterSheetFormatterSkill — ficha de combate -> Markdown pronto para copiar.

Usa APENAS os valores da ficha atual e do catálogo do Akira.
Não transforma limites de usos em cooldown, nem duração base em turnos restantes.
O texto é somente leitura: nenhuma ação, recurso ou estado é alterado.
"""
from ..catalog import load_catalog
from ..models import Character
from .attributes import ATTRIBUTE_FIELDS, ATTRIBUTE_LABELS, attribute_modifier


def _value(value: object) -> str:
    return "?" if value is None else str(value)


def _resource(current: object, maximum: object) -> str:
    return _value(current) if maximum is None else f"{_value(current)}/{_value(maximum)}"


def _registered_details(technique: dict | None) -> str:
    """Acrescenta detalhes registrados manualmente sem encobrir a habilidade original."""
    if not technique:
        return ""
    parts = []
    if technique.get("ea_cost") is not None:
        parts.append(f"EA {technique['ea_cost']}")
    if technique.get("damage"):
        parts.append(f"dano {_safe(technique['damage'])}")
    if technique.get("accuracy_bonus"):
        parts.append(f"acerto {_safe(technique['accuracy_bonus'])}")
    if technique.get("effect"):
        parts.append(_safe(technique["effect"]))
    if technique.get("status") == "synthetic":
        parts.append("[SINTÉTICA, não confirmada]")
    elif technique.get("status") == "placeholder":
        parts.append("[PENDENTE]")
    return " — " + "; ".join(parts) if parts else ""


def _safe(text: object) -> str:
    """Preserva nomes, impede que campos livres quebrem a estrutura de linhas."""
    return " ".join(str(text).replace("\r", " ").replace("\n", " ").split())


def _ability_line(technique: dict) -> str:
    name = _safe(technique.get("name", "Técnica sem nome"))
    details = []
    cooldown = technique.get("cooldown")
    details.append(f"{_value(cooldown)}c")
    if technique.get("ea_cost") is not None:
        details.append(f"EA {technique['ea_cost']}")
    if technique.get("damage"):
        details.append(f"dano {_safe(technique['damage'])}")
    if technique.get("accuracy_bonus"):
        details.append(f"acerto {_safe(technique['accuracy_bonus'])}")
    line = f"* {name} ({'; '.join(details)})"
    if technique.get("effect"):
        line += f" — {_safe(technique['effect'])}"
    if technique.get("status") == "synthetic":
        line += " [SINTÉTICA, não confirmada]"
    elif technique.get("status") == "placeholder":
        line += " [PENDENTE]"
    return line


class CharacterSheetFormatterSkill:
    """Exporta qualquer personagem; Akira recebe seções de seu arsenal confirmado."""

    def format(self, sheet: dict) -> str:
        character = Character.model_validate(sheet).model_dump()
        is_akira = character["id"] == "akira"
        catalog = load_catalog() if is_akira else None
        abilities = {a["id"]: a for a in catalog["abilities"]} if catalog else {}

        lines: list[str] = [
            f"# {_safe(character['name'])}",
            f"HP ({_resource(character['hp'], character['max_hp'])})",
            f"EA ({_resource(character['ea'], character['max_ea'])})",
        ]
        if character["level"] is not None:
            lines.append(f"Nível ({character['level']})")
        if character["tier"]:
            lines.append(f"Grau ({_safe(character['tier'])})")

        self._section(lines, "Atributos")
        for field in ATTRIBUTE_FIELDS:
            score = character.get(field)
            mod = attribute_modifier(score)
            detail = f"{_value(score)}/50"
            if mod is not None:
                detail += f"; mod. {mod:+d}"
            elif score is not None:
                detail += "; modificador pendente"
            lines.append(f"* {ATTRIBUTE_LABELS[field]} ({detail})")

        custom = [t for t in character["techniques"] if t["category"] == "technique"]
        canonical_map = {t["name"].casefold(): t for t in custom}
        if is_akira:
            self._akira_forms(lines, character, abilities, canonical_map)
            self._akira_mangekyou(lines, character, abilities, canonical_map)

        self._section(lines, "Habilidades Extras")
        extra = [t for t in character["techniques"] if t["category"] == "extra"]
        if extra:
            lines.extend(_ability_line(t) for t in extra)
        else:
            lines.append("* Nenhuma cadastrada")

        self._section(lines, "Técnicas")
        if is_akira:
            self._akira_techniques(lines, character, abilities, canonical_map)
        canonical = {a["name"].casefold() for a in abilities.values()} if is_akira else set()
        canonical_names = {
            "crimson dragon's fangs", "crimson dragon's maw", "dragon scales",
            "dragon assault", "flame connection", "flames shō", "amaterasu"
        } if is_akira else set()
        filtered = [
            t for t in custom
            if t["name"].casefold() not in canonical | canonical_names
        ]
        lines.extend(_ability_line(t) for t in filtered)
        if not is_akira and not filtered:
            lines.append("* Nenhuma cadastrada")

        self._section(lines, "Itens")
        custom_kenrykat = next((item for item in character["items"]
                                if item["name"].casefold() == "kenrykat"), None) if is_akira else None
        if is_akira:
            weapon = abilities.get("kenrykat")
            if weapon:
                damage = (custom_kenrykat.get("damage") if custom_kenrykat and
                          custom_kenrykat.get("damage") else weapon.get("damage"))
                suffix = (f"; {_safe(custom_kenrykat['effect'])}" if custom_kenrykat and
                          custom_kenrykat.get("effect") else "")
                lines.append(
                    f"* {_safe(weapon['name'])} ({_value(damage)})"
                    f" — Kokusen ({character['critical_count']}/3 críticos){suffix}"
                )
        for item in character["items"]:
            if is_akira and item["name"].casefold() == "kenrykat":
                continue
            line = f"* {_safe(item['name'])}"
            if item["damage"]:
                line += f" ({_safe(item['damage'])})"
            if item["effect"]:
                line += f" — {_safe(item['effect'])}"
            lines.append(line)
        if len(lines) and lines[-1] == "# Itens":
            lines.append("* Nenhum cadastrado")

        if character["effects"]:
            self._section(lines, "Efeitos ativos")
            lines.extend(f"* {_safe(effect)}" for effect in character["effects"])

        if character["notes"].strip():
            self._section(lines, "Observações")
            lines.append(_safe(character["notes"]))

        if character["sheet_origin"] == "synthetic":
            lines += ["-", "* ATENÇÃO: ficha sintética, não oficial."]
        elif character["origin_warning"]:
            lines += ["-", f"* {_safe(character['origin_warning'])}"]
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _section(lines: list[str], title: str) -> None:
        lines.extend(["-", f"# {title}"])

    def _akira_forms(self, lines: list[str], character: dict, abilities: dict,
                     custom: dict[str, dict]) -> None:
        scales = abilities.get("scales", {})
        assault = abilities.get("assault", {})
        self._section(lines, "Dragon Scales (?t restantes)")
        lines += [
            f"* Estado ({'ativa' if character['form'] == 'scales' else 'inativa'})",
            f"* Duração base ({_value(scales.get('duration_turns'))}t)",
            f"* Durabilidade ({_value(scales.get('durability'))})",
            f"* Defesa ({_value(scales.get('defense'))})",
            f"* Punição ({_value(scales.get('punishment'))})",
            f"* Chamas ({_value(scales.get('weapon_flames'))})",
        ]
        if "dragon scales" in custom:
            t = custom["dragon scales"]
            lines.append(f"* Cooldown cadastrado ({_value(t.get('cooldown'))}c)" + _registered_details(t))
        self._section(lines, "Dragon Assault (?t restantes)")
        extra = assault.get("weapon_damage_bonus", "")
        parts = [piece.strip() for piece in extra.split("+")] if extra else []
        lines += [
            f"* Estado ({'ativa' if character['form'] == 'assault' else 'inativa'})",
            f"* Duração base ({_value(assault.get('duration_turns'))}t)",
            f"* Velocidade ({_value(assault.get('speed_bonus'))})",
            f"* Boost ({parts[0] if len(parts) >= 1 else '?'})",
            f"* Dano ({parts[1] if len(parts) >= 2 else '?'})",
            f"* Chamas ({parts[2] if len(parts) >= 3 else '?'})",
        ]
        if "dragon assault" in custom:
            t = custom["dragon assault"]
            lines.append(f"* Cooldown cadastrado ({_value(t.get('cooldown'))}c)" + _registered_details(t))

    def _akira_mangekyou(self, lines: list[str], character: dict, abilities: dict,
                         custom: dict[str, dict]) -> None:
        systems = load_catalog().get("systems", {})
        level = systems.get("mangekyou", {}).get("akira_level")
        limit = abilities.get("amaterasu", {}).get("limit")
        self._section(lines, "Mangekyō Sharingan")
        lines.append(f"* Nível ({_value(level)})")
        lines.append(f"* Amaterasu ({character['amaterasu_used']}/{_value(limit)} uso)")
        t = custom.get("amaterasu")
        cd = t.get("cooldown") if t else None
        label = f"* Cooldown de Amaterasu ({_value(cd)}c"
        label += " — não cadastrado" if cd is None else ""
        lines.append(label + ")" + _registered_details(t))

    def _akira_techniques(self, lines: list[str], character: dict, abilities: dict,
                          custom: dict[str, dict]) -> None:
        for tech_id, used in (("fangs", "fangs_used"), ("maw", "maw_used")):
            ability = abilities.get(tech_id)
            if ability:
                t = custom.get(ability["name"].casefold())
                cd = t.get("cooldown") if t else None
                lines.append(
                    f"* {_safe(ability['name'])} "
                    f"({character[used]}/{_value(ability.get('limit'))} usos)"
                    f" — cooldown {_value(cd)}c" + _registered_details(t)
                )
        for tech_id in ("scales", "assault"):
            ability = abilities.get(tech_id)
            if ability:
                t = custom.get(ability["name"].casefold())
                cd = f"; {_value(t.get('cooldown'))}c" if t else ""
                lines.append(f"* {_safe(ability['name'])} (?t restantes{cd})" + _registered_details(t))
        for tech_id in ("flame_connection", "flames_sho"):
            ability = abilities.get(tech_id)
            if ability:
                t = custom.get(ability["name"].casefold())
                cd = t.get("cooldown") if t else None
                lines.append(f"* {_safe(ability['name'])} ({_value(cd)}c)" + _registered_details(t))
