# MGS Finance — RunCloud protected deployment

> Histórico da etapa 1545928620462313645. Banco/login/gate abaixo foram supersedidos pela confirmação 1545934831664242748 e pelo estado ativo em [PG-AUTH-RUNBOOK.md](PG-AUTH-RUNBOOK.md). O gate 503 permanece artefato de rollback, não a resposta pública atual.

Authorization: Rodolfo `1545928620462313645`, thread `1545426987756298340`.

## Exact target and state

- MatteiInc01 / RunCloud server 290075 / 162.55.28.178.
- Custom webapp mgs-finance-dash / 3012868; user mgsfinance / 2069220.
- Hostname dash.mgsdigitalcorp.com; Cloudflare A proxied TTL automatic. Zone accessible via 1Password item `Cloudflare MGS Admin Token - mattei20052`, not the other similarly named item.
- RunCloud API credential: `RunCloud API - MGS`. Technical account password is in `MGS Finance Dash - MatteiInc01 - mgsfinance`; never place values in argv/stdout or Git.
- Actual application: /home/mgsfinance/apps/finance-system (not the webapp document root).
- Web root: /home/mgsfinance/webapps/mgs-finance-dash/public-gate; contains no financial source/database.
- Isolated Node v22.23.2; global Node v18.20.8 unchanged. Node official tarball SHA256 verified before upload.
- systemd mgs-finance-dash.service, enabled; PrivateNetwork=true, NoNewPrivileges, memory/CPU limits, private writes confined to application private/.
- PGlite is still the homologation database; no production PostgreSQL or Supabase was provisioned.
- HTTPS valid with Let's Encrypt; HTTP redirects. Public paths return intentional 503 preparation gate. This is not a working end-user login or final product.

## Validation and backup

15 Python tests and Node integration including persistence/restore passed on target. Baseline PARITY_PASS. Source and runtime release files verified by SHA256 after transfer. Existing 77 webapps unchanged, previous Nginx config hashes unchanged.

Protected remote backups: /home/zeus/mgs-finance-backups/1545928620462313645/. Contains pre-Nginx archive+manifest, pre-network-isolation unit, and consistent private-state archive captured with only the new service stopped. Not an off-host disaster recovery solution. Do not delete backups without the applicable critical confirmation.

Local private evidence: ../private/deployment-1545928620462313645/ (relative to app root: private/deployment-1545928620462313645). Runtime credential helpers only resolve 1Password in memory. API payloads/responses containing passwords, pull keys, private keys must not be dumped.

## Health checks

Nginx binary on this server is `/usr/local/sbin/nginx-rc`; use `sudo -n /usr/local/sbin/nginx-rc -t`. Known preexisting Wantabrand ssl_stapling warnings are not caused by this app.

The application's TCP port exists ONLY inside its systemd network namespace. Host-loopback curl failure is expected, not service failure. As root/authorized sudo, obtain MainPID from `systemctl show mgs-finance-dash -p MainPID --value`, then `nsenter -t PID -n curl --fail http://127.0.0.1:8765/api/health`. Never use the gateway restart workflow for this service.

Public checks use curl with certificate verification: `https://dash.mgsdigitalcorp.com/`, `/api/scenarios`, `/private/source.json`, `/.env`, `/storage.mjs` must return 503 and only the preparation message. Origin check uses curl --resolve dash.mgsdigitalcorp.com:443:162.55.28.178, without -k. Python urllib's default UA returned Cloudflare 1010; curl reached the intended gate. Do not weaken Cloudflare protections to make that UA work.

## Opening access is a distinct gate

Do not simply remove the 503 guard. Current app still enforces localhost Host/Origin, lacks end-user authentication and uses a private network namespace. Auth, identity-based audit, private proxy transport (e.g. permissioned Unix socket), authorized Host/Origin, strict origin TLS and off-host backups must be designed/validated before opening financial data. Cloudflare's inherited zone SSL mode Full was not changed globally.

## Rollback scope

Stop/disable only mgs-finance-dash and preserve its private data. Keep the public gate. Restore only the new app's affected configuration from verified backups; never replace the full shared Nginx tree over concurrent site changes. Nginx syntax check before reload. Destructive cleanup and DNS deletion need the applicable separate authorization.

## Infrastructure/schema observations

GET RunCloud detail may return a direct object; lists use data. Accept both meta.lastPage and meta.pagination.total_pages and validate collected counts. New user POST /servers/290075/users and custom webapp POST /servers/290075/webapps/custom were exercised on API v3; SSL POST and exact GET /webapps/3012868/ssl returned issued certificate metadata. Filter API response fields before logging. Creation is asynchronous: verify by API AND live server; first immediate Nginx request after reload was stale 404, subsequent readback reached the 503 gate.
