"""Mudanças de estado exigem confirmação; nunca deduzir efeitos ao ler planos."""
from .. import store

class BattleUpdateSkill:
    def confirm_field(self, character_id: str, field: str, value: int):
        if field not in {"hp", "ea", "spirit", "dexterity"}:
            raise ValueError("Campo não permitido no comando de chat.")
        return store.update_character(character_id, {field: value}, kind="chat_update")

    def undo(self):
        return store.undo_last()

    def next_turn(self):
        return store.new_turn()
