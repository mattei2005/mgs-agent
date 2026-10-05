---
name: application-database-retirement-governance
description: "Use when an app or database may be orphaned or retired."
tags: [runcloud, database, mysql, mariadb, phpmyadmin, dependency-mapping, retirement, backup, cleanup]
---

# Application and Database Retirement Governance

## Purpose

Determine whether a web application, database-admin UI, schema, user, or domain is active, orphaned, or merely stale in a control plane. Never infer that a database is unused because a similarly named Web Application disappeared; map control-plane and guest-runtime dependencies before any backup, retention, or destructive decision.

## Standing rules for Rodolfo

- Read-only mapping may proceed; database export, restore test, retention change, user/grant mutation, application retirement, and deletion remain separate actions.
- Use two authorization stages for meaningful or personal data: first authorize the reversible backup/restore proof, then request the exact Critical Subset deletion confirmation only after that proof and a fresh target readback exist.
- Bind the final confirmation to a hashed destructive manifest containing exact IDs, paths, ordered actions, failure boundaries, explicit exclusions, backup hashes, retention, and irreversible effect. Any scope change, including a reduction, requires a new manifest and confirmation.
- Treat each restore-test schema as a destructive target: create no new user or explicit grant, require zero application connections, and include its exact name in the final deletion manifest. Record any pre-existing global privileges separately; absence of a row in `mysql.db` does not make a same-instance restore permission-isolated. Use separately authorized stronger isolation when the copied data requires it.
- Do not inspect or report message bodies, subscriber values, passwords, authentication strings, or credential files. Structural table names, aggregate sizes/counts, timestamps, users, hosts, and grants are sufficient.
- Report facts, inference, gap, recommendation, option impact, and the exact decision needed. Keep a dependency pending when a human owner has been asked but has not replied. When retirement was already requested, acknowledge the existing business decision and name only the outstanding protection or Critical confirmation gate; do not reframe an execution backlog as a new question about whether the owner wants retirement.
- For an account-by-account explanation, reconcile the complete historical identity set against live existence before reporting totals. Explain each account's application, domain, schema, current privilege scope, evidence, gap and recommended treatment; distinguish SQL service identities from human WordPress logins and keep already-retired identities visible as historical, not open risks. State the shared privilege problem and its proven technical cause once, then explain each account in numbered plain-language blocks; do not imply that excessive privileges prove an intrusion or that every account should be deleted.
- Distinguish privilege isolation from content changes and retirement before proposing an action: limiting an application's SQL account to its own schema preserves the account, database and editorial state; deleting a schema removes its data. Articles placed in draft, or a planned business strategy not launched, do not themselves authorize either action. Preserve concurrently managed editorial work and label owner-reported context separately from runtime verification.

## Workflow

0. **Reconcile decisions before proposing or resuming work.** Read the current checkpoint, its canonical decision source, and completion receipts. Map numbered replies to the exact preceding account list, preserving usernames, schemas, provider IDs and host pairs. Classify each target as protected/no-change, explanation-only, requested retirement with a pending gate, or completed. Persist an explicit no-change instruction as an execution exclusion; do not absorb protected accounts into a fleet-wide permissions batch. After a subset closes, subtract the verified completed targets from the original request and keep the remainder visible with its exact next gate. A subset's confirmation or backup never covers the remainder automatically.

1. **Separate the object classes.** Build distinct records for:
   - control-plane application;
   - web root and virtual host;
   - phpMyAdmin or other administration UI;
   - MySQL/MariaDB schema;
   - database user and grants;
   - public domain/DNS/TLS;
   - consuming application configuration.

   A phpMyAdmin Web Application is an interface, not the database itself.

2. **Read the live control plane.** For RunCloud, query and sanitize:
   - `GET /api/v3/servers/{serverId}/webapps`;
   - `GET /api/v3/servers/{serverId}/webapps/{webappId}`;
   - `GET /api/v3/servers/{serverId}/databases`;
   - `GET /api/v3/servers/{serverId}/databases/{databaseId}`;
   - `GET /api/v3/servers/{serverId}/databaseusers`;
   - `GET /api/v3/servers/{serverId}/databases/{databaseId}/grant`.

   Retain only an explicit allowlist of IDs, names, types, roots, domains, creation timestamps, and relationships. Never print or persist a raw control-plane object: composite fields can embed sensitive material even when their names are not exactly `key` or `token`. Drop every field whose case-insensitive name contains `password`, `token`, `key`, `secret`, `credential`, or `auth` unless a narrower safe allowlist explicitly names it.

