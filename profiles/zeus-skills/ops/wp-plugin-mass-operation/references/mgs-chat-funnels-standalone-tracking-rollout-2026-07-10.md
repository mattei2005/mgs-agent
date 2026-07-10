# MGS Chat Funnels — standalone tracking rollout (2026-07-10)

Use this reference when moving multiple installed `MGS Chat Funnels` routes from WordPress-global rendering to plugin-owned standalone rendering with editable GTM/GA4 fields.

## Scope discipline

- “Todos os sites” means only sites where `mgs-chat-funnels` is already installed unless Rodolfo explicitly authorizes a new installation project.
- Audit the technical inventory first. In the 2026-07-10 rollout, 8 installations were targets and 24 sites were explicitly excluded because the plugin was absent.
- CAR and EMP are independent configs. Validate both even when they share one WordPress installation.
- Never copy a canary JSON across sites. Add only `standalone`, `tracking_mode`, `gtm_container_id`, and `ga4_measurement_id`; preserve routes, offers, tags, provider, company and ad domain.

## Canonical provider matrix

The canonical package must preserve all three provider branches:

1. **JBF:** `gpt.js`, `window.tags`, one `digital-trust_* .builder.js`, JBF rewarded preload/show.
2. **ActView/Zuout:** `scr.actview.net/zuout.js`, `av-rewarded`, anchor CTA contract, `zout_rewarded` close callback and `#zout_top_wrapper > #zout_top`. No JBF wrapper.
3. **M2/Wantabrand:** `c.pubguru.net/pg.wantabrand.js`, `pg-rewarded`, PubGuru top slot and no JBF/ActView loader.

A common package that lacks any active branch is not deployable across providers. Version `0.3.23` was the first validated common merge of standalone tracking + JBF + ActView + M2.

## Build and focused tests

Before deployment:

- synchronize the plugin header version and `MGS_Chat_Funnels::VERSION`;
- `php -l` the main plugin;
- `node --check assets/chat-funnels.js`;
- parse every live config JSON;
- render JBF, ActView and M2 locally through a WordPress-stub harness;
- assert standalone calls zero `wp_head`, `wp_body_open` and `wp_footer` hooks;
- assert admin step 3 renders `standalone`, `tracking_mode`, `gtm_container_id`, and `ga4_measurement_id` for every provider;
- assert direct GA4 mode never loads GTM.

Provider-specific HTML checks:

- JBF: GTM 1, GPT 1, wrapper 1, button CTA, no ActView/M2.
- ActView: GTM 1, ActView 1, JBF 0, anchor CTA with `av-rewarded`, `zout_top` present after the in-chat ad step.
- M2: GTM 1, PubGuru 1, GPT/JBF/ActView 0, `pg-rewarded`, PubGuru top-slot code present.

## Backup and deployment

- Create a complete local tar backup per plugin installation.
- On RunCloud, also create `mgs-chat-funnels.zeus-bak-<timestamp>` beside the live plugin before writing.
- Deploy only the three canonical code files (`mgs-chat-funnels.php`, `templates/ciro-index-template.html`, `assets/chat-funnels.js`) plus individually prepared config files.
- Check live file hashes against the backup before the first write; stop on drift.
- Use the correct owner: `runcloud` or `runcloud2`.
- On Bitnami, use WordPress Plugin Editor safety checks for code/template/JS and the plugin raw-JSON form for configs; validate every file by readback. SFTP is read-only and is used for backup/readback only. Never use WPCode for this rollout.

## Canary sequence

Use one canary per provider before the broad batch:

- JBF: Cliquet;
- ActView: Zuout CAR;
- M2: Wantabrand.

Only advance when the canary confirms HTTP 200, correct provider loader, zero unrelated WordPress assets, one GTM source, one real GA4 `page_view`, working gate/chat and no unresolved JS errors.

## Runtime validation

For every CAR and EMP route:

- HTTP 200 with cachebuster;
- no unresolved `{{...}}` placeholders;
- no `/wp-includes/`, theme, CF7 or Yoast assets;
- GTM script 1 + noscript 1;
- actual GA4 `g/collect ... en=page_view` with the expected measurement ID;
- correct provider loader exactly once;
- admin config readback confirms standalone + GTM fields;
- plugin version and hashes match the canonical package.

Known observations from the validated rollout:

- Newsoun and Zuout EMP had duplicate ad stacks before standalone; standalone reduced each to one provider stack.
- `finance.topfeed.fun` intentionally had different effective JBF domains between CAR (`topfeed`) and EMP (`finance`); preserve per-chat behavior instead of normalizing silently.
- Wantabrand WP-CLI can emit the known `yoast-rest-meta.php` permission warning without blocking the plugin operation; report it.
- Browser automation may receive a PubGuru CAPTCHA on Wantabrand. Validate loader, `window.pga`, GTM/GA4 and static flow; do not attempt to solve the CAPTCHA.
