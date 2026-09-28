# Payments monthly indicators, MGS alias and profit ranking

## Authority and scope

Rodolfo messages `1547706561210753114`, `1547706760251449445`, `1547707970731638945`, `1547708328073896066` and `1547711786688708759`, thread `1545426987756298340`.

This change is presentation/readback only:

- show the month's USD→BRL exchange rate and invalids in Payments for every selectable month;
- display internal `SEM_COMISSAO` as `MGS` (G002), never as a person or unknown manager;
- rank “Sites em destaque” by site net profit, not gross revenue;
- explain the July closed snapshot versus the later live Sheet without rewriting closed history.

It does not change any revenue, spend, invalid rate, exchange value, payment, ledger entry, site ownership, commission eligibility or closed-month snapshot.

## Current per-rate confirmation and propagation

Authority: Rodolfo1552079131628281897. Supersedes the always-Provisório workspace labels below; the exchange-only strip from `current-realized-cutoff-site-status-history-refresh.md` remains current.

- Read values from the selected scenario's calculated exchange fields and confirmation from that same scenario's `additions` rate records. `mode=fixed` AND `status=confirmed` renders Confirmado; absent metadata, automatic mode or provisional status renders Provisório. Never infer confirmation from month completion, a nonzero/fixed value, another exchange or another month.
- Render per-exchange labels. Mixed states must show the confirmed and provisional exchanges separately, with a partially-confirmed summary. Historical January–July remains Fechado; do not rewrite frozen history. Currency confirmation does not mean the entire financial month is approved or all invalid rates are settled.
- Keep invalids out of the Payments strip, but test that an actual invalid-rate change reaches daily facts, totals, manager views and the payable amount. Same-value confirmation must preserve the exact calculation; changed financial inputs still recalculate before success.
- Verify a real edit in isolated stage, then compare the complete recalculated payload consumed by Dashboard/Relatório Diário/Despesas Gerais/Funcionários, all five manager APIs and Payments. Preserve the other month byte-for-byte. Do not mutate a real settled rate solely to test propagation.
- Production acceptance reads every selectable month and compares each live Payment indicator value/status against Câmbio e inválidos, on desktop/mobile. Historical source uses `/api/history?period=YYYY-MM&book=principal`, not the live `/api/finance/ledger` endpoint. Materialize the real immutable July `finance_history` fixture when testing August carry. Enumerate public managers from `managerKeys`; Ícaro's public key is `icaro`, while `george` is only a calculation namespace.

Verified: 356 tests; stage real FX/invalid edits, mixed status, no-recalculation confirmation and month isolation; production24 API checks,48 Payment viewport checks and34 general/daily viewport checks; August's three exchanges Confirmado, USD/BRL5.08 preserved, no financial POSTs and unchanged scenario fingerprints. Evidence: `reports/finance-rate-propagation-1552079131628281897.md`.

## Historical Payments indicators baseline — superseded presentation

The original owner/general Payments rendered one compact `Câmbio e inválidos do mês` table:

- `USD → BRL`: six-decimal rate used by that month;
- `Inválidos do mês`: total deduction in USD and BRL plus the available network rates;
- historical months show `Fechado` and their capture date;
- August2026–December2027 workspaces show scenario values as `Provisório`.

Historical January–July values come exclusively from each frozen monthly payload through `HistoryDashboard.project()`. Current/future workspace indicators come from the selected scenario's exact `result.results` rate keys and `domain.cash.invalid`. Do not query Google Sheets at render time or recalculate a closed month.

Company-wide indicators remain hidden from manager logins: API returns `indicators:null`, and manager Payments renders no indicator table. Owner and authorized general views retain them.

On mobile the indicator table uses the existing horizontal scroller. Validate document width, that scroll width exceeds viewport and that the last cell becomes fully visible after horizontal scrolling; a static screenshot cutting the next column is not by itself a layout failure.

Historical BRL invalid total is the sum of the original per-site BRL values. It can differ by cents from multiplying the displayed rounded USD total by the displayed FX; preserve the original, do not force a synthetic conversion.

## MGS / G002 presentation

`SEM_COMISSAO` is the internal calculation key for MGS/G002 revenue that does not feed an employee commission. It is not missing attribution. Keep the internal key for calculations, but normalize display aliases:

- `SEM_COMISSAO`, `NÃO MAPEADO`, `Geizian`, `g002` → `MGS`;
- `george`→`Ícaro`; title-case `isliago`, `joe`, `kelly`, `nicolas`.

Deduplicate labels so imported native G002 facts do not show `MGS · SEM_COMISSAO`. Cephyric, Escalatepower and Mavroa remain site-status pending unless separately registered; this confirmation changes their displayed/financial manager identity to MGS only, not site status or expense allocation.

## Profit ranking

Current dashboard: calculate `net_profit = grouped fact profit + the sum of that site's segment expenses`, then sort descending and display `Maiores lucros líquidos no mês` / `Lucro líquido após despesas do site · USD`. This preserves imported native facts while including the monthly site-expense allocation exactly once. Do not rank on gross or on fact-level operating profit alone. Use nonnegative bar widths so a negative net profit never produces invalid CSS; still display the signed value.

Closed months: build ranking from each site's original settlement row labeled `LUCRO:`, not the gross-revenue row. Preserve source values and month-specific layout. This applies to every historical month without re-running current rules.

## July 2026 difference diagnosis

