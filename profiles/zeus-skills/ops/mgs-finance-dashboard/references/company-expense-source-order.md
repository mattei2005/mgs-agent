# Company expenses: source order and original-currency basis

Authority: Rodolfo1547239702464045076, confirmed1547240897752604704; thread1545426987756298340. Canonical decision/evidence: `/root/mgs-agent/docs/finance-company-expenses-order.md`.

## Active rule; supersedes alphabetical company sorting
- UI correction Rodolfo1547250519414935592: remove the caption “Valor ajustado na dash” from expense rows. Rodolfo1553040522287784077 subsequently also removed `Despesa extra` from listing rows. Both are display-only: preserve amounts, currencies, audit/history, order, SB labels and calculated-payroll explanations.
- In the Dash, August2026–December2027 company expenses follow the exact Sheet/print order. Preserve existing IDs and current display names, including SB LeadsOn Hub, SB Tech Bot and SB Wire Fee. Do not rename them back to JBF. Personnel and closed January–July views retain their previous order.
- August keeps the original amounts/currencies of its own tab; September its own tab. October2026–December2027 copy September's **origin amount + currency**, never converted USD/BRL or the September FX. Each period retains its own rates and conversion logic.
- Do not copy payment/review state or dates. Do not modify personnel inputs, revenue, media, network/site/account bindings or source Sheets.

## Supersessão pontual de despesas — setembro2026

Rodolfo1553021450158342275: desde agosto2026, arquivar `company|109` (Topveiw AI dif de cobranca), `company|131` (wordfence premium plugin) e `company|141` (SB LeadsOn Hub); `company|143` (SB Wire Fee) passa a40 CAD. Rodolfo1553029057153728553: arquivar `company|119` (Adspower membro extra) desde setembro2026; não reescrever agosto. Todas17competências existentes até dezembro2027 foram conferidas. Preserve `SB Wire Fee usd:` e qualquer outra despesa nativa criada pelo usuário. Fonte: `docs/finance-company-expenses-order.md`; prova: `reports/finance-wavesbee-expenses-1553019425706217652.md`. Isto supersede somente os valores/status anteriores desses IDs/períodos; não reexecutar o seed antigo para restaurá-los.

## Cobranças por data — Rodolfo1553040522287784077

Desde setembro2026, Despesas Gerais usam componentes `charges[{id,date,amount}]`, moeda única e soma decimal exata no servidor; a lista conserva uma linha por despesa. Agosto mantém valor único. Data da cobrança pertence à competência e é independente de `checked_on`; não inventar data para legado. Novas linhas exigem data válida; componentes legados sem data só preservam o valor existente. Arquivar/restaurar e conferir preservam componentes. Guardar a definição completa no cenário; impedir alteração escalar incoerente de despesa que já tem componentes. Nunca transportar datas de cobrança/conferência para outro mês.

Desde agosto2026, arquivar Wire fee FB `company|128`, uptimerobot `company|130`, pagcorp `company|132`, sendgrid `company|134` e ubbersuggest seo `company|125`. Rodolfo1553050044813283478: Ferramenta ver artigos `company|122` desde setembro, preservando agosto. Verificados17meses até dezembro2027. Onboarding futuro deve preservar essas vigências, não restaurar seed antigo. Prova: `reports/finance-expense-charges-1553040522287784077.md`.

Remover a legenda `Despesa extra` da listagem conforme confirmação1553040522287784077; isso supersede sua preservação visual anterior, sem retirar a distinção interna de origem.

Em modal móvel com linhas repetíveis, limitar a altura do formulário e rolar somente `#editorBody`, mantendo cabeçalho/rodapé fora da rolagem; validar que Salvar/Cancelar permaneçam inteiros. Testar em browser real criar duas cobranças, reabrir, editar, remover, total único, data independente, legado sem data e rejeição de datas inválidas/fora do mês. A API pública do workspace não inclui `summary`: verificar erros pelo resultado persistido ou endpoint apropriado, nunca assumir shape de cálculo interno.


Em testes de restore, o peer PostgreSQL `mgsfinance` é limitado à base produtiva. Executar bases isoladas como `mgs_pg`, com cópia privada do código legível por esse usuário; não alterar pg_hba/permissões/credenciais para contornar uma recusa. Ao alterar despesas, preservar cotas e critérios de rateio, não exigir igualdade dos valores rateados: o montante deve recalcular. Em escrita interrompida, ler primeiro targets e audits por autoridade/período e retomar somente os meses faltantes; recibo local ausente não prova ausência de commit.

## Créditos e estornos — Rodolfo1553049180434604103

Modele crédito empresarial com `direction=credit`; débito usa `direction=debit`. Permita crédito somente em `category=company` e preserve o tipo em edição, conferência, componentes e audit. Exiba sinal positivo e saldo líquido; nunca transforme o sinal com `abs` sem transportar a direção. Para um item existente, atualize o mesmo ID em vez de criar linha duplicada.

Valide separadamente (1) valor bruto do crédito e (2) efeito líquido do indicador do sócio. Despesas Gerais alimentam remunerações automáticas; logo metade do crédito bruto pode diferir da variação final após regras dependentes. Em agosto2026, `company|122` é crédito BRL2522, `Crédito/estorno SPYFLIX — 26 lançamentos indevidos`, no lugar de -BRL97; a troca elevou Despesas Gerais em BRL2619, remuneração dependente em BRL74,20 e o indicador de metade em BRL1272,40. Setembro em diante continua arquivado. Fonte canônica e prova: `docs/finance-company-expenses-order.md` e `reports/finance-spyflix-credit-1553049180434604103.md`.

