# Smart Routing destination preflight for DTR migrations

Use this procedure when legacy/Keitaro destinations in DigitalTRChat will be replaced by an existing Smart Bidding Smart Routing family. This is a read-only qualification step; it does not authorize creating pools, changing DNS, or writing DTR.

## 1. Freeze the Page population and destination authority

1. Freeze every candidate as `login + imported account ID/name + DTR Page ID + Facebook Page ID + Page name + current legacy family`.
2. Classify each Page from the approved Page-level source. Keep `confirmed`, `corroborated_not_authoritative`, `conflict`, and `unresolved` disjoint. Only confirmed Pages enter the catalog plan unless Rodolfo explicitly resolves/overrides another class.
3. Freeze the authorized manager/medium per Page separately from the vertical. A URL migration preserves attribution unless Rodolfo explicitly changes ownership.
4. Partition every surface before confirmation: existing Auto Principal Drip, Get Started, No Match, Persistent Menu, and absent surfaces. Count current scoped URL occurrences dynamically.

## 2. Resolve the exact Smart Routing publisher

1. Use the authorized Smart Bidding identity whose live `GET /company` exposes the intended publisher. Do not substitute a similarly named publisher or infer access from another session.
2. Capture the exact `publisherId`. Query `POST /routing` with only the selected publisher IDs.
3. Filter the candidate family by all metadata dimensions: `DOMAIN`, `SOURCE`, `COUNTRY`, `VERTICAL`, `LANGUAGE`, `MEDIUM`, and the exact pool-name family. Do not merge normal and `finanzas` publishers merely because the brand is shared.

## 3. Prove semantic catalog completeness

1. Parse `ROUTES` from every pool in the family and unite them by identity.
2. Derive the semantic label from `utm_content`, not from pool order or a normalized route string.
3. A complete Drip catalog requires exactly one each of `m0`, `nm`, and `m1–m28`—30 unique labels—with no blank, missing, duplicate, or extra identity.
4. Require every route to have a non-empty `route`, non-empty `utm_content`, non-empty `jbf_operation`, `healthy=true`, and `freeze=false` unless Rodolfo explicitly authorized a temporary freeze.
5. Preserve each route path byte-for-byte from live readback. Historical paths can contain irregular prefixes, especially M0. Never “repair” the path by applying the dominant family naming pattern.
6. If any gate fails, stop the DTR migration. Creating or repairing Smart Routing pools is a separate production scope.

## 4. Resolve and verify the public routing host

`DOMAIN` and each route's destination `url` describe dashboard ownership and final content; neither proves the public redirect hostname.

1. Resolve the public Smart Routing hostname from the canonical domain configuration or an already-proven live route.
2. Test representative M0, NM, and M28 URLs with HTTP redirects enabled.
3. Require a valid public response and a final destination consistent with the route's live `url` family.
4. A 404 on the destination domain does not invalidate the route when the dedicated Smart Routing subdomain succeeds; conversely, a healthy destination page does not prove the redirect host exists.
5. Creating a new router/subdomain requires separate confirmation for DNS/ingress plus pool creation. Do not imply that a DTR link-migration authorization covers those writes.

## 5. Materialize the Page-level catalog

For each Page and semantic position:

1. Use the exact confirmed public host plus the exact live route path for that semantic label.
2. Build only the approved canonical parameters, including `utm_source`, the Page-authorized `utm_medium`, literal `utm_campaign=pg_#PAGE_ID#`, and the matching `utm_content`.
3. Do not carry a legacy `utm_term` unless the approved destination catalog explicitly requires it.
4. Preserve `#PAGE_ID#` literally. For parsing only, replace it with a sentinel and validate the untouched source afterward.
5. Preserve existing flow depth: an M0–M15 Page receives only its existing positions; do not add M16–M28.
6. An absent flow remains absent. Existing-position migration may update authorized action surfaces but never installs Auto Principal Drip.

## 6. Confirmation freeze before any write

Before asking Rodolfo to confirm application, report one frozen plan that includes:

- requested, confirmed, conflict, unresolved, excluded, and unchanged Page totals;
- destination host/family and medium partition per cohort;
- complete Smart Routing route/operation/health/freeze evidence;
- Pages with and without each DTR surface;
- occurrence counts to change by surface;
- every omitted surface that would retain the legacy family;
- action-only Pages and exactly what can change on them;
- canary families, backup/rollback method, and independent readback.

Interpret `all Pages` as population scope only. A request for `Auto Principal Drip + No Match` excludes Get Started unless Rodolfo separately confirms it. Once he confirms, bind execution to that exact Page set, surface set, catalogs, and mediums; any later reduction or expansion needs a new confirmation.
