"""Mega Brain do Akira — regras fornecidas, estado e rolagens naturais.

Regras:
- Estado pessoal, duração 1 turno, custo 0 EA, cooldown base 2 turnos.
- Ao ativar, consome TODAS as ações bônus remanescentes do turno.
- Enquanto ativo: resultados NATURAIS de 15+ no d20 são críticos.
- Stun, paralisia, fear e qualquer CC confirmado encerram o estado.
- O efeito nunca concede acerto automático nem soma dano não informado.
"""

MEGA_BRAIN_NAME = "Mega Brain"
MEGA_BRAIN_COOLDOWN = 2
MEGA_BRAIN_DURATION = 1
MEGA_BRAIN_CRITICAL_THRESHOLD = 15
MEGA_BRAIN_EFFECT = (
    "Estado pessoal de concentração extrema. Ao ativar, consome todas as ações bônus "
    "do turno. Durante 1 turno, resultados naturais de 15+ no d20 contam como crítico. "
    "Encerrado imediatamente ao sofrer CC (Stun, Paralisia, Fear etc.)."
)


def mega_brain_technique() -> dict:
    return {
        "name": MEGA_BRAIN_NAME, "category": "extra",
        "ea_cost": 0, "cooldown": MEGA_BRAIN_COOLDOWN,
        "duration_turns": MEGA_BRAIN_DURATION,
        "effect": MEGA_BRAIN_EFFECT, "status": "user_provided",
    }


class MegaBrainSkill:
    def can_activate(self, sheet: dict) -> tuple[bool, str]:
        if sheet.get("id") != "akira":
            return False, "Mega Brain pertence à ficha do Akira."
        if sheet.get("mega_brain_active"):
            return False, "Mega Brain já está ativa."
        if sheet.get("mega_brain_cooldown_remaining", 0) > 0:
            return False, "Mega Brain ainda está em cooldown."
        if sheet.get("bonus_actions", 0) <= 0:
            return False, "Não há ações bônus disponíveis para consumir na ativação."
        return True, "Disponível."

    def activate_changes(self, sheet: dict) -> dict:
        allowed, reason = self.can_activate(sheet)
        if not allowed:
            raise ValueError(reason)
        return {
            "bonus_actions": 0,
            "mega_brain_active": True,
            "mega_brain_turns_remaining": MEGA_BRAIN_DURATION,
            "mega_brain_cooldown_remaining": MEGA_BRAIN_COOLDOWN,
        }

    @staticmethod
    def interrupt_changes(sheet: dict) -> dict:
        """O CC encerra a duração, mas NÃO apaga o cooldown restante."""
        if not sheet.get("mega_brain_active"):
            return {}
        return {"mega_brain_active": False, "mega_brain_turns_remaining": 0}

    @staticmethod
    def next_turn_changes(sheet: dict) -> dict:
        """Passagem de turno explicitamente aprovada pelo jogador.

        A recarga começa na ativação e reduz em 1 por novo turno do Akira;
        essa convenção fica explícita porque o mestre pode adotar outro marco.
        """
        duration = max(0, sheet.get("mega_brain_turns_remaining", 0) - 1)
        cooldown = max(0, sheet.get("mega_brain_cooldown_remaining", 0) - 1)
        return {
            "mega_brain_turns_remaining": duration,
            "mega_brain_active": bool(sheet.get("mega_brain_active") and duration > 0),
            "mega_brain_cooldown_remaining": cooldown,
        }

    @staticmethod
    def is_critical(sheet: dict, natural_d20: int | None) -> bool | None:
        """None fora do estado: regra de crítico normal ainda não conhecida.

        Apenas o D20 NATURAL; valores com modificadores não são aceitos.
        """
        if natural_d20 is None or not 1 <= natural_d20 <= 20:
            return None
        if not sheet.get("mega_brain_active") or sheet.get("mega_brain_turns_remaining", 0) <= 0:
            return None
        return natural_d20 >= MEGA_BRAIN_CRITICAL_THRESHOLD
