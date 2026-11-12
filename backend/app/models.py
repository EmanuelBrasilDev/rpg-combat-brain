from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator
from .skills.attributes import migrate_attribute_keys

Team = Literal["player", "ally", "enemy"]

class CombatTechnique(BaseModel):
    """Uma técnica cadastrada numa ficha. Não pressupõe efeito oficial."""
    name: str = Field(min_length=1, max_length=100)
    damage: str | None = Field(default=None, max_length=120)
    ea_cost: int | None = Field(default=None, ge=0)
    cooldown: int | None = Field(default=None, ge=0)
    effect: str | None = Field(default=None, max_length=400)
    accuracy_bonus: str | None = Field(default=None, max_length=100)
    status: Literal["user_provided", "synthetic", "placeholder", "confirmed"] = "user_provided"
    observed: bool = False  # uso confirmado em combate, sem validar campos sintéticos prévios
    category: Literal["technique", "extra"] = "technique"  # separação na ficha textual


class CombatItem(BaseModel):
    """Item conhecido do combatente; dano e descrição são opcionais."""
    name: str = Field(min_length=1, max_length=100)
    damage: str | None = Field(default=None, max_length=120)
    effect: str | None = Field(default=None, max_length=400)


class Character(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str = Field(min_length=1, max_length=80)
    team: Team = "ally"
    level: int | None = Field(default=None, ge=1)
    hp: int | None = Field(default=None, ge=0)
    max_hp: int | None = Field(default=None, ge=0)
    ea: int | None = Field(default=None, ge=0)
    max_ea: int | None = Field(default=None, ge=0)
    strength: int | None = Field(default=None, ge=0, le=50)
    speed: int | None = Field(default=None, ge=0, le=50)
    resistance: int | None = Field(default=None, ge=0, le=50)
    intellect: int | None = Field(default=None, ge=0, le=50)
    spirit: int | None = Field(default=None, ge=0, le=50)
    form: Literal["none", "scales", "assault"] = "none"
    main_actions: int = Field(default=2, ge=0, le=2)
    bonus_actions: int = Field(default=2, ge=0, le=2)
    reaction_available: bool = True
    fangs_used: int = Field(default=0, ge=0, le=6)
    maw_used: int = Field(default=0, ge=0, le=6)
    amaterasu_used: int = Field(default=0, ge=0, le=1)
    critical_count: int = Field(default=0, ge=0, le=3)
    reinforcement_used: int = Field(default=0, ge=0, le=30)
    output_used: int = Field(default=0, ge=0, le=30)
    reverse_used: int = Field(default=0, ge=0, le=20)
    effects: list[str] = Field(default_factory=list)
    notes: str = Field(default="", max_length=3000)
    tier: str | None = Field(default=None, max_length=80)
    reinforcement_level: int | None = Field(default=None, ge=0, le=10)
    output_level: int | None = Field(default=None, ge=0, le=10)
    reverse_level: int | None = Field(default=None, ge=0, le=10)
    domain_level: int | None = Field(default=None, ge=0, le=10)
    techniques: list[CombatTechnique] = Field(default_factory=list, max_length=60)
    items: list[CombatItem] = Field(default_factory=list, max_length=40)
    extra_metrics: dict[str, int | str | bool | None] = Field(default_factory=dict)
    sheet_origin: Literal["manual", "user_example", "synthetic"] = "manual"
    origin_warning: str = Field(default="", max_length=600)

    @model_validator(mode="before")
    @classmethod
    def upgrade_old_attributes(cls, payload):
        return migrate_attribute_keys(payload) if isinstance(payload, dict) else payload

class CreateCharacter(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    team: Team

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    character_id: str = "akira"

class ChatResponse(BaseModel):
    intent: str
    answer: str
    alternatives: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    requires_confirmation: bool = False
    report_id: int | None = None

class BattleEvent(BaseModel):
    id: int
    character_id: str
    kind: str
    before: dict | None = None
    after: dict | None = None
    created_at: str
