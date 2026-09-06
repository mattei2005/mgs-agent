# PostgreSQL + login for financial homologation

Authority: Rodolfo 1545934831664242748. Active implementation and exact recovery paths: `/root/mgs-agent/apps/finance-system/deploy/PG-AUTH-RUNBOOK.md`. Product direction and checkpoint remain canonical for unfinished business scope.

## Reusable deployment lessons

- On a shared host, simulate the package transaction first. A database install can upgrade shared client libraries even without a general upgrade. When preserving existing sites is part of the approved scope, use a verified isolated runtime prefix or stop at the new dependency gate; never silently upgrade global libraries. An extracted private runtime needs explicit patch/update ownership because the OS package manager will not maintain it.
- Keep PostgreSQL on a local Unix socket with peer identities and a least-privilege application role. Do not solve shared-host isolation by trusting loopback alone. A permissioned systemd socket can connect Nginx to a PrivateNetwork application without exposing a TCP port or giving the application the web-server group as its primary identity.
- Separate immutable imported source/baseline, mutable scenarios, append-only audit and auth/session tables. Enforce source/locked-scenario protection with grants/triggers, not only disabled UI controls.
- Production startup must fail closed without auth configuration and the PostgreSQL adapter. Never silently fall back to PGlite or run DDL/imports as the restricted runtime role.
- Test authentication with a real HTTPS browser: Secure/HttpOnly/__Host cookie, CSRF, unauthorized APIs, private-path denial, expiry/revocation, logout, desktop/mobile and actual baseline. External safe GET navigation to login must not be rejected merely for Sec-Fetch-Site cross-site; unsafe requests remain blocked.
- Compare every migrated table using semantic hashes and counts, then restore into a separate database and exercise real PostgreSQL transactions/rollback/persistence/privileges. A total-only comparison is insufficient.
- Preserve credentials only in 1Password. Automated smoke credentials travel in memory/stdin and never appear in traces, argv, saved browser sessions or Git.
- Restrict Cloudflare TLS changes to the exact hostname and verify origin certificates without disabling certificate checks. Do not change the whole zone to fix one application.
- Rollback to the old unauthenticated release is safe only with the public 503 gate restored. Keep snapshots and database test artifacts; deletion/retention requires the applicable separate gate.
- A deployment dump and a second-host copy are not scheduled encrypted disaster recovery. Describe backup automation, encryption, retention and RPO/RTO as unimplemented until independently authorized and proven.
- Login + PostgreSQL + August parity still do not complete the full requested native financial system. Preserve the open cadastros/vigências/períodos/formula-migration checkpoint.
