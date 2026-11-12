# RPG Combat Brain 🧠⚔️

Assistente conversacional tático e **local-first** para o RPG **JJK — Era da Calamidade**. Implementado com SvelteKit, Python/FastAPI e SQLite, **sem LLM, tokens ou APIs externas de IA**.

**Status: MVP v0.1 em desenvolvimento.** As recomendações são heurísticas explicáveis; não substituem as regras ou decisões do mestre.

## Funcionalidades

- **Centro de comando responsivo**, com chat, estado de batalha, indicadores e ações disponíveis.
- **Fichas editáveis** do Akira, aliados e inimigos, incluindo HP, EA, ESP, DES, habilidades usadas, forma ativa, reações e efeitos.
- **CharacterSheetAnalyzer** para consultas e comparação de fichas.
- **16 Skills planejadas e módulos iniciais implementados:** conhecimentos, cálculos, combos, reações, análise adversária, interpretação, atualizações e respostas.
- **Memória persistente** com SQLite: fichas, histórico de edição, conversas e desfazer a última edição.
- **Motor tático inicial** que busca sequências de até duas ações, valida os limites, estima médias de dano quando há dados e informa incertezas.
- **Catálogo inicial** de Akira baseado nos materiais e explicações fornecidos na conversa.

## Como executar localmente

Pré-requisitos: **Python 3.11+**, **Node.js 20+**.

**Terminal 1 — API FastAPI**

~~~bash
cd backend
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
~~~

Documentação interativa: http://127.0.0.1:8000/docs

Banco SQLite: \`backend/data/combat_brain.sqlite3\`, criado automaticamente e ignorado pelo Git. Pode ser alterado pela variável de ambiente \`RPG_DB_PATH\`.

**Terminal 2 — Frontend SvelteKit**

~~~bash
cd frontend
npm install
npm run dev
~~~

Abra http://127.0.0.1:5173. Para mudar o backend, crie \`frontend/.env\` com \`VITE_API_URL=https://...\` (veja \`.env.example\`).

**Testes**

~~~bash
cd backend && python -m pytest -q
cd ../frontend && npm run check && npm run build
~~~

O arquivo \`.github/workflows/ci.yml\` configura testes automáticos no GitHub.

## Exemplos de comandos

| Mensagem | Resultado |
|---|---|
| "Qual a ficha do Akira?" | Consulta do estado atual |
| "Mostre todos os inimigos" | Comparação de fichas |
| "Qual minha melhor abertura?" | Recomendações táticas e alternativas |
| "Devo bloquear ou esquivar?" | Análise de ações possíveis |
| \`/set akira ea 400\` | Atualiza a EA e registra evento |
| "atualiza o HP do Akira Uchiha para 550" | Atualiza HP explicitamente |
| "Desfazer" | Desfaz a última edição suportada |
| "Novo turno" | Restaura ações e reação; mantém efeitos |

**Importante:** mensagens como "vou usar Fangs" não descontam recursos. Simulações e planos são diferentes de ações confirmadas.

## Estrutura

~~~text
frontend/                SvelteKit + TypeScript + CSS
backend/app/main.py      API FastAPI
backend/app/store.py     Fichas persistidas e eventos em SQLite
backend/app/skills/      Skills determinísticas
backend/app/data/        Catálogo estruturado de regras
backend/tests/           Testes unitários e de API
~~~

## Skills

- **Conhecimento:** RulebookSkill, AkiraProfileSkill, CombatMemorySkill, CharacterSheetAnalyzer.
- **Cálculos:** EnergyOptimizer, DamageCalculator, DiceProbability, ActionValidator.
- **Estratégia:** OpeningArchitectSkill, ComboForge, ReactionMasterSkill, EnemyAnalysisSkill, TacticalDecision.
- **Conversação:** CombatInterpreter, BattleUpdateSkill, TacticalResponse.

As 16 funções estão representadas na base de código em estágios diferentes de integração. **O motor de combos e o interpretador ainda são versões iniciais, não um agente conversacional de linguagem irrestrita.**

## Dados confirmados versus pendentes

A base \`backend/app/data/catalog.json\` foi estruturada a partir de **Sistema.txt, Akira.txt e dos esclarecimentos fornecidos pelo jogador**, sem introduzir habilidades não confirmadas. Os arquivos TXT completos não foram reproduzidos neste repositório.

Exemplos de informações deliberadamente pendentes:

- Akira **600 HP e 731 EA são valores atuais**. Máximos e valores exatos de ESP/DES não foram presumidos.
- **Fangs custa 35 EA originalmente e 25 EA com Fornalha**, conforme confirmação. A progressão 35 → 25 → 16 → 11 informada não coincide com a composição direta dos percentuais declarados; outros custos e descontos são exibidos como incompletos.
- Custos de ativação de **Dragon Scales / Dragon Assault** ainda não informados.
- Efeitos completos de Kokusen, condições do pós-Amaterasu, rolamentos de defesa e duração de alguns efeitos ainda precisam de validação.
- Em cenas com informações desconhecidas, a pontuação tática é **uma heurística do software**, não uma probabilidade verificada ou regra do mestre.

## Caminho híbrido para publicação

A v0.1 é executada **localmente**. É possível publicar futuramente o **frontend na Vercel**, apontando \`VITE_API_URL\` para uma API hospedada separadamente.

**Não publique o backend deste MVP como um serviço aberto.** Ele foi feito para uma única máquina, sem contas, autenticação ou segregação de fichas. SQLite local **não oferece persistência confiável em funções serverless**. Antes de publicar com dados reais, implementar PostgreSQL persistente, autenticação, autorização, política de CORS e backups.

## Próximas entregas

1. Separar ficha-base permanente de estado temporário de batalha.
2. Padronizar execução confirmada de ações, turnos, cooldowns e custos.
3. Confirmar atributos e regras ainda pendentes.
4. Integrar mais profundamente as Skills e calibrar avaliação estratégica com batalhas reais.
5. Implementar usuários, sincronização e implantação online.
