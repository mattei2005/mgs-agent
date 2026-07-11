# BR/CAR — creditoparaveiculo.com

## Context

First MGS WordPress quiz lead funnel migrated from Lovable/Supabase into a first-party WordPress plugin.

- Country: BR
- Vertical: CAR / crédito veicular
- Site: `creditoparaveiculo.com`
- Plugin: `mgs-quiz-carro`
- Purpose: capture financing leads, route to SMS Funnel by gestor, then redirect to REC page preserving UTMs.

## Runtime e modelos visuais

`creditoparaveiculo.com` usa o plugin de quiz `mgs-quiz-carro`; não há plugin de chat nesse site. Quando Rodolfo disser “chat” informalmente sobre essas URLs, confirmar o produto real no runtime e tratar o pedido como quiz, sem envolver `mgs-chat-funnels`.

Versão validada em produção em 2026-07-10: `mgs-quiz-carro` v1.6.2.

Relatório de custo SMS v1.6.2:

- A página `MGS Quiz > Relatório` calcula o custo estimado a partir de todas as linhas absorvidas pelo relatório/banco, respeitando os filtros ativos; não consulta nem reconcilia com o dashboard do SMS Funnel.
- O custo é `8 centavos × total de registros filtrados`, com cálculo em centavos inteiros e exibição BRL fixa (`R$ 1.234,56`), independentemente do locale do WordPress.
- O dashboard mostra cards de custo unitário e custo estimado total, além de uma tabela por quiz com nome, slug, registros absorvidos, custo unitário e custo estimado.
- Status SMS, validade do telefone, duplicidade ou visibilidade no fornecedor não excluem linhas do cálculo. A métrica representa o que foi absorvido no relatório WordPress.

Hardening operacional v1.6.1:

- A atualização central de SMS deve rodar somente com `wp_options` e `wp_mgs_quiz_config` em InnoDB, iniciar transação antes da leitura, carregar as quizzes com `SELECT ... FOR UPDATE`, verificar falhas de start/select/update/commit e invalidar o cache da option em rollback.
- Elementos inválidos dentro de `sms_funnel_urls` devem abortar com rollback, nunca causar propagação parcial ou TypeError.
- URLs centrais são válidas apenas com HTTPS, host `v2.smsfunnel.com.br` e path `/integrations/lists/<id>/add-lead`; option inválida cai nos defaults canônicos e POST inválido é bloqueado sem alterar option/configs.
- O escopo atual é deliberadamente G001–G006. Antes de introduzir código legado/customizado, migrar explicitamente e ampliar a fonte central; não permitir fallback manual silencioso no editor.

Correções operacionais v1.6.0:

- `Nome/label` e `URL add-lead` no editor da quiz são somente leitura. O operador escolhe apenas o gestor no seletor; o backend resolve os dados server-side para evitar erro humano ou adulteração de POST.
- O menu MGS Quiz possui submenu `SMS`, página central para gerenciar os presets G001–G006. A fonte central é a option `mgs_quiz_sms_presets`, com os valores canônicos do plugin apenas como fallback inicial.
- Salvar a página SMS exige label não vazio e URL HTTPS para todos os gestores. A alteração deve ser propagada para todas as linhas `sms_funnel_urls` das quizzes com o mesmo `gestor_code`, mantendo o runtime REST em paridade com a fonte central.
- O editor da quiz não oferece modo manual e exige uma seleção válida de gestor antes de salvar.

Correção operacional v1.5.3:

- Quando a quiz usa seletor único de gestor/SMS, não exibir controles redundantes de multi-lista (`Usar este`, `+ Adicionar gestor` ou `Remover`). Manter apenas o seletor canônico e, abaixo, os campos preenchidos para conferência/edição manual; o índice default pode ser enviado como hidden `0`.

Correções operacionais v1.5.2:

- O admin oferece um seletor `Gestor / lista SMS Funnel` com os presets canônicos G001–G006. Ao escolher um gestor, a UI preenche automaticamente código, nome/label e URL add-lead.
- No salvamento, o código selecionado é resolvido server-side contra os presets canônicos; não confiar apenas nos campos preenchidos por JavaScript. A configuração persistida deve conter exatamente uma linha ativa e default para a quiz.
- Configs antigas com várias linhas são normalizadas visualmente para a linha marcada como default; ao salvar pelo seletor, são persistidas como escolha única.

Correções operacionais v1.5.1:

