# UTM-medium-only migration and exact DTR login resolution

Use this procedure when Rodolfo authorizes changing only `utm_medium` on an existing DigitalTRChat Page while preserving host, path, all other UTM fields, messages, topology, scheduling, button configuration, and identifiers.

## Exact-login prerequisite

- Treat the supplied login as an exact identity boundary; never substitute a near-match with a missing/extra suffix.
- Refresh the 1Password metadata lookup before concluding a newly added login is absent.
- The shared DTR resolver currently builds its username map from item titles containing `digitaltrchat`. A newly added exact credential under a generic title may therefore exist in 1Password but not appear in that map.
- If the refreshed map misses the login, enumerate vault items and inspect only username/email fields in memory to find an **exact** username match. Scan all vault item categories, not only `LOGIN`: DTR credentials may be stored as `API_CREDENTIAL`. Require exactly one match, then fetch that item by immutable ID and re-check its username before login. Do not expose the credential or persist its value.
- If zero or multiple exact matches remain, stop. Do not use a similarly named site/vertical item.

## Narrow pre-write gate

1. Confirm the exact login, imported account/segurador, Page name, internal DTR Page ID, and Facebook Page ID. For a site/template-wide reassignment, first derive the population from live SB template IDs and Page rows, then resolve each Page's real DTR container; a brand login is not the batch boundary.
2. Open the exact `Auto Principal Drip` using the yellow Edit action and read the live graph when it exists.
3. Read Get Started and No Match independently and require their hidden `page_table_id` and `page_id` to match the target Page. Inspect every existing Persistent Menu editor as a separate surface.
4. Inventory every HTTP URL carrying `utm_medium` across the graph, Get Started, No Match and Persistent Menu. For a homogeneous-medium request, require every tracked value to equal the expected before-medium. Mixed media fail closed unless Rodolfo explicitly authorizes changing every current medium to the new value.
5. Freeze a Page-level backup containing the raw graph, both action before-states, Persistent Menu fields, target identities and editor routes.
6. Treat missing surfaces as absence, never as permission to create them. If all four surfaces are absent or contain zero scoped URLs, record `zero_surface_validated`, perform zero writes and keep the Page in the disposition partition.

## Safe replacement

- Replace only the value of the existing `utm_medium` query parameter. Preserve the delimiter and every other byte of the URL, including literal `#PAGE_ID#` and any platform-added subscriber suffix.
- Walk only HTTP URL strings in node data; do not perform a blind replacement over serialized graph JSON or unrelated text fields.
- Count changed URL occurrences dynamically. Do not hardcode Button versus Generic Template counts.
- Save the Flow Builder once, reload, and verify the exact occurrence count moved from the authorized before-medium set to the after-medium.
- Update Get Started and No Match through their normal editors and `Update`; update each existing Persistent Menu through its normal `Submit`. Reload every changed surface and verify Page identity plus the new medium.
- When an error occurs after a possible save, read back that surface before retrying or rolling back. Mark a surface as written before submitting so an ambiguous post-save failure enters reconciliation instead of being silently omitted from rollback.

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
