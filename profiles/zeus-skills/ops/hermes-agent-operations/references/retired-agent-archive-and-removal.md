# Retired-agent archive and operational removal

Use this playbook when Rodolfo retires an MGS/Hermes agent and wants it absent from active operation while preserving consultable history outside the runtime.

## Scope gate

1. Read `AGENT.md`, the current agent map/routes, permissions, inventory, audit, and reverse-dependency references.
2. Separate the requested result into:
   - active runtime/profile/service;
   - versioned MGS code/config/data/docs;
   - shared dependencies still used by active agents;
   - credentials and external integrations;
   - historical/audit/session material.
3. Obtain the Critical Subset confirmation with an exact target list before moving/deleting profiles, systemd units, credentials, Discord resources, or thousands of files.
4. Define the search boundary honestly. “Zero operational references” is achievable; “zero bytes anywhere” usually conflicts with Git, audit, session databases, browser stores, and Discord history. Preserve or remove each class according to the confirmed scope—never silently redefine success.

## Archive-first sequence

1. Freeze a checkpoint and timestamp; reconcile concurrent writes via audit → inventory → REPORT-INFRA → Git → sessions.
2. Measure each exclusive root and enumerate named/text references without truncation.
3. Create an archive outside `/root/mgs-agent` and all active Hermes profiles, owner-only (`0700`).
4. Export external history before deletion (Discord messages/threads, metadata for archived credential items). Never print secret values.
5. Build a pre-move manifest with relative paths, byte sizes, modes, timestamps, and SHA-256.
6. Move exclusive roots atomically where possible; copy+verify first when filesystems differ.
7. Rewrite shared operational files surgically. Archive agent-specific references; keep reusable class-level procedures under neutral names.
8. Only after archive validation, remove original profile, unit, timers/crons, scripts, state, route entries, monitor lists, and integration bindings.

## External surfaces

### Discord

- Export the dedicated channel/thread history before deletion.
- Remove the bot member, dedicated channel/category, and managed role; a managed bot role may disappear automatically after the bot is kicked, so validate by readback instead of treating an earlier role-delete `400` as final failure.
- Archived public threads may reject rename while archived. With a valid bot token and a nonempty `User-Agent`, read thread metadata, PATCH `{"archived": false}`, then PATCH the neutral `name` with `{"archived": true}`. Verify final name and archived state.
- Do not delete unrelated historical threads unless they were included in the confirmed destructive scope. Neutralizing a title is not equivalent to deleting message bodies.

### 1Password

- Archive exact retired-agent items rather than exposing/copying their fields.
- Validate that the active vault listing returns zero matching titles.
- Archiving a 1Password item does not revoke a Discord application token; guild removal and developer-portal/app revocation are separate controls.

### Honcho

- Remove dedicated sessions and all active session associations first.
- Clear cards/metadata, set `observe_me=false`, and validate zero sessions/conclusions.
- Honcho v3 may expose no workspace peer-delete route; an empty disabled peer shell can remain even after DELETE returns `405`. Report that vendor limitation precisely instead of claiming the peer object was deleted. Deleting an entire workspace merely to remove one peer requires a separate scope and migration plan.

## Operational-reference cleanup

- Search names and text case-insensitively with token boundaries; avoid substring false positives such as unrelated words containing the same letters.
- Scan active maps, scripts, configs, JSON/YAML, SOUL mirrors, live skills, cron registries, channel directories, patch artifacts, and the deployed Hermes runtime.
- Remove the retired profile from every active agent list and monitor loop; adjust cardinality assertions (for example, `4/4` → `3/3`).
- Keep live and versioned skill/SOUL mirrors synchronized.
- For current Ares metadata inherited from a retired creative agent, preserve provenance in the external archive and use neutral legacy labels only where the current data must remain active.
- A raw byte match inside JPEG/PNG/MP4 compressed payload is not semantic evidence. Inspect metadata/chunks first; do not corrupt media or databases to eliminate coincidental byte sequences.
- Session DBs, browser LevelDB/SQLite stores, audit logs, and Git history are historical classes. Either include their deletion explicitly in the confirmation or list them as preserved exceptions.

## Patch guard and Git

- If auto-commit blocks a changed documentation path merely because its filename contains `token`, `secret`, `password`, or another guard term, do not broaden the sensitive-path allowlist by directory.
- Prefer renaming the reusable document to a neutral class-level filename and updating all pointers; the old path becomes a deletion (safe for the guard) and the new path is scanned normally.
- If the sensitive name is semantically required, use an exact-file allowlist only after a secret scan and readback.
- Let the canonical MGS watcher commit/push unless Rodolfo explicitly requests manual Git. Validate the filtered watcher pathspec, then prove `HEAD == origin/main` and auto-push failures returned to zero.
- Reconcile unrelated concurrent files instead of claiming the whole working tree is clean.

## Manifest and reporting invariant

- The final checksum list is valid only while the archive is frozen.
- Any later archive write—even a corrected Discord export/result JSON—invalidates the reported aggregate. Regenerate the checksum list, verify every entry, and explicitly supersede the prior REPORT-INFRA evidence.
- REPORT-INFRA must use the canonical embed helper, empty content, no mentions, and one validated message per material closure/supersession.

## Acceptance checklist

- [ ] Archive outside active runtime, mode `0700`
- [ ] Pre/post manifests and SHA-256 readback match
- [ ] Retired profile absent
- [ ] Systemd unit absent and daemon reloaded
- [ ] No process, timer, cron, route, monitor, or active credential remains
- [ ] Discord bot/channel/category/role readback absent
- [ ] Honcho sessions/conclusions zero; any undeletable peer shell disclosed
- [ ] Exact-token operational text scan = 0
- [ ] Exact-token operational path scan = 0
- [ ] Active agents and patch guard/tests pass
- [ ] Inventory, checkpoint, audit, Git sync, and REPORT-INFRA complete
- [ ] Preserved historical exceptions listed explicitly
