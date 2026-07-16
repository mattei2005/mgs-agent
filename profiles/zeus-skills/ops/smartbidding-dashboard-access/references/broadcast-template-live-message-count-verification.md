# Live verification — Broadcast Template message counts

Use this when Rodolfo asks whether the “templates de broad/broadcast” are currently at 20 messages.

## Interpretation

- Treat “templates de broad” as `Accounts > Messenger > Broadcast Template`, not as template names containing the word `broad`.
- For the MGS production rule, evaluate templates with live Broadcast Template `PAGES > 0`.
- Expected state: linked templates have 20 active messages; unlinked templates normally have 10, but test/legacy/`NAO USAR` rows may retain larger banks and should not distort the linked-template answer.

## Required live check

1. Capture the frontend `GET /broadcast/Messenger` response using the authenticated SPA session.
2. Confirm the request scope contains both:
   - `companies[]=digital-trust`
   - `companies[]=digital-trust-2`
3. Parse `MESSAGES` when it is a JSON-encoded array and count the decoded entries.
4. Partition rows by Broadcast Template `PAGES > 0` versus `PAGES == 0`.
5. For linked rows, report:
   - total templates;
   - count at 20;
   - exact exceptions with template name, message count, and linked-page count.

## Reporting shape

Answer yes/no first. If there is drift, use the compact form:

- `X de Y templates com páginas: 20 mensagens`
- exception: template name, actual message count, linked pages

Do not claim all are at 20 from tracker state, cached JSON, or the configured target alone. Runtime `/broadcast/Messenger` readback wins.

## Durable lesson from 2026-07-16

A literal name search for `broad` returned no rows even though Broadcast Template contained the relevant inventory. The correct semantic interpretation was the tab/entity plus `PAGES > 0`, not a substring in `NAME`.
