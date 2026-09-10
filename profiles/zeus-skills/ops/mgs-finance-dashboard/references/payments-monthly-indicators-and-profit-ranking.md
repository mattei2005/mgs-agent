# Payments monthly indicators, MGS alias and profit ranking

## Authority and scope

Rodolfo messages `1547706561210753114`, `1547706760251449445`, `1547707970731638945`, `1547708328073896066` and `1547711786688708759`, thread `1545426987756298340`.

This change is presentation/readback only:

- show the month's USD→BRL exchange rate and invalids in Payments for every selectable month;
- display internal `SEM_COMISSAO` as `MGS` (G002), never as a person or unknown manager;
- rank “Sites em destaque” by site net profit, not gross revenue;
- explain the July closed snapshot versus the later live Sheet without rewriting closed history.

It does not change any revenue, spend, invalid rate, exchange value, payment, ledger entry, site ownership, commission eligibility or closed-month snapshot.

## Payments indicators

Owner/general Payments renders one compact `Câmbio e inválidos do mês` table:

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
