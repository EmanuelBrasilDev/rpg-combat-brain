<script lang="ts">
  import { onMount } from 'svelte';
  import ExperiencePanel from '$lib/ExperiencePanel.svelte';
  import {
    AlertTriangle, ArrowRight, Beaker, BookOpen, BrainCircuit,
    CheckCircle2, ChevronRight, Database, Dices, FlaskConical,
    Play, RotateCcw, ShieldAlert, Sparkles, Swords
  } from 'lucide-svelte';
  import { api, type EnemyArchetype, type EnemyProfile, type EnemyTemplate, type LabScenario,
    type LearningRun, type BenchmarkSummary } from '$lib/api';

  export let onEnemyAdded: () => Promise<void>;
  let template: EnemyTemplate = 'procedural';
  let archetype: EnemyArchetype = 'balanced';
  let difficulty = 2;
  let seed = 42;
  let samples = 8;
  let scenario: LabScenario = 'opening';
  let enemies: EnemyProfile[] = [];
  let runs: LearningRun[] = [];
  let selectedId = '';
  let summary: BenchmarkSummary | null = null;
  let latestRun: LearningRun | null = null;
  let busy = false;
  let warning = '';
  let notice = '';

  $: selected = enemies.find((enemy) => enemy.id === selectedId) ?? null;

  async function refresh() {
    const [profiles, history] = await Promise.all([api.labEnemies(), api.labRuns()]);
    enemies = profiles;
    runs = history;
    if (!selectedId && profiles.length) selectedId = profiles[0].id;
    if (selectedId && !profiles.some((p) => p.id === selectedId)) selectedId = profiles[0]?.id ?? '';
  }
  onMount(() => { void refresh().catch((err) => warning = String(err)); });

  async function generate() {
    if (busy) return;
    busy = true; warning = ''; notice = '';
    try {
      const profile = await api.generateEnemy({ template, archetype, difficulty, seed });
      await refresh();
      selectedId = profile.id;
      latestRun = null;
      summary = null;
      notice = 'Adversário criado no laboratório. A ficha real de combate não foi modificada.';
    } catch (error) { warning = error instanceof Error ? error.message : String(error); }
    finally { busy = false; }
  }

  async function adopt() {
    if (!selected || busy) return;
    busy = true; warning = ''; notice = '';
    try {
      await api.adoptEnemy(selected.id);
      await onEnemyAdded();
      notice = 'Ficha adicionada aos inimigos de combate. Revise atributos e técnicas antes da batalha.';
    } catch (error) { warning = error instanceof Error ? error.message : String(error); }
    finally { busy = false; }
  }

  async function evaluate() {
    if (!selected || busy) return;
    busy = true; warning = '';
    try {
      latestRun = await api.evaluateEnemy({ enemy_id: selected.id, character_id: 'akira', scenario });
      runs = await api.labRuns();
      summary = null;
      notice = 'Teste registrado. Nenhuma ação foi executada no combate real.';
    } catch (error) { warning = error instanceof Error ? error.message : String(error); }
    finally { busy = false; }
  }

  async function batch() {
    if (busy) return;
    busy = true; warning = ''; notice = '';
    try {
      const result = await api.benchmark({ archetype, difficulty, start_seed: seed, samples, character_id: 'akira' });
      summary = result.summary;
      latestRun = result.runs[0] ?? null;
      await refresh();
      notice = 'Bateria concluída. Resultados armazenados como testes sintéticos, sem ajustar pesos automaticamente.';
    } catch (error) { warning = error instanceof Error ? error.message : String(error); }
    finally { busy = false; }
  }

  function numeric(value: number | null): string { return value === null ? 'Não informado' : String(value); }
  function role(value: string | null): string {
    return ({ balanced: 'Equilibrado', assault: 'Ofensivo', defense: 'Defensivo', control: 'Controle' } as Record<string,string>)[value || ''] ?? 'Referência';
  }
  function source(value: EnemyProfile['origin']): string { return value === 'synthetic' ? 'HIPOTÉTICO' : 'EXEMPLO FORNECIDO'; }
  const scenarios: {value: LabScenario; name: string}[] = [
    {value:'opening', name:'Abertura de combate'},
    {value:'under_attack', name:'Sob ataque'},
    {value:'close_combat', name:'Corpo a corpo'},
    {value:'long_range', name:'Longa distância'},
    {value:'area', name:'Vários inimigos'}
  ];
