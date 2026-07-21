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

Use `scripts/openzed_link_catalog.py` to generate and validate exact destinations. Do not manually interpolate country/language strings in production.

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
- Get Started editor: `/messenger_bot/edit_bot/<setting_id>/1/getstart`
- No Match editor: `/messenger_bot/edit_bot/<setting_id>/1/nomatch`
- Persistent Menu list: `/messenger_bot/persistent_menu_list/<DTR_PAGE_ID>/1`
- Persistent Menu editor: follow the exact `Edit persistent menu` link; its setting ID differs from the DTR Page ID

Never click `Reset all action button settings to default`, `Install template`, `Delete`, `Remove persistent menu`, or `Publish persistent menu` as part of URL replacement.

## Surface-specific URL contract

- Use the exact canonical catalog URL for every migrated surface and semantic position.
- Do not preserve or append legacy `#SUBSCRIBER_ID_REPLACE#` suffixes in Get Started, No Match or other URL fields; Rodolfo confirmed they are unnecessary for this Openzed migration.
- Preserve the literal `#PAGE_ID#` exactly as present in the canonical catalog.
- Flow Builder, Get Started, No Match and Persistent Menu therefore converge on the same exact catalog representation for M0/NM/M1–M28, according to each surface's semantic position.
- Do not add any parameter absent from the approved catalog.

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