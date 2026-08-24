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

Versão validada em produção em 2026-08-24: `mgs-quiz-carro` v1.7.8.

Inclusão de listas SMS v1.7.8:

- A página `MGS Quiz > SMS` mantém os presets existentes e oferece `+ Adicionar lista` para criar outro código no formato `G001`, nome/label e URL `add-lead` válida do SMS Funnel.
- A UI sugere automaticamente o próximo código disponível, mas o backend normaliza e valida o código, bloqueia duplicidade, host/path inválidos e omissão de listas existentes.
- Presets customizados persistidos em `mgs_quiz_sms_presets` passam a ser carregados, exibidos na página central e disponibilizados no seletor `Gestor / lista SMS Funnel` das quizzes.
- O salvamento central continua transacional e propaga label/URL somente às quizzes que já usam o código correspondente; adicionar um código novo sem quiz vinculada não altera configurações existentes.

Correção de timezone v1.7.7:

- O plugin mantém `created_at` em UTC e usa `America/Sao_Paulo` como timezone de negócio no relatório e no CSV.
- Datas selecionadas em São Paulo são convertidas para limites UTC semiabertos antes do SQL. Exemplo validado: `15/07/2026` → `2026-07-15 03:00:00` até, sem incluir, `2026-07-16 03:00:00`.
- Gráficos agrupam por data local de São Paulo; tabelas e CSV convertem os timestamps UTC para São Paulo na apresentação.
- Readback histórico validado: o período local de 15/07 contém 6.813 linhas; rotas públicas e REST permaneceram HTTP 200.

Correção do filtro de período v1.7.6:

- O botão `Aplicar` do seletor de período grava `from`/`to` e submete o formulário GET completo `mgsqReportFilters`, recarregando cards, custos, receita, ROI, gráficos e listas com todos os filtros atuais.
- O botão `Filtrar relatório` permanece visível e funcional como caminho alternativo explícito.
- Datas incompletas continuam bloqueadas no calendário; nenhum submit ocorre até início e fim estarem selecionados.

Correção responsiva FMYBC/SMS v1.7.5:

- O layout `fmybc_sms` usa `border-box` no contêiner e nos descendentes, largura total limitada ao viewport e `overflow-x: clip` apenas como proteção. A validação em viewports simulados de 390 px e 360 px deve exigir `documentElement.scrollWidth === documentElement.clientWidth` e zero elementos visíveis excedendo a largura.
- A imagem do carro usa `display:block`, `width:100%`, `max-width:320px`, `height:auto` e `object-fit:contain`.
- A quiz `/quiz-car-001-cl001/` usa o asset first-party transparente `public/images/polo-transparent.webp`, em vez do JPEG externo com fundo branco. Validar HTTP 200, `image/webp`, hash do asset, canal alpha real e readback exato de `car_image_url`.

Relatório de custo SMS v1.6.2:

- A página `MGS Quiz > Relatório` calcula o custo estimado a partir de todas as linhas absorvidas pelo relatório/banco, respeitando os filtros ativos; não consulta nem reconcilia com o dashboard do SMS Funnel.
- O custo é `8 centavos × total de registros filtrados`, com cálculo em centavos inteiros e exibição BRL fixa (`R$ 1.234,56`), independentemente do locale do WordPress.
- O dashboard mostra cards de custo unitário e custo estimado total, além de uma tabela por quiz com nome, slug, registros absorvidos, custo unitário e custo estimado.
- Status SMS, validade do telefone, duplicidade ou visibilidade no fornecedor não excluem linhas do cálculo. A métrica representa o que foi absorvido no relatório WordPress.

Hardening operacional v1.6.1:

