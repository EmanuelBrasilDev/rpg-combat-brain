"""Contratos do laboratório — não são fichas oficiais nem personagens de batalha."""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

Origin = Literal["user_example", "synthetic"]
BuildTemplate = Literal["curse_grade_3", "mahito_reference", "procedural"]
Archetype = Literal["assault", "defense", "control", "balanced"]
Scenario = Literal["opening", "under_attack", "close_combat", "long_range", "area"]

class EnemyTechnique(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    damage: str | None = None
    ea_cost: int | None = Field(default=None, ge=0)
    cooldown: int | None = Field(default=None, ge=0)
    effect: str | None = None
    accuracy_bonus: str | None = None
    status: Literal["user_provided", "synthetic", "placeholder"]

class EnemyProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str = Field(min_length=1, max_length=100)
    tier: str | None = None
    origin: Origin
    template: BuildTemplate
    archetype: Archetype | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)
    seed: int = Field(ge=0, le=999999)
    hp: int | None = Field(default=None, ge=0)
    ea: int | None = Field(default=None, ge=0)
    spirit: int | None = Field(default=None, ge=0)
    dexterity: int | None = Field(default=None, ge=0)
    reinforcement_level: int | None = Field(default=None, ge=0, le=10)
    output_level: int | None = Field(default=None, ge=0, le=10)
    reverse_level: int | None = Field(default=None, ge=0, le=10)
    domain_level: int | None = Field(default=None, ge=0, le=10)
    extra_metrics: dict[str, int | str | bool | None] = Field(default_factory=dict)
    techniques: list[EnemyTechnique] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    approved_for_real_combat: bool = False

class GenerateEnemyRequest(BaseModel):
    template: BuildTemplate = "procedural"
    archetype: Archetype = "balanced"
    difficulty: int = Field(default=2, ge=1, le=5)
    seed: int = Field(default=42, ge=0, le=999999)

class EvaluateRequest(BaseModel):
    enemy_id: str
    character_id: str = "akira"
    scenario: Scenario = "opening"

class BatchRequest(BaseModel):
    template: Literal["procedural"] = "procedural"
    archetype: Archetype = "balanced"
    difficulty: int = Field(default=2, ge=1, le=5)
    start_seed: int = Field(default=0, ge=0, le=999999)
    samples: int = Field(default=8, ge=1, le=24)
    character_id: str = "akira"

class LearningRun(BaseModel):
    id: int
    enemy_id: str
    scenario: Scenario
    source: Literal["synthetic_benchmark"] = "synthetic_benchmark"
    recommendation: str | None = None
    candidates_considered: int = 0
    score: float | None = None
    warnings: list[str] = Field(default_factory=list)
    actual_result: None = None
    verified: bool = False
    created_at: str
