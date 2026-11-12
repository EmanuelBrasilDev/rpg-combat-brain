export type EnemyTemplate = 'curse_grade_3' | 'mahito_reference' | 'procedural';
export type EnemyArchetype = 'assault' | 'defense' | 'control' | 'balanced';
export type LabScenario = 'opening' | 'under_attack' | 'close_combat' | 'long_range' | 'area';
export interface EnemyTechnique {
  name: string;
  damage: string | null;
  ea_cost: number | null;
  cooldown: number | null;
  effect: string | null;
  accuracy_bonus: string | null;
  status: 'user_provided' | 'synthetic' | 'placeholder';
}
export interface EnemyProfile {
  id: string;
  name: string;
  tier: string | null;
  origin: 'user_example' | 'synthetic';
  template: EnemyTemplate;
  archetype: EnemyArchetype | null;
  difficulty: number | null;
  seed: number;
  hp: number | null;
  ea: number | null;
  strength: number | null;
  speed: number | null;
  resistance: number | null;
  intellect: number | null;
  spirit: number | null;
  reinforcement_level: number | null;
  output_level: number | null;
  reverse_level: number | null;
  domain_level: number | null;
  extra_metrics: Record<string, string | number | boolean | null>;
  techniques: EnemyTechnique[];
  assumptions: string[];
  approved_for_real_combat: boolean;
}
export interface LearningRun {
  id: number;
  enemy_id: string;
  scenario: LabScenario;
  recommendation: string | null;
  score: number | null;
  candidates_considered: number;
  source: 'synthetic_benchmark';
  warnings: string[];
  actual_result: null;
  verified: false;
  created_at: string;
  details: {
    enemy_name: string;
    explanation: string;
    metrics_note: string;
    alternatives: Alternate[];
  };
}
export interface BenchmarkSummary {
  tests: number;
  tests_with_recommendation: number;
  tests_without_recommendation: number;
  unique_recommendations: number;
  most_frequent_recommendations: { name: string; count: number }[];
  scenarios: Record<string, number>;
  learning_status: string;
  limitation: string;
}

export type Team = 'player' | 'ally' | 'enemy';
export type Form = 'none' | 'scales' | 'assault';
export type CombatTechnique = {
  name: string;
  damage: string | null;
  ea_cost: number | null;
  cooldown: number | null;
  duration_turns?: number | null;
  effect: string | null;
  accuracy_bonus: string | null;
  status: 'user_provided' | 'synthetic' | 'placeholder' | 'confirmed';
  observed?: boolean;
  category?: 'technique' | 'extra';
};
export type CombatItem = {
  name: string;
  damage: string | null;
  effect: string | null;
};
export type CharacterExport = {
  character_id: string;
  character_name: string;
  format: 'markdown';
  content: string;
};
export type RollObservation = {
  actor: 'player' | 'enemy' | 'ally' | 'unknown';
  kind: string;
  expression: string | null;
  total: number | null;
  source: string;
  context: string;
};
export type EnemyDiscovery = {
  enemy_id: string | null;
  name: string;
  damage: string | null;
  ea_cost: number | null;
  cooldown: number | null;
  effect: string | null;
  evidence: string;
  ignored: boolean;
};
export type EnemyDiscoveryEdit = Omit<EnemyDiscovery, 'evidence'> & { index: number };

export type CombatReport = {
  id: number;
  character_id: string;
  status: 'pending' | 'confirmed' | 'discarded';
  created_at: string;
  reviewed_at: string | null;
  feedback: { rating: 'good' | 'neutral' | 'bad'; note: string } | null;
  parsed: {
    message: string;
    character_id: string;
    rolls: RollObservation[];
    techniques: string[];
    outcome: string;
    damage_received: number | null;
    ea_spent: number | null;
    proposed_updates: Record<string, Partial<Character>>;
    proposed_discoveries?: EnemyDiscovery[];
    warnings: string[];
    enemy_attack_observed: boolean;
  };
};
export type LearningOverview = {
  confirmed_reports: number;
  feedback_count: number;
  feedback: { good: number; neutral: number; bad: number };
  reported_roll_results: number;
  techniques_observed: { name: string; count: number }[];
  reported_outcomes: Record<string, number>;
  learning_status: string;
  note: string;
};

export interface Character {
  id: string;
  name: string;
  team: Team;
  level: number | null;
  hp: number | null;
  max_hp: number | null;
  ea: number | null;
  max_ea: number | null;
  strength: number | null;
  speed: number | null;
  resistance: number | null;
  intellect: number | null;
  spirit: number | null;
  form: Form;
  main_actions: number;
  bonus_actions: number;
  reaction_available: boolean;
  fangs_used: number;
  maw_used: number;
  amaterasu_used: number;
  mega_brain_active: boolean;
  mega_brain_turns_remaining: number;
  mega_brain_cooldown_remaining: number;
  critical_count: number;
  reinforcement_used: number;
  output_used: number;
  reverse_used: number;
  effects: string[];
  notes: string;
  tier: string | null;
  reinforcement_level: number | null;
  output_level: number | null;
  reverse_level: number | null;
  domain_level: number | null;
  techniques: CombatTechnique[];
  items: CombatItem[];
  extra_metrics: Record<string, string | number | boolean | null>;
  sheet_origin: 'manual' | 'user_example' | 'synthetic';
  origin_warning: string;
}

