<script lang="ts">
  import { ClipboardCopy, Check, FileText, RotateCcw, AlertCircle } from 'lucide-svelte';
  import { onMount } from 'svelte';
  import { api, type Character, type EnemyProfile } from '$lib/api';

  export let character: Character | EnemyProfile;
  export let source: 'combat' | 'lab' = 'combat';

  let text = '';
  let loading = false;
  let copied = false;
  let error = '';
  let lastFingerprint = '';
  let latestRequest = 0;
  let mounted = false;

  onMount(() => { mounted = true; });

  $: fingerprint = JSON.stringify({ source, character });
  $: if (mounted && fingerprint !== lastFingerprint) {
    lastFingerprint = fingerprint;
    void generate();
  }

  async function generate() {
    const token = ++latestRequest;
    loading = true;
    copied = false;
    error = '';
    try {
      const result = source === 'lab' ? await api.exportLabEnemy(character.id) : await api.exportCharacter(character.id);
      if (token === latestRequest) text = result.content;
    } catch (err) {
      if (token === latestRequest) {
        text = '';
        error = err instanceof Error ? err.message : 'Falha ao exportar a ficha.';
      }
    } finally {
      if (token === latestRequest) loading = false;
    }
  }

  async function copy() {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      copied = true;
      error = '';
    } catch {
      error = 'A cópia automática não foi permitida. Selecione e copie o texto abaixo.';
    }
  }
</script>

<section class="sheet-export" aria-label="Ficha textual">
  <div class="sheet-export-head">
    <div class="sheet-export-title">
      <FileText size={21}/>
      <div>
        <strong>Ficha em texto estilizado</strong>
        <small>Markdown pronto para copiar · baseado no estado atual da ficha</small>
      </div>
    </div>
    <div class="sheet-export-actions">
      <button type="button" disabled={loading} on:click={generate} aria-label="Atualizar ficha textual">
        <RotateCcw size={15}/> Atualizar
      </button>
      <button type="button" class="copy" disabled={!text || loading} on:click={copy}>
        {#if copied}<Check size={15}/> Copiado{:else}<ClipboardCopy size={15}/> Copiar texto{/if}
      </button>
    </div>
  </div>
  {#if source === 'lab'}<p class="note"><strong>Enemy Forge:</strong> apenas leitura. Exportar não adiciona o adversário ao combate; dados sintéticos continuam sinalizados.</p>{/if}
  <p class="note">Usos e cooldowns são diferentes. <code>?c</code> indica recarga desconhecida e <code>?t</code> indica turnos restantes não controlados; nenhum deles é tratado como zero.</p>
  {#if error}<p role="alert" class="error"><AlertCircle size={15}/>{error}</p>{/if}
  {#if loading && !text}<p class="loading">Preparando ficha...</p>{/if}
  {#if text}<pre aria-label="Prévia Markdown da ficha">{text}</pre>{/if}
</section>

<style>
  .sheet-export{margin-top:22px;padding:18px 20px;border:1px solid #32475b;border-radius:13px;background:#151e2a;min-width:0}
  .sheet-export-head{display:flex;gap:14px;justify-content:space-between;align-items:center;flex-wrap:wrap}
  .sheet-export-title{display:flex;gap:11px;align-items:center;color:#96c6e9;min-width:0}
  .sheet-export-title strong{font-size:13px;color:#e4ebf7;display:block}
  .sheet-export-title small{font-size:10px;color:#9cafc5;display:block;line-height:1.5;margin-top:4px}
  .sheet-export-actions{display:flex;gap:7px;flex-wrap:wrap}
  .sheet-export-actions button{background:#253346;color:#d5e3f3;border:1px solid #435872;border-radius:8px;padding:9px 11px;font-size:11px;display:flex;align-items:center;gap:7px;cursor:pointer}
  .sheet-export-actions button.copy{background:#2d5947;color:#d5f4df;border-color:#3f775f}
  .sheet-export-actions button:disabled{opacity:.5;cursor:not-allowed}
  .note{font-size:10px;line-height:1.6;color:#b3becd;margin:12px 0}
  .note code{color:#e5b68b}
  .error{display:flex;align-items:flex-start;gap:7px;color:#ffb0aa;font-size:11px;line-height:1.5}
  .loading{font-size:11px;color:#9cafc5}
  pre{margin:12px 0 0;max-height:520px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.65;font:12px/1.65 ui-monospace,SFMono-Regular,Consolas,'Liberation Mono',monospace;background:#0d141d;color:#dbe7f7;border:1px solid #2e3a4b;border-radius:9px;padding:16px}
  @media(max-width:550px){.sheet-export{padding:14px}.sheet-export-actions{width:100%}}
</style>