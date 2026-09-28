# RunCloud Webapp Headers, Cache, Edge and Origin TLS

## Purpose

Use this for a RunCloud-hosted webapp when public HTML, cache-busted HTML, direct origin, security headers, Cloudflare transforms, or origin TLS evidence disagree. The goal is to attribute the layer before changing WordPress, Cloudflare, Nginx, or certificates.

## 1. Freeze the three delivery paths

Probe the same route through all three paths before diagnosing it:

1. **Bare public URL** — the exact URL users receive.
2. **Unique-query public URL** — reveals whether a full-page cache hit differs from a dynamic render.
3. **Direct origin with correct SNI/Host** — bypasses the edge while preserving the virtual host.

For each path, record status, final URL, body hash/size, cache markers, `Server`, and the exact presence/value of HSTS, CSP, Referrer Policy, Permissions Policy, X-Frame-Options, X-Content-Type-Options, and X-XSS-Protection. Compare body markers separately from headers; an edge transform can alter one without the other.

Imperative pitfall: never call a WordPress hook broken from the bare response alone — a full-page cache drop-in may return before WordPress loads the MU plugin or `send_headers` hook.

## 2. Classify origin TLS before proposing certificate work

Run the direct-origin TLS probe with SNI and inspect the leaf subject, issuer, validity, presented-chain count, and verify code. Then compare with the public edge and provider control plane.

- A **Cloudflare Origin CA** leaf is intentionally trusted only on Cloudflare→origin, not by public operating-system CA bundles. Direct-origin verify code 20 is therefore expected when the edge is publicly valid and Cloudflare can reach the origin.
- Call it an incomplete or broken public chain only when the public edge fails, the provider reports invalid/expired origin TLS, or Cloudflare→origin validation fails.
- Do not alter certificate files merely to silence `ssl_stapling` warnings for an origin-only certificate; first prove that OCSP stapling is useful and supported for that certificate class.

## 3. Discover the canonical Nginx control points

On RunCloud MGS hosts, prefer the validated binary path:

```text
/usr/local/sbin/nginx-rc
```

Validate the binary explicitly with `-v`, `-t`, and `systemctl is-active nginx-rc`. Do not choose the first filesystem executable matching `nginx*`; helper wrappers can interpret `-T` as a filename and create a false diagnosis.

Run `nginx-rc -T` and use its `# configuration file ...` boundaries to map the exact vhost and includes. Never edit RunCloud-generated files such as `conf.d/<app>.conf`, `<app>.domains.d/*.conf`, or `<app>.d/main.conf`.

Use a provider-supported extension point only after the dump proves it. For per-app headers, the safe pattern is typically:

```text
/etc/nginx-rc/extra.d/<app>.headers.<purpose>.conf
```

but only when the generated `<app>.d/headers.conf` actually includes `<app>.headers.*.conf`. Freeze whether the target exists, every sibling override, hashes, owner/mode, and the generated vhost hash before requesting a system-config confirmation.

## 4. Attribute cache and edge transformations

When dynamic/origin responses contain PHP-added headers but the bare response does not, stop patching PHP. Put headers at the proven Nginx extension point so both full-page cache hits and dynamic responses receive them.

A dormant W3TC/sample Nginx file under the webroot is not active evidence. Require that `nginx-rc -T` actually includes it before treating its directives as live.

For Cloudflare email obfuscation, compare origin and edge HTML:

- normal `mailto:` at origin plus `/cdn-cgi/l/email-protection` or `email-decode.min.js` only at edge proves an edge transform;
- protect only the intended anchor with `<!--email_off-->...<!--/email_off-->` and revalidate before proposing a zone-wide Scrape Shield change.

## 5. Pre-canary CSP without changing production

Before requesting a Critical system-config write, enforce the candidate CSP in Playwright by intercepting only same-site `document` responses, removing stale content-length/content-encoding headers, and fulfilling the response with the candidate CSP added.

Run representative routes in desktop and mobile viewports. Require:

- all document responses 2xx;
- zero CSP console violations;
- zero page errors;
- zero failed same-site requests;
- zero broken images, fatal templates, or overflow;
- key forms, CAPTCHA frames, menus, and conversion UI still present.

This proves compatibility of the candidate policy but does not replace production syntax and response validation.

## 6. Freeze one exact Critical manifest

Bind authorization to a manifest hash containing:

- exact app/server and target path;
- before state (`absent` or current SHA-256/size/owner/mode);
- complete candidate bytes and SHA-256;
- each header/value;
- pre-canary evidence;
- exact test/reload commands;
- preserved layers (generated vhost, Cloudflare, WordPress, database, firewall);
- rollback steps and acceptance gates.

A broad request to “fix everything” does not authorize an unknown `/etc` diff or Nginx reload. Discover first, then ask against the frozen manifest.

## 7. Apply with a no-reload-on-failure gate

After confirmation:

1. Re-read the exact target and sibling state; stop on drift.
2. Create a protected backup/rollback set.
3. Write the candidate atomically with frozen owner/mode.
4. Require `/usr/local/sbin/nginx-rc -t` success.
5. Reload `nginx-rc` only after syntax passes; do not restart the host or unrelated services.
6. Validate bare public, unique-query public, direct origin, cache-hit regeneration, full browser matrix, and public crawl.
7. Confirm generated vhost hashes stayed unchanged.
8. On regression, remove/restore only the exact app-scoped include, retest syntax, reload, and repeat the same acceptance matrix.

## 8. Classify crawler findings instead of weakening security

Preserve raw crawl output and produce a separate actionable classification:

- followed 301 aliases can share the destination title and are not duplicate canonical pages;
- bare oEmbed without required parameters can validly return 400;
- deliberately hidden REST users can validly return 404;
- blocked XML-RPC can validly return 403.

Require zero actionable issues. Never loosen a valid redirect or security control merely to make a generic crawler report zero raw non-2xx responses.
