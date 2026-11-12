# EnemyForgeSkill → LearningLabSkill

## Finalidade

Esta Skill **não serve principalmente para colocar inimigos novos na batalha real**.
Ela é um **gerador de cenários de teste** que alimenta os experimentos do Learning Mode, permitindo regressões antes de alterar o sistema estratégico.

### Fluxo

1. \`EnemyForgeSkill\` gera um adversário a partir de uma **semente** e um **arquétipo**.
2. O laboratório persiste a ficha em \`lab_enemies\`, **separada** das fichas reais.
3. \`LearningLabSkill\` chama \`TacticalDecision\` em um cenário ("abertura", "sob ataque", "corpo a corpo", "longa distância" ou "área").
4. A decisão, pontuação relativa, contexto e avisos são persistidos em \`learning_runs\`.
5. A bateria pode repetir 5–24 testes, comparando escolhas e cobertura do motor em diferentes situações.
6. O Learning Mode poderá comparar resultados entre versões do algoritmo, consultar decisões e receber feedback humano.

## Fichas de referência e fichas sintéticas

**Maldição Grau 3**: HP 300, EA 200 e Ataque de Garras 5d8 + 3d2, conforme o exemplo fornecido. Os níveis de Output, Reforço, Reversa e Domínio permanecem **desconhecidos**.

**Mahito**: HP 1000, EA 1200 e seis espaços de técnica com \`0c\` (como no exemplo). **Não foram inventadas técnicas, efeitos ou estatísticas canônicas.** Este é um rascunho de referência, não uma ficha do anime ou oficial.

**Procedural**: quatro arquétipos originais, dificuldades 1–5, seed determinística e até cinco técnicas sintéticas mais um domínio hipotético, conforme a dificuldade. Atributos e técnicas são **inteiramente fabricados pelo laboratório** e claramente etiquetados como tais. Os níveis das proficiências não equivalem automaticamente a custo ou habilidade disponível até suas mecânicas serem implementadas no motor do inimigo.

## Invariantes de segurança de dados

- O laboratório **não modifica** \`characters\`, \`events\` ou o estado real da batalha.
- Nenhum resultado de laboratório é rotulado como "vitória", "derrota", "taxa de sucesso" ou "prova de habilidade".
- \`actual_result=null\` e \`verified=false\` em todas as avaliações sintéticas.
- Nenhum aprendizado automático altera os pesos de \`TacticalDecision\` na v0.2.
- Futuramente, dados observados em combates reais deverão ser armazenados com **procedência própria** e avaliação humana.
- Fichas sintéticas não viram automaticamente inimigos oficiais sem aprovação do jogador/mestre.

## Endpoints

- \`POST /api/lab/enemies/generate\` — cria perfil isolado.
- \`GET /api/lab/enemies\` — consulta fichas do laboratório.
- \`POST /api/lab/evaluate\` — executa cenário contra perfil salvo.
- \`POST /api/lab/benchmarks\` — roda uma bateria sintética de 1 a 24 cenários.
- \`GET /api/lab/runs\` — consulta avaliações históricas.

## Limite atual

Os adversários são perfis ricos, mas **não agentes táticos executáveis**. O simulador atual avalia a resposta do Akira a contextos de texto e **ainda não gera uma luta bilateral com resultados de dados, defesa do inimigo, consumo de EA adversário ou vitória real**.

A próxima fase deverá criar um motor de turnos para inimigos e permitir experimentos realmente comparáveis entre versões (componente de planejamento adversarial e validação de regras). Esta versão inicial é um **benchmark de decisões e cobertura**.
