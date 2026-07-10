# Template Canary → Production Replacement → Diagnosis Plan — 2026-07-07

Source: Rodolfo + Felipe Vidal operational plan, confirmed in Zeus thread 1522619776072155347.

## Context

DTR/SB page reconciliation is paused pending partner review. The active workstream shifts to Messenger Utility/Broadcast Templates.

## Phase 1 — Canary template per vertical

Create **1 test template per vertical/language/country**, for example `US-CC-EN`.

For each vertical:

1. Choose **1 known-good page** that is currently OK and sending messages.
2. Create/link the canary template to that one page only.
3. Put the **20 messages** for that vertical into the canary template.
4. Send/run approval.
5. Iterate message replacement until the approval/status bar is **100% green** for all messages in the canary.

Rationale: one page makes the approval loop fast; the goal is to validate the message bank without page-scale noise.

## Phase 2 — Replace current production templates

After the canary is all green:

1. Update the current/production templates with the corrected approved messages.
2. Preserve template routing, page bindings, and link sequences unless Rodolfo explicitly asks to alter them.
3. Let Ciro's system read the templates again at midnight ET and send the messages to the pages.

## Phase 3 — Next-day status analysis

Analyze the following day which templates/messages still show:

- gray/no-status;
- red/rejected;
- purple/invalid/error.

Do not collapse these statuses into a single "bad message" bucket. Each color can imply a different root cause.

Purple is especially diagnostic: if a canary-approved template turns purple when linked to production pages, the issue may be a page/app/segurador verification blocker rather than copy quality.

## Phase 4 — Remediation and future cron policy

After root cause is understood:

1. Fix the problematic page when it is recoverable.
2. Or block/disable the page in the dashboard when it is causing template verification problems.
3. Define/update the cron policy for future cases so purple/gray/red handling is automated only after the diagnosis rule is clear.

## Guardrails

- Phase 1 is canary-only and should be fast because it uses one known-good sending page per vertical.
- Phase 2 should not start for a vertical until its canary messages are 100% green.
- Do not auto-rewrite purple globally; investigate linked pages first.
- Do not auto-block pages until the status behavior is confirmed by next-day evidence.
- Keep DTR/SB reconciliation paused separately; template work is its own stream.