- A listagem de quizzes deve exibir a linha SMS marcada como `default=1`; nunca assumir que `sms_funnel_urls[0]` é a selecionada. Se não houver `default` legado, usar a primeira linha ativa, em paridade com o fallback do backend.
- A duplicação deve copiar a configuração, gerar novo `id`, nome e slug, limpar os links SMS para escolha explícita e redirecionar para `admin.php?page=mgs-quiz-new&id=<novo-id>&duplicated=1` somente após confirmar que `$wpdb->insert()` teve sucesso.
- A tabela `wp_mgs_quiz_config` não possui coluna `created_at`. Incluir `created_at` no insert de duplicação faz o insert falhar e abre uma tela de quiz vazia apontando para um ID inexistente. Nunca inserir colunas sem validar o schema real; em falha, registrar `$wpdb->last_error` no log e retornar erro na listagem.
- As rotas públicas são rewrites virtuais do WordPress; não existem pastas físicas por quiz. Alterar a slug muda a chave no banco. A versão 1.5.1 não mantém histórico nem cria redirect automático da slug antiga; sem config correspondente, a URL antiga cai no comportamento normal do WordPress/site.

Modelos disponíveis no campo admin `Modelo visual`:

- `layout_template` vazio — Quiz padrão, pergunta primeiro e formulário depois.
- `fmybc_sms` — landing FMYBC/SMS com dados primeiro, checklist e badges.
- `quiz_maker_sb` — Quiz Maker SB, réplica first-party do layout de duas etapas da Smart Bidding: pergunta com opções verdes, depois nome/telefone, mantendo backend, SMS Funnel e redirect da MGS.

## Public Quiz Routes

Rotas confirmadas no banco em 2026-07-10:

- G001 — `/quiz-car-parcelas-g001/`
- G002/default — `/quiz-car-parcelas/`
- G003 — `/quiz-car-parcelas-g003/`
- G004 — `/quiz-car-parcelas-g004/`
- G005 — `/quiz-car-parcelas-g005/`
- G006 — `/quiz-car-parcelas-g006/`
- QM001 — `/quiz-car-parcelas-g002-qm001/` (`layout_template=quiz_maker_sb`) — renomeada por Rodolfo a partir da G007 criada por Zeus; mantém dados internos da G002/default.
- QM002 — `/quiz-car-parcelas-g002-qm002/` (`layout_template=quiz_maker_sb`) — duplicada por Rodolfo a partir da QM001; validada com lead `ok:G002`.
- Modelo FMYBC/SMS — `/quiz-car-002-g002/` (`layout_template=fmybc_sms`).

A slug temporária `/quiz-car-parcelas-g007/` não é mais uma quiz ativa após a renomeação para QM001. G002 is the default route without suffix. New campaign variants use the naming defined by Rodolfo.

## SMS Funnel Routing

Each gestor has its own SMS Funnel add-lead URL. Keep fallback blank when all gestor URLs are configured.

Do not expose full credentials/tokens in chat. SMS Funnel list URLs are operational integration URLs; display only when necessary and avoid dumping them unnecessarily.

Routing is validated by stored WP lead status:

- `ok:G001`
- `ok:G002`
- `ok:G003`
- `ok:G004`
- `ok:G005`
- `ok:G006`

For normal production quiz configs, the operator chooses **one SMS Funnel link per quiz** in the admin UI. That selected link is the destination for every lead from that quiz, regardless of UTMs/campaign/adgroup or whether the visitor returns later with a clean URL. Do not make UTM-based routing the normal behavior when a quiz-level SMS link is selected.

The SMS response body should include `success:true` and the expected `list_id` for the selected link.

## Redirect

Canonical final redirect:

`https://creditoparaveiculo.com/rec-br-financiamento-de-carro-sem-entrada/`

All incoming params must be preserved automatically: `utm_*`, `fbclid`, `gclid`, etc.

Redirect split UI should be business-facing:

- `+ Adicionar URL`
- URL field
- weight field
- remove action
- default 100 for single URL

## Admin UX Decisions

- Normal operator path for new variant: Duplicate → name → slug → choose one SMS Funnel link for the quiz (`Usar este`).
- The quiz-level selected SMS link wins for all submissions; do not expose normal operators to multi-condition routing by UTM.
- CSV import is technical/migration-only and should stay hidden behind advanced/details UI.
- Reports should show 5 days/leads by default, with per-page selectors.
- Tables should avoid narrow wrapping for gestor, SMS, phone.
- After saving an edit, redirect back to the same edit screen (`admin.php?page=mgs-quiz-new&id=<id>&saved=1`), not to the quiz list, so the operator keeps context.

## SMS Cost Reporting

Decision confirmed by Rodolfo for this site/report:

