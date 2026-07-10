# Test Template Canary Rollout — 2026-07-07

Session: Rodolfo created 11 `Teste-*` Messenger Broadcast Templates for one-page canaries. Zeus populated them, linked each to its test page, ran approval, then replaced gray/red rows and re-ran approval.

## Scope

One canary template per active vertical:

- `CA-CC-EN`
- `DE-CC-DE`
- `GB-CC-EN`
- `ES-CC-ES`
- `MX-CC-ES`
- `US-CAR-EN`
- `US-CC-EN`
- `US-CC-ES`
- `US-JOB-ES`
- `ZA-CC-EN`
- `AR-CC-ES`

Each canary template name encoded the page identity:

```text
Teste-<VERTICAL>-<Site>-<Page Name>-<FB_PAGE_ID>-<PAGE_ID>
```

## Step 1 — Populate canary templates

For each test template:

1. Find a currently active production template with `PAGES > 0` for the same vertical.
2. Prefer the same site/domain if available, otherwise use the strongest same-vertical active source.
3. Copy exactly the first/current 20 messages from the active source template into the `Teste-*` template.
4. Replace the target template's existing messages entirely.
5. Preserve the source message fields (`TEXT`, `CTA_1`, `LINK_1`, etc.) and renumber `MESSAGE_ID` sequentially 1–20 if needed.
6. Save via `POST /broadcast/Messenger` and validate live readback: target has exactly 20 messages and digest matches the prepared payload.

Validated result in-session: 11/11 templates updated, 11x HTTP 201, 11/11 readback OK.

## Step 2 — Link one test page to each canary

For each test page:

1. Find the SB Messenger Page row by large `FB_PAGE_ID`.
2. Validate the small `PAGE_ID` and exact `PAGE_NAME` before writing.
3. Backup the full row.
4. Change only `BROADCAST_TEMPLATE_ID` to the `Teste-*` template ID, preserving status, schedules, message pointers, and restrictions.
5. Save via the same row-save path as the Page edit modal.
6. Validate fresh full-table readback: `BROADCAST_TEMPLATE_NAME` equals the `Teste-*` template.

Validated result in-session: 11/11 pages linked, all with readback OK.

## Step 3 — Run approval

Run Approval against all 11 `Teste-*` templates after they are linked to one page each.

Endpoint pattern:

```text
POST /broadcast/messenger/{template_id}/approve
fallback: /broadcast/Messenger/{template_id}/approve
```

Validated result in-session: 11/11 approval requests accepted, 11x HTTP 202.

## Step 4 — Replace gray/red and re-approve

After initial processing, read status from live `MESSAGES` counters:

- green/approved: keep unchanged;
- red/rejected: replace;
- gray/no-status: replace in controlled canary only;
- purple/error/invalid: diagnose separately unless Rodolfo explicitly includes it.

For this controlled canary loop, Rodolfo explicitly instructed replacing all red and gray rows, saving, and running approval again. Zeus generated replacement Utility-style copy by vertical/language, preserved each row's existing link slot, reset status counters only on changed rows, saved via `POST /broadcast/Messenger`, then ran approval again.

Validated result in-session:

```text
Templates processed: 11/11
Messages replaced: 194
POST update: 11x HTTP 201
Run Approval: 11x HTTP 202
Readback: 11/11 digest OK with 20 messages
```

## Important distinction

The global rollout rule remains stricter: red-only replacement, gray hold/alert, purple diagnosis. This session's gray replacement was safe because it was an explicitly controlled one-page canary experiment ordered by Rodolfo.

Do not generalize gray replacement to global production templates unless Rodolfo explicitly authorizes it.
