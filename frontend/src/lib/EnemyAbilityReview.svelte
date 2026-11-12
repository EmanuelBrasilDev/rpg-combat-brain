<script lang="ts">
  import { AlertCircle, Check, Eye, Save, Sparkles } from 'lucide-svelte';
  import type { Character, EnemyDiscovery, EnemyDiscoveryEdit } from '$lib/api';

  export let reportId: number;
  export let index: number;
  export let discovery: EnemyDiscovery;
  export let enemies: Character[] = [];
  export let onSave: (reportId: number, edit: EnemyDiscoveryEdit) => Promise<void>;
  export let onDirty: (key: string, dirty: boolean) => void;

  let enemyId = discovery.enemy_id ?? '';
  let name = discovery.name;
  let cooldown = discovery.cooldown === null ? '' : String(discovery.cooldown);
  let eaCost = discovery.ea_cost === null ? '' : String(discovery.ea_cost);
  let damage = discovery.damage ?? '';
  let effect = discovery.effect ?? '';
  let ignored = discovery.ignored ?? false;
  let dirty = false;
  let saving = false;
  let error = '';
  let saved = false;
  const key = reportId + ':' + index;

  function markDirty() {
    dirty = true;
    saved = false;
    onDirty(key, true);
  }
  function optionalInt(value: string): number | null {
    return value.trim() === '' ? null : Number(value);
  }
  async function save() {
    if (!ignored && !name.trim()) { error = 'Informe um nome ou marque como ignorada.'; return; }
    saving = true; error = '';
    try {
      await onSave(reportId, {
        index, enemy_id: enemyId || null, name: name.trim(),
        cooldown: optionalInt(cooldown), ea_cost: optionalInt(eaCost),
        damage: damage.trim() || null, effect: effect.trim() || null, ignored
      });
      dirty = false;
      saved = true;
      onDirty(key, false);
    } catch (err) { error = err instanceof Error ? err.message : String(err); }
    finally { saving = false; }
  }
</script>

<div class="discovery">
  <div class="discovery-head">
    <span class="discovery-icon"><Eye size={16}/></span>
    <div><strong>Habilidade inimiga revelada</strong><small>Descoberta #{index+1} · dados aguardando revisão</small></div>
    <span class="new-label"><Sparkles size={12}/> NOVA</span>
  </div>
  <p class="evidence">{discovery.evidence}</p>
  <div class="fields">
    <label>Ficha do inimigo
      <select bind:value={enemyId} on:change={markDirty}>
        <option value="">Selecionar inimigo…</option>
        {#each enemies as enemy}
          <option value={enemy.id}>{enemy.name}</option>
        {/each}
      </select>
    </label>
    <label>Nome da técnica
      <input bind:value={name} on:input={markDirty} maxlength="100" placeholder="Nome revelado pelo mestre"/>
    </label>
    <label>Cooldown (turnos)
      <input bind:value={cooldown} on:input={markDirty} type="number" min="0" max="999" placeholder="Desconhecido"/>
    </label>
    <label>Custo de EA
      <input bind:value={eaCost} on:input={markDirty} type="number" min="0" placeholder="Desconhecido"/>
    </label>
    <label>Dano (fórmula)
      <input bind:value={damage} on:input={markDirty} placeholder="Ex.: 5d8 + 3d2"/>
    </label>
    <label>Efeito observado
      <input bind:value={effect} on:input={markDirty} placeholder="Ex.: causa queimadura ao acertar"/>
    </label>
  </div>
  <div class="footer">
    <label class="ignore"><input type="checkbox" bind:checked={ignored} on:change={markDirty}/> Ignorar esta descoberta</label>
    <button disabled={saving || !dirty} on:click={save}><Save size={15}/> Salvar técnica</button>
  </div>
  {#if !enemyId && !ignored}
    <p class="warn"><AlertCircle size={14}/> Identifique o inimigo antes de confirmar o relato ou marque como ignorada.</p>
  {/if}
  {#if dirty}<p class="warn"><AlertCircle size={14}/> Há alterações não salvas. Clique em "Salvar técnica" antes de confirmar.</p>{/if}
  {#if saved}<p class="ok"><Check size={14}/> Descoberta revisada e salva no rascunho.</p>{/if}
  {#if error}<p class="warn"><AlertCircle size={14}/>{error}</p>{/if}
</div>

<style>
.discovery{border:1px solid #5c4a3d;background:#272a2b;border-radius:10px;padding:14px;margin:15px 0}
.discovery-head{display:flex;align-items:center;gap:9px}
.discovery-icon{background:#48382e;color:#ecb793;display:grid;place-items:center;padding:9px;border-radius:8px}
.discovery-head>div{flex:1;min-width:0}.discovery-head strong{font-size:11px;display:block;color:#f3d5b9}.discovery-head small{display:block;font-size:9px;color:#aa9689;margin-top:4px}
.new-label{display:flex;align-items:center;gap:4px;font-size:8px;font-weight:900;letter-spacing:.5px;color:#f0b98e;border-radius:20px;background:#493b2e;padding:5px 7px;white-space:nowrap}
.evidence{border-left:2px solid #b37e66;padding-left:10px;font-size:10px;color:#baa99e;line-height:1.6;white-space:pre-wrap}
.fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:11px;margin-top:14px}
.fields label{display:grid;gap:5px;color:#d7b9a6;font-size:10px;font-weight:700}
.fields input,.fields select{min-width:0;width:100%;background:#141b23;border:1px solid #665347;color:#e9e6e3;border-radius:7px;padding:10px;font-size:11px;min-height:37px}
.fields input:focus,.fields select:focus{outline:2px solid #a67258}
.footer{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:15px}
.footer>.ignore{display:flex;align-items:center;gap:8px;font-size:10px;color:#bba798;font-weight:650}
.footer>.ignore input{accent-color:#c58d69}
.footer button{display:flex;align-items:center;gap:6px;border-radius:8px;padding:9px 12px;background:#b07858;border:1px solid #dd9c75;color:#201713;font-size:10px;font-weight:850;white-space:nowrap}
.footer button:disabled{opacity:.45}
.warn,.ok{display:flex;align-items:flex-start;gap:7px;font-size:10px;line-height:1.5;color:#f2bd99;margin:10px 0 0}
.ok{color:#9fd2b3}
@media(max-width:560px){.fields{grid-template-columns:1fr}.footer{flex-wrap:wrap}}
</style>
