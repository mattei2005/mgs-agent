# Live webapp backup and isolated restore

Use this procedure when a production webapp needs a dedicated filesystem/database recovery set and a preserved isolated restore before remediation. It is a protection phase, not authorization to repair the application, upgrade the host, or delete any artifact.

## 1. Freeze the exact protection phase

Record the webapp, server, webroot, production schema, backup root, isolated filesystem path, isolated schema name, retention floor, and confirmation source before writing anything.

Keep these boundaries explicit:

- production webroot and schema remain read-only;
- the only new durable objects are the named backup root, filesystem restore, and isolated schema;
- no database user or grant is created for the isolated schema;
- backup/restore deletion is a later destructive manifest and confirmation;
- temporary SSH access has its own create/readback/use/revoke lifecycle.

Create a checkpoint before a long run and keep each phase independently verifiable: preflight, filesystem backup, filesystem restore, database backup, database restore, access revocation, independent readback, and governance closure.

## 2. Preflight live health and real headroom

Capture live webroot size, target filesystem free bytes, WordPress/core version, plugin/theme state digests, static-code digest, production schema structure, table engines, and required services.

Compute peak additional storage from artifacts that still need to be created:

```text
compressed filesystem archive
+ extracted filesystem restore
+ compressed database backup
+ database roundtrip dump
+ allocated isolated schema
+ explicit safety reserve
```

Do not use an arbitrary `3× + fixed large reserve` gate. It can reject a safe run after a large valid archive already occupies disk. Recalculate after every partial attempt from current `df` plus the exact artifacts already present.

For a live database, require transactional table engines before using `--single-transaction`. If nontransactional engines are present, stop and obtain a controlled consistency plan rather than pretending a nonlocking dump is a coherent snapshot.

Hash a bounded static-code set before backup—core, plugins, mu-plugins, themes, `wp-config.php`, and root PHP entrypoints—so cache/content churn does not make the production-integrity gate meaningless.

## 3. Use one fail-closed temporary-access lifecycle

When no approved persistent SSH route exists:

1. Require the control plane to show the expected baseline credential count.
2. Generate one local Ed25519 key in a temporary directory.
3. Create the named temporary credential and validate its ID by GET/list readback.
4. Build the SSH command before the POST so the `finally` path can always test revocation.
5. Run backup plus an independent validator through that credential.
6. In `finally`, delete the exact credential, require GET 404, require the baseline list count, require the same key to fail SSH, and require the local temporary directory to be absent.

A retry inside the same confirmed scope is recovery, not permission to expand targets. Reconcile partial remote effects before creating another credential or replaying a write.

## 4. Create and restore the filesystem archive

Stream the webroot archive and capture both pipeline exit codes:

```bash
tar --acls --xattrs --numeric-owner --one-file-system \
  -C "$WEBROOT_PARENT" -cpf - "$WEBROOT_NAME" \
  | gzip -1 > "$BACKUP_ROOT/filesystem.tar.gz"
```

Require root-owned `0600`, `gzip -t`, archive SHA-256, byte size, and a bounded stderr file. Extract into the named isolated restore and compare the extracted tree against the archive:

```bash
tar --extract --gzip --preserve-permissions --acls --xattrs --numeric-owner \
  --file="$ARCHIVE" --directory="$RESTORE_PARENT"

tar --compare --gzip --acls --xattrs --numeric-owner \
  --file="$ARCHIVE" --directory="$RESTORE_PARENT"
```

Also require the restored static-code digest to equal the pre-backup production digest.

### Recovering a tar code 1 safely

Treat `file changed as we read it` as a classification task, not automatic corruption and not automatic success.

- Preserve the archive; do not delete, truncate, or recreate it implicitly.
- Accept a resume only when stderr contains the exact bounded directory-metadata warning expected, not missing-file or read errors.
- Require `gzip -t`, complete archive listing, sufficient remaining headroom, no downstream restore/schema effects, and an empty known restore scaffold.
- Resume by extracting the preserved archive, comparing archive to restore, and proving static code matches production.
- If any condition fails, stop at a separately authorized cleanup/retention decision.

Do not compare a resumed archive's full file count to a later live tree as a hard gate: caches/uploads may legitimately change between attempts. Archive-to-restore equality plus static-code equality is the durable proof.

## 5. Create and restore the database backup

Use local socket/root execution or a protected defaults file; never place database credentials in argv, logs, manifests, or output. Dump one schema without `--databases` so the payload is schema-neutral:

```bash
mariadb-dump --single-transaction --quick --routines --triggers --events \
  --hex-blob --default-character-set=utf8mb4 --skip-lock-tables \
  --skip-comments --order-by-primary --no-tablespaces "$SOURCE_DB" \
  | gzip -1 > "$BACKUP_ROOT/database.sql.gz"
```

Only pass options supported by the installed dump binary. Capture both pipeline exit codes, bound stderr, set `0600`, run `gzip -t`, and hash both compressed bytes and the uncompressed SQL payload.

Create the isolated schema with the source charset/collation, create no user/grant, and stream the backup into it. Validate:

- table names, types, and engines;
- ordered columns and definitions;
- ordered indexes;
- triggers, routines, and events;
- exact row count for every base table and exact total;
- zero grants and zero non-validator connections;
- source schema still present.

Redump the isolated schema with the same deterministic options. Compare the **uncompressed SQL payload** hash and byte count to the backup payload; compressed gzip bytes are not deterministic proof because headers can differ.

## 6. Run an independent readback before revoking access

Use a separate validator implementation, not the same success flag. It must re-read and verify:

- backup root `0700`;
- backup files root-owned `0600`;
- exact bytes and SHA-256;
- all gzip tests;
- archive-to-filesystem-restore compare;
- production and restored static-code digests;
- production and isolated schema existence;
- isolated table/row digests, grants, and connections;
- WordPress core checksum and required services;
- retention plus separate-deletion confirmation marker.

After access revocation, perform external public/origin HTTP checks and a final control-plane credential-list readback.

## 7. Close with honest failure recovery and governance

The completion report must lead with PASS/FAIL, then state backup bytes/hashes, restore paths/schema, independent check count, production postchecks, access revocation, retention, and the exact next authorization gate.

Disclose recovered failures by mechanism, not narrative: false headroom rejection, exact tar metadata warning, preserved partial archive, and verified resume. Never hide a failed attempt merely because the final retry passed.

Update the checkpoint, inventory, audit log, and REPORT-INFRA when MGS operational data or a skill changed. If repository auto-commit is intentionally inactive or unrelated dirty work makes a manual commit unsafe, do not bundle concurrent changes; report local/runtime closure separately from pending Git persistence.
