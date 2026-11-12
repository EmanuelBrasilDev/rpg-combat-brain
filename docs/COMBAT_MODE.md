# Combat Mode — narração, rolagens, fichas e memória real

O jogador controla a narrativa com o mestre. O RPG Combat Brain **não executa uma luta sozinho**, não rola dados por conta própria e não aplica dano sem confirmação.

## Mega Brain — estado do Akira

A habilidade extra **Mega Brain** (Estado, Pessoal, 0 EA, duração 1 turno, cooldown 2 turnos) está registrada como regra fornecida pelo jogador. Para ativá-la, use **Ativar Mega Brain** na ficha do Akira ou informe **"Ativei Mega Brain"** e confirme o relato; todas as ações bônus restantes são consumidas, sem gasto de EA. Durante o turno ativo, resultados **naturais** de 15+ no d20 são críticos. **Stun, Paralisia, Fear** ou outro CC confirmado encerram o estado.

O estado ativo, turnos restantes e cooldown restante são separados do cooldown **base**. O novo turno explicitamente avançado pelo jogador encerra o estado de 1 turno e reduz a recarga restante em 1 (contagem iniciada na ativação); o campo da ficha permite correção caso a convenção do mestre seja outra. A interrupção por CC não elimina o cooldown. A interpretação de relatos é conservadora e requer confirmação humana antes de mudar o estado.

Sem indicação de que um número é um **resultado natural do d20**, o motor não presume crítico. Mesmo com resultado natural 15+, não modifica automaticamente o contador de Kokusen, pois os critérios de confirmação ainda dependem da mesa.

## Fichas de outras personagens e adversários do Enemy Forge

A **SheetTargetResolverSkill** procura a ficha solicitada tanto no combate quanto nos adversários **salvos no laboratório**. Em pedidos como *"Transforme a ficha do Guardião de Pedra em texto no modelo do Akira"*, a ficha-alvo é **Guardião de Pedra**; "modelo do Akira" informa apenas o padrão de formatação.

