## Approved/Rejected Message Bank

Rodolfo correction 2026-07-07: Utility approval work must maintain a durable message bank so Zeus does not lose track of which copies were approved/rejected across canaries and production templates. Do not rely only on per-run work artifacts. This bank is not just for the current canary: it is the long-term source of memory for future real/active template replacements, so every check, approval, rejection, replacement, reuse, and production rollout must read/update it first. Detailed reference: `references/utility-message-bank-and-canary-loop-2026-07-07.md`.

Canonical files:

```text
/root/mgs-agent/data/utility-message-bank.json
/root/mgs-agent/data/utility-canary-approval-state.json
```

`utility-message-bank.json` is the durable copy registry. Track each unique message by a stable `text_cta_hash` using normalized visible `TEXT + CTA_1` (do not include `LINK_1`, because links are template/page-specific slots). Minimum fields per record:

```json
{
  "text_cta_hash": "sha256",
  "vertical": "US-CC-EN",
  "country": "US",
  "language": "EN",
  "text": "...",
  "cta_1": "...",
  "first_seen_at": "ISO ET",
  "last_seen_at": "ISO ET",
  "first_approved_at": "ISO ET|null",
  "last_approved_at": "ISO ET|null",
  "approved_count": 0,
  "rejected_count": 0,
  "gray_count": 0,
  "purple_count": 0,
  "status": "approved|rejected|testing|diagnostic",
  "seen_in": [
    {"template":"...", "message_id": 3, "page_name":"...", "fb_page_id":"...", "observed_color":"verde", "observed_at":"ISO ET"}
  ]
}
```

`utility-canary-approval-state.json` is volatile loop state for the current 3-hour canary runner. Track by `template + MESSAGE_ID`, with fields:

```json
{
  "template": "Teste-US-CC-EN-...",
  "message_id": 1,
  "text_cta_hash": "sha256",
  "ever_green": true,
  "gray_attempt_count": 0,
  "last_color": "verde|cinza|vermelho|roxo",
  "replacements_done": 0,
  "approval_runs": ["ISO ET"]
}
```

Rules:

0. Before any template check, replacement, production rollout, or message generation, load `utility-message-bank.json` and use it as the source of operational history.
1. Every readback of canary/template approval statuses must upsert the message bank before deciding replacements.
2. Green updates `first_approved_at`/`last_approved_at`, increments `approved_count`, and sets `status=approved` unless the record already has red history, in which case keep `mixed_history`.
3. Red increments `rejected_count` and updates the same message record; do not create a separate disconnected record for the same `TEXT+CTA`. If a previously approved message later turns red, keep the full history (`approved_count` + `rejected_count`) and mark the record as `mixed_history` / `needs_review` rather than forgetting prior approval.
4. Gray increments `gray_count` only and must not erase an approved/mixed status.
5. Purple increments `purple_count`. If `approved_count > 0` and `rejected_count == 0`, preserve ever-green eligibility as `approved_diagnostic`; otherwise use `diagnostic`. Purple is not proof of copy rejection.
6. Replacement candidate selection should prefer the same vertical/language/country with `approved_count > 0` and `rejected_count == 0`, including `approved_diagnostic`, and must skip `TEXT+CTA` already present in the target template.
7. Do not generate or install new messages blindly when the bank already has enough approved candidates for the same vertical/language/country.
8. Do not reuse a message in a target if the bank says it is rejected for that same vertical/context unless Rodolfo explicitly chooses to retest it.
9. Record usage history every time a message is installed: template, message slot, page/template context, link slot preserved, timestamp, and whether it was canary or production.
10. Never let a temporary canary state file be the only source of known approvals; sync every green/red/purple observation into `utility-message-bank.json`.

## Pending Template Utility10 Conversion

When Rodolfo identifies Broadcast Templates that were not included in an existing Utility rollout, treat them as pending migration targets:

1. Do not rework schedules if the schedule step was already completed; schedule updates and message-bank conversion are separate phases.
2. Convert each target to exactly **10 Utility-style messages**.
3. For CC templates, use the known-approved Utility copy structure from the already-converted 10→20 templates and translate/adapt to the template language/country. Preserve commercial intent and Utility/status framing.
4. Preserve the target template's existing `LINK_1` sequence exactly for the first 10 slots. Never invent or normalize URLs.
5. If a Page row's `COUNTRY` conflicts with the template name/code, route language/timezone/content decisions by the **template code** (`DE-CC-DE`, `MX-CC-ES`, etc.), not the Page row country.
6. Trigger `Run Approvals` after installing the 10-message bank, then close/save the template flow correctly and validate via readback.
7. Add the converted templates into the same recurring rollout tracker/process as the original Utility templates so they continue through status monitoring, replacement of bad rows, and 10→20→30→40→50 progression.

Approval ETA after Utility10 uses Ciro's rule: `pages × 10 messages × 8s`. Templates with no linked Pages can be converted and tracked, but have no meaningful approval ETA until Pages exist.

See `references/pending-template-utility10-rollout-2026-07-02.md` for the session-specific pending-template workflow and validation expectations.