- Canonical unit cost: **R$ 0,08 per row counted by the WordPress quiz-leads report**.
- The source of truth is exclusively the rows in `{$wpdb->prefix}mgs_quiz_leads` satisfying the same `report_where()` filters used by `admin.php?page=mgs-quiz-report`.
- Count the entire filtered result set, not only the current paginated table page. Group by `quiz_slug` and show quiz, counted WP rows, unit cost, and estimated cost.
- Formula: `filtered_report_row_count × 8 centavos`; perform arithmetic in integer centavos and convert only for presentation.
- Do **not** filter by `sms_funnel_status`, phone uniqueness, phone validity, duplication, or downstream dashboard visibility. Rows with `ok:*`, `fail:*`, `error`, `historical_import`, `skipped`/NULL, duplicate phones, or semantically invalid phones are counted when they belong to the filtered WP result.
- Do not query or reconcile against the SMS Funnel dashboard for this metric. Label it **Custo estimado de SMS — base WP** (or equivalent), because WordPress does not observe the vendor's actual outbound-message event.
- Reuse `report_where()` and its parameter list for both consolidated cost and per-quiz aggregation, keeping `slug`, date range, gestor, parcela, and search filters identical to the existing report. The current `Gestor` filter is specifically `UPPER(utm_medium)`, not `sms_funnel_status`; do not silently reinterpret it in the cost query.
- The CSV exporter currently has a narrower filter contract than the report (`slug/from/to` only); do not use CSV equality as validation when `gestor`, `parcela`, or `q` is active unless export filtering is updated too.
- Validate with one read-only SQL snapshot that the filtered total equals the sum of grouped quiz rows and that `total_rows × 8` equals the sum of grouped centavos.
- If the business later changes from “one charged SMS per WP report row” to actual outbound-message billing or multiple sends per lead, treat that as a different metric requiring a vendor event/webhook or imported send-count report.

## Smart Bidding SMS Revenue Backfill

Production state validated on 2026-07-10: `mgs-quiz-carro` v1.7.0, schema version `1.3.0`, with `wp_mgs_quiz_sms_revenue` populated for closed dates from 2026-05-22 through 2026-07-09.

Keep Smart Bidding revenue distinct from estimated SMS cost and lead rows:

- Source contract and API/date pitfalls live in `smartbidding-dashboard-map/references/sms-report-api-contract-and-backfill.md`.
- When **Discount revenue share** is enabled in Smart Bidding, the primary BRL value displayed in the `REVENUE` column is `NET_REVENUE`; WordPress must sum `net_revenue_cents`. Gross `REVENUE` remains stored for audit.
- Revenue is domain/date-level. It respects the report's date range, but it must not pretend to respect quiz, gestor, parcela, or lead-search filters without trustworthy attribution.
- Include every campaign for `digital-trust_creditoparaveiculo`; filtering only G001–G006 loses historical generic campaigns.
- The deployed table uses unique `(revenue_date, publisher, utm_campaign)` aggregates with BRL currency, gross/net cents, source-row count/hash, and sync timestamp.
- Upsert replaces each deterministic aggregate; never increment. Deduplicate API rows by signed-looking source PK before grouping, especially across UTC−3 chunk boundaries.
- Reconcile aggregate count, source-row count, date count/min/max, gross/net cent sums, uniqueness, and source hashes. Treat the current day as provisional and do not delete omitted days after a partial fetch.

### Schema lifecycle guard

A report query referencing a new table is not sufficient implementation. Before deployment:

1. Ensure the activator/upgrader creates the revenue table with `dbDelta()` or equivalent.
2. Bump the plugin DB schema version and add an upgrade path for active installations; activation hooks do not run merely because files are replaced.
3. Validate the live table and indexes before rendering the report or importing revenue.
4. Smoke-test no-data, populated history, an exact single-day filter, and idempotent re-import.

For v1.7.0, the active-install upgrade hook created schema `1.3.0`; the closed-day backfill reconciled 61 source rows across 49 dates, gross `R$ 13.923,73`, net `R$ 12.531,37`. No daily cron was created in this phase.

### Read-only source/provenance check before proposing a patch

- Confirm the active plugin version and live plugin directory via WP-CLI.
- Compare SHA-256 of the live files with the candidate baseline package; do not assume an ephemeral `/tmp` worktree is canonical, especially when it is not a Git repository.
- Inspect the live table prefix/schema/status distribution without selecting PII or response bodies.
- Distinguish three states explicitly: production runtime, immutable baseline package, and un-deployed working candidate.
- A report-only change needs no schema/DB-version bump. Stage and lint the whole plugin, back up the live plugin directory, replace the admin implementation first and the version/bootstrap file last, then validate filtered totals and the authenticated report. Never deploy during a read-only audit request.

## Known Interpretation

If WordPress records `ok:G00X` and SMS Funnel returns `success:true` with the correct `list_id`, but SMS Funnel dashboard still shows zero, treat it as likely SMS Funnel dashboard delay/cache/indexing/filter/deduplication unless contrary evidence appears.
