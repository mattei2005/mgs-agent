# GB/US CC Utility Template Reduction, Link Order, and Raw Approval Results — 2026-06-30

## Context

During the Utility Template rollout, Rodolfo reduced the operational template size from ~187/201 messages to ~70 messages because Ciro estimated approval runtime around `8s/message * 10 messages/page * ~3k pages`, making 200-message templates too slow to approve daily. The goal was faster approval while preserving strong conversion copy.

## Durable lessons

### 1. Reducing to 70 is not “first 70”

When Rodolfo asks to reduce a production template to 70 messages, select the strongest/conversion-oriented messages, not the first 70 rows.

Good selection signals:
- strong hook in first line;
- card/credit/profile/application/approval/limit/delivery framing;
- curiosity or urgency without becoming generic filler;
- strong CTA;
- commercial relevance to credit-card funnels.

### 2. Link sequence and message selection are separate

Critical correction from Rodolfo: for templates with numbered `mct-###` URLs, the links must remain in their proper numeric sequence. Do **not** carry the old link from the selected message’s original row when reordering/ranking messages by appeal.

Correct pattern:
1. Rank/select the best 70 message texts/CTAs.
2. Extract the target template’s original link sequence from the pre-change template.
3. If the template uses numbered URLs, assign links in numeric order to the final 70 rows:
   - `mct-001`
   - `mct-001-2`
   - `mct-002`
   - `mct-002-2`
   - `mct-003`
   - `mct-003-2`
   - etc.
4. Preserve the exact URL string. Do not edit domains, query params, `utm_medium`, `utm_campaign`, `utm_content`, `-2` variants, or masks.
5. If all links are the same/non-numbered, leave them as-is.

Validated examples:
- Numbered templates needing ordered reassignment: Ducapes Finance, Eggbev, Infinitynexx, Lyzmo, Marevelx, Newsoun, Financetopfeed, Zytiva.
- Single/non-numbered link templates to leave alone: Cliquet, Openzed AV variants, Wavesbee, Zuout.

### 3. Approval result sheets must reflect the Dash source, not a “smart” consolidation unless requested

When Rodolfo gives specific SB template names and says the results are there, the task is to read those templates from SB/Dash and put their rows into the sheet. Do not infer, merge, or consolidate unless explicitly asked.

Wrong pattern from the session:
- Consolidating three test templates by `TEXT+CTA` and making `APPROVED` override previous blank/error states.

Correct pattern:
- Read the exact named templates from SB.
- Create a raw/results tab with one row per message per template.
- Include identifying/status columns:
  - `TEST_TEMPLATE`
  - `TEMPLATE_RUN`
  - `SOURCE_MESSAGE_ID`
  - `STATUS`
  - `APPROVED`
  - `REJECTED`
  - `INVALID_FORMAT`
  - `ERROR`
  - `REJECTED_REASON`
- Keep the original `MESSAGE_ID` from each template.
- Add a summary tab with per-template counts.

This lets Rodolfo see exactly which messages in the first template had no color/status and which retest template produced the later result.

### 4. Status classification from SB message fields

For each message row:

```text
APPROVED > 0        → APPROVED
REJECTED > 0        → REJECTED
INVALID_FORMAT > 0  → INVALID_FORMAT
ERROR > 0           → ERROR
otherwise           → NO_STATUS
```

Do not treat `NO_STATUS` as failed; it means the Dash did not return a color/status for that row.

## SB/Dash implementation notes

- The authenticated `/broadcast/Messenger` payload contains `MESSAGES` as a JSON-encoded array with fields like `MESSAGE_ID`, `TEXT`, `CTA_1`, `LINK_1`, `APPROVED`, `INVALID_FORMAT`, `REJECTED`, `ERROR`, `REJECTED_REASON`.
- When using the internal API from Playwright, keep the browser/context alive while making API writes. Closing the browser before `ctx.request.post(...)` causes `TargetClosedError`.
- If a direct `ctx.request.get(...)` returns `401`, trigger/capture the real dashboard request by navigating to Messenger → Broadcast Template and reuse the captured request context/headers; do not conclude credentials are wrong.

## Reporting to Rodolfo

Be explicit when correcting a previous bad write:

```text
Corrigido. Agora está bruto por template, sem consolidação.
Aba: GB-CC-EN Dash Results Raw
Resumo: [counts]
Readback Sheet: OK
```

If the previous output was consolidated incorrectly, say so directly and replace it with the raw tab rather than defending the previous transformation.
