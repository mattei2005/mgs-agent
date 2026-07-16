# Canonical resource cutover across MGS agents

Use when Rodolfo replaces a shared operational resource (Drive root, folder tree, endpoint, account, channel, or similar) while preserving the logical structure.

## Procedure

1. **Confirm the canonical target**
   - Record the new immutable ID, canonical name/path, owning/admin identity, and whether names/hierarchy stay unchanged.
   - If the change touches another agent's skill/runtime, apply the `AGENT.md` Critical Subset confirmation before editing.

2. **Inventory stale references by identity and aliases**
   - Search active context, scripts, routed/versioned skills, and live profile mirrors for:
     - old immutable ID and old parent/container IDs;
     - old URL;
     - former root aliases and temporary cutover names;
     - old ownership/storage assumptions embedded in prose or code.
   - Classify results as **active operational**, **runtime mirror**, or **historical/audit**. Preserve append-only logs, migration manifests, imported threads, and rollback evidence unless Rodolfo explicitly authorizes destroying audit history.

3. **Back up the exact target set**
   - Take one timestamped backup containing both versioned and live-profile copies before mutation.
   - Do not overwrite a live profile from its versioned mirror until their pre-change backups are identical; otherwise reconcile the divergence first.

4. **Update semantics, not only strings**
   - Replace IDs, URLs, names, ownership rules, capability gates, watchdog messages, and credential/storage assumptions.
   - Keep historical migration utilities fail-closed after cutover so they cannot target the new canonical resource accidentally.
   - Review path parsing after replacing a root alias. Example pitfall: changing `MGS-CRIATIVOS` to `MGS-AGENTS/CRIATIVOS` breaks code that does `parts = path.split('/')` and compares only `parts[0]`; validate the prefix as two components and iterate from `parts[2:]`.

5. **Synchronize runtime and versioned mirrors as one cutover**
   - Update both sides in the same execution window. A periodic runtime→Git sync can revert a versioned-only edit before the runtime copy is changed.
   - Use the cross-profile guard override only after Rodolfo's explicit authorization.
   - Recheck mirror byte equality after any sync cron has had a chance to run.

6. **Validate behavior and absence of stale operational state**
   - Require zero active hits for old IDs, aliases, temporary names, and old parent IDs.
   - Syntax-check every modified script.
   - Exercise path builders/parsers with the new canonical path and assert the old alias is rejected.
   - Dry-run affected watchdogs/runners and verify the new immutable ID is used.
   - Confirm versioned/runtime mirror equality and a clean Git worktree after auto-versioning.

7. **Close governance**
   - Regenerate `data/infra-inventory.json` from live state.
   - Append a concise audit event with authorization, canonical target, scope, backup, and validation.
   - Send one canonical REPORT-INFRA embed and validate its Discord message ID; do not duplicate it as text.

## Pitfalls

- A narrow search for only the old ID misses aliases, temporary drive names, prose assumptions, and path constants.
- Blind global replacement can produce syntactically valid but behaviorally invalid path code.
- Updating only Git or only runtime invites mirror drift or sync rollback.
- Removing migration manifests destroys the only old→new ID/hash mapping; operational cleanup is not audit deletion.
- A completed one-shot migration script should not remain runnable with the canonical destination as both source and target.