3. **Validate the guest runtime.** Confirm exact root existence, type, owner, mode, bounded file inventory, routing config, log paths, and whether the domain still resolves. A retired hostname reaching a default vhost or redirect proves only fallback routing; it does not prove the original admin UI or application still exists.

   When Rodolfo cannot find an application in the dashboard, answer with its exact live application name, hosting server/IP, domain and provider ID—not its SQL username. Re-fetch that exact application before asserting that it still exists, and do not invent a filter, account-permission or recreation explanation for a UI/API disagreement.

   When Rodolfo reports deleting an application manually, immediately reconcile its exact provider ID, root, configuration and routes; query its schemas and users independently. Attribute the verified deletion to the owner, never replay it, and preserve separate before/after receipts because deleting a webapp may leave its database and account intact.

4. **Map application → database references.** Parse common sources in memory—`.env`, `wp-config.php`, `application/config/database.php`, and framework database configs—while returning only database name, username, host classification, source path, hash, owner, and mode. Never return passwords. Search other app configs for the exact schema/user to identify shared consumers.

5. **Reconcile control-plane metadata with MySQL reality.** Compare dashboard users/grants with:

   ```sql
   SELECT User, Host, plugin, account_locked, password_expired FROM mysql.user;
   SELECT Host, User, Db, Select_priv, Insert_priv, Update_priv, Delete_priv FROM mysql.db;
   SELECT TABLE_SCHEMA, GRANTEE, PRIVILEGE_TYPE FROM information_schema.SCHEMA_PRIVILEGES;
   ```

   Runtime tables win. A control plane may retain a user/grant after the real MySQL account was removed; report stale metadata, not active access. Test application database identities with `mysql --no-defaults` as the first client option and secret values confined to the child environment or a protected input channel; inherited administrator option files can override an application password and make every valid account appear broken. Return only `CURRENT_USER()`, `DATABASE()`, exit status and sanitized error class, never passwords or raw client defaults. Retain failed and recovered receipts separately, and validate every exact configured consumer before assigning an authentication defect.

6. **Prove or bound current use with independent signals.** Combine exact config references, real users/grants, listener/bind address, several processlist samples without query text, indexed application timestamps, table update metadata, cron/service references, routing, and access logs.

   A short zero-connection sample is weak alone. No config, no user/grant, localhost-only listener, no recent activity, and no connections together support an inactive/orphan classification. A localhost listener blocks direct remote access but not a privileged SSH tunnel.

   For deletion conditioned on no writes during a historical window, inspect existing binary/general/audit logging and its actual coverage before asserting the condition. Aggregate only event timestamps (MAX and recent-row counts), excluding birthdates, expiry and future scheduling, and corroborate with table metadata plus datadir mtime/ctime. Treat these as evidence of stale data, not complete commit history: UPDATE_TIME may be NULL, stored dates can be backdated, and old file timestamps do not rule out reads. No writes never proves no use. If continuous history is unavailable, report the precise gap and keep conditional deletion blocked; obtain a decision on the bounded orphan evidence instead of silently treating the condition as proven. Do not enable logging retroactively or inspect personal row content as an incidental check.

7. **Measure impact honestly.** Report table count, table-name signatures, largest tables, logical data+index bytes, physical datadir bytes, estimated rows, and likely data classes. Label InnoDB `TABLE_ROWS` as estimates. Logical and physical sizes can differ because of allocation and fragmentation.

   Enumerate existence from `information_schema.SCHEMATA`, then LEFT JOIN `information_schema.TABLES` and count `TABLE_NAME` for each exact target; grouping only `TABLES` silently omits an existing empty schema. An empty associated schema does not make a globally privileged account harmless or prove that it cannot consume another schema.

8. **Search for recoverability without overclaiming.** Check bounded backup/config roots for exact schema/app names and record paths only. No matching local filename is not proof that provider snapshots or differently named backups do not exist.