</script>

<div class="lab-page">
  <div class="page-heading">
    <div>
      <div class="eyebrow"><span></span> MODO LABORATÓRIO</div>
      <h1>Enemy Forge <em>&amp; Learning Mode.</em></h1>
      <p>Gere fichas de inimigos para utilizar com suas narrações. Revise experiências reais confirmadas no Learning Mode.</p>
    </div>
    <span class="mode-pill"><FlaskConical size={14}/> AMBIENTE ISOLADO</span>
  </div>

  <div class="lab-intro">
    <div class="lab-intro-icon"><Beaker size={23}/></div>
    <div>
      <strong>Você narra o combate, o agente acompanha as decisões.</strong>
      <p>O Enemy Forge cria fichas editáveis de inimigos; após copiá-las para o combate, você informa habilidades, rolagens e resultados. Os relatos confirmados alimentam o aprendizado. Os benchmarks sintéticos continuam opcionais.</p>
    </div>
  </div>

  {#if warning}<div class="lab-alert"><AlertTriangle size={18}/>{warning}</div>{/if}
  {#if notice}<div class="lab-success"><CheckCircle2 size={18}/>{notice}</div>{/if}

  <ExperiencePanel />

  <div class="lab-grid">
    <section class="panel lab-controls">
      <div class="lab-head"><span class="head-icon"><Dices size={19}/></span><div><h2>Gerador de adversários</h2><p>EnemyForgeSkill · v0.2 experimental</p></div></div>
      <div class="lab-control-body">
        <label>Origem da ficha
          <select bind:value={template}>
            <option value="procedural">Procedural — adversário original</option>
            <option value="curse_grade_3">Maldição Grau 3 — exemplo informado</option>
            <option value="mahito_reference">Mahito — referência com técnicas pendentes</option>
          </select>
        </label>
        {#if template === 'procedural'}
          <div class="two">
            <label>Arquétipo
              <select bind:value={archetype}>
                <option value="balanced">Equilibrado</option>
                <option value="assault">Ofensivo</option>
                <option value="defense">Defensivo</option>
                <option value="control">Controle</option>
              </select>
            </label>
            <label>Dificuldade de teste
              <select bind:value={difficulty}>
                <option value={1}>1 — Baixa</option><option value={2}>2 — Média-baixa</option>
                <option value={3}>3 — Média</option><option value={4}>4 — Alta</option>
                <option value={5}>5 — Extrema</option>
              </select>
            </label>
          </div>
        {/if}
        <label>Semente de geração
          <input type="number" min="0" max="999999" bind:value={seed}/>
          <small>Reutilize a mesma semente para repetir os mesmos números e técnicas.</small>
        </label>
        <button class="lab-primary" disabled={busy} on:click={generate}><Sparkles size={17}/> Gerar ficha de laboratório <ArrowRight size={16}/></button>
        <div class="lab-divider"></div>
        <div class="section-caption"><Database size={14}/> ADVERSÁRIOS SALVOS <span>{enemies.length}</span></div>
        <div class="saved-list">
          {#each enemies.slice(0, 30) as enemy (enemy.id)}
            <button class:active={selectedId === enemy.id} on:click={() => {selectedId = enemy.id; latestRun = null; summary = null;}}>
              <span class="opponent-dot"></span>
              <span class="enemy-name"><strong>{enemy.name}</strong><small>{source(enemy.origin)} · {role(enemy.archetype)}</small></span>
              <ChevronRight size={15}/>
            </button>
          {/each}
          {#if enemies.length === 0}<p class="placeholder">Nenhum adversário de laboratório. Gere o primeiro à esquerda.</p>{/if}
        </div>
      </div>
    </section>

    <section class="panel lab-sheet">
      <div class="lab-head"><span class="head-icon coral"><BookOpen size={19}/></span><div><h2>Ficha do adversário</h2><p>Dados e mecânicas disponíveis para avaliação</p></div></div>
      {#if selected}
        <div class="lab-control-body">
          <div class="profile-identity">
            <div><small>{source(selected.origin)}</small><h3>{selected.name}</h3><p>{selected.tier ?? 'Categoria não informada'} · {role(selected.archetype)}</p></div>
            <span class="profile-lock"><ShieldAlert size={15}/> TESTE</span>
          </div>
          <div class="lab-stats">
            <div><small>HP</small><strong>{numeric(selected.hp)}</strong></div>
            <div><small>EA</small><strong>{numeric(selected.ea)}</strong></div>
            <div><small>ESP</small><strong>{numeric(selected.spirit)}</strong></div>
            <div><small>DES</small><strong>{numeric(selected.dexterity)}</strong></div>
          </div>
          <div class="section-caption"><BrainCircuit size={14}/> PROFICIÊNCIAS</div>
          <div class="prof-grid">
            <div><span>Reforço</span><strong>{selected.reinforcement_level === null ? '—' : 'Nv ' + selected.reinforcement_level}</strong></div>
            <div><span>Output</span><strong>{selected.output_level === null ? '—' : 'Nv ' + selected.output_level}</strong></div>
            <div><span>Energia Reversa</span><strong>{selected.reverse_level === null ? '—' : 'Nv ' + selected.reverse_level}</strong></div>
            <div><span>Expansão de Domínio</span><strong>{selected.domain_level === null ? '—' : 'Nv ' + selected.domain_level}</strong></div>
          </div>
          <div class="section-caption"><Swords size={14}/> TÉCNICAS <span>{selected.techniques.length}</span></div>
          <div class="skills-list">
            {#each selected.techniques as skill, i}
              <div class="skill-row">
                <span class="skill-num">{String(i + 1).padStart(2,'0')}</span>
                <div><strong>{skill.name}</strong>
                  <p>{skill.effect ?? 'Efeito não informado'}</p>
                  <small>{skill.damage ?? 'Dano pendente'} · {skill.ea_cost === null ? 'EA pendente' : skill.ea_cost + ' EA'} · {skill.status === 'placeholder' ? 'Placeholder' : skill.status === 'synthetic' ? 'Sintética' : 'Fornecida'}</small>
                </div>
              </div>
            {/each}
          </div>
          <details class="assumptions"><summary><AlertTriangle size={14}/> Premissas e limites da geração</summary>{#each selected.assumptions as assumption}<p>{assumption}</p>{/each}</details>
          <button class="lab-adopt" disabled={busy} on:click={adopt}><Swords size={17}/> Adicionar esta ficha aos inimigos do combate</button>
          <p class="lab-explain">Esta ação cria uma cópia editável na ficha real. A origem fictícia ou incompleta continuará identificada.</p>
          <div class="lab-divider"></div>
          <div class="section-caption"><Play size={14}/> TESTE SINTÉTICO OPCIONAL</div>
          <div class="two eval-fields">
            <label>Cenário
              <select bind:value={scenario}>
                {#each scenarios as item}<option value={item.value}>{item.name}</option>{/each}
              </select>
            </label>
            <button class="lab-primary" disabled={busy} on:click={evaluate}><Play size={16}/> Avaliar decisão</button>
          </div>
        </div>
      {:else}
        <div class="empty-state"><Dices size={35}/><strong>Sem adversário selecionado</strong><p>Crie uma ficha sintética ou carregue um dos exemplos informados.</p></div>
      {/if}
    </section>
  </div>

  <details class="optional-benchmarks">
    <summary>Exibir laboratório de benchmarks sintéticos (opcional)</summary>
  <div class="lab-grid below">
    <section class="panel lab-benchmark">
      <div class="lab-head"><span class="head-icon lavender"><RotateCcw size={19}/></span><div><h2>Bateria de cenários</h2><p>Teste várias sementes e situações de combate</p></div></div>
      <div class="lab-control-body">
        <p class="lab-explain">Roda uma série de avaliações contra adversários procedurais. Nenhuma ação é registrada na ficha real e os adversários não são considerados oficiais.</p>
        <div class="two eval-fields">
          <label>Quantidade de cenários
            <select bind:value={samples}><option value={5}>5 testes</option><option value={8}>8 testes</option><option value={12}>12 testes</option><option value={20}>20 testes</option></select>
          </label>
          <button class="lab-primary" disabled={busy || template !== 'procedural'} on:click={batch}><RotateCcw size={17}/> Rodar bateria</button>
        </div>
        {#if template !== 'procedural'}<p class="lab-explain">Para baterias, selecione o modelo procedural no gerador.</p>{/if}
        {#if summary}
          <div class="bench-metrics">
            <div><small>TESTES</small><strong>{summary.tests}</strong></div>
            <div><small>COM RECOMENDAÇÃO</small><strong>{summary.tests_with_recommendation}</strong></div>
            <div><small>ROTAS DISTINTAS</small><strong>{summary.unique_recommendations}</strong></div>
          </div>
          <div class="bench-results"><strong>Rotas mais frequentes</strong>
            {#each summary.most_frequent_recommendations as item}<p><span>{item.name}</span><b>{item.count}×</b></p>{/each}
          </div>
          <p class="disclaimer">{summary.learning_status}</p>
        {/if}
      </div>
    </section>
    <section class="panel lab-history">
      <div class="lab-head"><span class="head-icon"><Database size={19}/></span><div><h2>Memória de avaliações</h2><p>Experiências sintéticas guardadas para regressão</p></div></div>
      <div class="lab-control-body">
        {#if latestRun}
          <div class="latest-run">
            <span>ÚLTIMA AVALIAÇÃO</span>
            <strong>{latestRun.details.enemy_name}</strong>
            <p>Recomendação: {latestRun.recommendation ?? 'Nenhuma sequência validada'}</p>
            <small>{latestRun.candidates_considered} opções retornadas · score {latestRun.score ?? '—'} (não é chance de vitória)</small>
          </div>
        {/if}
        <div class="section-caption"><Database size={14}/> HISTÓRICO DO LABORATÓRIO <span>{runs.length}</span></div>
        <div class="runs-list">
          {#each runs.slice(0, 12) as run (run.id)}
            <button on:click={() => {latestRun = run; summary = null;}}>
              <span class="run-indicator"><CheckCircle2 size={15}/></span>
              <span><strong>{run.details.enemy_name}</strong><small>{run.scenario} · {run.recommendation ?? 'Sem recomendação'}</small></span>
              <ChevronRight size={15}/>
            </button>
          {/each}
          {#if !runs.length}<p class="placeholder">Nenhuma avaliação foi registrada ainda.</p>{/if}
        </div>
        <div class="lab-footnote"><AlertTriangle size={15}/><span>O Learning Mode receberá estes testes como dados sintéticos. Eles não comprovam vitórias nem corrigem automaticamente a estratégia.</span></div>
      </div>
    </section>
  </div>
  </details>
</div>

<style>
.lab-adopt{background:#2c5943;border:1px solid #498166;color:#e4f8ea;font-size:11px;font-weight:800;padding:12px;border-radius:9px;width:100%;display:flex;align-items:center;justify-content:center;gap:9px;margin:22px 0 10px}.lab-adopt:hover{background:#3b7557}.lab-adopt:disabled{opacity:.5}.optional-benchmarks{margin-top:20px}.optional-benchmarks>summary{cursor:pointer;font-size:12px;color:#b9c5d4;font-weight:750;border:1px solid #344254;padding:14px;border-radius:10px;background:#1b2631}.lab-page{min-width:0}.lab-page :global(.page-heading){margin-bottom:23px}
.lab-intro,.lab-alert,.lab-success{display:flex;align-items:flex-start;gap:13px;padding:17px 20px;border-radius:12px;margin:0 0 20px}
.lab-intro{background:linear-gradient(95deg,#24283b,#1b2634);border:1px solid #343b51}
.lab-intro-icon{color:#b5a6f9;background:#34344f;padding:11px;border-radius:11px}
.lab-intro strong{display:block;font-size:12px;color:#e5e8f3}
.lab-intro p{font-size:11px;color:#a2aec2;line-height:1.65;margin:6px 0 0}
.lab-alert{background:#422d2d;color:#ffb4a6;border:1px solid #654444;font-size:12px}
.lab-success{background:#23392f;color:#a2e4c0;border:1px solid #35644d;font-size:12px}
.lab-grid{display:grid;grid-template-columns:minmax(300px,.85fr) minmax(0,1.28fr);gap:18px;align-items:start}.lab-grid.below{margin-top:18px;grid-template-columns:repeat(2,minmax(0,1fr))}
.lab-head{padding:19px 21px;border-bottom:1px solid #2b3542;display:flex;align-items:center;gap:12px}
.head-icon{width:39px;height:39px;display:grid;place-items:center;background:#2b334b;color:#aeb8f7;border-radius:10px;flex-shrink:0}
.head-icon.coral{background:#423037;color:#f19b89}.head-icon.lavender{background:#38314b;color:#c3b0ee}
.lab-head h2{margin:0 0 5px;font-size:14px}.lab-head p{margin:0;color:#8b9aad;font-size:10px}
.lab-control-body{padding:20px}.lab-control-body label{display:grid;gap:8px;font-size:10px;font-weight:750;color:#aab8c9;margin-bottom:17px}
.lab-control-body input,.lab-control-body select{background:#111720;color:#ebeff7;border:1px solid #364254;border-radius:8px;min-height:40px;padding:9px 11px;width:100%;font-size:11px}
.lab-control-body label small{font-weight:400;color:#75869b;line-height:1.5}
.lab-control-body input:focus,.lab-control-body select:focus{outline:2px solid #a1645d;outline-offset:1px}
.two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.lab-primary{min-height:41px;border:1px solid #ef907b;background:#ea7a65;border-radius:9px;color:#251718;display:flex;align-items:center;justify-content:center;gap:9px;font-size:11px;font-weight:850;width:100%;padding:10px 12px}
.lab-primary:hover{background:#ff947e}.lab-primary:disabled{opacity:.5}
.lab-divider{height:1px;background:#2c3847;margin:25px 0 20px}
.section-caption{display:flex;align-items:center;gap:8px;color:#8796a7;font-size:9px;letter-spacing:1.2px;font-weight:800;margin:14px 0}
.section-caption span{margin-left:auto;color:#dfe7f0}
.saved-list,.runs-list{display:grid;gap:5px;max-height:310px;overflow:auto}
.saved-list button,.runs-list button{display:flex;align-items:center;gap:10px;background:#1b2430;border:1px solid transparent;border-radius:9px;padding:11px;color:#bdcad9;text-align:left;width:100%}
.saved-list button.active,.saved-list button:hover,.runs-list button:hover{border-color:#506177;background:#252e3d}
.opponent-dot{height:8px;width:8px;flex-shrink:0;border-radius:50%;background:#e37d71}
.enemy-name,.runs-list button>span:nth-child(2){min-width:0;flex:1}
.enemy-name strong,.enemy-name small,.runs-list strong,.runs-list small{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.enemy-name strong,.runs-list strong{font-size:11px}.enemy-name small,.runs-list small{font-size:9px;color:#8d9cac;margin-top:4px}
.placeholder{font-size:11px;color:#8392a5;line-height:1.6;padding:12px}
.profile-identity{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:20px}
.profile-identity small{font-size:9px;letter-spacing:1.2px;color:#efac98;font-weight:800}
.profile-identity h3{font-size:21px;margin:7px 0 6px}.profile-identity p{font-size:11px;color:#90a1b5;margin:0}
.profile-lock{display:flex;align-items:center;gap:6px;color:#e1b391;background:#46372f;border:1px solid #644f3c;padding:7px;border-radius:6px;font-size:9px;font-weight:800;white-space:nowrap}
.lab-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin-bottom:25px}
.lab-stats div{background:#192431;border:1px solid #2c3b4d;padding:12px;border-radius:10px;min-width:0}
.lab-stats small{display:block;color:#8a9bac;font-size:9px;font-weight:800}.lab-stats strong{display:block;font-size:14px;margin-top:8px;overflow-wrap:anywhere}
.prof-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-bottom:22px}
.prof-grid>div{padding:10px;background:#1a2330;border:1px solid #2c3745;border-radius:8px;display:flex;justify-content:space-between;gap:10px}
.prof-grid span,.prof-grid strong{font-size:10px}.prof-grid span{color:#96a5b6}
.skills-list{display:grid;gap:9px}.skill-row{padding:12px;border:1px solid #303d4d;border-radius:9px;background:#19222e;display:flex;align-items:flex-start;gap:12px}
.skill-num{color:#db877e;background:#402f34;border-radius:6px;padding:6px;font-size:10px;font-weight:800}
.skill-row strong{font-size:12px}.skill-row p{font-size:11px;color:#aab9ca;line-height:1.4;margin:5px 0}
.skill-row small{font-size:9px;color:#8597ac;line-height:1.4}
.assumptions{font-size:11px;color:#e2af8d;background:#362d2a;border:1px solid #564239;border-radius:9px;padding:12px;margin-top:18px}
.assumptions summary{display:flex;align-items:center;gap:7px;cursor:pointer;font-weight:750}
.assumptions p{color:#bba99c;line-height:1.5;margin:10px 0 0}
.eval-fields{align-items:end}.eval-fields label{margin:0}.eval-fields button{margin-bottom:0}
.lab-explain{font-size:11px;color:#a1afc2;line-height:1.65;margin:0 0 17px}
.bench-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin-top:20px}
.bench-metrics div{background:#222d3b;border:1px solid #3a495e;border-radius:9px;padding:12px}
.bench-metrics small{display:block;color:#96a6b8;font-size:8px;letter-spacing:.7px;line-height:1.5;font-weight:800}
.bench-metrics strong{display:block;font-size:20px;margin-top:7px}
.bench-results{margin-top:19px}.bench-results>strong{font-size:11px}.bench-results p{display:flex;justify-content:space-between;gap:12px;font-size:11px;color:#a5b4c5;border-bottom:1px solid #2b3745;padding:11px 0;margin:0}
.bench-results b{color:#e5edf7}.disclaimer{font-size:10px;color:#94ad9f;line-height:1.6;margin-top:17px}
.latest-run{background:#23382f;border:1px solid #355745;border-radius:9px;padding:14px;margin-bottom:17px}
.latest-run span{font-size:9px;letter-spacing:1px;color:#a8d7bb;font-weight:800;display:block}
.latest-run strong{font-size:13px;display:block;margin-top:7px}.latest-run p{font-size:11px;line-height:1.5;color:#c6ddce}
.latest-run small{font-size:10px;color:#a1b7ab}
.run-indicator{background:#283b36;color:#70c5a0;padding:7px;border-radius:7px}
.lab-footnote{display:flex;align-items:flex-start;gap:9px;background:#2b2b31;padding:13px;border:1px solid #45414a;border-radius:9px;color:#adabad;font-size:10px;line-height:1.5;margin-top:20px}
.lab-footnote svg{flex-shrink:0}
@media(max-width:1100px){.lab-grid,.lab-grid.below{grid-template-columns:1fr}}@media(max-width:520px){.lab-stats{grid-template-columns:repeat(2,1fr)}.lab-grid{display:block}.lab-grid>.panel{margin-bottom:14px}.two{grid-template-columns:1fr}.prof-grid{grid-template-columns:1fr}.eval-fields button{margin-top:0}.lab-control-body{padding:15px}}
</style>
