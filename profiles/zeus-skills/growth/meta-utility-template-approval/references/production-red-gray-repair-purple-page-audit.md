# Production red/gray repair and purple page attribution

## Trigger

Use this reference when Rodolfo asks to keep linked SmartBidding Broadcast Templates at a fixed message count, automatically repair red/gray messages, or identify pages behind purple approval errors.

## Repair policy currently agreed — superseded 2026-08-03

Rodolfo reopened purple handling after confirming the SmartBidding/Ciro reset semantics. The following policy supersedes the 2026-07-16 purple hold for the dedicated fixed-30 executor only:

- Operate only on `digital-trust` / `digital-trust-2` production templates with live Broadcast Template `PAGES > 0` and exactly 30 messages.
- Exclude names beginning with `Teste` and names containing `NAO USAR` / `NÃO USAR`.
- Treat the immutable Broadcast Template ID as the transaction/lock unit. Never run two rounds for the same template simultaneously.
- Any `Update + Save`, even without visible content change, resets the whole template version to gray. Therefore a slot-level content edit also clears the status of green, gray, red, and purple slots in that template. Backups can restore content but cannot restore the erased color log.
- A 30/30 green template is terminal success and must not be touched.
- Red: replace every red slot in that template in one batch with unique, same-country/vertical/language copies from `data/utility-message-bank.json`; preserve each target slot's IDs, links, media and metadata. Then perform one `Update + Save`, confirm 30 gray on readback, and perform one `Run Approval`.
- Duplicate visible text is actionable repair work, not a terminal blocked state. Normalize visible `TEXT` by removing zero-width characters, trimming, collapsing whitespace and comparing case-insensitively. Preserve one occurrence of each copy and replace every additional occurrence with a unique copy from the same country/vertical/language bank, while preserving the target slot's link, IDs, media and metadata. Validate 30 unique visible texts before `Update + Save`, confirm 30 gray on readback, run one Approval and verify the final statuses after the full ETA.
- If the approved bank cannot supply enough unique copies for all red or duplicate slots, do not partially repair the production template and do not leave it generically blocked. Calculate the exact deficit, generate that many new distinct utility copies for the same country/vertical/language, and route them through a controlled approval template/canary. Only a live green readback promotes a copy into `data/utility-message-bank.json` as reusable approved inventory; gray remains pending, purple remains diagnostic and red/rejected is never recycled as approved. Resume the original production repair only after the approved bank can cover the full deficit, then validate unique text, preserved slot links and final live statuses.
- The executor/report must distinguish `needs_generation`, `testing_new_copies` and `ready_to_repair` from a true safety/runtime block so these templates progress automatically instead of remaining indefinitely in a generic blocked bucket.

### Runtime implementation (2026-08-07)

Canonical runtime paths:

- `scripts/sb-broadcast-template-repair.py`: detects duplicate visible text, preserves the safest occurrence, repairs only the extra slots, and emits `needs_generation` with an exact vertical deficit when the unique approved bank is insufficient.
- `scripts/sb-utility-candidate-approval.py`: stages only model-written candidates in a configured 20-message test template, preserves slot links/metadata, requires all-gray save readback, triggers Approval, waits the full page × message × 12s + margin ETA, and promotes only live-green observations into `data/utility-message-bank.json`.
- `data/sb-utility-generated-candidates.json`: candidate reservoir written by GPT/current Zeus model; scripts must never mechanically synthesize final copy.
- `data/sb-utility-candidate-approval-config.json`: fail-closed rollout config and vertical-to-canary mapping.
- `data/sb-utility-candidate-approval-state.json`: pending/completed candidate cycles, placements, hashes, ETA, backup and readback state.
- `scripts/sb-broadcast-template-repair.sh`: canonical wrapper; `dispatch` stages candidates before eligible production repair, and `check` reads candidate approvals before production-template readback.

Rollout stages are `canary → staged → full`; promotion occurs only when every candidate in the current stage is confirmed live green. Red candidates remain rejected, gray candidates may receive at most the configured Approval retries, purple is diagnostic, and any content drift or candidate-catalog deficit blocks fail-closed and posts a compact embed to `#broadcast-templates`. A candidate that remains gray after the maximum retries, turns red, or turns purple is durably retired from automatic selection; a new model-written candidate must replace it. Production dispatch never installs a candidate still in testing. Discord notification transport is non-authoritative: persist the live state before posting, record HTTP failures without repeating the write, and recover rollout promotion idempotently on the next check. Daily quota counts every template already started that day, including a cycle whose notification failed.
- Purple without red: do not change visible copy. Perform a no-op content reset (`Update + Save`), confirm 30 gray, then perform one `Run Approval`. Improvement is measured by aggregate counts; exact causal Page IDs are not required. A reduction such as 50 purple to 30 purple is positive progress.
- Gray: wait the full Approval ETA. The first executor version does not automatically replace gray-only slots because any edit resets the entire template.
- Approval ETA is `PAGES × 30 messages × 12 seconds`, plus the configured safety margin. Do not start a round that cannot finish before the next 00:00 America/Sao_Paulo cutoff.
- Normal dispatch is 08:00 America/Sao_Paulo, initially limited to templates with at most 150 pages and one cycle per template/day. Larger templates require a separately validated window.
- Every readback must update `data/utility-message-bank.json` before deciding. Preserve `approved_count` / ever-green history after later gray or purple observations; a later red creates mixed history rather than deleting prior approval.
- Rollout is canary (1 small template) → staged (3/day) → full controlled batch. Halt/pause on drift, write/readback mismatch, missing approved copy, no progress, or transport/runtime failure.
- Discord lifecycle alerts go directly to `#broadcast-templates` (`1522487422510694450`) as compact embeds: one start and one result/blocked event per touched template, plus one daily digest. Suppress identical fingerprints; never dump every message ID or repeated prose.

