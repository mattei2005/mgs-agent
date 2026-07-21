# Openzed country/vertical/language reference

## Page-level classification

Canonical Openzed Page-classification source:

- spreadsheet: `openzed`;
- spreadsheet ID: `180vUUBqQOoJM1oHEAj1VBCA-OuLCfAHgz-aRND3cuik`;
- access: canonical MGS Service Account only;
- identity match: internal DTR Page ID, cross-checked by Facebook Page ID;
- destination fields: explicit `vertical`, `pais`, and `lingua`;
- eligibility fields: tab (`broad` versus `blocked e on hold`) plus row status.

A current explicit Rodolfo correction wins. Otherwise, use the exact spreadsheet row. Never classify from the DTR login, Page name, domain, current template assignment, or live/exported `utm_term`: Rodolfo confirmed that `utm_term` can contain human error. `utm_content` remains useful only for mapping a legacy URL to M0, NM, or the same-number M1–M28 position.

When the spreadsheet classification conflicts with a current URL or template, preserve both in the manifest, label the live value as legacy discrepancy, and select the replacement catalog from `vertical + pais + lingua`. If the row is absent, duplicated, ID-mismatched, or internally ambiguous, stop for reconciliation.

## Canonical catalog approved by Rodolfo — 2026-07-21

Every combination has exactly 30 URLs: M0, NM, and M1–M28.

- `US-CC-EN`: host `sr.openzed.com`; path prefix `op-us-cc-en-drip-`; content prefix `drip_us_cc_`
- `GB-CC-EN`: host `sr.openzed.com`; path prefix `op-gb-cc-en-drip-`; content prefix `drip_gb_cc_`
- `US-CC-ES`: host `srf.openzed.com`; path prefix `opf-us-cc-es-drip-`; content prefix `drip_us_cc_`
- `ES-CC-ES`: host `srf.openzed.com`; path prefix `opf-es-cc-es-drip-`; content prefix `drip_es_cc_`

For label `X`:

`https://<host>/<path-prefix><X>/?utm_source=facebook&utm_medium=g003-d&utm_campaign=pg_#PAGE_ID#&utm_content=<content-prefix><X>`

Labels: `m0-1`, `nm`, then `m1-1` through `m28-1`.

Use `scripts/openzed_link_catalog.py` to generate and validate exact destinations. Do not manually interpolate country/language strings or mutate query parameters ad hoc in production. The default is `utm_medium=g003-d`; use `--utm-medium g001-d` only for a Page set explicitly mapped by Rodolfo to gestor `g001-d`, and persist that per-Page override in the manifest.

### Explicit Ducapes gestor override — 2026-07-21

Rodolfo confirmed that the following DTR Pages under login `disparosducapesusccen@gmail.com` / segurador `Phong Huynh` belong to gestor `g001-d`: `19236`, `19221`, `8347`, `19193`, `19214`, `13931`, `11037`, and `19235`. Their classification remains `US-CC-EN`; only the catalog medium differs from the global default. Generate all M0/NM/M1–M28 targets for these exact Pages with `utm_medium=g001-d`. Do not generalize the override to other Pages merely because they are Ducapes or share a login label.

## DTR discovery details

A login may contain multiple imported Facebook accounts. Account switches use:

- selector: `a.account_switch[data-id]`
- endpoint: `POST /social_accounts/fb_rx_account_switch`, form field `id`
- reload `/messenger_bot/bot_list` after switching

Read current identity from:

- Page name/FB ID: Page's `a[href*="facebook.com/"]`
- DTR Page ID: `#bot_flow_settings[data-page-id]`

Useful routes:

- Flow manager: `/visual_flow_builder/flowbuilder_manager/<DTR_PAGE_ID>/1`
- Action settings: trigger `#action_button_settings` on `/messenger_bot/bot_list`
- Get Started editor: `/messenger_bot/edit_bot/<setting_id>/1/getstart`; active URL field `#text_with_button_web_url_1_1`; update control `#submit`
- No Match editor: `/messenger_bot/edit_bot/<setting_id>/1/nomatch`; active URL field `#text_with_button_web_url_1_1`; update control `#submit`
- Persistent Menu list: `/messenger_bot/persistent_menu_list/<DTR_PAGE_ID>/1`
- Persistent Menu editor: follow the exact `/messenger_bot/edit_persistent_menu/<setting_id>/1` link; its setting ID differs from the DTR Page ID; active URL field `#text_with_button_web_url_1`

