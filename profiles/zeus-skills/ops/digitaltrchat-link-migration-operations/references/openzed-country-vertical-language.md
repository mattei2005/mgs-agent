# Openzed country/vertical/language reference

## Page-level classification

Classify from a live pre-write URL's `utm_term` and corroborate with `utm_content`:

- `openzed-us-cc-en-dp` → `US-CC-EN`
- `openzed-card-us-cc-en-funil` → legacy `US-CC-EN`
- `openzed-gb-cc-en-dp` → `GB-CC-EN`
- `openzed-us-cc-es-dp` → `US-CC-ES`
- `openzed-es-cc-es-dp` → `ES-CC-ES`

If neither exact term nor an unambiguous equivalent exists, stop. Do not classify from the DTR login. The canonical replacement catalog omits `utm_term`, so save the classification evidence in the pre-write backup.

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

## Surface-specific preservation

- Flow graph URLs observed in the pilot did not contain `#SUBSCRIBER_ID_REPLACE#`; use the exact canonical catalog string when the pre-write value also lacks it.
- Get Started and No Match fields observed in the pilot already ended with `&subscriber_id=#SUBSCRIBER_ID_REPLACE#`; preserve that suffix while replacing the canonical base URL.
- Persistent Menu items observed in the pilot lacked subscriber tracking; use canonical M0 without inventing a suffix.
- These observations are not universal defaults: preserve each live field's placeholder behavior and validate the submitted readback.

## `#PAGE_ID#` parser pitfall

`urllib.parse.urlparse` and browser URL parsers treat `#PAGE_ID#` as a fragment delimiter. A naive query validation falsely reports missing `utm_campaign`/`utm_content`.

Safe validation:

1. require exactly one literal `#PAGE_ID#` in the original;
2. replace the complete placeholder with `PAGE_ID_PLACEHOLDER` in a temporary copy;
3. parse and validate the temporary copy;
4. compare/save the untouched original string.

## Read-only pilot discovery — 2026-07-21

The requested pilot was up to two Pages in each of four DTR logins. Prerequisite discovery found:

- `Hortensia Martínez`, DTR `1084`: `US-CC-EN`; 147/147 nodes reachable; 29 HTTP destinations, M0 plus M1–M28.
- `Marlowe Curtis`, DTR `3351`: legacy `US-CC-EN`; 82/82 nodes reachable; 16 HTTP destinations, M0 plus M1–M15.
- `Luisa Gallardo`, DTR `22273`: `ES-CC-ES` from `utm_term`, despite residing in the US-CC-ES-named DTR login; 147/147 nodes reachable; 29 HTTP destinations.
- `Rosalind Montague`, DTR `22097`: only Page in the GB login; no Flow Builder rows and no `Auto Principal Drip`.
- `Lucia Sánchez`, DTR `22094`: only Page in the Spain login; no Flow Builder rows and no `Auto Principal Drip`.

The two ineligible Pages demonstrate that missing flow is a prerequisite failure, not permission to install one. The legacy Marlowe flow demonstrates that link replacement must not become a topology migration.

No production write occurred during this discovery. Rodolfo was asked to authorize the reduced three-Page scope before mutation.