## Purple attribution distinction retained

Purple is still an aggregate message/template state and SB does not identify the causal Page ID. The fixed-30 retry flow may reset and re-run Approval without page attribution, but any claim about *which page caused purple* still requires the separate SB→Page→DTR corroboration workflow below. Do not label all linked pages as confirmed purple pages.

## Do not revive the legacy rollout manager in place

The old hourly manager contains obsolete 10/20/30 scaling, a stale tracker, and older gray rules. Freeze its history as legacy/superseded for audit and backups. Build a dedicated fixed-30 repair state instead of deleting historical records.

## Purple-error attribution workflow

1. Fresh-read `/broadcast/Messenger` under the full operational account scope.
2. Parse `MESSAGES[].REJECTED_REASON`. Remember that a reason total is a **message count**, not a page count.
3. Select templates whose reason contains `pages_utility_messaging` or the other purple app errors.
4. Map each affected immutable `BROADCAST_TEMPLATE_ID` to `/campaigns/Messenger` rows.
5. Reconcile page-row status against Broadcast Template `PAGES` before counting. In the validated MGS mapping, `Broadcast` + `Campaign` rows formed the active page universe; `Ready`, `On-hold`, and `Blocked` rows were attached but excluded from `PAGES`. Do not hardcode that forever: assert the grouped active count equals each live `/broadcast/Messenger[].PAGES` value and stop on mismatch.
6. Required operational fields and presentation order:
   - `PROFILE_NAME` → `Segurador`
   - `PAGE_NAME` → `Página`
   - `BROADCAST_TEMPLATE_NAME` → explicit `Nome do template` column immediately after `Página`
   - `https://facebook.com/{FB_PAGE_ID}` → clickable `Link da página`
   - `USER_LOGIN` or `LOGIN` → `Usuário do bot`
   - `FB_PAGE_ID` → Facebook Page ID
   - `PAGE_ID` → internal PG/Page ID
   - `STATUS`, purple category/reason for audit
7. Independently inspect the latest completed DigitalTRChat campaign report for each candidate page. Record only safe error code/subcode evidence; never export tokens, cookies, access tokens, or full raw responses.
8. Be precise about attribution and vocabulary:
   - purple is a message/template state, not a page-level color returned by SB;
   - `/broadcast/Messenger` aggregates errors by message and does not identify the failing Page ID;
   - “pages linked to templates with purple” is a measurable universe, while “pages that caused purple” is not exact without a per-page DTR/Meta result;
   - a page list mapped from affected templates is an operational suspect list unless corroborated. Even with corroboration, distinguish “same page-level failure observed” from proof that a specific Graph permission is missing.
9. Produce a verified XLSX with:
   - `Resumo`;
   - `Páginas vinculadas` for the complete active universe (never label these rows as confirmed “purple pages”);
   - a named subset sheet such as `Subconjunto #200` when the request singles out one reason;
   - `Rows não ativas` for attached `Ready`/`On-hold`/`Blocked` rows.
   Include `Nome do template` as a prominent explicit column, clickable Facebook links, filters, frozen header, readable widths, purple category/reason, and a methodology caveat. Reopen the workbook and validate sheet names, row counts, column placement, and hyperlinks before delivery.

## 2026-07-16 observed case

The first answer incorrectly let a reason-specific subset sound like the total purple scope. The corrected live reconciliation was:

```text
Category                         Templates  Purple messages  Active linked pages
#200 pages_utility_messaging             6               51                   17
Application deleted                      1               30                    1
Application lacks permission             2               50                  131
Generic status=error                     1                1                   13
Total                                   10              132                  162
```

- `51` was the number of purple **messages**, not pages.
- The 17 pages belonged only to the six-template `#200 pages_utility_messaging` subset.
- The full purple universe was 132 messages in 10 templates linked to 162 active `Broadcast`/`Campaign` pages.
- Another 96 attached rows were `Ready`, `On-hold`, or `Blocked` and were separated from the active universe.
- Latest DTR reports for all 17 active `#200` rows showed `OAuthException code 100 / subcode 1689001`. This corroborated a page-level failure but was not represented as direct Graph proof of `pages_utility_messaging` state.
- When challenged on a surprisingly small page total, immediately recompute **all purple reason families** before defending the subset count.