## Review-only saving performance — Rodolfo1552090743085076510

The company-expense editor must not rerun the financial graph merely to change review status/date when the existing original amount/currency and financial definition are proven unchanged. The conservative eligibility and tests live in `current-security-performance-and-dr.md`. Preserve SB Tech Bot629.28CAD, audit/revision and exact calculation; an actual amount/currency/definition change still recalculates. Do not extend this fast path to payroll or inherit a raw-input freeze by inference. Verified report: `reports/finance-expense-save-1552090743085076510.md`.

## Reusable execution and validation
1. Read Sheets only through canonical SA helper. Resolve gids/names live. For expense inputs prefer narrowly scoped M100:P143 plus R106 and R141:R143; do not print or export unrelated notes/columns, which may contain operational access data. Compare `userEnteredValue`, not formatted/effective calculated money. Snapshot privately.
2. Classify origin by formula chain: manual O→USD; O=SUM(P/F1) with manual P→BRL; R/G1→UNITS; R/H1→CAD. Preserve blank versus entered zero. R106 quantity=0 with P106 derived was preserved as existing zero; nonzero or unknown chains require explicit modeling, never silently choose the calculated result as origin.
3. August SMS Funnel uses USD4099.78. Rodolfo1551644766125428847 superseded the prior F17 dual-display preservation **only for August2026**, requesting alignment with the dashboard: principal P121 now `=O121*$F$1`, preserving O121=-4099.78 and the dashboard's USD basis. Prior manual BRL20000 is retained in backup/evidence, not an active equivalent value. Currencies/rates remain monthly; live BRL totals can differ briefly with independent quote refreshes. September SMS origin remains BRL30000 and every other month is unchanged.
4. Match stable company IDs and labels; the validated catalog is44 IDs company|100 through company|143. No duplicate/new rows for existing expenses. Unknown/ambiguous IDs or formulas fail closed.
5. Dual-host code/database backup with hashes; restore exactly to an isolated database. Test all target months, idempotency, facts/input preservation and alternative FX before canary. Preserve source/default display aliases.
6. Apply in bounded per-month transactions with revision locks and audit. Recompute from original inputs, preserving every monthly override and non-company addition. Read exact targets back. Do not restore a full production database over concurrent work as rollback; use revision-bounded recovery from backup.
7. Verify both Summary and Despesas Gerais order, 44 rows/no duplicates, original currency/value, and each conversion. Exercise actual HTTPS login on desktop/mobile, all17months, static app hash and zero JS/overflow errors. Credentials only via stdin from1Password; log out and read back401.

## Verified release2026-09-09
- Evidence root: `apps/finance-system/private/company-expenses-1547240897752604704/`.
-17months ×44rows=748 origin/ID checks;34desktop/mobile month views. August0financial edits;16later months42existing rows filled each, including explicit zeros. All88protected invariant checks passed; FX/monthly overrides/history/ledger/users and source daily facts preserved.
- Isolated alternative FX test USD/BRL6 and USD/CAD1.5 passed without origin edits; live verification returned0pending changes.
- Code: `company-expense-basis-cli.mjs`, deployment `deploy/company-expense-basis-release.py`, frontend `public/app.js`; tests `tests/expense-sort.test.mjs`, `tests/company-expense-public.mjs`, `tests/test_expense_origin.py`.
- The deployment runner is an authority-bounded one-shot for this request, not a cron and not permission to replay new financial overwrites. Live script uses revision locks; scripts/artifacts remain for evidence/rollback. No gateway/service restart.

## SB Tech Bot CAD supersession — Rodolfo1547697182948458611
- `company|142`, displayed as SB Tech Bot, keeps original amount629.28 and uses CAD from July2026 onward. This supersedes only its former UNITS/month-divisor origin; every other company expense keeps the source-order rule above. Future period onboarding must preserve this CAD basis unless Rodolfo changes it explicitly.
- July2026 is closed history, so never overwrite the immutable `finance_history` row or apply August rules. Create auditable successor documents, preserve the six prior active versions, recalculate the exact dependent graph and move only the July pointers atomically. The validated correction changed4,086 cells across principal+five manager documents and updated JulyF132/internal July→August carry. Source Sheets remained untouched.
- August–October2026 were already CAD. November2026–December2027 required14 writes; all17 registered active workspaces now read amount629.28/CAD. Preserve IDs, labels, statuses, checked dates, rates, inputs and non-target additions.
- Use one transaction with row/revision locks, per-period audit, exact readback and an idempotent second pass. Backup PostgreSQL on both hosts and restore to an isolated database before production. Evidence/report: `apps/finance-system/private/sb-tech-cad-1547697182948458611/` and `reports/finance-sb-tech-cad-1547697182948458611.md`.
- Validate audit completion by this operation's actor/authority and action names, not by the total global audit-row increase: login/activity events may be written concurrently. If a mutating wrapper exits nonzero after commit, read the target and audit first; never replay the financial batch blindly.