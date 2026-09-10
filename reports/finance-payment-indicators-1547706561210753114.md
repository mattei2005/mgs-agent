# Finance dashboard — payment indicators, MGS alias and profit ranking

Authority: Rodolfo messages `1547706561210753114`, `1547706760251449445`, `1547707970731638945`, `1547708328073896066`, `1547711786688708759`, thread `1545426987756298340`.
Status: production published and validated.

## Delivered

- Payments shows `Câmbio e inválidos do mês` for all 24 selectable periods:
  - January–July 2026: frozen exchange, invalid totals/rates and capture date from each historical monthly payload.
  - August 2026–December 2027: current scenario exchange and invalids marked provisional.
- The line shows USD→BRL, invalid total in USD/BRL, network rates available and state (`Fechado`/`Provisório`).
- Company-wide indicators are hidden for manager logins; Nicolas API returns `indicators:null` and his Payments UI has no table.
- `SEM_COMISSAO` is now displayed as `MGS`, because it is the internal G002/no-employee-commission key. Cephyric, Escalatepower and Mavroa show MGS; their site status remains pending and expense allocation remains unchanged.
- Internal manager labels are normalized to Ícaro/Isliago/Joe/Kelly/Nicolas. Yolo no longer exposes `SEM_COMISSAO` or lowercase internal names.
- `Sites em destaque` now ranks by descending net profit:
  - current periods: grouped daily fact `profit` plus each site's monthly segment expenses exactly once, preserving native imported facts;
  - closed periods: each original site settlement row `LUCRO:`.
- September live top six validated against the API: Eggbev, Openzed, CreditoParaVeiculo, Zytiva, Helixenit, Openzed Finanzas.

## July difference versus the live Sheet

Active dashboard snapshot:

- captured `2026-09-08T21:22:14.922395+00:00`;
- due F103 BRL 71,984.7652668042;
- final F132 BRL −1,090.0485236818608.

Consistent live Service Account readback on September 10:

- due F103 BRL 71,930.21337098593;
- previous F129 BRL 135.0062095139292;
- final F132 BRL −1,144.6004195001296.

Difference: BRL −54.55189581827. FX remained 5.098 and invalid rates remained ActiveView 0.18%, YMonetize 0.537%, SB Rede1 0.108%; adjustments/payments and previous balance did not change. The live H136 result fell USD 21.401292984805:

- the JBF Tech Bot company expense increased USD 21.776754265246. Frozen value corresponds to 629.28 ÷ 1.40461; current formula uses `I1=1.3395`, producing USD 469.7872340425532;
- Isliago personnel expense decreased USD 0.3754612804345;
- half of the net USD decrease × 5.098 exactly explains BRL 54.55189581827.

The discrepancy is post-capture Sheet drift, not exchange or invalid-rate drift. The dashboard keeps July frozen by design. No historical refresh or financial correction was performed.

## Deployment and validation

- Five-file bundle: `finance-ops.mjs`, `public/operations.js`, `public/history-operations.js`, `public/app.js`, `public/history-dashboard.js`.
- 103/103 bounded Node tests PASS; focused16/16 PASS.
- Public owner browser: 24/24 payment months, July source values, current profit order, MGS labels, desktop1440/mobile390 and JS errors0.
- Mobile indicator table has horizontal overflow by design; final cell was fully reachable after real scroll and document width stayed within viewport.
- Nicolas manager browser: company indicator API/UI absent, no financial writes.
- Visual review passed indicator and ranking layout. Historical invalid BRL is the sum of original per-site BRL values and may differ by cents from displayed USD total × displayed FX; no synthetic rewrite.
- PostgreSQL scenario/result/overrides/additions, ledger, history and users semantic manifests were identical before/after. No financial data, payment, ledger, Sheet, credential, permission, account, campaign or gateway change.
- Semantic follow-up: the current ranking was tightened from operating `profit` to `profit + site segment expenses`, so “lucro líquido” includes the site's monthly expense allocation once. Only `public/app.js` changed, atomically, without service restart; full103/103 tests and24-month public validation passed again. Rollback file: `/home/zeus/mgs-finance-backups/1547706561210753114/app-profit-before.js`, SHA256 `e58f5d9a259e179bba854cf22069f51927c660b9b24a305c1f83fef95f719b60`.
- Services active: PostgreSQL, finance dashboard and socket.

## Backup and recovered failures

- Backup: `/home/zeus/mgs-finance-backups/1547706561210753114/code-before.tar.gz`.
- SHA256: `314dde1101a545b7f28bd889f188cb1cd47140899e792cc1786b5054b96f4bc1`.
- Two publish attempts restored the five original files and services automatically:
  1. external Cloudflare probe from the origin returned403;
  2. direct socket probe ran as Zeus, who correctly lacks socket permission.
- Final health probe used the protected Unix socket as `runcloud-www`, with exact Host and forwarded-proto headers: login200/API401. No Cloudflare or socket permission was weakened.
- July analysis initially compared the active dashboard to an older raw capture and then mixed volatile live reads. It was corrected to the active version selected by `master-history-source` and a single consistent live read; the final bridges close below0.000001.
- One focused UI test expected the negative sign after the currency symbol; Intl PT-BR correctly emits it before the symbol. The oracle was corrected, not the interface.
