# WordPress frontend validation: cache vs origin

Use this when a WordPress custom plugin deploy/report says the route returns HTTP 200 but the frontend still appears blank or old after a code fix.

## Durable lesson

A successful origin/plugin fix can still look broken on the public URL when Cloudflare/APO or edge cache serves an old rendered HTML page. This is especially misleading for plugins that embed JSON config in HTML: the origin may emit valid raw JSON, while the cached public route still contains `&quot;...` and breaks `JSON.parse(script.textContent)`.

## Validation pattern

Always compare **bare public URL** vs **cache-busted URL** before concluding the plugin fix failed:

```bash
# Bare URL: what users see
curl -sS -I -L 'https://example.com/chat/emp/br1' \
  | tr -d '\r' \
  | grep -Ei 'HTTP/|cf-cache-status|age|cache-control|last-modified|cf-apo-via|cf-edge-cache'

# Cache-busted URL: likely origin/BYPASS path
curl -sS -L 'https://example.com/chat/emp/br1?zeus_cache_bust=TIMESTAMP' -o /tmp/chat.html
```

Then inspect the rendered HTML:

```bash
python3 - <<'PY' /tmp/chat.html
import sys, re, json
s = open(sys.argv[1], encoding='utf-8', errors='replace').read()
print('bytes', len(s))
print('has_quot', '&quot;' in s)
print('has_config_script', 'mgs-chat-funnel-config' in s)
print('asset_versions', sorted(set(re.findall(r'mgs-chat-funnels[^"\']*?ver=([0-9.]+)', s))))
m = re.search(r'<script[^>]*mgs-chat-funnel-config[^>]*>(.*?)</script>', s, re.S)
if not m:
    raise SystemExit('config script missing')
json.loads(m.group(1).strip())
print('json_parse_raw OK')
PY
```

Browser-check both paths when possible:
- bare URL can render `(empty page)` if edge cache still has old HTML;
- cache-busted URL should render the real funnel controls if origin is fixed.

## Interpretation

- `cf-cache-status: HIT` + high `age` + old asset `ver=` + `&quot;` in config script = edge cache is serving stale broken HTML.
- Cache-busted URL with `cf-cache-status: BYPASS`, current asset `ver=...`, raw JSON parse OK, and visible DOM = origin/plugin is fixed; purge Cloudflare/APO for the affected routes.
- Do not ACK `[REPORT-INFRA]` as clean until the user-facing bare URL is also valid, unless the report explicitly says the remaining action is cache purge.

## Operational response

If origin is fixed but public URL is stale, report it as a cache purge blocker, not a code failure:

`❌ Erro ao processar: origin/plugin validado com cachebuster, mas URL pública ainda serve cache Cloudflare/APO antigo; purgar /chat/... e revalidar sem querystring.`