O sistema não recorre ao Akira se o nome solicitado estiver ausente ou for ambíguo. Em múltiplas gerações do mesmo nome-base (ex.: Guardião de Pedra · D2/S11 e · D4/S12), solicita o nome completo ou \`/ficha-texto <id>\`. Sem nome explícito, o comando \`/ficha-texto\` ainda usa a ficha de combate selecionada.

A exportação \`GET /api/lab/enemies/{id}/export\` e o botão **Copiar texto** do Enemy Forge formatam perfis sem criar fichas de combate, alterar dados ou converter valores sintéticos em fatos.

## Exportação estilizada da ficha

A nova **CharacterSheetFormatterSkill** gera um texto Markdown da ficha persistida. O usuário pode copiar o resultado na aba **Fichas de combate** ou pedir pelo chat "ficha em texto", "ficha estilizada" ou \`/ficha-texto\`. Os campos são dinâmicos: HP, EA, atributos, usos de técnica, efeitos e habilidades personalizadas refletem os valores salvos.

Nas seções de Akira, Dragon Scales/Assault, Mangekyō Sharingan, técnicas e Kenrykat são exibidos com **valores conhecidos do catálogo**; equipamentos e habilidades extras só aparecem se cadastrados. Fichas de inimigos usam **seus próprios dados**, sem emprestar o arsenal do Akira.

As marcações \`?c\` (cooldown desconhecido) e \`?t\` (turnos restantes desconhecidos) impedem que o sistema declare cooldown ou duração restante de zero sem evidência. A exportação é somente leitura, sem rolagens, sem ações executadas ou alteração de HP/EA.

API: \`GET /api/characters/{id}/export\`.

## Descoberta de habilidades inimigas

Ao contrário da ficha inicial, as técnicas dos inimigos surgem gradualmente. A **EnemyAbilityDiscoverySkill** reconhece habilidades relatadas e cria um rascunho na mesma memória de combate. Exemplo:

> "A Maldição Grau 3 usou Ataque de Garras, dano 5d8 + 3d2, cooldown 2 turnos."

No painel de revisão, escolha o inimigo responsável, revise o **nome**, indique **cooldown** e os detalhes que o mestre realmente revelou. Depois, salve a proposta e confirme o relato. A habilidade aparece na ficha desse inimigo.

Se o nome não estiver claro, use o comando estruturado \`@tecnica Inimigo | Nome da Técnica | cd=2 | dano=5d8+3d2 | ea=20 | efeito: observação\`, ou edite manualmente o rascunho. Com vários inimigos sem identidade clara, nenhuma ficha é selecionada automaticamente. Também não há registros por palavras genéricas como "usou uma técnica".

Técnicas observadas não são duplicadas pelo nome normalizado, informações faltantes não são inventadas, e divergências com valores já cadastrados exigem revisão humana. Um cooldown informado descreve a **recarga da habilidade**, mas não representa uma contagem regressiva automática durante turnos.

**Limitação:** a interpretação é orientada por padrões, funciona melhor com frases explícitas, e pode não identificar descrições complexas. Sempre revise antes de confirmar.

## Fluxo

1. Cadastre as fichas na aba **Fichas de combate**. Cada aliado ou inimigo pode ter HP, EA, Força, Velocidade, Resistência, Intelecto, Espírito (0–50), níveis de Reforço/Output/Reversa/Domínio e técnicas próprias.
2. Na aba **Enemy Forge & Learning**, gere uma ficha original ou carregue uma referência. Clique **Adicionar esta ficha aos inimigos do combate** para copiar os dados. Essa ação é explícita e não torna as técnicas sintéticas regras oficiais.
3. No chat da **Visão geral**, descreva o evento real:
   - "O inimigo usou Ataque de Garras e tirou 24 no acerto. Eu tentei esquivar e tirei 19. Recebi 35 de dano e atualizei meu HP para 565."
4. \`CombatInterpreter\` identifica o relato. \`DiceRollInterpreter\` extrai os resultados informados e as fórmulas, separando total rolado de expressão não rolada.
5. \`CombatEventTracker\` prepara um **relato pendente**. O painel **Relatos de combate** mostra o texto original, rolagens e alterações absolutas propostas.
6. Clique **Confirmar relato** ou **Descartar**.
7. O backend confere a ficha **novamente**. Apenas estados finais absolutos relatados podem ser gravados; dano e EA gastos sem estados finais são observações. Se a ficha já foi atualizada para o valor desejado, **não há duplo desconto**. Se houver alteração conflitante posterior, a confirmação é bloqueada.
8. O relato confirmado fica disponível para \`CombatContextAnalyzer\` e \`CombatLearningSkill\`.
9. Pergunte "Qual minha melhor ação agora?" e o agente usará o estado atual da ficha. Relatos ainda pendentes **não** são fatos e o histórico de ataques **não** significa que a ameaça continua ativa.
10. Na aba **Enemy Forge & Learning**, a seção de experiências reais permite avaliar o relato como boa, neutra/inconclusiva ou ruim, com justificativa. Essas avaliações são registradas como feedback humano.

## Atributos e modificadores

Os cinco atributos canônicos são **Força, Velocidade, Resistência, Intelecto e Espírito**. O antigo campo \`dexterity\` é migrado para \`speed\` (Velocidade). O Akira possui valores iniciais confirmados **26, 34, 26, 30 e 34** nessa ordem. Valores já editados nas fichas antigas não são descartados.

O modificador de cada atributo de **10 a 50** é \`(valor - 10) // 2\`, com 50 → +20. Valores abaixo de 10 ainda não possuem fórmula confirmada, e campos não informados permanecem desconhecidos. As comparações com inimigos exibem vantagens/desvantagens **informativas**, sem inventar bonificações para testes não descritos pelo mestre. Técnicas cuja notação usa \`ESP d10\` continuam multiplicando os dados pelo valor bruto de Espírito, e não pelo modificador.

## Segurança de estados

- Relato de *plano* ("vou usar Fangs") não consome recurso e não é um evento confirmado.
- Relato de fato passado ("usei Fangs") pode gerar um rascunho; nunca é confirmado automaticamente.
- O valor "35 de dano recebido" **não** autoriza o sistema a subtrair 35 de HP. Somente um estado final como "meu HP ficou em 565" pode propor atualização absoluta.
- Se já alterou a ficha manualmente para 565 HP, confirmar o relato mantém 565.
- Não presumimos o custo final de técnicas cujos descontos estão pendentes.
- Nenhuma declaração de rolagem ou defesa é inventada.
- Fichas originárias do laboratório são identificadas como **sintéticas** ou **exemplos fornecidos**, e suas técnicas não são emprestadas para outros personagens.
- Confirmação repetida do **mesmo ID de relato** é idempotente. Relatos diferentes podem falar do mesmo acontecimento; revise antes de confirmar.
- Quando a ficha muda para um estado conflitante depois da criação do rascunho, o servidor retorna erro 409 e exige revisão humana.

## Progresso atual e limitações

Esta entrega implementa uma extração **por padrões de texto** (não há LLM local/externo). Ela reconhece alguns verbos de ações concluídas, expressões de dados e estados finais, mas ainda pode deixar passar narrativas longas/ambíguas. Revise as informações antes de confirmar.

A recomendação tática ainda usa o motor heurístico inicial e não explora todas as respostas inimigas ou custos de técnicas cadastradas manualmente. A presença de uma técnica na ficha de inimigo permite consultar e reconhecer o nome, **não** torna a técnica executável automaticamente.

**Learning Mode nesta versão**: recebe relatos confirmados, contagem de rolagens e avaliação humana, com memória persistente. Não altera regras nem pesos táticos automaticamente, porque ainda não temos validação estatística suficiente. Os benchmarks sintéticos antigos continuam opcionais e armazenados separadamente.

## Endpoints adicionais

- \`GET /api/combat/reports?status=pending\`
- \`POST /api/combat/reports/{id}/review\` com \`{"decision":"confirmed"}\` ou \`{"decision":"discarded"}\`
- \`POST /api/combat/reports/{id}/feedback\` com \`{"rating":"good","note":"..."}\`
- \`GET /api/learning/overview\`
- \`POST /api/lab/enemies/{id}/adopt\`
