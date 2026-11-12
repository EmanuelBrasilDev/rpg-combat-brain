<script lang="ts">
  import { onMount } from 'svelte';
  import { BrainCircuit, CheckCircle2, ClipboardList, Dices, MessageSquare, RefreshCw, ShieldAlert } from 'lucide-svelte';
  import { api, type CombatReport, type LearningOverview } from '$lib/api';

  let reports: CombatReport[] = [];
  let overview: LearningOverview | null = null;
  let loading = true;
  let busyId: number | null = null;
  let error = '';
  let noteById: Record<number, string> = {};
  let ratingById: Record<number, 'good' | 'neutral' | 'bad'> = {};

  async function refresh() {
    try {
      const [data, stats] = await Promise.all([api.combatReports('confirmed'), api.learningOverview()]);
      reports = data;
      overview = stats;
      error = '';
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    } finally { loading = false; }
  }
  onMount(() => { void refresh(); });

  async function save(report: CombatReport) {
    busyId = report.id;
    try {
      await api.feedbackReport(
        report.id,
        ratingById[report.id] ?? report.feedback?.rating ?? 'neutral',
        noteById[report.id] ?? report.feedback?.note ?? ''
      );
      await refresh();
    } catch (err) { error = err instanceof Error ? err.message : String(err); }
    finally { busyId = null; }
  }
</script>

<section class="experience">
  <div class="experience-head">
    <div class="experience-title"><span><BrainCircuit size={19}/></span><div><h2>Aprendizado com relatos reais</h2><p>Experiências confirmadas e avaliação humana</p></div></div>
    <button class="refresh" on:click={refresh} aria-label="Atualizar experiências"><RefreshCw size={17}/></button>
  </div>
  {#if error}<div class="exp-error"><ShieldAlert size={15}/>{error}</div>{/if}
  {#if overview}
    <div class="exp-metrics">
      <div><small>RELATOS CONFIRMADOS</small><strong>{overview.confirmed_reports}</strong></div>
      <div><small>AVALIAÇÕES DO JOGADOR</small><strong>{overview.feedback_count}</strong></div>
      <div><small>ROLAGENS REGISTRADAS</small><strong>{overview.reported_roll_results}</strong></div>
    </div>
    <p class="exp-limit">{overview.learning_status} Nenhuma vitória ou regra nova é deduzida automaticamente.</p>
  {/if}
  <div class="exp-list">
    {#each reports.slice(0,12) as report (report.id)}
      <article class="exp-item">
        <div class="exp-meta"><CheckCircle2 size={14}/> RELATO CONFIRMADO #{report.id}{#if report.feedback}<span>· AVALIADO</span>{/if}</div>
        <p>{report.parsed.message}</p>
        {#if report.parsed.rolls.length}
          <div class="exp-rolls"><Dices size={14}/> {report.parsed.rolls.filter(r=>r.total!==null).map(r=>r.total).join(', ') || 'Fórmulas sem total informado'}</div>
        {/if}
        <div class="feedback-form">
          <label>Avaliação da decisão
            <select value={ratingById[report.id] ?? report.feedback?.rating ?? 'neutral'} on:change={(e) => ratingById[report.id] = e.currentTarget.value as 'good' | 'neutral' | 'bad'}>
              <option value="good">Boa decisão</option>
              <option value="neutral">Aceitável / inconclusiva</option>
              <option value="bad">Decisão ruim</option>
            </select>
          </label>
          <label>Observação sobre o resultado
            <input value={noteById[report.id] ?? report.feedback?.note ?? ''} on:input={(e) => noteById[report.id] = e.currentTarget.value} maxlength="1200" placeholder="Ex.: defesa valeu a pena apesar da rolagem baixa"/>
          </label>
          <button disabled={busyId !== null} on:click={() => save(report)}><MessageSquare size={14}/> Salvar avaliação</button>
        </div>
      </article>
    {/each}
    {#if !loading && !reports.length}
      <p class="empty-exp"><ClipboardList size={22}/> Você ainda não confirmou nenhum relato no Combat Mode. Quando confirmar um acontecimento, ele aparecerá aqui para revisão.</p>
    {/if}
  </div>
</section>

<style>
  .experience{border:1px solid #345146;background:linear-gradient(120deg,#172622,#19212b);border-radius:13px;overflow:hidden;margin:0 0 19px}
  .experience-head{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:18px;border-bottom:1px solid #31473e}
  .experience-title{display:flex;align-items:center;gap:11px}
  .experience-title>span{width:40px;height:40px;border-radius:10px;background:#2e4a3f;color:#78d0a5;display:grid;place-items:center}
  .experience-title h2{margin:0;font-size:14px}.experience-title p{margin:5px 0 0;font-size:10px;color:#98b8a9}
  .refresh{background:transparent;border:none;color:#a2b2bc;padding:8px}
  .exp-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;padding:18px}
  .exp-metrics>div{background:#21372f;padding:14px;border:1px solid #355547;border-radius:10px}
  .exp-metrics small{font-size:9px;color:#9ebdab;font-weight:750;letter-spacing:.6px;display:block}
  .exp-metrics strong{font-size:22px;display:block;margin-top:6px}
  .exp-limit{font-size:11px;color:#a6bfae;line-height:1.6;margin:0 18px 17px}
  .exp-list{padding:0 18px 18px;display:grid;gap:11px;max-height:740px;overflow:auto}
  .exp-item{background:#1d2b29;border:1px solid #365046;padding:14px;border-radius:10px}
  .exp-meta{display:flex;align-items:center;gap:7px;color:#8ee1b1;font-size:10px;letter-spacing:.6px;font-weight:750}
  .exp-item p{font-size:12px;color:#dae9df;line-height:1.65;white-space:pre-wrap}
  .exp-rolls{display:flex;align-items:center;gap:7px;color:#9db3a6;font-size:11px}
  .feedback-form{display:grid;grid-template-columns:minmax(150px,.8fr) minmax(160px,1.3fr) auto;gap:9px;align-items:end;margin-top:12px}
  .feedback-form label{font-size:10px;color:#b5cbbd;display:grid;gap:6px}
  .feedback-form input,.feedback-form select{width:100%;min-width:0;background:#101d1c;border:1px solid #486456;color:#e5f0e8;padding:10px;border-radius:8px;font-size:11px}
  .feedback-form button{height:39px;border:1px solid #6bae8e;border-radius:8px;background:#3a785d;color:#e7fff0;display:flex;align-items:center;gap:7px;justify-content:center;padding:0 12px;white-space:nowrap;font-size:10px;font-weight:800}
  .feedback-form button:disabled{opacity:.5}
  .empty-exp{display:flex;align-items:center;gap:12px;font-size:11px;color:#aac2b2;padding:15px}
  .exp-error{font-size:11px;color:#ffb5a0;display:flex;align-items:center;gap:8px;margin:12px}
  @media(max-width:850px){.feedback-form{grid-template-columns:1fr}.exp-metrics{grid-template-columns:1fr 1fr 1fr}}
  @media(max-width:480px){.exp-metrics{grid-template-columns:1fr 1fr}.experience-title h2{font-size:12px}}
</style>