## Common Pitfalls

1. **Editing approved copies.** Alterou texto, mudou hash, resetou approval. Preserve approved copies.
2. **Treating approval as performance.** Approval only means Meta accepted the message; it does not prove ROI.
3. **Scaling before a seed batch is stable.** Probe first, expand after approval rate is acceptable.
4. **Mixing languages.** EN, ES, PT etc. need separate banks and separate approval tracking.
5. **Using the Felipe CSV blindly.** It shows a successful structure, but some claims may be too aggressive for long-term resilience.
6. **Confusing Meta approval with business-quality copy.** A lot can approve because it looks like “utility”; still reject or rewrite copy that does not make sense for the funnel. For credit-card funnels, do not let package/home-delivery/courier language dominate unless the page actually supports physical-card logistics.
7. **Generating mechanical variants.** “NEW”, emoji swaps, and shuffled status wording may pass technical validation but are weak creative. Rodolfo expects GPT/Zeus to write CCO-level copy ideas first, then use scripts only for CSV/validation.
8. **Forgetting the 12/day/page math.** The inventory target exists because daily broadcast rotation burns copies quickly.
9. **Adding images/message 2 too early.** Current priority is delivery via text + button. Optimization comes later.
10. **Not refreshing dashboard.** After approval, F5 is required to see updated status.

11. **Forgetting the parent Save after Import/Update.** In SB, upload + `Update` inside Messenger Messages can show the right message count in the modal, but the template is not safely persisted until the parent `Edit Messenger Broadcast` modal is also saved. Always validate via `/broadcast/Messenger` after Save.
12. **Normalizing production links.** When replacing messages in existing templates, do not simplify or invent link rotations from examples. Preserve the exact `LINK_1` sequence from each target template, including repeated links, `-2` variants, AV/YM single-link templates, and query params.
13. **Confusing raw Dash results with consolidated approval bank.** If Rodolfo names specific test templates and asks to put results into a Sheet, read those exact templates from SB and output rows raw per template with source/status columns. Do not merge by `TEXT+CTA` or make `APPROVED` override blank/error rows unless he explicitly asks for a consolidated bank. If the named template is not present in the latest local raw cache, refresh the live SB/Dash payload by capturing the authenticated `/broadcast/Messenger` browser response, then find the exact `NAME`. Blank status rows are valid pending/no-counter rows, not automatic failures.
14. **Breaking numbered link order when selecting best messages.** If you rank/select the best 70 messages, do not keep each selected message's original-row link. For numbered `mct-###` templates, assign links back in numeric order while preserving exact URL strings. Single-link templates can remain unchanged.
15. **Zero-width scope/density and forbidden first-name placeholder.** When Rodolfo asks for zero-width on Utility copies, apply it only where explicitly requested. If he says “apenas nas mensagens”, alter `TEXT` only; do not alter `CTA 1`, links, or tracking params. As of 2026-08-08, `{{first_name}}` is forbidden in every MGS Broadcast Template message under `digital-trust` and `digital-trust-2`, including linked, unlinked, test and `NAO USAR` rows. Remove it without leaving dangling commas/spaces, preserve IDs/links/counts, run Approval only for linked rows, and require a full-scope live readback with zero remaining occurrences. Candidate generation and approved-bank selection must sanitize/reject the placeholder so it cannot be reintroduced. If zero-width is too dense, switch to the lighter `2 visible letters + U+200B` pattern.
16. **Selecting 70 before approval.** When preparing a new country/language approval probe, do not rank down to 70 before approval unless Rodolfo explicitly asks. First export all eligible messages for approval; after approval results come back, filter approved rows and then choose the best 70 for production templates.
17. **Raw cron JSON in Discord.** For SB Utility rollout crons running script-only/no-agent, stdout is the user-facing message. Do not print raw `{"status":"OK",...}` payloads when templates change. Keep machine payloads in log files and print a compact human summary; print nothing for no-op runs.
18. **Gray/purple behavior unresolved by default.** Do not assume gray or purple is safe to replace after N days in routine/global automation. Treat persistent gray/no-status and purple/error as Ciro/SB/page diagnosis unless Rodolfo explicitly defines a one-time normalization exception. In the approved 23/30 link-bank rollout, every linked non-green slot (red, gray, and purple) is replaced once; this does not establish a daily auto-repair rule.
19. **Deleting/editing template resets status.** If the whole template is erased/reuploaded, or a message is edited and Update is clicked, SB can make everything gray again. This is an SB/Ciro bug/behavior, not proof that every message needs reapproval. Avoid destructive erase/update unless explicitly requested and backed up.
20. **Bank versus template duplicate guards.** The durable bank can remain keyed by normalized `TEXT+CTA`, with `LINK` excluded because it is template-specific. The stricter live-template payload gate is normalized visible `TEXT`: strip zero-width and normalize whitespace, and block a repeated body even when CTA differs.
21. **Restarting a partial mass rollout from zero.** A timeout or transient 5xx after many successful templates must not replay earlier writes. Persist one validated record per target and resume only pending names; retry one identical 5xx payload once, then stop if it still fails.
22. **Hashing asynchronous approval counters.** `APPROVED`, `REJECTED`, `INVALID_FORMAT`, and `ERROR` can change after another template's approval starts. Do not use a full `MESSAGES` hash containing those counters as the pre-approval deployment guard. Verify immutable `MESSAGE_ID + TEXT + CTA_1 + LINK_1` separately from status reporting.
23. **Assuming one dashboard credential has the full inventory.** If Rodolfo's UI count and an API capture disagree, compare authorized dashboard accounts and immutable IDs. A narrower account returning fewer rows is an access-scope divergence, not proof that the missing templates do not exist.

## Verification Checklist

Before saying a batch is ready:

- [ ] CSV columns match dashboard import format.
- [ ] Every row has `TEXT`, `CTA 1`, and `LINK 1`.
- [ ] No unsupported image/text2/CTA2 fields unless explicitly approved by tech.
- [ ] If the batch style uses emoji, all generated rows preserve emoji in text and/or CTA.
- [ ] If the batch style uses headline + body, all generated rows preserve headline + blank line + body.
- [ ] Representative rows from start, middle, and end were manually inspected for concept quality.
- [ ] For emoji CSV import into SB, a UTF-8 BOM/CRLF version exists and was preferred for dashboard upload.
- [ ] For production replacement CSVs, `LINK 1` was copied from the exact target template sequence, not normalized from examples.
- [ ] During SB import, current template JSON/CSV backup was saved before `Erase all`.
- [ ] Import tab showed the expected uploaded/total count.
- [ ] For normal import workflows, `Update` was clicked in Messenger Messages and `Save` was clicked in the parent Edit Messenger Broadcast modal.
- [ ] For Rodolfo's 23/30 link-bank normalization, the corrected order was followed instead: `Run Approval → Update → Save → readback` for linked templates, and `Update → Save → readback` for unlinked templates.
- [ ] Authenticated `/broadcast/Messenger` readback confirms expected message count and the complete ordered text+CTA+link payload, not merely first/last rows.
- [ ] Template is linked to at least 1 page before any approval action.
- [ ] `Run Approval` was executed only where the selected workflow and live `PAGES > 0` require it.
- [ ] Dashboard was refreshed with F5.
- [ ] Approved/rejected/invalid counts were captured.
- [ ] Approved copies were stored separately as immutable positive bank.
- [ ] Rejected copies were removed or queued for rewrite.
- [ ] Bank progress toward ~200 approved messages per page was reported.
- [ ] Performance after deployment is tracked separately from approval.
