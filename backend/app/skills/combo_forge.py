"""Busca de combinações pequenas com limites de turno e custos conhecidos."""
from .action_validator import ActionValidator
from .damage_calculator import DamageCalculator
from .energy_optimizer import EnergyOptimizer

class ComboForge:
    def __init__(self):
        self.validator = ActionValidator()
        self.damage = DamageCalculator()
        self.energy = EnergyOptimizer()

    def available_moves(self, character: dict, threat: bool, close_range: bool, far_range: bool = False) -> list[dict]:
        if character["id"] != "akira":
            return []  # Kit do Akira não deve ser emprestado para outras fichas.
        moves = [
            dict(id="kenrykat", label="Atacar com Kenrykat", main=1, reaction=0, offensive=1, tags=["melee"]),
            dict(id="fangs", label="Crimson Dragon's Fangs", main=1, reaction=0, offensive=1, tags=["technique"]),
            dict(id="maw", label="Crimson Dragon's Maw", main=1, reaction=0, offensive=1, tags=["area", "technique"]),
        ]
        if far_range:
            moves = [m for m in moves if 'melee' not in m['tags']]
        if close_range and not far_range:
            moves.append(dict(id="flames_sho", label="Flames Shō (ação)", main=1, reaction=0, offensive=1, tags=["melee", "guaranteed"]))
            if threat:
                moves.append(dict(id="flames_sho", label="Flames Shō (reação)", main=0, reaction=1, offensive=1, tags=["melee", "guaranteed", "defense"]))
        if threat:
            moves += [
                dict(id="block", label="Bloquear", main=0, reaction=1, offensive=0, tags=["defense"]),
                dict(id="dodge", label="Esquivar", main=0, reaction=1, offensive=0, tags=["defense"])
            ]
        boosted = []
        for move in moves:
            if move['id'] == 'kenrykat':
                boosted.append({**move, 'label': 'Reforço Nv4 + ' + move['label'], 'buff': 'reinforcement', 'extra_cost': 20, 'extra_damage': 24.0})
            if move['id'] in ('fangs', 'maw'):
                boosted.append({**move, 'label': 'Output Nv3 + ' + move['label'], 'buff': 'output', 'extra_cost': 10, 'extra_damage': 7.5})
        moves.extend(boosted)
        return [m for m in moves if self.validator.check(character, [m])[0]]

    def sequences(self, character: dict, threat=False, close_range=False, far_range=False) -> list[list[dict]]:
        moves = self.available_moves(character, threat, close_range, far_range)
        result = [[move] for move in moves]
        # Expandir apenas duas ações principais neste MVP.
        for first in moves:
            for second in moves:
                if first["main"] == 1 and second["main"] == 1:
                    candidate = [first, second]
                    if self.validator.check(character, candidate)[0]:
                        result.append(candidate)
        return result