- A atualização central de SMS deve rodar somente com `wp_options` e `wp_mgs_quiz_config` em InnoDB, iniciar transação antes da leitura, carregar as quizzes com `SELECT ... FOR UPDATE`, verificar falhas de start/select/update/commit e invalidar o cache da option em rollback.
- Elementos inválidos dentro de `sms_funnel_urls` devem abortar com rollback, nunca causar propagação parcial ou TypeError.
- URLs centrais são válidas apenas com HTTPS, host `v2.smsfunnel.com.br` e path `/integrations/lists/<id>/add-lead`; option inválida cai nos defaults canônicos e POST inválido é bloqueado sem alterar option/configs.
- O escopo inicial G001–G006 permanece como fallback canônico, mas a fonte central aceita novos códigos no formato `G` + pelo menos três dígitos. Nunca introduzir fallback manual silencioso no editor; toda lista customizada deve ser criada na página SMS, persistida na option central e selecionada explicitamente na quiz.

Correções operacionais v1.6.0:

- `Nome/label` e `URL add-lead` no editor da quiz são somente leitura. O operador escolhe apenas o gestor no seletor; o backend resolve os dados server-side para evitar erro humano ou adulteração de POST.
- O menu MGS Quiz possui submenu `SMS`, página central para gerenciar os presets iniciais G001–G006 e adicionar listas posteriores. A fonte central é a option `mgs_quiz_sms_presets`, com os valores canônicos do plugin como fallback inicial.
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
- When the operator opens `admin.php?page=mgs-quiz-report` without explicit `from`/`to` query parameters, default both **Data inicial** and **Data final** to the previous calendar day in the WordPress site timezone. Explicitly submitted dates must remain unchanged.
- The report date UI uses one business-facing `Período` control: two months side by side on desktop, one month on mobile, manual start/end selection, month navigation, Cancelar/Aplicar, and shortcuts for Hoje, Ontem, Últimos 7 dias, Últimos 30 dias, Este mês, Mês anterior, and Personalizado. It continues submitting the canonical `from`/`to` GET fields. Do not add the reference UI's `Compare to` section or 730-day-limit notice. Bind click handlers directly to generated day buttons and directly to preset/navigation controls; do not rely only on delegated bubbling from the popover, because WordPress admin/runtime handlers can prevent the click from reaching the container. Regression QA must click a start day, click an end day, verify both visual classes/summary, click Aplicar, and read back the hidden `from`/`to` values.
- For `wp eval-file` report smoke tests, do not pass `--skip-plugins`: that prevents `MGS_Quiz_Admin` from loading. Historical smoke SQL must use the exact same date/publisher/domain scope rendered by the report; querying the entire revenue table becomes stale as the daily sync adds newer dates.

### WordPress timezone vs lead-table timestamps

The site option `timezone_string=America/Sao_Paulo` controls WordPress application clocks such as `wp_timezone()`, `current_time()`, default report dates, and the General Settings display. It does not automatically change MySQL `CURRENT_TIMESTAMP`.

Historical pre-fix contract observed on `creditoparaveiculo.com` v1.7.6:

- MySQL session/global use `SYSTEM`, and the server system timezone is UTC; therefore `NOW()` equals `UTC_TIMESTAMP()`.
- `wp_mgs_quiz_leads.created_at` is declared `DEFAULT CURRENT_TIMESTAMP`.
- The REST insert omits `created_at`, so MySQL stores UTC.
- The old report chose the default date using `wp_timezone()` but compared raw local-looking strings such as `YYYY-MM-DD 00:00:00` directly against the UTC column, creating a three-hour boundary mismatch for São Paulo.

Current contract from v1.7.7:

- UTC storage is preserved; never rewrite historical timestamps or begin storing local values in the same column.
- The plugin business timezone is explicitly `America/Sao_Paulo` for date defaults, filtering, grouping, display, and CSV.
- Selected local days become UTC half-open ranges (`>= start`, `< next-day start`).
- Display/export converts UTC back to São Paulo.
- Validation must cover both midnight boundaries before using dashboard subtraction as an SMS reconciliation source.

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

Production state validated on 2026-07-12: `mgs-quiz-carro` v1.7.4, schema version `1.3.0`, with `wp_mgs_quiz_sms_revenue` populated for closed dates from 2026-05-22 onward by the daily sync.

Keep Smart Bidding revenue distinct from estimated SMS cost and lead rows:

