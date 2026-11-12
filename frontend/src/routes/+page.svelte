<script lang="ts">
  import { onMount, tick } from 'svelte';
  import {
    Activity, AlertCircle, ArrowRight, BookOpen, BrainCircuit,
    Check, ChevronDown, ChevronRight, CircleHelp, Clock3,
    Database, Flame, History, Menu, MessageCircle, Plus,
    RotateCcw, Send, Settings2, Shield, Skull, Sparkles,
    Swords, Target, Trash2, UserRound, UsersRound,
    X, Zap
  } from 'lucide-svelte';
  import { api, type Ability, type BattleEvent, type Catalog, type Character, type ChatMessage, type Team } from '$lib/api';

  type View = 'overview' | 'characters' | 'abilities' | 'history';
  let view: View = 'overview';
  let characters: Character[] = [];
  let messages: ChatMessage[] = [];
  let catalog: Catalog | null = null;
  let events: BattleEvent[] = [];
  let selectedId = 'akira';
  let selected: Character | null = null;
  let loading = true;
  let apiError = '';
  let pending = false;
  let fieldSaving = '';
  let messageDraft = '';
  let messageEnd: HTMLDivElement;
  let mobileMenu = false;
  let showCreate = false;
  let newName = '';
  let newTeam: Team = 'ally';
  let activeSideTab: 'sheet' | 'abilities' = 'sheet';
  let showPending = false;
  let toast = '';

  $: selected = characters.find((c) => c.id === selectedId) ?? null;
  $: allies = characters.filter((c) => c.team === 'ally');
  $: enemies = characters.filter((c) => c.team === 'enemy');

  function num(value: number | null): string {
    return value === null ? '—' : String(value);
  }
  function bar(value: number | null, maximum: number | null): number | null {
    return value !== null && maximum !== null && maximum > 0
      ? Math.max(0, Math.min(100, Math.round((value / maximum) * 100)))
      : null;
  }
  function parseOptionalNumber(text: string): number | null {
    return text.trim() === '' ? null : Number(text);
  }
  function clean(text: string): string {
    return text.replace(/\*\*/g, '');
  }
  function when(date: string): string {
    const parsed = new Date(date);
    return Number.isNaN(parsed.getTime()) ? date : parsed.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
  }
  function actionName(kind: string): string {
    return ({ edited: 'Ficha alterada', chat_update: 'Comando confirmado', undo: 'Edição desfeita', new_turn: 'Novo turno', created: 'Ficha cadastrada' } as Record<string, string>)[kind] || kind;
  }
  function notify(text: string) {
    toast = text;
  }
  async function refresh() {
    try {
      const [c, m, e, cat] = await Promise.all([
        api.characters(), api.messages(), api.events(), api.catalog()
      ]);
      characters = c;
      messages = m;
      events = e;
      catalog = cat;
      apiError = '';
      if (!c.some((item) => item.id === selectedId) && c.length) selectedId = c[0].id;
    } catch (error) {
      apiError = error instanceof Error ? error.message : 'Não foi possível conectar ao backend local.';
    } finally {
      loading = false;
    }
  }
  onMount(() => { void refresh(); });

  async function update(field: keyof Character, value: unknown) {
    if (!selected) return;
    fieldSaving = String(field);
    try {
      const changed = await api.patchCharacter(selected.id, { [field]: value } as Partial<Character>);
      characters = characters.map((c) => c.id === changed.id ? changed : c);
      events = await api.events();
      notify('Ficha atualizada e registrada no histórico.');
    } catch (error) {
      notify(error instanceof Error ? error.message : 'Falha ao salvar a ficha.');
    } finally {
      fieldSaving = '';
    }
  }
  async function createCharacter() {
    if (!newName.trim()) return;
    pending = true;
    try {
      const item = await api.addCharacter(newName.trim(), newTeam);
      characters = await api.characters();
      selectedId = item.id;
      events = await api.events();
      showCreate = false;
      newName = '';
      view = 'characters';
      notify('Nova ficha criada.');
    } catch (error) {
      notify(error instanceof Error ? error.message : 'Não foi possível criar a ficha.');
    } finally {
      pending = false;
    }
  }
  async function sendMessage(value?: string) {
    const text = (value ?? messageDraft).trim();
    if (!text || pending || !selected) return;
    messageDraft = '';
    pending = true;
    messages = [...messages, {
      id: -Date.now(), role: 'user', content: text, created_at: new Date().toISOString()
    }];
    await tick();
    messageEnd?.scrollIntoView({ behavior: 'smooth' });
    try {
      await api.chat(text, selected.id);
      const [fresh, sheets, history] = await Promise.all([api.messages(), api.characters(), api.events()]);
      messages = fresh;
      characters = sheets;
      events = history;
      apiError = '';
      await tick();
      messageEnd?.scrollIntoView({ behavior: 'smooth' });
    } catch (error) {
      notify(error instanceof Error ? error.message : 'Falha ao enviar a mensagem.');
      messages = messages.filter((m) => m.id > 0);
    } finally {
      pending = false;
    }
  }
  async function undo() {
    if (pending) return;
    pending = true;
    try {
      await api.undo();
      characters = await api.characters();
      events = await api.events();
      notify('Última alteração desfeita.');
    } catch (error) {
      notify(error instanceof Error ? error.message : 'Não foi possível desfazer.');
    } finally {
      pending = false;
    }
  }
  async function newTurn() {
    if (pending || !selected) return;
    pending = true;
    try {
      await api.newTurn(selected.id);
      characters = await api.characters();
      events = await api.events();
      notify('Ações e reações restauradas. Efeitos permanecem inalterados.');
    } catch (error) {
      notify(error instanceof Error ? error.message : 'Erro ao criar turno.');
    } finally {
      pending = false;
    }
  }
  function chooseCharacter(id: string) {
    selectedId = id;
    mobileMenu = false;
  }
  function changeView(next: View) {
    view = next;
    mobileMenu = false;
  }
