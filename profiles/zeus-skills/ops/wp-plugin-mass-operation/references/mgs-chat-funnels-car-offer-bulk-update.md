# MGS Chat Funnels — CAR-BR offer copy/URL bulk update

Use when Rodolfo asks to swap the 3 final CAR chat offers across the already-installed `MGS Chat Funnels` sites without changing plugin code.

## Scope validated

Validated on mixed targets:

- RunCloud/WP-CLI writable config files: `zuout.com`, `zytiva.com`, `finance.topfeed.fun`, `newsoun.com`, `wantabrand.com`, `eggbev.com`.
- Bitnami/WP Admin raw JSON save: `openzed.com`, `cliquet.com`.

The target config is usually:

```text
wp-content/plugins/mgs-chat-funnels/configs/car-br-01.json
```

Public route:

```text
/chat/car/br1/
```

## Durable pattern

1. Treat this as a **config/content update**, not a plugin code deploy, unless JS/PHP behavior must change.
2. Start from the canonical local config at `/root/mgs-agent/plugins/mgs-chat-funnels/configs/car-br-01.json` to preserve schema, mode, gate, persona and ad wrapper settings.
3. For each site, update only:
   - `offers[N].messages`
   - `offers[N].target`
   - `offers[N].reject_label` only as needed; last sequential offer should normally have no reject label.
4. Preserve:
   - `mode: sequential`
   - `utm_passthrough: true`
   - `ads_enabled`, `ad_company`, `ad_domain`
   - route `/chat/car/br1`
5. Validate JSON before and after remote write.

## RunCloud write method

- Use the owning webapp user: `runcloud` vs `runcloud2`.
- Use `sudo -n` for file operations under `/home/runcloud*`. If direct SSH as `zeus` can read but cannot write the plugin config (`Permission denied`), run the remote updater itself with `sudo -n python3 -` rather than trying to write as the webapp user from an unprivileged shell.
- Source `/root/mgs-agent/.env` with `set -a` / `set +a` before calling `op` from a local helper script, so the 1Password service-account token is exported for subprocesses.
- Before overwrite, copy backup:

```text
car-br-01.json.zeus-bak-YYYYMMDD-HHMMSS
```

- For simple target URL swaps, a safe batch updater can load each JSON, update only `offers[0..2].target`, write a temp JSON, re-parse it, atomically replace the config, then `chown {user}:{user}` the config and backup.
- Validate plugin active before writing when using WP-CLI:

```bash
sudo -u {user} wp --path={path} plugin is-active mgs-chat-funnels --allow-root
```

- Validate JSON with PHP directly instead of fragile `wp eval` quoting:

```bash
sudo -u {user} php -r 'json_decode(file_get_contents($argv[1]), true, 512, JSON_THROW_ON_ERROR); echo "json_ok\n";' /path/to/car-br-01.json
```

This avoids quote/escape failures in `wp eval` when paths or string literals contain `/` and nested quotes.

## Bitnami/WP Admin method

For `openzed.com` / `cliquet.com`, if direct filesystem write is unavailable:

1. Login via `/rodloguda/` using the site’s `wordpress zeus` 1Password item.
2. Open:

```text
/wp-admin/admin.php?page=mgs-chat-funnels&funnel=CAR-BR-01
```

3. Extract `mgs_cf_nonce` and the current `<textarea name="raw_json">` content from the authenticated admin page.
4. POST raw JSON with:

```text
mgs_cf_action=save_raw
raw_json=<updated config>
```

5. Validate the save response contains `JSON salvo com sucesso` or equivalent success notice.
6. Re-fetch the admin page and parse `raw_json` again; verify the 3 saved `offers[N].target` values exactly match the requested URLs. A success notice alone is not sufficient.

A lightweight Python `requests.Session()` flow is enough for this; avoid adding dependencies just to parse the form. Regex extraction of `mgs_cf_nonce` and `raw_json` is acceptable when immediately followed by JSON parse + public-route validation.

## Related mode conversion

