# SMS Funnel Routing Reference

## Payload

Current MGS quiz funnels send only:

```json
{
  "name": "Lead Name",
  "phone": "11999999999"
}
```

Do not add UTMs or extra fields unless Rodolfo confirms SMS Funnel accepts them.

## Routing Source

Preferred resolution order:

1. Explicit `gestor_code` in request, if provided.
2. Parse gestor from `utm_medium`, e.g. `g003-s` → `G003`.
3. Parse gestor from quiz slug, e.g. `quiz-car-parcelas-g003` → `G003`.
4. If exactly one configured list exists, use it.
5. Fallback URL, only if configured.

## Status Semantics

- `ok:G003` — the SMS Funnel ingestion endpoint returned an application-level success for the G003 route. This is delivery-attempt evidence, not proof that the lead was persisted or is visible in the dashboard.
- `fail:500` / `fail:4xx` — HTTP failure from SMS Funnel.
- `error` — WordPress/network/WP_Error failure. A timeout is indeterminate: the vendor may still have processed the request, so reconcile by phone before classifying the lead as absent.
- `skipped` — no URL or sending intentionally skipped.
- `historical_import` — imported into WP reporting only; not sent to SMS Funnel.

The observed success response can expose the routed list as `lead.list_id`, not necessarily as a top-level `list_id`. Parse both shapes when validating the expected destination.

## Require SMS Success

When enabled:

- WP still saves the lead first.
- The frontend only confirms/redirects if the SMS Funnel endpoint returns application-level success.
- If SMS Funnel returns an explicit failure, the frontend shows an error and does not redirect.

This blocks known submission failures during cutover, but it does **not** prove downstream persistence or dashboard visibility. Reconciliation is still required when the business symptom is a missing lead.

## Diagnostic Standard

Always test both layers when the symptom is “I filled the quiz but the lead didn’t arrive”:

1. Direct REST/backend test — proves WordPress → SMS Funnel.
2. Browser/frontend submit — proves actual user flow.
3. DB query — confirms stored `sms_funnel_status` and response.
4. Compare returned `list_id` to the expected list.

If both direct and browser tests return `success:true`, escalate suspicion to SMS Funnel dashboard delay/cache/indexing/filter/deduplication.

## Read-only reconciliation: WordPress day × SMS Funnel dashboard

Use this sequence when Rodolfo asks which WordPress leads from a date are absent from SMS Funnel:

1. Resolve the date in the WordPress site timezone and query `mgs_quiz_leads` for the half-open interval `[00:00:00, next day 00:00:00)`.
2. Keep the full name/phone dataset in a mode-0600 temporary file; do not dump all PII into logs or chat.
3. Authenticate from the 1Password item `SMS Funnel Dashboard` using `POST https://web2.smsfunnel.com.br/api/login`; keep the bearer token only in process memory.
4. Enumerate dashboard lists with `GET /api/lists`. For each relevant list, export read-only with `POST /api/leads/export/<list_id>`. An empty list can return HTTP 404 instead of an empty CSV; treat that as empty only when the preceding `/api/lists` readback says `leads_count=0`.
5. Normalize Brazilian phones conservatively: remove punctuation; strip country code `55` only from 12/13-digit values, never from a normal 10/11-digit phone whose DDD is 55.
6. Compare current dashboard membership by normalized phone across the six quiz lists and then across every dashboard list. Keep date-specific dashboard counts separate from the membership answer because deduplication can leave a lead present with an older `Created` date.
7. For every candidate still absent, validate directly against every non-empty list with `GET /api/lists/<list_id>/leads?page=1&per_page=10&filter=<phone>`. Report a lead as absent only when exports and direct searches agree without request errors.
8. Reconcile duplicate WordPress submissions by unique phone, but preserve row count and timestamps so repeated submissions are not hidden.
9. Treat WordPress `ok:G00X` plus stored vendor `success:true` as delivery-attempt evidence, not dashboard-membership proof. If the lead is absent after the direct readback, report the inconsistency explicitly.
10. Delete temporary exports, credentials state, and PII files after producing the validated result.