9. **Classify the result.**
   - **Active:** current config plus working user/grant or observed use.
   - **Shared/unknown:** partial evidence or external owner/tunnel cannot be excluded.
   - **Orphaned/inactive candidate:** no consumer identified in the declared search scope, no activity observed in the bounded checks, and owner-confirmed disuse or other corroborating evidence. A surviving account or grant is a retirement target to inventory, not evidence that an application still consumes it. Preserve uncertainty about external or manual consumers until resolved.
   - **Control-plane drift:** dashboard metadata disagrees with runtime tables.

   Keep facts separate from name-based inference. Similar names can support historical linkage but cannot prove it after source/config removal.

10. **Prepare the decision, not the deletion.** Treat a human owner's generic statement that a legacy bot/app is unused or “can be removed” as business-dependency evidence only. If the statement does not name the technical objects, close the owner-confirmation gap but do not infer authorization for similarly named schemas, users, applications, or domains. Revalidate the live targets, identify exact IDs/paths, state explicit exclusions, and obtain Rodolfo's Critical confirmation for that frozen scope.

    For an orphan containing meaningful or personal data, recommend:
    1. owner confirmation;
    2. protected logical backup with hash;
    3. restore test into an isolated schema;
    4. explicit retention period;
    5. fresh dependency/activity recheck;
    6. exact destructive manifest and Critical confirmation;
    7. deletion of schema, stale metadata, and empty application only within confirmed scope;
    8. post-cleanup validation of unrelated apps and services.

    Load `references/runcloud-retirement-execution.md` for the executable backup/restore, manifest, RunCloud deletion, default-app, and postcondition recipe.

## Pitfalls

- For an explicitly approved MariaDB account-isolation change, inventory global/schema/table/column/routine/role/proxy grants without authentication material, preserve a private privilege-only rollback, and grant the exact own-schema scope before revoking global scope. Escape `_` and `%` in database grant patterns; an unescaped name can authorize matching schemas, not just the literal database. Remove superseded unescaped patterns only for the approved account. Validate one account first, then the next: own-schema authentication works, an administrative-schema probe returning only a constant is denied, no global privileges remain, and all other accounts' grants, password material, article-status aggregates and source descriptors are unchanged. Keep schema-level application privileges distinct from instance administration; do not describe this as complete WordPress or Unix isolation.
- Bind future backup disposal to the exact retained dumps and their hashes after restore proof, a precise timezone/deadline, a final Critical confirmation and a fail-closed owner-hold/message reconciliation rule. A requested retention date is not proof that deletion has been scheduled; report scheduler activation separately. Preserve unrelated dumps, rollback metadata and earlier protected backup sets.
- Pass remote configuration-parser source verbatim from a syntax-checked file or AST-extracted function instead of nesting regex/backreference code inside interpreted string templates. A second interpretation of escapes can turn valid credentials/configs into false parse failures; abort before deletion, repair the collector, preserve the failed receipt and rerun every protected consumer without exposing secret values.
- Before clearing a retirement reference as absent, corroborate empty indexed/grep results with bounded direct reads or a filesystem scan of the exact active roots. Search tools can honor Git/ignore filters and silently omit generated reports or profile files; separate live catalogs/tasks from immutable audit, archived reports, recovery evidence and unrelated portfolio history.
- Never equate a deleted phpMyAdmin app with a deleted schema.
- Never recreate or reconnect a database merely because an old UI disappeared.
- Never call an orphan safe to delete based only on DNS failure, an empty root, or a brief processlist sample.
- Never export sensitive data as an incidental audit step; backup is a separate approved action with protected storage.
- Never auto-reassign a sole default webapp while retiring it; changing the default changes unmatched-IP/domain routing. Record whether it is the sole default in the destructive manifest, require explicit authorization for any replacement, and otherwise fail closed if RunCloud refuses deletion.
- When a human owner is being consulted, persist the item as pending and continue independent work; silence is not approval.

## Completion output

Use five concise blocks:

1. **O que cada nome representa** — app, admin UI, schema, user, domain.
2. **Vínculos atuais** — configs, users/grants, listener, connections.
3. **Dados e última atividade** — estimated volume and recency.
4. **Risco** — operational, data/privacy, and deletion impact.
5. **Decisão recomendada** — preserve, archive, or backup/restore-test before a separately confirmed retirement.