The classic action editor may reorder options in hidden `*_post_id_*` selectors between loads and expose the first option as their DOM value even when the active button type is `web_url`. Do not classify that display-order delta as a stored postback mutation; validate the active template type and compare semantic, non-empty active fields plus the exact target URL.

Never click `Reset all action button settings to default`, `Install template`, `Delete`, `Remove persistent menu`, or `Publish persistent menu` as part of URL replacement.

## Surface-specific URL contract

- Use the exact canonical catalog URL as the input for every migrated surface and semantic position.
- Do not manually preserve or append a legacy `#SUBSCRIBER_ID_REPLACE#`; Rodolfo confirmed it is not required as migration input.
- DigitalTRChat's normal Get Started and No Match editors may append `&subscriber_id=#SUBSCRIBER_ID_REPLACE#` automatically on save. Accept that platform-enforced suffix only when the canonical base matches exactly; do not bypass the UI merely to remove it.
- Flow Builder button URLs, Generic Template `imageClickDestinationLink` URLs and Persistent Menu URLs must use the exact canonical string without an invented subscriber suffix.
- Preserve the literal `#PAGE_ID#` exactly as present in the canonical catalog.
- Do not add any other parameter absent from the approved catalog.

## Transactional batch write and verification

For a multi-Page migration, treat each Page as its own transaction:

1. Materialize a Page-specific manifest from the exact pre-write graph and settings; include DTR/FB identity, flow depth, every scoped field, before/after URLs, and hashes.
2. Back up Flow Builder, Get Started, No Match, and Persistent Menu before the first mutation on that Page.
3. Build the expected post-write Rete graph by changing only the manifest's URL fields. Before saving, require the editor dry-run JSON to equal that expected graph exactly.
4. Save and reload every surface, then open a fresh browser context for independent Page-level readback before advancing to the next Page.
5. If any surface or identity check fails, stop the batch and roll back only the current Page from its manifest; never stack corrective writes across later Pages.
6. Validate equal pre/post node count, reachability, connections, schedule, message/button/image data, and scoped URL count. A legacy M0–M15 Page remains M0–M15; absence of M16–M28 is an invariant, not a gap to fill.
7. In classic action forms, compare active semantic fields. Hidden inactive `*_post_id_*` selectors can expose a different first option after reload as catalog ordering changes; ignore that display-only delta only after proving the active button type remains `web_url` and all non-empty semantic fields are unchanged.

## `#PAGE_ID#` parser pitfall

`urllib.parse.urlparse` and browser URL parsers treat `#PAGE_ID#` as a fragment delimiter. A naive query validation falsely reports missing `utm_campaign`/`utm_content`.

Safe validation:

1. require exactly one literal `#PAGE_ID#` in the original;
2. replace the complete placeholder with `PAGE_ID_PLACEHOLDER` in a temporary copy;
3. parse and validate the temporary copy;
4. compare/save the untouched original string.

## Read-only pilot discovery — 2026-07-21

The requested pilot was two Pages with complete M01–M28 flows in each of four DTR logins. Complete Social Accounts/Page enumeration plus live graph inspection found:

- GB login: `Emily Watson` DTR `22040` and `Fiona Caldwell` DTR `22026`, both complete M01–M28. Spreadsheet classification: `GB-CC-EN`.
- Spain login: `Lucía Maldonado` DTR `22093` and `Paula Pacheco` DTR `22092`, both complete M01–M28. Spreadsheet classification is `ES-CC-ES` for Lucía and `US-CC-ES` for Paula; Paula's legacy current template/UTM disagreed with the sheet.
- mixed US login: `Hortensia Martínez` DTR `1084` had a complete flow but the spreadsheet places it in `blocked e on hold` with status `On-hold`, so it is no-write. `Lily Thompson` DTR `13828` had a complete `US-CC-EN` flow and remained in `broad` as Restricted Broadcast. A replacement for Hortensia still had to be selected.
- US-ES login: `Luisa Gallardo` DTR `22273` had a complete M01–M28 flow. Spreadsheet classification is `US-CC-ES`; the live legacy `utm_term=openzed-es-cc-es-dp` was a human-error discrepancy and must not drive the replacement catalog. The other eleven Pages under that segurador did not have a complete qualifying Auto Principal Drip at the time of inspection.

The discovery also corrected an early false negative: Bot Manager flow tables populate asynchronously, so a 500 ms read can incorrectly report no flow. Wait for the DataTable to settle or the exact flow text before concluding absence. The first visible Page card is not a complete account inventory; enumerate all Pages under the selected segurador and switch segurador when needed.

No production write occurred during this discovery.