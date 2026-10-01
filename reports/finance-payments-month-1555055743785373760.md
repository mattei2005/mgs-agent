# Pagamentos — filtro mensal para todos os beneficiários

Autoridade: Rodolfo `1555055743785373760`, após diagnóstico `1555054071151329292`, thread `1545426987756298340`.
Release: `payments-month-1555055743785373760`.
Estado: **publicado e validado em produção**.

**Complemento posterior — Rodolfo1555083506529468438:** esta aceitação ocorreu antes da virada para outubro. O filtro foi preservado, mas a virada ativou um erro preexistente no parsing de Decimal `0E-30`; a UI mantinha setembro visível quando a consulta falhava. Ambos foram corrigidos e validados em `reports/finance-payments-rollover-1555083506529468438.md`, com simulação explícita de viradas, recuperação de erro e proteção contra respostas atrasadas. Este complemento delimita a cobertura da validação anterior, sem apagar sua evidência.

## Causa e abrangência confirmadas

A API consulta o ledger cumulativo até a competência para calcular corretamente o saldo anterior. A tabela de `public/operations.js` excluía apenas itens anulados, sem restringir `entry.period` à referência selecionada. Esse renderer é compartilhado por todos os beneficiários/perfis, não exclusivo de Geizian.

Leitura direta somente leitura do PostgreSQL e da função produtiva `ledger` encontrou 13 IDs de beneficiário em cada um dos 17 meses nativos (agosto2026–dezembro2027). O ensaio do código anterior reproduziu linhas indevidas em meses posteriores para 11 IDs: Geizian, Joe, Nicolas, Isliago, Kelly gestor, Ícaro (rótulo legado George), Samuel, Ially, Jislaine, Raquel e Kelly criativos. Gustavo e Rafael não tinham lançamentos ativos; por isso não mostravam visualmente o problema, embora usassem a mesma lógica. Nenhum cadastro ou rótulo foi alterado.

## Contrato aprovado e implementado

- A lista mostra somente itens ativos cuja **Referência** é o mês selecionado.
- Referência não é data de pagamento: um item de agosto registrado em setembro permanece em agosto.
- Mês sem itens próprios mostra `Nenhum lançamento neste mês.`.
- O texto informa que itens anteriores continuam no saldo anterior e não se repetem na lista.
- API cumulativa, saldos, regras financeiras, edit/delete, permissões e dados persistidos permanecem iguais.
- Janeiro–julho usa o renderer histórico próprio, que já recebe um documento da competência; esse código e seus valores foram preservados.

## Validação executada

- Teste RED anterior à alteração reproduziu a ausência do filtro; teste GREEN cobre todos os perfis, identidades genéricas de beneficiário, referência versus data, itens anulados, mês vazio, cartões preservados e ausência de ações para gestor.
- Gates completos: **223 Node +179 Python =402 testes aprovados**, sem skips.
- Dependências produtivas: npm audit reportou zero vulnerabilidades.
- Baseline de navegador isolado com respostas reais capturadas:442 combinações (13beneficiários ×17meses ×2larguras), com defeito reproduzido nos11IDs com movimentos.
- Stage do código candidato:1054 verificações desktop/mobile em owner, partner e cinco perfis manager; zero erro JS/POST financeiro. Dados financeiros são capturas reais de leitura produtiva; identidades/sessão do stage são simulação isolada da apresentação, não novos logins produtivos.
- Navegador público com login owner real: **442 verificações**, cobrindo13IDs,17meses e1440/390px. Troca pelo seletor mensal e pelo seletor de beneficiário, referências, linhas, mensagens vazias, botões, cartões versus resposta API e overflow passaram. Nenhum POST financeiro.
- Cenários (revisão/result/overrides/additions) **e ledger completo** idênticos imediatamente antes/depois do cutover sob admissão exclusiva.
- Hash local/remoto de `public/operations.js`: `92e625a1add9cd03c375e198e8b3b794e6f6cad73a5a44cd8fb9c54c63de51b7`.
- Hash do teste persistente `tests/finance-ops.test.mjs`: `364a9f5ef09c65338f7a73d0e430ef3a18886ef4ef1d66cd1f283647f613c8f1`.
- PostgreSQL, serviço financeiro e socket ativos; `/api/health` autenticado confirmou produção. Sessão isolada de validação encerrada por logout.

## Recuperação e limites

A preparação inicial apontou ausência de uma fixture imutável `simple-review-1551798771661275147/backup.json` na fonte candidata anterior. O arquivo real existente foi recuperado de evidência protegida, sem inventar dados nem enfraquecer testes; os gates integrais passaram depois. Nenhuma falha produtiva no cutover/readback.

Publicação feita pelo controlador canônico com backup, journal, locks, fence e readback. Somente o serviço financeiro foi recarregado; nenhum gateway, cron, credencial, pagamento, banco ou histórico foi modificado por este ajuste. O teste protege esta classe de filtro mensal; não é garantia universal contra regressões futuras.

## Evidência e continuidade

- Evidência privada: `apps/finance-system/private/payments-month-1555055743785373760/` (`snapshot.json`, `browser-baseline.json`, `browser-stage.json`, `browser-production.json`, `candidate/private/gates`, `manifest.json`, `published.json`, fingerprints).
- Backups/journal: `apps/finance-system/private/releases/payments-month-1555055743785373760/`; preservados, sem exclusão.
- Contrato reutilizável: skill canônica `mgs-finance-dashboard`, `references/payments-approvals-nicolas-pilot.md`, seção Filtro mensal do extrato.
- Checkpoint: `ZEUS-FINANCE-PAYMENTS-MONTH-1555055743785373760`.
- Esta decisão supersede somente a apresentação cumulativa antiga da lista, sem superseder o cálculo de carry ou a regra de competência do lançamento.
