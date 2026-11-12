# Combat Mode — narração, rolagens, fichas e memória real

O jogador controla a narrativa com o mestre. O RPG Combat Brain **não executa uma luta sozinho**, não rola dados por conta própria e não aplica dano sem confirmação.

## Fluxo

1. Cadastre as fichas na aba **Fichas de combate**. Cada aliado ou inimigo pode ter HP, EA, ESP, DES, níveis de Reforço/Output/Reversa/Domínio e técnicas próprias.
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
