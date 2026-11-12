# Decisões arquiteturais — RPG Combat Brain

## Objetivo

Um assistente de RPG que **não depende de LLM nem de API de IA**. A conversação usa identificação de intenções, frases pré-definidas e consulta a dados estruturados; decisões são geradas por algoritmos de busca e validação.

## Fluxo de dados

1. O jogador consulta ou altera a **ficha**.
2. A API valida o payload e registra a alteração como **evento**.
3. As Skills consultam a última versão persistida.
4. O motor expande sequências possíveis de até duas ações principais.
5. O validador elimina ações que violam limites e falta de EA **confirmada**.
6. A heurística compara as sequências; as lacunas de regras são exibidas ao usuário.
7. A resposta apresenta uma recomendação **provisória**, alternativas, custos de referência e riscos.

## Regras para evitar alucinação mecânica

- O exemplo ESP=8 do Amaterasu **não se torna atributo do Akira**.
- \`600 HP\` e \`731 EA\` são **valores atuais**, sem assumir máximos.
- \`35 EA\` original e \`25 EA\` sob Fornalha são confirmados para Fangs. Descontos adicionais não estão validados.
- Custo ORIGINAL não equivale a custo final. A UI indica quando um valor precisa de confirmação.
- Ações planejadas não modificam a ficha. Só mudanças explícitas e edições são persistidas.
- Personagens aliados ou inimigos não herdam as técnicas de Akira.
- O mestre é a autoridade final para regras ambíguas e decisões narrativas.

## Separação de responsabilidades

\`store.py\`: persistência; \`catalog.py\`: conhecimento; \`combat_interpreter.py\`: intenção; \`action_validator.py\`: legalidade; \`combo_forge.py\`: busca; \`tactical_decision.py\`: classificação; \`tactical_response.py\`: exposição das justificativas.

## Evolução prevista

- Separar ficha-base e snapshot de batalha.
- Registrar ações como eventos de domínio, com gasto/cooldown e confirmação individual.
- Calcular probabilidades com modificadores conhecidos (nunca presumidos).
- Tornar explícita a distância narrativa e a condição de corpo a corpo.
- Melhorar o parser para tratar negação e correções sem confundir planos com fatos.
- Antes da Vercel: autenticação, PostgreSQL persistente, controle de acesso e CORS configurável.

## Ambiente de implantação

**Agora:** navegador SvelteKit local + API FastAPI local + SQLite local.

**Depois:** frontend pode seguir para Vercel; API e dados necessitam solução persistente externa ou backend redesenhado. Hospedagem pública não é uma capacidade já implementada.

CI: o frontend deve incluir o marcador `%sveltekit.head%` no template e manter as fichas inacessíveis a visitantes sem autenticação no futuro deploy.

Validação posterior: confirmar também o rastreamento de usos de Reforço e Output, a seleção de variantes e a checagem dos limites de 30 utilizações.
