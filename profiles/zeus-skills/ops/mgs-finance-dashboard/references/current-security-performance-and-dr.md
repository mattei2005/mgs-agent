# Current security, performance and DR hardening

Authority: Rodolfo messages `1548812376290234451` and `1548835136693600328` in finance thread `1545426987756298340`.

## Scope and sources

- Production is the RunCloud finance host and release named by `deploy/PG-AUTH-RUNBOOK.md`; local systemd state on Zeus is not production health.
- Preserve financial scenarios, revisions, facts, ledger, immutable history and audit records. Infrastructure tests are read-only unless a separate financial mutation is explicitly authorized.
- Take exact file/dump backups and freeze hashes before deployment. Validate the deployed files, service, private socket, authenticated browser and database fingerprints after restart.

## DR contract

- A full off-site bundle must contain the three operational Hermes profiles, MGS OS/context/data/scripts, versionable finance-system application files, every registry-referenced report required by knowledge validation, and a current PostgreSQL custom dump.
- Exclude `private/`, `node_modules/`, caches and generated secrets from the application component. The PostgreSQL dump is its own component with size, SHA-256 and `pg_restore --list` validation.
- Encrypt before upload. A corrective validation run uses `--no-retention`; do not trash an older backup merely to prove the new package.
- Restore validation must verify bundle/component hashes, ZIP safety, SQLite integrity, institutional knowledge, profile importability and the PostgreSQL archive catalog. A materialized PostgreSQL restore uses a uniquely named isolated database; never touch `mgs_finance`. Dropping the isolated database requires the exact Critical Subset confirmation.
- Record every restore attempt in state. Monitoring fails immediately when the newest attempt is FAIL, even if an older successful restore remains inside the age SLA.

## Performance contract

- `/api/workspace` may cache only the exact serialized payload, keyed by scenario id/revision, account-document revision and live-quote update marker. Limit cache residency and emit `X-MGS-Workspace-Cache` plus `Server-Timing` for verification.
- Revision change must force a miss. A hit must be byte-identical to the miss response. Never optimize by dropping fields or changing numeric/string semantics without separate parity tests.
- Keep API responses `no-store`. Static authenticated code assets may use `private, no-cache` with ETag so browsers revalidate without exposing data or serving stale public content.
- Benchmark warm sequential and 20-request concurrent access before and after. Treat raw payload slicing/lazy endpoints as a separate change if caching alone reaches the accepted latency without semantic risk.

## Authentication, sessions and headers

- Session lookup may refresh `last_seen` at most once per minute while preserving the 30-minute idle timeout. Tests must prove valid reuse, expiry, revocation and logout.
- Do not delete session/audit history incidentally. A cleanup policy needs explicit retention semantics and the production role must have only the grants required by the approved design.
- `/api/health` is authenticated and must report `mode=production`, `production=true` against the PostgreSQL adapter.
- Emit HSTS, restrictive CSP, Permissions-Policy, nosniff and no-referrer. Cookie remains `__Host-`, Secure, HttpOnly and SameSite=Strict; Host, Origin and CSRF gates remain mandatory.
- MFA creates/changes production authentication secrets and therefore requires exact double confirmation. Direct-origin firewall changes and `/etc/systemd` hardening also require their own Critical Subset confirmation and rollback data.

## Verification

1. Run the complete Node and Python suites plus dependency audit.
2. Compare local/deployed hashes and database revision/fact/audit fingerprints.
3. Restart only the remote finance service, never the active Hermes gateway.
4. Run owner, partner and all five manager browser checks on desktop/mobile; require zero JS errors and zero financial POSTs.
5. Re-run performance and security probes, then update report, checkpoint, inventory, audit and REPORT-INFRA.
6. If login or service validation fails after deployment, diagnose immediately, apply the smallest safe correction or restore exact predeploy files, restart and repeat the full acceptance path.
