# REPORT-INFRA — validação de formato Discord para scripts de relatório

Quando um agente reportar alteração em scripts que postam relatórios no Discord (`*-discord-post-*`, crons HOA/intraday, wrappers de logs), validar semanticamente a legibilidade no Discord — não só `py_compile` e hash.

## Caso validado

Ares ajustou relatórios HOA no `logs-aquisicao` para:
- listar todas as campanhas da página em foco, incluindo ativas, pausadas e histórico visível;
- ordenar por numeração da campanha (`001`, `002`, `003`...) e manter `ACTIVE` antes de `HIST` quando houver duplicidade;
- usar cabeçalho humano com horário no fuso da conta (`HOA — relatório das HH:MM (Europe/Madrid)`);
- evitar labels técnicos como `[parte 1/4]`, preferindo `Parte 1 de 4`;
- impedir que o chunker corte uma mensagem no meio de bloco fenced ```text, porque isso quebra tabela no Discord.

## Validação mínima para Zeus ao processar o REPORT-INFRA

1. Rodar sintaxe/hash:
   - `python3 -m py_compile <scripts>`
   - `sha256sum <scripts/skill>` e comparar com o report.
2. Gerar preview real/sanitizado do relatório quando o script tiver dry-run/always-output:
   - Ex.: `python3 scripts/ares-meta-hoa-manager.py --always-output > /tmp/preview.out`
3. Se houver poster/chunker Discord, passar o preview pelo poster em dry-run:
   - Ex.: `python3 scripts/ares-discord-post-with-thread.py --thread-id <thread> --dry-run < /tmp/preview.out`
4. Validar invariantes de Discord:
   - `all_under_2000=true` / `max_chunk_len < 2000`.
   - `balanced_code_fences=true` (`preview.count("```") % 2 == 0`).
   - Se o poster separa chunks, confirmar que cada chunk mantém blocos fenced completos quando possível.
   - Labels naturais: evitar `[parte 1/4]`; preferir `Parte 1 de 4` ou texto humano equivalente.
5. Validar layout semântico pedido por Rodolfo:
   - cabeçalho humano no fuso correto da operação/conta;
   - colunas esperadas presentes;
   - colunas técnicas/removidas ausentes (`Página`, `Idade`, `Campaign ID`, `Meta ID`, etc. quando o pedido foi removê-las);
   - ordenação esperada (`001,001,002,002...` quando o report declarar ordenação por campanha);
   - `ACTIVE` antes de `HIST` em duplicidade histórica, se aplicável.
6. Sincronizar skill runtime→versioned quando o report inclui skill de outro profile:
   - rodar `sync-souls.sh` quando aplicável;
   - comparar SHA runtime e versionado;
   - commitar apenas `infra-inventory.json`, scripts/skills versionados relevantes e nenhum audit/state gerado pelo preview.

## Pitfall

Um `dry-run` com chunks abaixo de 2000 caracteres ainda pode estar visualmente quebrado se o chunker dividir no meio de um bloco ```text. A validação precisa checar fences balanceadas e, quando houver múltiplos blocos, que os chunks preservam blocos completos. Hash correto não prova legibilidade no Discord.