</script>

<svelte:head>
  <title>RPG Combat Brain — Centro de Comando</title>
</svelte:head>

<div class="app-shell">
  {#if mobileMenu}
    <button class="mobile-overlay" aria-label="Fechar navegação" on:click={() => mobileMenu = false}></button>
  {/if}

  <aside class:mobile-open={mobileMenu} class="sidebar">
    <div class="brand">
      <div class="brand-icon"><BrainCircuit size={25} strokeWidth={1.8}/></div>
      <div>
        <strong>COMBAT<span>BRAIN</span></strong>
        <small>TACTICAL INTELLIGENCE</small>
      </div>
      <button class="icon-btn close-mobile" aria-label="Fechar menu" on:click={() => mobileMenu = false}><X size={18}/></button>
    </div>

    <div class="side-scroll">
      <div class="nav-caption">ESPAÇO DE TRABALHO</div>
      <nav class="nav-list" aria-label="Navegação principal">
        <button class:nav-active={view === 'overview'} on:click={() => changeView('overview')}><Activity size={18}/> Visão geral <ChevronRight size={15} class="nav-chevron"/></button>
        <button class:nav-active={view === 'characters'} on:click={() => changeView('characters')}><UserRound size={18}/> Fichas de combate <ChevronRight size={15} class="nav-chevron"/></button>
        <button class:nav-active={view === 'abilities'} on:click={() => changeView('abilities')}><Flame size={18}/> Arsenal de técnicas <ChevronRight size={15} class="nav-chevron"/></button>
        <button class:nav-active={view === 'history'} on:click={() => changeView('history')}><History size={18}/> Histórico <ChevronRight size={15} class="nav-chevron"/></button>
      </nav>

      <div class="nav-caption roster-heading"><span>COMBATENTES</span><button class="add-small" title="Adicionar ficha" aria-label="Adicionar personagem" on:click={() => showCreate = true}><Plus size={16}/></button></div>
      <div class="roster">
        {#each characters as combatant (combatant.id)}
          <button class:roster-active={combatant.id === selectedId} class="roster-item" on:click={() => chooseCharacter(combatant.id)}>
            <span class:enemy-avatar={combatant.team === 'enemy'} class:ally-avatar={combatant.team === 'ally'} class="avatar">
              {#if combatant.team === 'enemy'}<Skull size={17}/>{:else if combatant.team === 'ally'}<Shield size={17}/>{:else}<UserRound size={17}/>{/if}
            </span>
            <span class="roster-name"><strong>{combatant.name}</strong><small>{combatant.team === 'player' ? 'Personagem principal' : combatant.team === 'ally' ? 'Aliado' : 'Inimigo'} · HP {num(combatant.hp)}</small></span>
            {#if combatant.id === selectedId}<span class="roster-dot"></span>{/if}
          </button>
        {/each}
        {#if characters.length === 0 && !loading}<p class="empty-roster">Nenhuma ficha disponível.</p>{/if}
        <button class="roster-add" on:click={() => showCreate = true}><Plus size={15}/> Adicionar combatente</button>
      </div>
    </div>

    <div class="side-footer">
      <div class="local-tag"><span class:offline={!!apiError} class="online-dot"></span>{apiError ? 'BACKEND OFFLINE' : 'MOTOR LOCAL ATIVO'}<span class="version">v0.1</span></div>
      <div class="side-footnote"><Database size={14}/> Sem tokens · Sem IA externa</div>
    </div>
  </aside>

  <div class="workspace">
    <header class="topbar">
      <div class="topbar-left">
        <button class="icon-btn menu-mobile" aria-label="Abrir menu" on:click={() => mobileMenu = true}><Menu size={21}/></button>
        <div class="breadcrumbs"><span>WORKSPACE</span><ChevronRight size={14}/><strong>{view === 'overview' ? 'Centro de comando' : view === 'characters' ? 'Fichas de combate' : view === 'abilities' ? 'Arsenal de técnicas' : 'Histórico'}</strong></div>
      </div>
      <div class="topbar-actions">
        <span class="mode-pill"><span class="mode-dot"></span> LOCAL-FIRST</span>
        <button class="icon-btn" title="Sincronizar dados" aria-label="Atualizar dados" on:click={() => void refresh()}><RotateCcw size={17}/></button>
        <span class="top-profile"><BrainCircuit size={18}/></span>
      </div>
    </header>

    {#if apiError}
      <div class="connection-error">
        <AlertCircle size={19}/>
        <div><strong>API local indisponível</strong><span>{apiError}. Execute o FastAPI na porta 8000 para habilitar fichas e conversação.</span></div>
        <button class="btn btn-outline" on:click={() => void refresh()}>Reconectar</button>
      </div>
    {/if}

    <main>
      {#if view === 'overview'}
        <div class="page-heading">
          <div>
            <div class="eyebrow"><span></span> CENTRO DE OPERAÇÕES</div>
            <h1>Bem-vindo ao <em>Combat Brain.</em></h1>
            <p>Sua inteligência tática, construída a partir das regras do seu RPG.</p>
          </div>
          <button class="btn btn-outline desktop-btn" on:click={newTurn}><RotateCcw size={16}/> Novo turno</button>
        </div>
        <div class="stat-grid">
          <div class="stat-card"><span class="stat-icon warm"><UserRound size={18}/></span><small>PERSONAGEM ATIVO</small><strong>{selected?.name ?? '—'}</strong><span class="stat-note">Nível {num(selected?.level ?? null)} · {selected?.form === 'none' ? 'Forma base' : selected?.form === 'scales' ? 'Dragon Scales' : 'Dragon Assault'}</span></div>
          <div class="stat-card"><span class="stat-icon green"><Activity size={18}/></span><small>VIDA ATUAL</small><strong>{num(selected?.hp ?? null)} <span>HP</span></strong><span class="stat-note">{selected?.max_hp != null ? 'Máximo: ' + selected.max_hp : 'Máximo não cadastrado'}</span></div>
          <div class="stat-card"><span class="stat-icon blue"><Zap size={18}/></span><small>ENERGIA AMALDIÇOADA</small><strong>{num(selected?.ea ?? null)} <span>EA</span></strong><span class="stat-note">{selected?.max_ea != null ? 'Máximo: ' + selected.max_ea : 'Máximo não cadastrado'}</span></div>
          <div class="stat-card"><span class="stat-icon violet"><UsersRound size={18}/></span><small>COMBATENTES</small><strong>{characters.length.toString().padStart(2, '0')} <span>ativos</span></strong><span class="stat-note">{allies.length} aliados · {enemies.length} inimigos</span></div>
        </div>

        <div class="dashboard-grid">
          <section class="panel chat-panel">
            <div class="panel-title">
              <div class="panel-title-left"><span class="feature-icon"><BrainCircuit size={20}/></span><div><h2>Combat Brain <span class="ai-tag">ENGINE</span></h2><p>Assistente estratégico determinístico</p></div></div>
              <span class="status-label"><span></span> PRONTO</span>
            </div>
            <div class="chat-stream">
              {#if messages.length === 0}
                <div class="chat-welcome">
                  <div class="chat-logo"><BrainCircuit size={36} strokeWidth={1.4}/></div>
                  <span class="eyebrow centered">INTELIGÊNCIA DE COMBATE</span>
                  <h3>Qual é o seu próximo movimento?</h3>
                  <p>Analiso fichas, regras, ações e combinações para encontrar suas melhores opções táticas.</p>
                  <div class="suggestions">
                    <button on:click={() => sendMessage('Qual minha melhor abertura de combate?')}><Target size={15}/> Melhor abertura</button>
                    <button on:click={() => sendMessage('Monte um combo usando a Kenrykat e Fangs')}><Swords size={15}/> Criar combo</button>
                    <button on:click={() => sendMessage('Qual a ficha do Akira?')}><BookOpen size={15}/> Consultar ficha</button>
                    <button on:click={() => sendMessage('Devo bloquear ou esquivar de um ataque?')}><Shield size={15}/> Analisar defesa</button>
                  </div>
                </div>
              {:else}
                <div class="messages">
                  {#each messages as message (message.id)}
                    <div class:human={message.role === 'user'} class="message">
                      <div class="message-avatar">{#if message.role === 'assistant'}<BrainCircuit size={17}/>{:else}<UserRound size={17}/>{/if}</div>
                      <div class="message-content">
                        <div class="message-top"><strong>{message.role === 'assistant' ? 'Combat Brain' : 'Você'}</strong><time>{when(message.created_at)}</time></div>
                        <div class="message-body">{clean(message.content)}</div>
                        {#if message.role === 'assistant' && message.alternatives && message.alternatives.length}
                          <div class="analysis-candidates">
                            {#each message.alternatives as option, i}
                              <div class:recommended={i === 0} class="candidate"><span class="candidate-index">{i === 0 ? '★' : '0' + (i + 1)}</span><div><strong>{option.title}</strong><small>{option.main_actions} ações principais · {option.cost_reference} EA {option.cost_verified ? '(referência confirmada)' : '(custo a validar)'}</small></div></div>
                            {/each}
                          </div>
                        {/if}
                        {#if message.role === 'assistant' && message.warnings && message.warnings.length}
                          <details class="chat-warnings"><summary><AlertCircle size={14}/> {message.warnings.length} observações e incertezas</summary>{#each message.warnings as warning}<p>{warning}</p>{/each}</details>
                        {/if}
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}
              {#if pending}<div class="thinking"><span class="thinking-dot"></span> Analisando com as Skills locais...</div>{/if}
              <div bind:this={messageEnd}></div>
            </div>
            <div class="chat-composer">
              <div class="composer-wrap">
                <textarea rows="2" aria-label="Mensagem para o Combat Brain" placeholder="Descreva a situação ou pergunte sobre uma estratégia..." bind:value={messageDraft} on:keydown={(event) => {if(event.key === 'Enter' && !event.shiftKey){event.preventDefault(); void sendMessage();}}}></textarea>
                <button class="send-button" aria-label="Enviar mensagem" disabled={pending || !messageDraft.trim()} on:click={() => sendMessage()}><Send size={18}/></button>
              </div>
              <div class="composer-foot"><span><Sparkles size={13}/> Respostas baseadas nas regras cadastradas</span><span>ENTER para enviar</span></div>
            </div>
          </section>

          <section class="panel intel-panel">
            <div class="panel-title compact"><div class="panel-title-left"><span class="feature-icon red"><Target size={19}/></span><div><h2>Battle Intel</h2><p>Monitoramento em tempo real</p></div></div></div>
            {#if selected}
              <div class="intel-body">
                <div class="intel-char">
                  <span class="large-avatar"><UserRound size={26}/></span>
                  <div><strong>{selected.name}</strong><small>{selected.team === 'player' ? 'COMBATENTE PRINCIPAL' : selected.team === 'ally' ? 'ALIADO' : 'ADVERSÁRIO'}</small></div>
                  <button class="tiny-action" title="Editar ficha" aria-label="Editar ficha" on:click={() => changeView('characters')}><Settings2 size={17}/></button>
                </div>
                <div class="resource-section">
                  <div class="resource-heading"><span><Activity size={14}/> VIDA</span><strong>{num(selected.hp)} <small>/ {num(selected.max_hp)}</small></strong></div>
                  <div class="resource-track"><span class="health-progress" style:width={(bar(selected.hp, selected.max_hp) ?? 100) + '%'}></span></div>
                  <div class="resource-heading"><span><Zap size={14}/> ENERGIA AMALDIÇOADA</span><strong>{num(selected.ea)} <small>/ {num(selected.max_ea)}</small></strong></div>
                  <div class="resource-track"><span class="energy-progress" style:width={(bar(selected.ea, selected.max_ea) ?? 100) + '%'}></span></div>
                  {#if selected.max_hp === null || selected.max_ea === null}<p class="resource-footnote">Barras ilustrativas até cadastrar os máximos.</p>{/if}
                </div>
                <div class="intel-subtitle">ESTADO DE COMBATE</div>
                <div class="intel-states">
                  <div><span>Forma ativa</span><strong>{selected.form === 'scales' ? 'Dragon Scales' : selected.form === 'assault' ? 'Dragon Assault' : 'Forma base'}</strong></div>
                  <div><span>Ações principais</span><strong>{selected.main_actions} / 2</strong></div>
                  <div><span>Ações bônus</span><strong>{selected.bonus_actions} / 2</strong></div>
                  <div><span>Reação</span><strong class:available={selected.reaction_available}>{selected.reaction_available ? 'Disponível' : 'Utilizada'}</strong></div>
                  <div><span>Críticos para Kokusen</span><strong>{selected.critical_count} / 3</strong></div>
                </div>
                <div class="intel-subtitle">USOS DE TÉCNICAS</div>
                <div class="usage-row"><span>Fangs</span><div class="usage-track"><div style:width={(selected.fangs_used / 6 * 100) + '%'}></div></div><strong>{selected.fangs_used}/6</strong></div>
                <div class="usage-row"><span>Maw</span><div class="usage-track"><div style:width={(selected.maw_used / 6 * 100) + '%'}></div></div><strong>{selected.maw_used}/6</strong></div>
                <div class="usage-row"><span>Amaterasu</span><div class="usage-track"><div style:width={(selected.amaterasu_used * 100) + '%'}></div></div><strong>{selected.amaterasu_used}/1</strong></div>
                <button class="btn btn-primary fullwidth" on:click={() => sendMessage('Analise o estado atual do combate e recomende a melhor sequência')}><BrainCircuit size={17}/> Analisar combate <ArrowRight size={15}/></button>
              </div>
            {:else}
              <div class="panel-empty"><UserRound size={26}/> Selecione ou crie uma ficha para começar.</div>
            {/if}
          </section>
        </div>
        <div class="bottom-info"><span><Check size={14}/> Decisões auditáveis</span><span><Shield size={14}/> Regras antes de recomendações</span><span><Database size={14}/> Histórico local persistente</span></div>

      {:else if view === 'characters'}
        <div class="page-heading">
          <div><div class="eyebrow"><span></span> GESTÃO DE PERSONAGENS</div><h1>Fichas de <em>Combate.</em></h1><p>Edite atributos em tempo real; as Skills consultarão a versão mais recente.</p></div>
          <button class="btn btn-primary" on:click={() => showCreate = true}><Plus size={17}/> Nova ficha</button>
        </div>
        <div class="sheet-grid">
          <section class="panel sheet-list-panel">
            <div class="section-label">SELECIONE UM COMBATENTE</div>
            {#each characters as combatant (combatant.id)}
              <button class:chosen={combatant.id === selectedId} class="sheet-list-item" on:click={() => chooseCharacter(combatant.id)}>
                <span class:enemy-avatar={combatant.team === 'enemy'} class:ally-avatar={combatant.team === 'ally'} class="avatar"><UserRound size={17}/></span>
                <span><strong>{combatant.name}</strong><small>{combatant.team === 'player' ? 'Principal' : combatant.team === 'ally' ? 'Aliado' : 'Inimigo'}</small></span>
                <ChevronRight size={16}/>
              </button>
            {/each}
            <button class="roster-add" on:click={() => showCreate = true}><Plus size={15}/> Adicionar ficha</button>
          </section>
          <section class="panel sheet-edit-panel">
            {#if selected}
              <div class="sheet-header"><div><span class="eyebrow">EDITAR ESTADO DO COMBATE</span><h2>{selected.name}</h2><p>As alterações são salvas e auditadas individualmente.</p></div><span class="saved-badge"><Check size={14}/> SQLite</span></div>
              <div class="field-group-title">Identificação e atributos</div>
              <div class="field-grid">
                <label>Nome<input value={selected.name} on:change={(e) => update('name', e.currentTarget.value)}/></label>
                <label>Nível<input type="number" min="1" value={selected.level ?? ''} on:change={(e) => update('level', parseOptionalNumber(e.currentTarget.value))}/></label>
                <label>HP atual<input type="number" min="0" value={selected.hp ?? ''} on:change={(e) => update('hp', parseOptionalNumber(e.currentTarget.value))}/></label>
                <label>HP máximo <small>(se conhecido)</small><input type="number" min="0" value={selected.max_hp ?? ''} on:change={(e) => update('max_hp', parseOptionalNumber(e.currentTarget.value))}/></label>
                <label>EA atual<input type="number" min="0" value={selected.ea ?? ''} on:change={(e) => update('ea', parseOptionalNumber(e.currentTarget.value))}/></label>
                <label>EA máxima <small>(se conhecida)</small><input type="number" min="0" value={selected.max_ea ?? ''} on:change={(e) => update('max_ea', parseOptionalNumber(e.currentTarget.value))}/></label>
                <label>Espírito (ESP)<input type="number" min="0" value={selected.spirit ?? ''} on:change={(e) => update('spirit', parseOptionalNumber(e.currentTarget.value))}/></label>
                <label>Destreza (DES)<input type="number" min="0" value={selected.dexterity ?? ''} on:change={(e) => update('dexterity', parseOptionalNumber(e.currentTarget.value))}/></label>
              </div>
              <div class="field-group-title">Estado e disponibilidade</div>
              <div class="field-grid">
                <label>Forma ativa<select value={selected.form} on:change={(e) => update('form', e.currentTarget.value)}><option value="none">Forma base</option><option value="scales">Dragon Scales</option><option value="assault">Dragon Assault</option></select></label>
                <label>Ações principais<select value={selected.main_actions} on:change={(e) => update('main_actions', Number(e.currentTarget.value))}><option value="0">0</option><option value="1">1</option><option value="2">2</option></select></label>
                <label>Ações bônus<select value={selected.bonus_actions} on:change={(e) => update('bonus_actions', Number(e.currentTarget.value))}><option value="0">0</option><option value="1">1</option><option value="2">2</option></select></label>
                <label>Reação<select value={selected.reaction_available ? 'yes' : 'no'} on:change={(e) => update('reaction_available', e.currentTarget.value === 'yes')}><option value="yes">Disponível</option><option value="no">Utilizada</option></select></label>
                <label>Fangs utilizados<input type="number" min="0" max="6" value={selected.fangs_used} on:change={(e) => update('fangs_used', Number(e.currentTarget.value))}/></label>
                <label>Maw utilizados<input type="number" min="0" max="6" value={selected.maw_used} on:change={(e) => update('maw_used', Number(e.currentTarget.value))}/></label>
                <label>Amaterasu utilizado<input type="number" min="0" max="1" value={selected.amaterasu_used} on:change={(e) => update('amaterasu_used', Number(e.currentTarget.value))}/></label>
                <label>Críticos acumulados<input type="number" min="0" max="3" value={selected.critical_count} on:change={(e) => update('critical_count', Number(e.currentTarget.value))}/></label>
              </div>
              <div class="field-grid field-full">
                <label>Efeitos ativos <small>(separados por vírgula)</small><input value={selected.effects.join(', ')} on:change={(e) => update('effects', e.currentTarget.value.split(',').map((x) => x.trim()).filter(Boolean))} placeholder="Ex.: queimadura, reforço ativo"/></label>
                <label>Observações de combate<textarea rows="3" value={selected.notes} on:change={(e) => update('notes', e.currentTarget.value)} placeholder="Informações confirmadas do mestre, limitações, fraquezas..."></textarea></label>
              </div>
              <div class="sheet-actions"><span>{fieldSaving ? 'Salvando ' + fieldSaving + '...' : 'Atualização automática ao alterar um campo'}</span><button class="btn btn-outline" on:click={undo}><RotateCcw size={15}/> Desfazer última edição</button></div>
            {:else}
              <div class="panel-empty">Selecione uma ficha.</div>
            {/if}
          </section>
        </div>

      {:else if view === 'abilities'}
        <div class="page-heading">
          <div><div class="eyebrow"><span></span> BASE DE CONHECIMENTO</div><h1>Arsenal de <em>Técnicas.</em></h1><p>Regras cadastradas, fontes e lacunas que ainda exigem confirmação.</p></div>
          <span class="mode-pill">{catalog?.abilities.length ?? 0} habilidades cadastradas</span>
        </div>
        <div class="arsenal-layout">
          <div class="ability-grid">
            {#each catalog?.abilities ?? [] as ability (ability.id)}
              <article class="panel ability-card">
                <div class="ability-head"><span class="ability-symbol"><Flame size={18}/></span><span class="ability-status">{ability.status === 'partial' ? 'PARCIAL' : 'CONFIRMADO'}</span></div>
                <h3>{ability.name}</h3><p>{ability.kind === 'form' ? 'Forma de combate' : ability.kind === 'weapon' ? 'Arma amaldiçoada' : 'Técnica de combate'}</p>
                <div class="ability-facts"><span>EA ORIGINAL</span><strong>{ability.base_cost === null ? 'Pendente' : ability.base_cost + ' EA'}</strong></div>
                {#if ability.damage}<div class="ability-detail"><span>DANO</span><strong>{String(ability.damage)}</strong></div>{/if}
                {#if ability.burn}<div class="ability-detail"><span>QUEIMADURA</span><strong>{String(ability.burn)}</strong></div>{/if}
                {#if ability.confirmed_cost_with_fornalha}<div class="ability-detail"><span>CUSTO CONFIRMADO (FORNALHA)</span><strong>{String(ability.confirmed_cost_with_fornalha)} EA</strong></div>{/if}
                {#if ability.notes}<p class="ability-note">{String(ability.notes)}</p>{/if}
              </article>
            {/each}
          </div>
          <section class="panel pending-panel">
            <div class="panel-title compact"><div class="panel-title-left"><span class="feature-icon red"><AlertCircle size={18}/></span><div><h2>Pontos pendentes</h2><p>Sem inferências inventadas</p></div></div></div>
            <div class="pending-list">{#each catalog?.pending ?? [] as item}<div><span class="pending-bullet"></span><p>{item}</p></div>{/each}</div>
          </section>
        </div>

      {:else if view === 'history'}
        <div class="page-heading">
          <div><div class="eyebrow"><span></span> MEMÓRIA PERSISTENTE</div><h1>Histórico de <em>Combate.</em></h1><p>Cada alteração confirmada na ficha fica registrada para revisão.</p></div>
          <button class="btn btn-outline" on:click={undo}><RotateCcw size={16}/> Desfazer último evento</button>
        </div>
        <div class="panel history-panel">
          {#if !events.length}
            <div class="panel-empty"><History size={28}/> Nenhum evento registrado.</div>
          {:else}
            <div class="timeline">
              {#each events as event (event.id)}
                <div class="event-row"><div class="event-mark"><Clock3 size={16}/></div><div><strong>{actionName(event.kind)}</strong><p>{event.after?.name ?? event.before?.name ?? event.character_id}{#if event.before && event.after && event.before.ea !== event.after.ea} · EA {num(event.before.ea ?? null)} → {num(event.after.ea ?? null)}{/if}{#if event.before && event.after && event.before.hp !== event.after.hp} · HP {num(event.before.hp ?? null)} → {num(event.after.hp ?? null)}{/if}</p></div><time>{when(event.created_at)}</time></div>
              {/each}
            </div>
          {/if}
        </div>
      {/if}
    </main>
  </div>
</div>

{#if showCreate}
  <div class="modal-backdrop">
    <button class="modal-dismiss" type="button" aria-label="Fechar janela" on:click={() => showCreate = false}></button>
    <div class="modal" role="dialog" tabindex="-1" aria-modal="true" aria-label="Criar nova ficha">
      <div class="modal-title"><div><span class="eyebrow">NOVO COMBATENTE</span><h2>Adicionar ficha</h2></div><button class="icon-btn" aria-label="Fechar" on:click={() => showCreate = false}><X size={19}/></button></div>
      <p>Cadastre aliados e inimigos mesmo com informações incompletas. A análise respeitará os campos desconhecidos.</p>
      <label>Nome do personagem<input maxlength="80" placeholder="Ex.: Maldição desconhecida" bind:value={newName}/></label>
      <label>Tipo de combatente<select bind:value={newTeam}><option value="ally">Aliado</option><option value="enemy">Inimigo</option></select></label>
      <div class="modal-actions"><button class="btn btn-outline" on:click={() => showCreate = false}>Cancelar</button><button class="btn btn-primary" disabled={!newName.trim() || pending} on:click={createCharacter}><Plus size={16}/> Criar ficha</button></div>
    </div>
  </div>
{/if}

{#if toast}
  <div class="toast" role="status"><Check size={16}/><span>{toast}</span><button aria-label="Fechar aviso" on:click={() => toast = ''}><X size={15}/></button></div>
{/if}
