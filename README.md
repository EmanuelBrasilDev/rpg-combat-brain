# RPG Combat Brain 🧠⚔️

Assistente conversacional tático e **local-first** para o RPG **JJK — Era da Calamidade**. Implementado com SvelteKit, Python/FastAPI e SQLite, **sem LLM, tokens ou APIs externas de IA**.

**Status: MVP v0.1 em desenvolvimento.** As recomendações são heurísticas explicáveis; não substituem as regras ou decisões do mestre.

## Descoberta gradual das técnicas inimigas

A \`EnemyAbilityDiscoverySkill\` cria propostas de técnicas inimigas com base nas ações **observadas** durante o combate. O sistema não exige conhecer todas as habilidades do inimigo desde o início.

Exemplo no chat: **"Mahito usou Transfiguração Ociosa, cooldown 2 turnos, custa 30 EA, efeito: transforma o alvo ao tocar."**

1. O motor reconhece a técnica e tenta localizar a ficha do inimigo nomeado. Se houver mais de um inimigo sem identificação clara, você escolhe a ficha.
2. Um painel em **Relatos de combate** permite revisar **nome, inimigo, dano, EA, cooldown e efeito** e salvar a proposta.
3. Somente após **Confirmar relato** a técnica é vinculada à ficha real, de forma transacional.
4. Campos desconhecidos continuam vazios. Se a técnica já existir, o motor preenche somente informações faltantes; divergências com dados já registrados bloqueiam a atualização.
5. O histórico real inclui o novo conhecimento, mas a ferramenta ainda não faz cálculo automático de todas as habilidades do adversário.

Comando estruturado opcional para nomes difíceis:
\`@tecnica Mahito | Transfiguração Ociosa | cd=2 | dano=5d8+3d2 | ea=30 | efeito: altera a forma do alvo\`.

**Não confundir**: observar o uso de uma técnica sintética não valida todos os seus atributos previamente gerados. Essa origem permanece sinalizada na ficha.

## Atributos do Akira — valores confirmados

Os atributos da ficha do RPG são **Força 26**, **Velocidade 34**, **Resistência 26**, **Intelecto 30** e **Espírito 34** (máximo **50** por atributo). A nomenclatura canônica nas fichas é \`strength\`, \`speed\`, \`resistance\`, \`intellect\`, \`spirit\`; o antigo campo \`dexterity\` foi substituído por \`speed\`, mantendo migração compatível.

| Atributo | Valor | Modificador |
|---|---:|---:|
| Força | 26 | +8 |
| Velocidade | 34 | +12 |
| Resistência | 26 | +8 |
| Intelecto | 30 | +10 |
| Espírito | 34 | +12 |

Para valores **de 10 a 50**, o modificador é \`(atributo - 10) // 2\`: 10 → +0, 12 → +1, 14 → +2, ..., 50 → +20. Em valores ímpares usa-se o piso (interpretação conservadora). A regra de modificadores abaixo de 10 não foi informada: o sistema sinaliza como pendente, não inventa valores negativos.

O Combat Brain mostra e compara esses valores para os inimigos, mantendo atributos não informados como desconhecidos. **Não soma modificadores a dano, acerto ou defesa sem regra específica.** Em uma fórmula como \`ESP d10\`, a quantidade de dados continua sendo o **valor bruto de Espírito**, e não o modificador.

O banco SQLite atualiza registros antigos ao iniciar: renomeia \`dexterity\` para \`speed\`, preenche no Akira os campos que estavam vazios com os valores confirmados, e **preserva valores já editados**. Valores legados acima de 50 são arquivados em \`extra_metrics\` antes de aplicar o teto de 50. O histórico registra o evento \`attribute_migration\`.

Exemplo de edição pelo chat: \`/set akira velocidade 36\` ou \`/set akira forca 28\`. Também é possível editar os cinco atributos na aba **Fichas de combate**.

## Hierarquia de graus das maldições

**Regra de classificação:** **Grau Especial > Grau 1 > Grau 2 > Grau 3 > Grau 4**. Para graus numerados, um número **menor** indica uma maldição **mais forte**.

O \`CurseGradeSkill\` reconhece graus explícitos da ficha e sinaliza cautela adicional quando o adversário é Grau 1 ou Especial, sem presumir danos, estatísticas ou uma derrota inevitável. Se o grau não for informado, permanece desconhecido.

**Atenção:** o campo \`difficulty\` da geração procedural (1 a 5) é uma escala **sintética e independente**, na qual valores maiores geram adversários de teste mais fortes. Ele **não** representa graus de maldição. Não é convertível automaticamente para Grau 4/3/2/1/Especial.

## Novo fluxo narrativo — Combat Mode + Learning Mode

**Seu papel:** narrar acontecimentos reais, informar rolagens e habilidades utilizadas, editar fichas de combate e confirmar o que realmente ocorreu.

**Papel do agente:** interpretar o relato por padrões, guardar os resultados de rolagens, acompanhar fichas, elaborar recomendações contextualizadas e coletar experiências reais confirmadas para análise posterior.

**Skills novas:**
- \`DiceRollInterpreter\` — separa fórmulas dos resultados efetivamente rolados e identifica autoria possível do teste;
- \`CombatEventTracker\` — cria rascunhos de eventos e propõe apenas estados finais absolutos explícitos;
- \`CombatContextAnalyzer\` — consulta relatos confirmados e dados recentes sem converter fatos antigos em ameaças atuais;
- \`CombatLearningSkill\` — resume experiências reais confirmadas e avaliações do jogador, sem alterar pesos automaticamente.

**Mudanças nas existentes:** Enemy Forge agora permite **copiar explicitamente** um inimigo gerado para a batalha real, com ficha e técnicas editáveis. O Learning Mode prioriza experiências reais; testes sintéticos continuam isolados e opcionais.

**Exemplo:** "O inimigo tirou 24 no ataque. Eu tirei 19 na esquiva, recebi 35 de dano e atualizei meu HP para 565." O chat prepara um relato **pendente**. Você revisa e confirma. Se HP já foi atualizado no painel, **não será descontado novamente**. Se informar somente "35 de dano", nenhum valor será descontado automaticamente.

> **Importante:** a interpretação é baseada em padrões locais, não em LLM. O usuário deve conferir os relatos; descrições complexas podem precisar de correção manual. A v0.3 registra aprendizado descritivo, mas ainda não treina pesos e nem executa ações de inimigos automaticamente.

Documentação completa: [docs/COMBAT_MODE.md](docs/COMBAT_MODE.md).

## Funcionalidades

- **Centro de comando responsivo**, com chat, estado de batalha, indicadores e ações disponíveis.
- **Fichas editáveis** do Akira, aliados e inimigos, incluindo HP, EA, os cinco atributos reais, habilidades usadas, forma ativa, reações e efeitos.
- **CharacterSheetAnalyzer** para consultas e comparação de fichas.
- **16 Skills planejadas e módulos iniciais implementados:** conhecimentos, cálculos, combos, reações, análise adversária, interpretação, atualizações e respostas.
- **Memória persistente** com SQLite: fichas, histórico de edição, conversas e desfazer a última edição.
- **Motor tático inicial** que busca sequências de até duas ações, valida os limites, estima médias de dano quando há dados e informa incertezas.
- **Catálogo inicial** de Akira baseado nos materiais e explicações fornecidos na conversa.

## Learning Lab e Enemy Forge (nova aba)

A aba **Learning Lab** permite gerar adversários de teste com **EnemyForgeSkill** e executar baterias de cenários pelo **LearningLabSkill**.

- Perfis fornecidos como exemplo: **Maldição Grau 3** (300 HP, 200 EA, garras 5d8 + 3d2) e **Mahito** (1000 HP, 1200 EA, seis técnicas pendentes).
- Perfis **procedurais**, com arquétipos de ataque, defesa, controle e equilíbrio; dificuldade 1–5, seed reproduzível e técnicas hipotéticas.
- Níveis de Reforço, Output, Reversa e Domínio simulados **apenas** em adversários procedurais, sem declarar esses números oficiais.
- Avaliações por cenário (abertura, sob ataque, curto alcance, longo alcance e área) e lotes para testes repetidos.
- Dados laboratoriais armazenados em tabelas SQLite **separadas das fichas e eventos reais**.
- Sem fingir vitórias: os resultados atuais são **benchmarks da qualidade/cobertura da recomendação**, não uma luta bilateral completa nem provas de sucesso. Não atualizam automaticamente os pesos do motor.

Detalhes: **[docs/LEARNING_LAB.md](docs/LEARNING_LAB.md)**.

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

- Akira **600 HP e 731 EA são valores atuais**. Os máximos de HP/EA continuam desconhecidos; os cinco atributos informados pelo jogador já foram cadastrados.
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
3. Confirmar regras de rolagem para aplicar modificadores dos atributos a acerto, defesa e resistências.
4. Integrar mais profundamente as Skills e calibrar avaliação estratégica com batalhas reais.
5. Implementar usuários, sincronização e implantação online.