- Source contract and API/date pitfalls live in `smartbidding-dashboard-map/references/sms-report-api-contract-and-backfill.md`.
- When **Discount revenue share** is enabled in Smart Bidding, the primary BRL value displayed in the `REVENUE` column is `NET_REVENUE`; WordPress must sum `net_revenue_cents`. Gross `REVENUE` remains stored for audit.
- Revenue is domain/date-level. It respects the report's date range, but it must not pretend to respect quiz, gestor, parcela, or lead-search filters without trustworthy attribution.
- ROI formula: `(receita líquida SB − custo estimado SMS) ÷ custo estimado SMS × 100`. Compute from integer centavos and format to two decimals. Show the estimated profit alongside it.
- ROI is comparable only when no quiz, gestor, parcela, or search filter is active, because revenue is domain/date-level while those filters narrow only the WordPress cost. With any such filter, display `Não comparável` instead of a misleading percentage. With no revenue or zero cost, display `Sem base`.
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

For v1.7.0, the active-install upgrade hook created schema `1.3.0`; the closed-day backfill reconciled 61 source rows across 49 dates, gross `R$ 13.923,73`, net `R$ 12.531,37`.

Daily sync deployed on 2026-07-11 after recovering Rodolfo's original instruction:

- root cron: `0 8 * * *` in VPS timezone `America/New_York`;
- wrapper: `/root/mgs-agent/scripts/sync-sb-sms-revenue-daily.sh`;
- collector/import coordinator: `/root/mgs-agent/scripts/sync-sb-sms-revenue-daily.py`;
- transactional importer: `/root/mgs-agent/scripts/import-sb-sms-revenue-day.php`;
- behavior: fetch yesterday in `America/Sao_Paulo`, require at least one correctly scoped row, deduplicate by source PK, aggregate by UTM campaign, upsert the exact closed date, and validate WordPress readback;
- credentials remain outside WordPress; the importer payload/runtime is staged under `/var/tmp/mgs-sb-sms-revenue` on RunCloud Inc02;
- failures alert `#alerts-infra` and mention Rodolfo; success remains log-only;
- log: `/root/mgs-agent/logs/sync-sb-sms-revenue-daily.log`.

The first corrective execution imported 2026-07-10 with 7 source rows / 7 campaign aggregates: gross `R$ 385,16`, net `R$ 346,64`; the WordPress report validated cost `R$ 175,92`, profit `R$ 170,72`, and ROI `97,04%`.

### Schema/backfill deployment recovery

For releases that combine a schema migration, data backfill, and report UI:

- Emit named checkpoints for `schema`, `table readback`, `import`, `report smoke`, and `public routes`; do not suppress the failing stage's diagnostic output.
- Make the backfill transactional and independently rerunnable. Validate it directly before retrying the full plugin swap.
- A plugin rollback does not necessarily roll back `dbDelta()`, the DB-version option, or a new table. After any failed rollout, inspect the live plugin version/hash, schema version, table existence, and row count before deciding the retry path.
- If schema creation succeeded but import did not, keep the empty additive table, run the idempotent importer with readback, then retry the UI deployment. Do not drop the table automatically.
- Re-run the same snapshot once to prove semantic idempotency, then smoke-test one exact historical date and a no-data date range.

### Read-only source/provenance check before proposing a patch

- Confirm the active plugin version and live plugin directory via WP-CLI.
- Compare SHA-256 of the live files with the candidate baseline package; do not assume an ephemeral `/tmp` worktree is canonical, especially when it is not a Git repository.
- Inspect the live table prefix/schema/status distribution without selecting PII or response bodies.
- Distinguish three states explicitly: production runtime, immutable baseline package, and un-deployed working candidate.
- A report-only change needs no schema/DB-version bump. Stage and lint the whole plugin, back up the live plugin directory, replace the admin implementation first and the version/bootstrap file last, then validate filtered totals and the authenticated report. Never deploy during a read-only audit request.

## Known Interpretation

If WordPress records `ok:G00X` and SMS Funnel returns `success:true` with the correct `list_id`, but SMS Funnel dashboard still shows zero, treat it as likely SMS Funnel dashboard delay/cache/indexing/filter/deduplication unless contrary evidence appears.