export interface Alternate {
  title: string;
  score: number;
  main_actions: number;
  reaction: number;
  damage_expected: number | null;
  cost_reference: number;
  cost_verified: boolean;
  notes: string[];
}
export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  alternatives?: Alternate[];
  warnings?: string[];
  created_at: string;
}
export interface BattleEvent {
  id: number;
  character_id: string;
  kind: string;
  before: Partial<Character> | null;
  after: Partial<Character> | null;
  created_at: string;
}
export interface Ability {
  id: string;
  name: string;
  kind: string;
  base_cost: number | null;
  status: string;
  [key: string]: unknown;
}
export interface Catalog {
  game: string;
  revision: string;
  abilities: Ability[];
  pending: string[];
  [key: string]: unknown;
}
export interface ChatResponse {
  intent: string;
  answer: string;
  alternatives: Alternate[];
  warnings: string[];
  report_id: number | null;
}
const BASE = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(BASE + path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers }
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(
      typeof detail?.detail === 'string'
        ? detail.detail
        : 'Erro ' + response.status + ' ao acessar o Combat Brain'
    );
  }
  return response.json();
}

export const api = {
  health: () => request<{status: string}>('/api/health'),
  catalog: () => request<Catalog>('/api/catalog'),
  characters: () => request<Character[]>('/api/characters'),
  exportCharacter: (id: string) => request<CharacterExport>('/api/characters/' + encodeURIComponent(id) + '/export'),
  megaBrain: (id: string, action: 'activate' | 'interrupt') =>
    request<Character>('/api/characters/' + encodeURIComponent(id) + '/mega-brain/' + action, {
      method: 'POST'
    }),
  addCharacter: (name: string, team: Team) =>
    request<Character>('/api/characters', { method: 'POST', body: JSON.stringify({ name, team }) }),
  patchCharacter: (id: string, values: Partial<Character>) =>
    request<Character>('/api/characters/' + encodeURIComponent(id), {
      method: 'PATCH', body: JSON.stringify(values)
    }),
  events: () => request<BattleEvent[]>('/api/events'),
  undo: () => request<Character>('/api/events/undo', { method: 'POST' }),
  newTurn: (character_id: string) => request<{characters: Character[]}>('/api/turns/next', { method: 'POST', body: JSON.stringify({ character_id }) }),
  combatReports: (status?: 'pending' | 'confirmed' | 'discarded') =>
    request<CombatReport[]>('/api/combat/reports' + (status ? '?status=' + status : '')),
  saveDiscovery: (report_id: number, payload: EnemyDiscoveryEdit) =>
    request<CombatReport>('/api/combat/reports/' + report_id + '/discovery', {
      method: 'PATCH', body: JSON.stringify(payload)
    }),
  reviewReport: (report_id: number, decision: 'confirmed' | 'discarded') =>
    request<CombatReport>('/api/combat/reports/' + report_id + '/review', {
      method: 'POST', body: JSON.stringify({ decision })
    }),
  feedbackReport: (report_id: number, rating: 'good' | 'neutral' | 'bad', note = '') =>
    request<CombatReport>('/api/combat/reports/' + report_id + '/feedback', {
      method: 'POST', body: JSON.stringify({ rating, note })
    }),
  learningOverview: () => request<LearningOverview>('/api/learning/overview'),
  adoptEnemy: (id: string) =>
    request<Character>('/api/lab/enemies/' + encodeURIComponent(id) + '/adopt', { method: 'POST' }),
  labEnemies: () => request<EnemyProfile[]>('/api/lab/enemies'),
  generateEnemy: (body: { template: EnemyTemplate; archetype: EnemyArchetype; difficulty: number; seed: number }) =>
    request<EnemyProfile>('/api/lab/enemies/generate', { method: 'POST', body: JSON.stringify(body) }),
  labRuns: () => request<LearningRun[]>('/api/lab/runs'),
  evaluateEnemy: (body: { enemy_id: string; character_id: string; scenario: LabScenario }) =>
    request<LearningRun>('/api/lab/evaluate', { method: 'POST', body: JSON.stringify(body) }),
  benchmark: (body: { archetype: EnemyArchetype; difficulty: number; start_seed: number; samples: number; character_id: string }) =>
    request<{ summary: BenchmarkSummary; runs: LearningRun[] }>('/api/lab/benchmarks', {
      method: 'POST', body: JSON.stringify(body)
    }),
  messages: () => request<ChatMessage[]>('/api/messages'),
  chat: (message: string, character_id: string) =>
    request<ChatResponse>('/api/chat', {
      method: 'POST', body: JSON.stringify({ message, character_id })
    })
};
