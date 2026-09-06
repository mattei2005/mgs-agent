# Finance system — protected RunCloud deployment

Authorization: Rodolfo `1545928620462313645`; server selection `1545922219161419777`; hostname `1545920429879730237`; thread `1545426987756298340`.

## Result

Created RunCloud custom webapp 3012868 / mgs-finance-dash and dedicated user 2069220 / mgsfinance on MatteiInc01 290075 (162.55.28.178). Credential safely created/read back in 1Password. Application code/data remain outside public web root. Isolated Node v22.23.2, systemd service enabled and active, private network namespace; Node18 and MariaDB of existing sites unchanged.

Cloudflare A record 9095714e71646c40c75eea53d06f20e6 maps dash.mgsdigitalcorp.com to 162.55.28.178, proxied/automatic TTL. Let's Encrypt SSL 2772040 issued; certificate metadata validUntil 2026-12-04T22:00:11.000000Z. TLS verified on origin and public hostname. HTTP301 -> HTTPS. HTTPS503 is the deliberate preparation/access gate, not financial access or user authentication.

## Validation

- 15 Python tests passed on target.
- Node integration suite passed including parity, mutation/persistence and restore.
- Running baseline PARITY_PASS: 53,091 formulas recalculated, 10 frozen quotes; cash/expense/daily failures zero. production_ready false.
- Five public/origin paths blocked, no financial data served: /, /api/scenarios, /private/source.json, /.env, /storage.mjs.
- Host-loopback cannot access the service namespace; another site user cannot read financial source files.
- 77 previous webapps' API metadata unchanged; previous Nginx configuration hashes unchanged.
- Protected pre-Nginx backup and consistent application private-state backup at /home/zeus/mgs-finance-backups/1545928620462313645/.
- Backup hashes and deployment manifests in apps/finance-system/private/deployment-1545928620462313645/.

## Remaining gates / risks

No Supabase account/billing or production PostgreSQL was installed. MariaDB adaptation vs separate PostgreSQL production installation remains a decision; Zeus recommends separate PostgreSQL without a subscription. PostgreSQL licence has no fee, but capacity, maintenance and off-host backups remain real operational costs.

Before opening financial access: application login/identity audit, Host/Origin and private proxy transport, strict origin validation and off-host backups. Current Cloudflare Full is inherited and unchanged globally. The existing Wantabrand ssl_stapling warning was observed before changes and remains outside scope.

Functional migration still incomplete: native versioned registrations, rules/effective dates, period workflows, imports and other spreadsheet functionality. Planilhas remain untouched.

## Recovered tooling issues

Narrow search queries returned no results; broader search and web_extract succeeded. Two guessed documentation paths were not found; corrected with the canonical Web Application docs. Direct urllib docs request returned403; web_extract worked. Browser harness daemon did not start; no browser/gateway restart was attempted and API/SSH were used. Default Python urllib UA on new hostname triggered Cloudflare1010; curl and origin verification reached intended503, without weakening security. First immediate request after Nginx reload was stale404; fresh readback reached503. No unresolved deployment failure was concealed by these fallback routes.

## References

Runbook apps/finance-system/deploy/README.md.
Private final-summary.json in the deployment evidence directory.
Canonical product direction docs/finance-system-product-direction.md.
PostgreSQL licence: https://www.postgresql.org/about/licence/.
