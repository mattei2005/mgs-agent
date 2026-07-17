# Openzed — Auto Principal Drip baseline

> Live read-only observation from 2026-07-16. Treat as a regression baseline, not permanent production truth; re-read the live builder before every operational conclusion or write.

## Access context

- DigitalTRChat account item: `Digitaltrchat - Disparos Openzed US-CC-EN`
- 1Password vault: `MGS Conteúdo`
- Login fields: `username` + concealed `credential` (fallback to `password` for other items)
- Page: `Hortensia Martínez`
- Internal DigitalTRChat page ID: `1084`
- Facebook Page ID observed in UI: `414945241702253`
- Flow: `Auto Principal Drip`

## Scope rule — active

For this Openzed account/page, the operational scope is **only** `Auto Principal Drip`.

Ignore these legacy automation flows completely unless Rodolfo explicitly reopens one of them in a future request:

- `BD 20 part 1`
- `BD 20 part 2`
- `BD 20 part 3`

They were prior automations that MGS will not use. Do not inspect, compare, edit, include in routine reports, or treat them as relevant alternatives merely because they remain visible in the Bot flow builder list.

## Historical baseline — before Rodolfo's M16 demonstration

- 82 nodes, all 82 reachable, no disconnected nodes
- Types: 32 `Text`, 17 `Button`, 16 `New Postback`, 15 `Sequence Single`, 1 `New Sequence`, 1 `Start Bot Flow`
- Sequence window: `00:00–24:00`, timezone `America/New_York`
- Promotional delays: 1m, 3m, 7m, 10m, 30m, 1h, then 3h through 11h
- Entry path: English greeting → `✔️ CONTINUE` → postback `Auto Principal Drip`
- The postback fans out to an immediate English offer and the timed M01–M15 sequence
- Immediate CTA: `✔️ ACCEPT CREDIT CARD` to `fineasier.com`
- Timed CTAs: 15 unique URLs on `tarjeta.openzed.com`, with `utm_content=drip_us_cc_m1-1` through `m15-1`

## Active readback — after Rodolfo's saved M16 demonstration

Rodolfo cloned M15 into M16 and used the global Save during his 2026-07-16 teaching video. Zeus reconciled this as an authorized concurrent change and re-read the live graph afterward:

- 87 nodes, all 87 reachable, no disconnected nodes;
- types: 34 `Text`, 18 `Button`, 17 `New Postback`, 16 `Sequence Single`, 1 `New Sequence`, 1 `Start Bot Flow`;
- M16 exists as a five-node cloned branch;
- M15 and M16 both use an 11-hour Sequence item;
- M16 inherited M15's message, button label and URL;
- M16's URL still carries `utm_content=drip_us_cc_m15-1`.

The 82-node state is historical and no longer active. Do not create another M16 on page 1084. This demonstration did not convert the legacy flow to the canonical 28-message schedule.

## Review findings to re-check live

- **Legacy language mixing is expected:** historically MGS did not separate EN and ES flows/pages consistently. Therefore an account/page labeled `US-CC-EN` may legitimately contain Spanish timed messages or Spanish UTM naming inherited from the older setup. Do not classify this fact alone as an anomaly or current configuration error. Newer operations are separated more carefully, but legacy pages can remain mixed unless Rodolfo explicitly requests a cleanup/migration.
- After the demonstrated clone, sixteen message nodes contained zero-width Unicode formatting characters (15 original plus cloned M16 text).
- M04 used `#LEAD_USER_LAST_NAME#`; most other messages used `#LEAD_USER_FIRST_NAME#`.
- Visible copy issues included `Chooce`, `asta` where `hasta` was expected, and `sóle`.
- Advertised limits varied from roughly `$8,700` to `$16,000`.
- Builder node metrics displayed zeroes; this view alone does not prove zero production traffic.

## Safety evidence

The list row exposed adjacent actions:

- Safe open: `a[title="Edit"].btn-outline-warning`, href containing `/visual_flow_builder/edit_builder_data/`
- Destructive action: `a[title="Delete"].delete_data.btn-outline-danger`, trash icon

Always identify the exact row by flow name and enforce these predicates. Never click by visual position.
