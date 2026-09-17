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

## Origin full-page cache can survive a Cloudflare purge

A Cloudflare purge does not clear WordPress full-page caches such as WP Fastest Cache. Diagnose this layer separately when the bare URL stays old after a successful zone purge:

1. Compare bare vs unique-query HTML. If bare still contains a legacy loader but `?mgs_nocache=<unique>` renders the current stack, the database/theme path is current and a full-page cache is stale.
2. Inspect response metadata. `CF-Cache-Status: DYNAMIC` plus an old `Last-Modified` rules out a Cloudflare edge HIT and points toward origin-rendered cache.
3. Read the active cache plugin and cache directory on the origin. For WP Fastest Cache, scan `wp-content/cache/all/**/index.html` for the exact legacy signature and compare file mtimes with the public `Last-Modified` value.
4. Check custom plugin routes that are absent from WordPress sitemaps (`/chat/...`, `/chat-sms/...`, landing handlers). A clean post/page crawl does not prove those routes use the current monetization stack.
5. Distinguish stale cache from active configuration: a cache-busted page proving the current wrapper does not clean a custom route whose own JSON/config still selects a legacy provider.

Only purge the origin full-page cache after the applicable deletion/production confirmation. For WP Fastest Cache 1.5.x, the live CLI implementation requires the positional argument even though `wp help fastest-cache clear` may omit it:

```bash
wp --path=/path/to/wordpress fastest-cache clear all --allow-root
```

`wp fastest-cache clear` alone prints `Wrong usage!` and does not clear anything. A successful clear can first move files under `wp-content/cache/tmpWpfc/<timestamp>/` while removing the served `cache/all/` tree; verify served cache paths immediately and poll the temporary tree until it disappears. Then validate bare URLs again, not only cache-busted URLs. A full public crawl may regenerate `cache/all/`; success means regenerated files contain the current stack and zero legacy signatures, not that the cache directory stays empty.

## Operational response

If origin is fixed but public URL is stale, report it as a cache purge blocker, not a code failure:

`❌ Erro ao processar: origin/plugin validado com cachebuster, mas URL pública ainda serve cache Cloudflare/APO antigo; purgar /chat/... e revalidar sem querystring.`