If Rodolfo wants the final offers to appear as 3 cards together, or says the reference has no “Mensagens da oferta” block, this is no longer a copy/URL-only update. Use `references/mgs-chat-funnels-car-cards-rollout.md` instead. That path changes plugin renderer/admin behavior and switches `mode` to `cards`.

## Combined rollout: legacy CAR copy + separate SMS variant

Use when Rodolfo asks, in the same operation, to update the three CAR cards on existing chats and create `/chat-sms/car/br1` only where the CAR chat is already installed.

1. Discover targets from live runtime, not the full site registry:
   - plugin active or public `/chat/car/br1` marker present;
   - legacy config is `CAR-BR-01`, `mode=cards`, exactly three offers;
   - do not touch `EMP-BR-01` merely because it also has three offers.
2. Upgrade old targets with a **code-only overlay** that excludes `configs/*.json`; preserve each site's providers, tracking, personas and targets.
3. Update only the CAR legacy card copy/headline, preserving all three existing own-domain destination URLs.
4. Create `CAR-BR-01-SMS` at `/chat-sms/car/br1` as a duplicate of that site's updated CAR config, then set `sms_enabled=true`, the selected canary manager code and the human field labels.
5. Copy the private manager catalog server-side or through authenticated admin POST. Never print, embed in public HTML, or commit the `add-lead` URLs.
6. Back up plugin/config and relevant DB state before writes. On RunCloud, prefer plugin tar + validated database export; on Bitnami, preserve exact authenticated plugin-editor/config readbacks for rollback when shell access is unavailable.
7. Validate delivery with a transactional mock: intercept `pre_http_request`, create one synthetic lead, require `ok:Gxxx`, delete only that synthetic row and prove the row count returns to its original value. Do not send a real SMS during rollout smoke.
8. Validate both routes on every target: HTTP 200, exact three cards, own-domain targets, legacy without form, SMS with Name/Phone, private URL absent, UTM hardening present and correct provider markers (JBF, M2/PubGuru or ActView).

### Bitnami plugin-editor fallback pitfall

The WordPress plugin editor can overwrite existing files but cannot create a new include file. If the SMS class must be kept inline in `mgs-chat-funnels.php` as a temporary Bitnami-compatible layout, adjust include-relative paths accordingly: inside the inline class, the config path is `__DIR__ . '/configs/'`, not `dirname(__DIR__) . '/configs/'`. The latter is correct only while the class lives under `includes/` and causes the transactional smoke to return `Chat SMS não encontrado.` when inlined.

Before deployment, lint the inline main file and the temporary transactional-smoke variant with real `php -l`. After smoke, restore the final main content and require exact authenticated plugin-editor readback with no temporary smoke marker.

## Public validation checklist

For every domain, fetch:

```text
https://DOMAIN/chat/car/br1/?zeus_cache=TIMESTAMP&utm_source=zeusqa&utm_campaign=carcheck
```

Confirm all of these before reporting success:

- HTTP 200.
- Route marker exists: standalone Ciro template has `const questions =`; shortcode renderer has `mgs-chat-funnel-config`; card-mode standalone routes may also expose `offer-card` links directly.
- All 3 expected per-domain target URLs appear in the HTML/source.
- All 3 new offer text snippets appear when copy was changed; for URL-only swaps, confirm the 3 expected car/card names or other stable card identifiers instead.
- Old offer copy snippets are absent when copy was changed.
- At least one browser smoke test reaches the final cards/offer CTA and confirms UTM passthrough in the rendered link (`utm_*`, `fbclid`, etc. carried from the chat URL to each target URL).

## Pitfalls

- Do not look only for `mgs-chat-funnel-config`; standalone Ciro-rendered routes do not use that marker. Use `const questions =` for standalone templates.
- A route can return HTTP 200 while serving stale/cached or old config. Use a cachebuster and check text/URLs, not status alone.
- `wantabrand.com` may emit the known `yoast-rest-meta.php` mu-plugin permission warning during WP-CLI. If the config write and public validation pass, this warning is unrelated to the chat update; mention it briefly but do not treat it as blocker.
- Preserve UTM passthrough. A content swap that breaks attribution is incomplete.
