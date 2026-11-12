"""Dados exatos, distribuição de rolagens e chance em disputas 1d20."""
from collections import Counter
from functools import lru_cache
import re

_DICE = re.compile(r"^(\d+)d(\d+)$", re.IGNORECASE)

def expected_dice(notation: str) -> float:
    match = _DICE.fullmatch(notation.strip())
    if not match:
        raise ValueError(f"Notação inválida: {notation}")
    number, sides = map(int, match.groups())
    if number > 200 or sides < 2 or sides > 1000:
        raise ValueError("Dados fora dos limites")
    return number * (sides + 1) / 2

@lru_cache(maxsize=32)
def distribution(n: int, sides: int) -> dict[int, int]:
    if not 1 <= n <= 30 or not 2 <= sides <= 100:
        raise ValueError("Parâmetros fora dos limites")
    counts = Counter({0: 1})
    for _ in range(n):
        next_counts = Counter()
        for total, frequency in counts.items():
            for face in range(1, sides + 1):
                next_counts[total + face] += frequency
        counts = next_counts
    return dict(counts)

def win_probability(modifier: int, opponent_modifier: int, ties_win: bool = False) -> float:
    """Chance EXATA de vencer em disputa simples de dois d20, supondo bônus fixos."""
    wins = sum(
        1 for a in range(1, 21) for b in range(1, 21)
        if a + modifier > b + opponent_modifier or
        (ties_win and a + modifier == b + opponent_modifier)
    )
    return wins / 400
