export type Team = 'player' | 'ally' | 'enemy';
export type Form = 'none' | 'scales' | 'assault';

export interface Character {
  id: string;
  name: string;
  team: Team;
  level: number | null;
  hp: number | null;
  max_hp: number | null;
  ea: number | null;
  max_ea: number | null;
  spirit: number | null;
  dexterity: number | null;
  form: Form;
  main_actions: number;
  bonus_actions: number;
  reaction_available: boolean;
  fangs_used: number;
  maw_used: number;
  amaterasu_used: number;
  critical_count: number;
  reinforcement_used: number;
  output_used: number;
  reverse_used: number;
  effects: string[];
  notes: string;
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
  addCharacter: (name: string, team: Team) =>
    request<Character>('/api/characters', { method: 'POST', body: JSON.stringify({ name, team }) }),
  patchCharacter: (id: string, values: Partial<Character>) =>
    request<Character>('/api/characters/' + encodeURIComponent(id), {
      method: 'PATCH', body: JSON.stringify(values)
    }),
  events: () => request<BattleEvent[]>('/api/events'),
  undo: () => request<Character>('/api/events/undo', { method: 'POST' }),
  newTurn: (character_id: string) => request<{characters: Character[]}>('/api/turns/next', { method: 'POST', body: JSON.stringify({ character_id }) }),
  messages: () => request<ChatMessage[]>('/api/messages'),
  chat: (message: string, character_id: string) =>
    request<ChatResponse>('/api/chat', {
      method: 'POST', body: JSON.stringify({ message, character_id })
    })
};
