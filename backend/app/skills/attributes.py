"""Atributos canônicos das fichas e modificadores informados pelo jogador.

Valores de 10, 12, 14 ... 50 têm modificadores 0, +1, +2 ... +20.
Para valores ímpares >=10 usamos piso, sem supor arredondamento para cima.
Abaixo de 10 não há regra confirmada de modificador: retornamos None.
Um modificador NÃO deve ser adicionado automaticamente a uma fórmula "ESP d10",
pois tal fórmula emprega o valor bruto do atributo como quantidade de dados.
"""

ATTRIBUTE_FIELDS = ("strength", "speed", "resistance", "intellect", "spirit")
ATTRIBUTE_LABELS = {
    "strength": "Força",
    "speed": "Velocidade",
    "resistance": "Resistência",
    "intellect": "Intelecto",
    "spirit": "Espírito",
}
AKIRA_ATTRIBUTES = {
    "strength": 26, "speed": 34, "resistance": 26,
    "intellect": 30, "spirit": 34,
}
ATTRIBUTE_MAX = 50


def attribute_modifier(score: int | None) -> int | None:
    """Retorna o modificador somente no intervalo suportado 10..50."""
    if score is None or not 10 <= score <= ATTRIBUTE_MAX:
        return None
    return (score - 10) // 2


def migrate_attribute_keys(payload: dict, *, seed_akira: bool = False) -> dict:
    """Renomeia DES/dexterity legado e preserva dados preenchidos pelo jogador.

    O Akira recebe valores iniciais confirmados para campos não registrados.
    Não substitui valores existentes, inclusive os que o jogador editou.
    """
    result = dict(payload)
    old_speed = result.pop("dexterity", None)
    if result.get("speed") is None and old_speed is not None:
        result["speed"] = old_speed
    if seed_akira:
        for field, baseline in AKIRA_ATTRIBUTES.items():
            if result.get(field) is None:
                result[field] = baseline
    return result


def summarize_attributes(character: dict) -> list[str]:
    lines = []
    for field in ATTRIBUTE_FIELDS:
        value = character.get(field)
        modifier = attribute_modifier(value)
        if value is None:
            detail = "desconhecido"
        elif modifier is None:
            detail = f"{value}/50 (modificador não definido pelas regras informadas)"
        else:
            detail = f"{value}/50 (modificador {modifier:+d})"
        lines.append(f"{ATTRIBUTE_LABELS[field]}: {detail}")
    return lines
