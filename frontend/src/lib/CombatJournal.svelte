<script lang="ts">
  import { Check, ClipboardCheck, Clock3, Dices, ShieldAlert, X } from 'lucide-svelte';
  import type { CombatReport } from '$lib/api';

  export let reports: CombatReport[] = [];
  export let selectedId: string = 'akira';
  export let onReview: (id: number, decision: 'confirmed' | 'discarded') => Promise<void>;

  let working: number | null = null;
  let error = '';
  $: pending = reports.filter((r) => r.status === 'pending' && r.character_id === selectedId);
  $: confirmed = reports.filter((r) => r.status === 'confirmed' && r.character_id === selectedId);

  async function review(id: number, decision: 'confirmed' | 'discarded') {
    working = id; error = '';
    try { await onReview(id, decision); }
    catch (err) { error = err instanceof Error ? err.message : String(err); }
    finally { working = null; }
  }
</script>

<section class="journal">
  <div class="journal-head">
    <span class="journal-icon"><ClipboardCheck size={19}/></span>
    <div class="journal-title"><strong>Relatos de combate</strong><small>Revisão humana · sem dedução automática de HP/EA</small></div>
    <span class="journal-count">{pending.length} pendente(s)</span>
  </div>
  {#if error}<div class="journal-error"><ShieldAlert size={15}/>{error}</div>{/if}
  {#if pending.length === 0}
    <p class="journal-empty">Quando você relatar uma ação concluída ou uma rolagem, o Combat Brain preparará um registro para sua confirmação. {confirmed.length} acontecimento(s) já confirmado(s) nesta ficha.</p>
  {:else}
    <div class="journal-entries">
      {#each pending.slice(0,5) as report (report.id)}
        <article class="journal-item">
          <div class="journal-item-meta"><Clock3 size={13}/> RELATO #{report.id} · AGUARDANDO CONFIRMAÇÃO</div>
          <p class="journal-quote">{report.parsed.message}</p>
          {#if report.parsed.rolls.length}
            <div class="roll-list">
              <Dices size={14}/>
              {#each report.parsed.rolls as roll}
                <span>{roll.actor === 'enemy' ? 'Inimigo' : roll.actor === 'player' ? 'Jogador' : 'Não identificado'}: {roll.total ?? 'fórmula sem total'}{roll.expression ? ' · ' + roll.expression : ''}</span>
              {/each}
            </div>
          {/if}
          {#if Object.keys(report.parsed.proposed_updates).length}
            <div class="journal-proposals">
              {#each Object.entries(report.parsed.proposed_updates) as [id, changes]}
                {#each Object.entries(changes) as [field, value]}
                  <span>{id} · {field}: <strong>{value === false ? 'consumida' : String(value)}</strong></span>
                {/each}
              {/each}
            </div>
          {/if}
          <div class="journal-actions">
            <button disabled={working !== null} on:click={() => review(report.id, 'confirmed')} class="confirm"><Check size={15}/> Confirmar relato</button>
            <button disabled={working !== null} on:click={() => review(report.id, 'discarded')}><X size={15}/> Descartar</button>
          </div>
        </article>
      {/each}
    </div>
  {/if}
</section>

<style>
  .journal{margin-top:20px;background:#151c26;border:1px solid #2b3542;border-radius:14px;overflow:hidden}
  .journal-head{display:flex;align-items:center;gap:11px;padding:17px 20px;border-bottom:1px solid #2b3542}
  .journal-icon{width:36px;height:36px;background:#2a3a3d;color:#8edbc7;border-radius:9px;display:grid;place-items:center}
  .journal-title{flex:1;min-width:0}
  .journal-title strong{font-size:13px;display:block}
  .journal-title small{font-size:10px;color:#8999aa;display:block;margin-top:4px}
  .journal-count{font-size:10px;font-weight:750;color:#e6bd94;border:1px solid #584539;background:#3a312a;padding:7px;border-radius:20px;white-space:nowrap}
  .journal-empty{font-size:11px;color:#8e9bad;line-height:1.7;padding:6px 20px 19px}
  .journal-entries{display:grid;gap:13px;padding:16px}
  .journal-item{border:1px solid #394450;border-radius:10px;padding:15px;background:#1d2631}
  .journal-item-meta{font-size:9px;color:#edac89;letter-spacing:1px;font-weight:850;display:flex;align-items:center;gap:7px}
  .journal-quote{font-size:12px;color:#d7e1ee;line-height:1.65;white-space:pre-wrap}
  .roll-list{display:flex;gap:7px;align-items:center;flex-wrap:wrap;color:#a9b7c8;font-size:10px;margin:10px 0}
  .roll-list span{padding:6px 8px;border:1px solid #3b4553;border-radius:7px;background:#242f3b}
  .journal-proposals{display:flex;flex-wrap:wrap;gap:7px;margin:8px 0}
  .journal-proposals span{font-size:10px;background:#293b36;border:1px solid #365a4e;border-radius:7px;padding:7px;color:#9dd6b8}
  .journal-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
  .journal-actions button{display:inline-flex;align-items:center;gap:7px;background:#282f3c;color:#c0ccda;border:1px solid #414b5b;border-radius:8px;padding:10px 12px;font-size:10px;font-weight:750}
  .journal-actions button.confirm{background:#29523f;border-color:#41745a;color:#ccf5db}
  .journal-actions button:hover{filter:brightness(1.15)}
  .journal-actions button:disabled{opacity:.5}
  .journal-error{display:flex;gap:7px;align-items:flex-start;margin:12px;color:#f1afa2;font-size:11px}
</style>