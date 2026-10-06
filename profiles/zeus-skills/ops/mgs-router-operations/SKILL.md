---
name: mgs-router-operations
description: "Use when operating MGS Router routes and panel."
version: 0.1.0
author: Rodolfo Mattei, Zeus MGS
license: Proprietary
platforms: [linux]
metadata:
  hermes:
    tags: [mgs, router, routes, panel, cloudflare, go]
    related_skills: [cloudflare-operations, onepassword-service-account-vault-operations, software-development-methods]
---

# MGS Router operations

## When to Use

Use for inspecting, troubleshooting or changing MGS Router routes, UI, deployment or panel accounts. Do not use for campaign strategy, DTR/SB migration, or agent-user authorization; those need their own approved scope.

## Scope and sources

- Product: self-hosted routes/redirects plus simple interface. Rodolfo1556896726403514390 explicitly added aggregate clicks by date, equal split button and same-menu list return; active scope/receipt is `docs/mgs-router-campaign-clicks-equal-distribution.md` and `data/mgs-router-campaign-features-validation.json`. This supersedes the earlier no-clicks scope only: no visitor identification, conversion tracking, postbacks or Keitaro/reporting suite. For click storage/QA/fractional weights load `references/campaign-clicks-and-equal-distribution.md`.
- Panel: https://route.mgsdigitalcorp.com/login. Initial host: current agents VPS, 2.25.165.171. Move only after an authorized migration if pressure makes it necessary.
- Read `docs/mgs-router-public-deployment.md`, `docs/mgs-router-domain-and-keitaro-import.md`, `data/mgs-router-deployment.json`, `data/mgs-router-public-validation.json`, and checkpoint `mgs-router-wantabrand-20261002` before state/resumption answers. Runtime beats historical plans.
- For domain onboarding or Keitaro route extraction/import, load `references/domain-and-keitaro-import.md`. Domain registration is not DNS activation; source landings and weights must be reconciled before import. The eleven-site initiative is in `docs/mgs-router-eleven-domains-migration.md` and checkpoint `mgs-router-keitaro-11-domains-20261003`; its complete historical configuration source is `data/mgs-router-complete-keitaro-source-20261003.json` (599 campaigns, 1274 Landing Pages), while `data/mgs-router-eleven-domains-keitaro-source.json` is the exact 428-campaign/18-host requested subset. Read the current checkpoint and fidelity validation before resuming; a saved snapshot alone is not an imported/cutover state.
- For date-only Última Verificação and popup DNS instructions, read `docs/mgs-router-domain-date-dns-dialog.md` and `data/mgs-router-dns-dialog-validation.json`; the long saved-check line and inline DNS panel are superseded. Keep the raw saved timestamp and fresh Verificar behavior unchanged.
- For the active domain table/independent domain groups, upper/lower pagination and hidden Landing Page ID display, read `docs/mgs-router-domain-layout-top-pagination.md`, `data/mgs-router-domain-layout-validation.json` and the domain extension in `references/scoped-groups.md`; this extends the previous UI receipts without changing traffic contracts. Public verification must use `mgs-op-with-service-account.sh` and saved domain observations only; online Verificar is a separate state-changing check.
- For the active bulk selection/clone/delete/enable/disable, dense horizontal actions and 30-item Campanhas/Landing Pages pagination, load `references/bulk-actions-pagination.md` and `docs/mgs-router-bulk-actions-pagination.md`. For independent groups and scoped dialogs, load `references/scoped-groups.md` and `docs/mgs-router-scoped-groups.md`. Schema2 `route_groups`/`destination_groups` supersedes the shared global groups registry/tab; preserve both scopes and catalog metadata on every write. Load `references/catalog-layout.md` only for underlying catalog/ID/shared-URL behavior.
- For group renaming or live Wantabrand DNS, load `references/dns-cutover-and-group-edit.md` and `docs/mgs-router-group-edit-and-wantabrand-cutover.md`. These are the active source for the authorized traffic cutover; earlier no-cutover statements are historical.
- Domain check colors persist via `/var/lib/mgs-router/domain-checks.json` and authenticated `/api/domains` checks; load `docs/mgs-router-domain-check-persistence.md` for reload/restart regressions. Each Verificar click performs a fresh DNS+HTTPS signed online check. Saved green is the last observation with its original timestamp, not continuous monitoring; keep this distinction visible and preserve the verification store in rollback inventories.
- Code `/root/mgs-agent/apps/mgs-router/`; binary `/opt/mgs-router/mgs-router`; unit `/etc/systemd/system/mgs-router.service`; private state `/var/lib/mgs-router/`.
- Logins `rodolfo` and `geizian` manage routes only. Their creation does not authorize them to command agents or access VPS/Cloudflare. Do not change agent authorization registry for panel accounts.

