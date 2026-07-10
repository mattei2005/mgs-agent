## Existing vs New Template Decision

Use existing template when:

- only a few copies failed;
- you can replace individual rejected messages without disturbing many approved ones;
- the dashboard workflow is stable;
- preserving current page assignment matters.

Create a new template when:

- most current copies failed;
- you need a clean approval experiment;
- you want to approve a new bank before touching production;
- you can bind it to at least 1 page for approval.

## Clean-page canary workflow

For Utility Template approval, use the clean-page canary workflow captured in `references/utility-template-clean-page-canary-workflow-2026-07-03.md` and the phase plan in `references/template-canary-production-diagnosis-plan-2026-07-07.md`: create **1 canary template per vertical/language/country** (example `US-CC-EN`), link **1 known-good page that is currently OK and sending**, load that vertical's **20 messages**, run approval, and iterate until the status bar is **100% green** for all messages. Purple on a clean page is infrastructure/page/app/SB diagnosis, not automatic copy rewrite. Phase C should start canaries for all relevant verticals in parallel where practical; do not wait for one vertical to finish before preparing the rest.

If a copy/template approves on the clean page but later fails after production rollout, treat those failures first as page/segurador/app/restriction diagnosis, not automatic copy failure.

Rodolfo correction 2026-07-03: do not wait to discover issues template-by-template in production. Create clean-page canary templates for every relevant vertical/language. Gray/no-status inside these controlled tests is not a passive hold state: keep cycling/replacing gray messages until the canary reaches all green or Rodolfo explicitly stops the experiment.

Rodolfo + Felipe Vidal plan 2026-07-07: after canary reaches 100% green, **Phase 2** is replacing the current production templates with the corrected approved messages, preserving routing/page bindings/link sequences unless explicitly changed. Ciro's system reads the templates again at midnight ET and sends them to the pages. **Phase 3** is next-day analysis of gray/red/purple statuses. **Phase 4** is remediation: fix the page or block/disable it in the dashboard, then define the future cron rule. Do not auto-rewrite purple globally; purple can indicate a linked page/app/segurador blocker preventing Meta verification.

### Phase 2 — linked production rollout from fully approved canaries

Rodolfo correction 2026-07-09: when he explicitly authorizes this Phase 2 migration, the first gate is live Broadcast Template `PAGES > 0`. Exclude test/`NAO-USAR` templates and templates already 20/20 green. This authorized migration is a scoped exception to the normal red-only repair rule: keep every green slot unchanged and replace red, purple, and gray slots with unique 20/20-approved messages from the exact same `COUNTRY-VERTICAL-LANGUAGE` canary. Preserve destination `MESSAGE_ID`, links, media, secondary fields, page bindings, and link order. Linked 10-message targets may be expanded to 20 only by cycling their own exact link/secondary-field sequence.

For large Phase 2 runs, freeze a live plan, independently validate it, backup every row, deploy one low-page production canary per vertical (including special 10→20 cases), validate immutable content/CTA/link readback, then resume the remaining targets from a per-template success journal. Retry transient 5xx only once with the identical payload. Trigger approvals after all writes validate. Approval counters are asynchronous: HTTP 202 means accepted, and post-approval safety checks must compare `MESSAGE_ID + TEXT + CTA_1 + LINK_1`, not a full message hash containing mutable status counters. See `references/linked-production-rollout-from-approved-canaries-2026-07-09.md`.

Controlled canary approval loop correction from Rodolfo 2026-07-07: in canary templates, **green = keep**, **red = replace only that message immediately**, **gray = do not replace immediately**. For gray/no-status, run approval retries up to **3 attempts with an interval** before treating it as needing replacement or manual diagnosis. This is different from global production rollout: the goal of canary is to get every message green quickly, but gray often means Meta/SB did not finish or did not hit yet, not bad copy. Never bulk-replace all gray rows on the first readback.

Critical canary state rule from Rodolfo 2026-07-07: once a specific message slot/text has ever become **green/approved**, register it as `green_locked` / known-good. If that same slot later appears gray/no-status, **do not replace it**, even after 3 gray cycles, because SB/Meta can temporarily show gray and later return green. Only messages that have **never been green** can be replaced after 3 consecutive gray approval attempts. Red still replaces immediately unless the message is green-locked and the operator explicitly wants to investigate first. The temporary canary cron may run for 3 hours; every cycle must persist state by `template + MESSAGE_ID` with: current text/CTA hash, ever_green flag, gray_attempt_count, last_color, replacements_done, and approval_run timestamps. On replacement, reset attempts for the new text and start the loop again. Rodolfo correction 2026-07-08: replacement loops must enforce **no repeated visible message text inside a template**. Duplicate guard is by normalized visible `TEXT` (strip zero-width and whitespace), not by `TEXT+CTA` and not by link. If any duplicate `TEXT` would exist after a proposed replacement, block the POST, pause/escalate, and do not run approvals on that broken set. CTA/body variations cannot reuse the same body/message concept repeatedly. Replacement copy generated by the canary/cron must include context-appropriate emojis in both headline/CTA when that style is used, with varied headlines and bodies per vertical (`CC`, `JOB`, `CAR`, language/country) instead of plain repeated utility bodies.

Canary setup execution rule from Rodolfo 2026-07-07: for each new `Teste-<vertical>-<site>-<page>-<FB_PAGE_ID>-<PAGE_ID>` template, copy exactly the 20 messages from an active linked template of the same vertical, preferably the same site when available (for example Newsoun for `US-CC-EN`, `US-CC-ES`, `DE-CC-DE`). Delete/replace existing test-template messages so only those 20 copied messages remain. Then link the test template to its selected page via `Accounts > Messenger > Page` / Broadcast `Message Template`, validating by large `FB_PAGE_ID`, small `PAGE_ID`, and `PAGE_NAME` before saving. Rodolfo prefers canary pages from the same site when possible; try Newsoun first when it has a clean page for that vertical.

Concrete 2026-07-07 execution: see `references/test-template-canary-rollout-2026-07-07.md` for the full validated sequence: populate 11 `Teste-*` templates from active same-vertical templates, link one page each, run approval, replace red+gray rows in controlled canary, and re-run approval. Important distinction: replacing gray rows is allowed in this controlled canary loop when Rodolfo explicitly asks; global production rollout still follows stricter gray/purple hold/diagnosis rules.

