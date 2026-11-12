from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

Team = Literal["player", "ally", "enemy"]

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
    spirit: int | None = Field(default=None, ge=0)
    dexterity: int | None = Field(default=None, ge=0)
    form: Literal["none", "scales", "assault"] = "none"
    main_actions: int = Field(default=2, ge=0, le=2)
    bonus_actions: int = Field(default=2, ge=0, le=2)
    reaction_available: bool = True
    fangs_used: int = Field(default=0, ge=0, le=6)
    maw_used: int = Field(default=0, ge=0, le=6)
    amaterasu_used: int = Field(default=0, ge=0, le=1)
    critical_count: int = Field(default=0, ge=0, le=3)
    effects: list[str] = Field(default_factory=list)
    notes: str = Field(default="", max_length=3000)

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

class BattleEvent(BaseModel):
    id: int
    character_id: str
    kind: str
    before: dict | None = None
    after: dict | None = None
    created_at: str