The dashboard's active July snapshot was captured `2026-09-08T21:22:14.922395+00:00` and intentionally remains frozen:

- dashboard due F103: BRL71,984.7652668042;
- dashboard final F132: BRL−1,090.0485236818608;
- live Sheet read on September10: F103 BRL71,930.21337098593; F132 BRL−1,144.6004195001296;
- exact difference: BRL−54.55189581827.

FX remained 5.098 and invalid rates remained ActiveView0.18%, YMonetize0.537%, SB Rede10.108%; payments/adjustment movement and previous balance remained unchanged in the consistent read. The change is downstream source drift after the snapshot:

- company JBF Tech Bot conversion/expense increased by USD21.776754265246 (the frozen value corresponds to 629.28÷1.40461; live formula uses I1=1.3395, yielding USD469.7872340425532);
- Isliago personnel expense decreased by USD0.3754612804345;
- net result decreased USD21.401292984805;
- half converted at5.098 decreased BRL54.55189581827.

Therefore the discrepancy is not caused by FX or invalid-rate changes. The Sheet is live and its formulas/dependencies changed after the historical dashboard capture; the dashboard preserves the approved frozen version by design. Do not refresh or overwrite July merely to match the current Sheet without a separate historical-source decision.

## August balance-difference diagnosis

Read-only request Rodolfo1552080963356594188, evidence in the current rate-propagation report. The live principal Sheet showed G132 BRL74377.49416357411; Payments showed BRL74376.81. FX5.08 matched; this is not caused by the confirmation-label bug and must not be dismissed as only rounding.

- Fincgriffin Sheet invalid formulas such as AAH5 reference L1/Rede1 at0.10%, while the August dashboard calculates Fincgriffin with Rede2 at0.12% (virtual XFD1). Its gross also retains more native precision: USD1682.833425801682038186 versus SheetUSD1682.83. Combined net/tax contribution to the partner-half difference is BRL+0.72348949646, Sheet minus dashboard.
- Remaining net-revenue/tax differences contribute BRL+0.01115441494; personnel differences contribute BRL−0.04715181346. Their sum is the exact pre-cent partner-half difference BRL0.68749209794. Reconcile the ledger's rounded due/opening independently before explaining the final displayed BRL0.68; do not sum already rounded component labels as proof.
- K1/YMonetize differed, but an isolated counterfactual proved zero impact in this August snapshot. Never attribute a difference to a mismatched input without proving downstream effect.
- Native imported facts can replace zeroed compatibility-graph facts. Comparing only legacy result cells to live Sheet totals produces false large discrepancies; reconcile the actual consolidated domain and source lineage.

This diagnosis authorizes no Sheet edit, network reassignment, salary change, forced rounding or balancing ledger entry. Preserve the currently approved source/period rules and obtain explicit authority for a financial correction. A historical diagnosis is not an active rate policy.

### Later explicit reconciliation — Rodolfo1552091292224196620

The earlier diagnosis was read-only. Rodolfo1552090743085076510 subsequently requested a G002/Fincgriffin Sheet adjustment and explicitly confirmed in1552091292224196620 that the intended direction is to reduce the final Sheet balance by BRL0.68. That supersedes the no-write state only for this bounded August correction, not financial-source rules generally.

The single existing management-adjustment input `Agosto 2026!ZQ175` (G002 block) changed from grossUSD1.12 toUSD0.8065678129204399. Shell Decimal calculation used `−0.68×2/[5.08×(1−0.001)×(1−0.10)×(1−0.05)] = −0.3134321870795601USD`; do not add0.68USD or increase revenue when the Sheet is already higher. Keep the prior note and append explicit authority, original value, adjustment basis and the fact that it is monthly management reconciliation, not original daily/GAM revenue.

Live readback: G13274376.8141635741, displayedBRL74376.81, matching the unchanged dashboard ledger display. Only that input/note changed; aggregate formulas, rate values, other manager inputs and the bounded September controls were preserved. This targets the displayed final balance, not bit-identical intermediate revenue/tax totals. It supersedes the prior gross-cent reconciliation only at this input; preserve the original value and note in the immutable backup. Never import the adjustment as a newly measured dashboard revenue or change the network assignment/invalid formula without separate authority. Evidence: `reports/finance-expense-save-1552090743085076510.md`.

## Validation and deployment

Validated release under request `1547706561210753114`:

- 103/103 bounded Node tests PASS plus focused16/16;
- Payments indicator rendered for24/24 months:7 historical +17 workspaces;
- July values/rates and capture note passed;
- current profit ranking exactly matched API fact profit plus each site's segment expenses; the final semantic one-file follow-up was deployed atomically with no service restart and passed the full103-test suite again;
- Cephyric/Escalatepower/Mavroa show MGS, and Yolo internal manager names are normalized;
- owner desktop/mobile and horizontal scroller PASS; zero JS errors;
- Nicolas manager API/UI shows no company indicators;
- PostgreSQL scenario/ledger/history/user manifests unchanged;
- five-file code bundle backed up at `/home/zeus/mgs-finance-backups/1547706561210753114/code-before.tar.gz` and deployed atomically; finance service/socket only, never Hermes gateway.

Two publish attempts rolled back cleanly because health probes used an external Cloudflare path and then lacked Unix-socket permissions. Final probe runs through the finance socket as `runcloud-www` with Host and forwarded-proto headers. Never weaken Cloudflare or socket permissions for a health check.