## Metric distinction: missing dashboard leads vs unsent messages

Do not answer these as the same question:

- **Lead absent from the dashboard:** reconcile current list membership by phone. Unique-phone deduplication is appropriate only for this membership question.
- **Aggregate sent-volume gap:** compare WordPress report rows with SMS Funnel `/api/daily-sents` only after proving both dashboards use the same timezone, calendar window, account/list scope, and one-expected-SMS-per-row rule. A raw subtraction is not an exact lead cohort.
- **Exact unsent cohort:** fetch event rows with `GET /api/messages?date=YYYY-MM-DD&page=<n>&per_page=<n>` and include the next send day to catch delayed deliveries. Match each WordPress submission to a sent-message control using the vendor `lead.list_id`, normalized phone, the ingestion timestamp returned in stored `lead.created_at`, and the message control `created_at`. Reconcile timeout rows separately because the vendor may have processed them.

WordPress `created_at` is stored as UTC in the observed quiz table, while SMS Funnel daily/message dates are presented by the São Paulo calendar. Convert the business-day interval before comparing; otherwise the raw dashboards cover different three-hour boundaries. Also separate controls created on a prior day, controls from another source, and messages sent on the next day.

The aggregate difference answers only a net counter gap. It does not identify rows that can safely be exported or imported. A recovery list must be built from event-level unmatched submissions, and SMS Funnel list import will deduplicate repeated submissions down to contact-level phones.

### Event-preservation rule for Rodolfo's SMS audits

When Rodolfo asks for **envios**, messages, registrations, or a comparison Sheet, preserve occurrence-level cardinality:

- One registration/expected-send occurrence equals one row. If the same person or phone registered three times, keep three rows in source and difference outputs.
- Never deduplicate by phone unless Rodolfo explicitly asks for unique contacts. Normalizing a phone for matching must not collapse repeated occurrences.
- Do not suppress, merge, or refuse analytical rows because a future resend could be duplicated. Producing the audit does not authorize a resend; the decision to send belongs to MGS.
- For the WordPress tab, follow the user's explicit event definition. If Rodolfo says “every time the user registered,” include every `mgs_quiz_leads` occurrence in the business-day window regardless of repeated phone or `sms_funnel_status`. Filter to `sms_funnel_status LIKE 'ok:%'` only when he specifically asks for successful WordPress→SMS Funnel handoffs. Never silently replace “all registrations/expected sends” with an `ok`-only subset, and never label a handoff as proof of outbound SMS.
- For the SMS Funnel tab, use actual outbound message events from `/api/messages`, preserving every event.
- Build the difference as a multiset: match/consume at most one SMS event for each WordPress occurrence using normalized phone plus the strongest available list/timestamp evidence, and emit every unmatched WordPress occurrence with its original name and phone. Extra SMS events do not cancel unrelated unmatched WordPress rows.

If source semantics are ambiguous, state the distinction concisely, but do not change the requested occurrence-level scope on Rodolfo's behalf.

## Execution posture for direct recovery-list requests

When Rodolfo directly instructs creation/import of a recovery list, do not turn the task into a routine approval loop. Reconcile the event-level cohort and platform deduplication first, then execute the exact verified scope without extra confirmation when it matches the request.

If the requested quantity is only an aggregate dashboard subtraction and does not identify that many real contacts:

1. Own any earlier mislabeling immediately.
2. State the verified event count and importable unique-phone count in one concise block.
3. Do not fabricate, pad, or arbitrarily select contacts to reach the aggregate number.
4. Ask only the single scope-changing question genuinely required by the mismatch; do not debate the instruction or repeat a long rationale.
5. If Rodolfo explicitly authorizes an arbitrary selection despite the mismatch, record that changed selection rule and execute it as instructed, while keeping the list unattached to automation unless sending was also authorized.