## Safety

- Credentials: 1Password vault MGS Conteúdo, items MGS Router - Rodolfo, MGS Router - Geizian, MGS Router - Origin TLS. Never emit values, headers, cookies or user-store contents. App stores salted hashes, not plaintext passwords.
- Cloudflare zone mgsdigitalcorp.com is visible through approved mattei20052 token scope. Resolve target visibility, not token validity alone.
- Origin TLS is self-signed for Cloudflare Full. Do not change zone SSL as an incidental fix. Direct origin traffic is refused using official Cloudflare peer CIDRs; trust client-IP headers only after peer verification. This is app-level restriction, not firewall or whole-VPS DDoS isolation.
- Initial service: half of one core (CPUQuota=50%), MemoryMax=256M, non-root mgs-router, ProtectSystem=strict, NoNewPrivileges. These do not eliminate all host network/disk contention.
- `/etc`, credential changes, deletion and billing follow AGENT.md Critical Subset. Initial confirmation is historical, never permanent authority. Never restart agent gateways to repair this app.
- Protected operational TLS files and private route/user state stay outside Git. Do not place them in versioned backups.

## Private panel indexing and favicon

Rodolfo1555940444473655388 requires SEO/indexing off for Router and financial dashboard; canonical decision and separate publication states: `docs/mgs-private-panels-indexing-policy.md`. On Router, keep the official MGS favicon public at `/favicon.ico`, linked/versioned in login and admin. Apply noindex/nofollow/noarchive/nosnippet/noimageindex HTTP headers and HTML robots meta only on the admin hostname; public robots.txt disallows all and sitemap remains absent. Never leak panel noindex into real traffic hosts or destination pages. Verify favicon HTTP/hash/browser decode, authenticated HTML and error/API headers, and unchanged real redirects. Finance implementation still uses its own model/release gates; Router success does not close that target.

## Verification

- Never treat a manually supplied HTTP Origin plus pre-authenticated browser cookies as sufficient proof of the native login form. Exercise a real browser form POST with browser-generated headers, and pair that transport check with the credential/login/API/logout checks. For password entry in browser, use the vault workflow, never DOM typing; the native-origin regression can use an intentionally empty form without credentials. Label these test scopes honestly.
- Keep HTML login/admin Referrer-Policy as `same-origin`: Chromium turns native form POST Origin into `null` under `no-referrer`. Do not fix that symptom by accepting opaque/null origins or weakening CSRF. Preserve `no-referrer` for traffic redirect responses. A regression must prove same-origin native POST transport, rejection of null/foreign origins and unchanged traffic privacy.

1. Reconcile current receipt/checkpoint and concurrent writes before mutation.
2. Read-only public verification: `scripts/mgs-router-verify-public.py`, authorized environment loaded silently. Resolves credentials in memory; checks HTTPS logins, authenticated API, real-browser UI, logout, origin denial and limits; emits sanitized results and writes no routes. Its empty-route expectation belongs to initial publication: update that assertion after legitimate imports, never clear routes to make tests pass.
3. Code tests use `/root/.local/share/mgs-router-toolchain/go/bin/go`: tests, race, vet, build; JS syntax via Node. QA deps are isolated, not installed into protected agent runtimes.
4. Browser QA uses short profile scratch TMPDIR to avoid Chromium Unix socket overflow; strict-CSP checks use locator assertions, not eval-string waits. Preserve existing compatible browser binaries.
5. Route imports are separate from panel publication. Resolve real domain/path/destination sources; never import synthetic QA URLs. Preserve fixed public host/path, approved per-route query semantics (default raw passthrough versus exact `keitaro_query`), and configuration-revision conflict checks.
6. Inventory/audit sanitized artifact and DNS/item metadata, update checkpoint, send one canonical REPORT-INFRA embed and validate exact readback. No raw traces on Discord.

## Initial executor boundary

`scripts/mgs-router-deploy-initial.py` is bound to confirmation 1555623974673842279 and initial binary hash. It is not a generic update command. Do not change its approval ID/hash to bypass a fresh gate or replay it to rotate accounts. After partial failure, reconcile receipt, vault items, unit and DNS before retry; never overwrite unrelated resources or regenerate existing keys blindly.
