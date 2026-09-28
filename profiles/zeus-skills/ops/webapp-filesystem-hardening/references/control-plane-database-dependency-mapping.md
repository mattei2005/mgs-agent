# Control-plane and database dependency mapping

Use this reference when a control-panel webapp is missing, is named like a database, is typed as phpMyAdmin, or appears to leave a database behind. The goal is to prove the current dependency graph without exposing credentials or changing data.

## Separate the layers

Never collapse these into one object:

1. **Control-plane webapp:** app ID/name/type, root/public path, domains, default-app status, linked-database field, creation time.
2. **Filesystem application:** root existence, code/product markers, config files, routing, cron/worker references, and logs.
3. **Database control plane:** schema record, database-user record, and recorded grants.
4. **Database data plane:** live schema, `mysql.user`, `mysql.db`, table grants, listeners, process list, tables, volume, and activity.
5. **Consumers:** current application configs, remote services, tunnels, scheduled jobs, and operator-confirmed external dependencies.

A phpMyAdmin webapp is an administration interface, not the database itself. Its removal does not prove schema deletion, and a `database: null` control-plane field does not prove the interface could never log in to a database.

## Read-only mapping sequence

1. **Query the control panel live.** List current webapps and databases; resolve exact IDs and types. Compare the old target with similarly named current apps instead of assuming they are the same.
2. **Inspect the root safely.** Record root mode/owner and a bounded inventory. Detect standard configs such as `.env`, `wp-config.php`, `application/config/database.php`, and `config/database.php`. Parse database name/user/host in memory, but never emit passwords or secret values.
3. **Map every current consumer.** Scan application config locations for the exact schema name and database username. Return only matching paths/apps and non-secret identifiers. Include Nginx/Apache routing and cron/worker references.
4. **Reconcile control plane with MySQL.** Compare database/user/grant records with `information_schema`, `mysql.user`, `mysql.db`, and table grants. Treat live MySQL and runtime configuration as authoritative for actual access; record stale control-plane metadata as drift rather than silently repairing it.
5. **Check exposure and use.** Record `bind_address`, listener addresses, direct versus remote-capable grants, and a bounded series of process-list samples without query text. A localhost-only listener plus no user/grant/config reference is strong isolation evidence, but still report privileged tunnels/root access as an untested path.
6. **Characterize the schema without reading user content.** Record table count, logical and physical size, estimated rows, product-signature table names, largest tables, and selected maximum timestamps. Use indexed date columns or metadata where possible; avoid unbounded full-table scans on large tables.
7. **Search for retained evidence.** Check bounded backup/config locations for exact schema/app names. Distinguish “no named local backup found” from “no backup exists anywhere.”
8. **Classify and stop at the decision gate.** Report one of: active dependency, ambiguous dependency, isolated orphan, or control-plane drift. Mapping never authorizes relinking, public phpMyAdmin exposure, user recreation, schema deletion, or cleanup of the empty default app.

## Orphan classification

Call a schema an **isolated orphan candidate** only when all of the following are evidenced:

- no current application config references the schema/user;
- no live MySQL account or grant can access it through the normal path;
- no active cron/worker/router references it;
- listener/grant posture does not expose it remotely;
- bounded connection samples observe no use;
- recency evidence is stale;
- control-plane and filesystem objects that previously served it are absent or empty.

Use “candidate” until the system owner confirms no external dependency. A short process-list sample alone is never sufficient.

## Activity and scale probes

Prefer metadata and indexed probes:

- `information_schema.TABLES` for table count, logical bytes, estimated rows, create/update metadata;
- `mysql.innodb_table_stats` for last stats update and row estimates;
- `MAX()` only on indexed or bounded operational timestamps such as login, schedule, or sent time;
- filesystem `du` for physical allocation;
- `statvfs`/`df` for backup capacity;
- several process-list snapshots over a bounded window, excluding query text.

Label InnoDB row counts as estimates. Keep logical table bytes separate from physical datadir bytes because fragmentation and allocation can differ substantially.

## Sensitive-data and deletion gate

A dormant bot/CRM schema can still contain subscriber identities, pages, message history, and tokens. Do not inspect row contents merely to prove ownership. Structure, counts, activity dates, users/grants, and configuration references are normally enough.

Before destructive retirement:

1. obtain owner confirmation for external dependencies;
2. create a protected logical backup and hash it;
3. restore into an isolated schema and validate tables/counts;
4. define retention and storage location;
5. obtain the required explicit destructive authorization;
6. delete schema, stale control-plane user/grant records, and empty frontend/app as separate reversible steps;
7. validate unrelated apps and the operational production instance after each step.

Do not re-expose phpMyAdmin or reconnect an old schema merely to test whether it was once related. Preserve the evidence and make the dependency decision from the mapped layers.
