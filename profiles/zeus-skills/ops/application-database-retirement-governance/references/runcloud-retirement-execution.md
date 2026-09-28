# RunCloud retirement execution

Use this recipe only after read-only mapping classifies the application/database set as inactive or orphaned and identifies every control-plane and runtime object separately.

## 1. Split the authorization gates

1. Complete owner confirmation, dependency mapping, activity checks, and impact measurement.
2. Obtain approval for the reversible protection phase: logical export, isolated restore, validation, and retention.
3. Execute and read back that phase without deleting any original target.
4. Freeze a destructive manifest from the post-restore live state and hash it with the shell (`sha256sum`).
5. Request the final Critical Subset confirmation bound to that hash.
6. Delete only after the user confirms the post-evidence manifest. A modified target list, order, default-app decision, or retention condition requires a new hash and confirmation.

Dropping the isolated restore schema is deletion. If it was not already named in a valid final confirmation, leave it grantless and connection-free and include it in the final manifest.

## 2. Prove the source is quiescent

Before export, require all of these:

- exact application/config search finds no consumer;
- MySQL runtime shows no account or schema privilege;
- several process-list samples show no connection to the schema;
- enabled events are absent, or `event_scheduler` is off;
- cron/service searches find no exact reference;
- current control-plane objects still match their IDs/names;
- backup storage has enough headroom for compressed dump, restored allocation, and safety margin.

For mixed InnoDB/MyISAM schemas, `--single-transaction` alone does not make MyISAM consistent. Use a non-locking dump only after the independent no-writer/event evidence is green; otherwise obtain a controlled lock window or stop.

## 3. Create a protected, schema-neutral backup

- Create one operation root under `/var/backups` with mode `0700`.
- Write the dump as root-owned `0600`.
- Dump a single schema without `--databases` so the SQL does not recreate/use the original name during the restore test.
- Use `mariadb-dump` when available, otherwise `mysqldump`, with a streaming pipeline such as:

  ```bash
  mariadb-dump --single-transaction --quick --routines --triggers --events \
    --hex-blob --default-character-set=utf8mb4 --skip-lock-tables "$DB" \
    | gzip -1 > "$BACKUP"
  ```

- Capture both pipeline exit codes; a zero exit from only the last process is insufficient.
- Validate `gzip -t`, compute SHA-256 with the shell, record byte size/mode/owner, and preserve bounded stderr.
- Never place database credentials in argv, logs, manifests, or reports.

Also archive the web root and exact Nginx/Apache route directories before application retirement. Validate the archive by listing it, extracting it into a temporary directory, and comparing a normalized inventory/hash; do not treat archive creation alone as a restore test.

## 4. Restore into an isolated schema

1. Create a clearly named temporary schema with the source charset/collation.
2. Do not create a user or grant for it.
3. Stream the compressed dump into that schema.
4. Compare source and restore using schema-independent digests of:
   - table names, types, and engines;
   - ordered columns and definitions;
   - ordered indexes;
   - triggers, routines, and events;
   - exact per-table row counts and the exact total.
5. Require the source and restore to remain present, with zero non-audit connections and zero schema grants.
6. Perform an independent readback of the backup hash/mode/gzip integrity and both schema states before preparing deletion.

Estimated `information_schema.TABLES.TABLE_ROWS` is not restore proof. Use exact `COUNT(*)` per table for the final data comparison, allowing a long foreground or silently managed bounded process when the schema is large.

## 5. Freeze the destructive manifest

The JSON manifest must contain:

- operation identity and server ID;
- exact database, database-user, webapp, domain, root, and restore-schema targets;
- validated backup paths, bytes, modes, hashes, retention date, and restore result;
- current existence, connections, grants, relationships, and default-app state;
- ordered destructive actions and stop conditions;
- required postconditions;
- explicit exclusions and unrelated systems that must remain unchanged;
- irreversible effect and practical recovery boundary.

Hash the complete file with `sha256sum` and quote the hash in the final confirmation request.

## 6. Apply RunCloud deletion fail-closed

### Web application

RunCloud deletes a webapp with:

```text
DELETE /servers/{serverId}/webapps/{webappId}
```

Deletion can remove its files and linked database. Prove the database relationship first and archive the app/routes. When the target is the sole default app:

- state that unmatched IP/domain traffic will lose that fallback;
- never select or create another default implicitly;
- if no replacement was explicitly authorized, attempt only the confirmed deletion and stop before database deletion if RunCloud refuses it because of default-app constraints.

Putting the webapp step first preserves the fail-closed boundary: a default-app refusal leaves the original database untouched.

### Database and database-user metadata

RunCloud deletes a database with an explicit body:

```text
DELETE /servers/{serverId}/databases/{databaseId}
{"deleteUser": true|false}
```

Set `deleteUser` explicitly. Use `true` only after proving every associated database-user object is stale and unshared. Otherwise revoke only the confirmed relationship with:

```text
DELETE /servers/{serverId}/databases/{databaseId}/grant
{"id": databaseUserId}
```

Then delete an independently confirmed stale user, if required:

```text
DELETE /servers/{serverId}/databaseusers/{databaseUserId}
```

After each call, read back the exact object before continuing. A successful DELETE response is not completion.

### Guardrail: `deleteUser=true` can create a runtime residue

Never assume that a control-plane user 404 means the MySQL account is absent. After `DELETE .../databases/{databaseId}` with `{"deleteUser": true}`, independently query `mysql.user`, runtime privilege tables, and active connections for the exact account. A drifted control plane can materialize a previously metadata-only user during deletion, including with global privileges.

If that happens, fail post-validation, prove the account did not exist in the preflight, confirm the exact user/host is inside the frozen manifest, require zero connections, classify privileges without persisting raw `SHOW GRANTS`, and remove only that exact residue before rerunning the full closure validation. Never print or store raw `SHOW GRANTS`: MariaDB may include an authentication hash in the statement.

## 7. Validate closure

Require all postconditions independently:

- deleted RunCloud webapp/database/user GETs return 404 and list endpoints omit them;
- original and restore schemas are absent from MySQL;
- real MySQL user/grant rows are absent;
- retired root and virtual-host routes are absent;
- retained backup files still match size, mode, owner, SHA-256, and `gzip -t`/archive extraction tests;
- explicitly protected webapps, databases, crons, PHP runtime, and HTTP routes remain healthy;
- no unapproved default-app reassignment occurred;
- the control plane and guest runtime agree.

If any stage fails, stop the later destructive actions, preserve all recovery artifacts, name the exact partial state, and retry only after readback proves the next action is safe. Backup deletion after the retention date is a separate destructive manifest and confirmation.
