# SB Broadcast Template API + Utility Approval Workflow (2026-06-29)

## Context

Rodolfo explained the operational purpose of mapping `Messenger > Broadcast Template`: use the current template inventory to plan Utility approval and later replace messages in real production templates by vertical/country/language.

## Confirmed runtime/API behavior

While logged into the SB dashboard as the Zeus session, the Broadcast Template table calls:

```text
https://api.jbfdigital.com.br/broadcast/Messenger?companies[]=digital-trust&companies[]=digital-trust-2&source=Messenger
```

The response is JSON and includes backend fields that may not all be visible to every UI viewport/user view:

```text
ID
NAME
MESSAGES
COMPANY
PUBLISHER_ID
LANGUAGE
UTM_CONTENT_MASK
PAGES
LEADS
```

Important: `LEADS`, `PAGES`, and `MESSAGES` are backend-provided values, not Zeus-calculated values.

The UI table for Zeus rendered these columns:

```text
COMPANY
DOMAIN
LANGUAGE
NAME
MESSAGES
LEADS
PAGES
APPROVAL
```

Rodolfo's own UI screenshot only showed through `MESSAGES`; treat `LEADS/PAGES` as backend/API-derived and not necessarily visible in every UI layout.

## Auth/API caveat

This is an internal authenticated API, not a public/open API contract.

- Direct unauthenticated/request-context calls returned `401 Unauthorized`.
- Browser `fetch()` may fail from CORS if not executed with the same runtime context/header behavior.
- The SPA uses an authorization header internally; never print or persist that token.
- If probing API endpoints, capture only status/count/keys/sample non-secret fields.

## Company scope observed

Endpoint `/company` returned only the companies visible to Zeus:

```text
digital-trust   — Digital trust
digital-trust-2 — Digital trust 2
```

Candidate company names like `jbf`, `jbfdigital`, `smartbidding`, `smartbiddingdigital`, `sb`, `legacy`, and `mgs` did not appear in the Zeus-visible company scope.

The `/broadcast/Messenger` endpoint appeared to fall back to the authorized company scope even when invalid `companies[]` values were supplied, returning the same `digital-trust/digital-trust-2` rows. Do not interpret that as those candidate companies existing.

## Utility approval workflow explained by Rodolfo

High-level process:

1. Create a new template in SB for one vertical/country/language combination, e.g. `US-CC-EN`, `GB-CC-EN`, `AR-CC-ES`, `ZA-CC-EN`.
2. Put the candidate messages into that new template.
3. Link that template to one canary domain/page.
4. Open template edit and click `Run Approval`.
5. Ciro's backend submits the messages to Meta/Facebook; approval result returns in roughly 5–10 minutes.
6. If canary approval succeeds, replace the messages in the real production template for that vertical/country/language.
7. At midnight, Ciro's scheduler reads the production template linked across all pages and submits/uses the approved Utility messages across the page set.

Operational interpretation:

- New/canary template = approval bench.
- Existing production template = high-impact target to edit only after canary success.
- Editing messages changes hash/approval state; never change production template messages without explicit Rodolfo instruction naming the target template and approved message lot.
- First automate one template replacement end-to-end, validate, then scale by vertical.

## Replacement safety checklist

Before replacing messages in an existing template:

1. Confirm exact template name and vertical/country/language.
2. Confirm exact approved message lot/CSV/Sheet tab.
3. Export/read current template messages as backup.
4. Dry-run compare: message count, IDs, text, CTA, links, image/text2 fields.
5. Apply only after explicit permission to save/update.
6. Validate readback in UI/API: count, sample rows, emojis/encoding, CTAs, links.
7. Report whether approval/hash was reset or preserved, based on SB behavior observed.

## Redaction rule

The `/company` endpoint can include sensitive nested publisher data (panel/VPS/WordPress fields). Never paste raw `/company` JSON into chat or logs. Summarize only non-secret company IDs/names/counts unless Rodolfo explicitly asks for an internal file audit, and still redact credentials.
