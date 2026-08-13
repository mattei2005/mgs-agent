# UTM-medium-only migration and exact DTR login resolution

Use this procedure when Rodolfo authorizes changing only `utm_medium` on an existing DigitalTRChat Page while preserving host, path, all other UTM fields, messages, topology, scheduling, button configuration, and identifiers.

## Exact-login prerequisite

- Treat the supplied login as an exact identity boundary; never substitute a near-match with a missing/extra suffix.
- Refresh the 1Password metadata lookup before concluding a newly added login is absent.
- The shared DTR resolver currently builds its username map from item titles containing `digitaltrchat`. A newly added exact credential under a generic title may therefore exist in 1Password but not appear in that map.
- If the refreshed map misses the login, enumerate vault items and inspect only username/email fields in memory to find an **exact** username match. Require exactly one match, then fetch that item by ID and re-check its username before login. Do not expose the credential or persist its value.
- If zero or multiple exact matches remain, stop. Do not use a similarly named site/vertical item.

## Narrow pre-write gate

1. Confirm the exact login, imported account/segurador, Page name, internal DTR Page ID, and Facebook Page ID.
2. Open the exact `Auto Principal Drip` using the yellow Edit action and read the live graph.
3. Read Get Started independently and require its hidden `page_table_id` and `page_id` to match the target Page.
4. Inventory every HTTP URL carrying `utm_medium` in the graph. For a homogeneous-medium request, require all tracked graph URLs and Get Started to equal the expected before-medium. Mixed media fail closed unless Rodolfo explicitly scopes the mixed case.
5. Freeze a Page-level backup containing the raw graph, Get Started before-state, target identities, and editor routes.

## Safe replacement

- Replace only the value of the existing `utm_medium` query parameter. Preserve the delimiter and every other byte of the URL, including literal `#PAGE_ID#` and any platform-added subscriber suffix.
- Walk only HTTP URL strings in node data; do not perform a blind replacement over serialized graph JSON or unrelated text fields.
- Count changed URL occurrences dynamically. Do not hardcode Button versus Generic Template counts.
- Save the Flow Builder once, reload, and verify the exact occurrence count moved from the before-medium to the after-medium.
- Update Get Started through its normal editor and `Update`, then reload and verify identity plus the new medium.

## Structural verification

Before and after, compare:

- node count;
- edge count;
- total HTTP URL count;
- tracked `utm_medium` occurrence count;
- a normalized graph hash that replaces only the authorized old/new medium value with one sentinel and excludes runtime-only `labelIdTexts`.

The normalized hash must remain equal. This proves the only graph delta is the authorized medium value while preserving messages, topology, delays, images, button fields, paths, and other query parameters.

Finally, open a fresh authenticated browser context and repeat identity, graph, medium-count, and Get Started checks. Report success only when this independent readback passes. Keep the backup as rollback material.

## Validated production shape

A production Page was migrated from one homogeneous medium to another across Get Started plus 43 tracked URLs in a 147-node/146-edge graph. Both saves returned HTTP 200; immediate reload and fresh-session readback confirmed all 43 graph URLs plus Get Started carried the new medium, with identical normalized graph hash and unchanged node/edge/HTTP counts.
