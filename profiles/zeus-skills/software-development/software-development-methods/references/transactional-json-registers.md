# Transactional JSON Registers

Use for small operational JSON databases modified by several scripts, agents, cron jobs, or processes.

## Core invariants

1. Every mutator—including status transitions such as `done`—must acquire the same exclusive lock before reading. Locking only ID creation still allows stale-read overwrite and silent data loss.
2. Reload after acquiring the lock. Never mutate a snapshot read before locking.
3. Derive new sequential IDs from the actual union of live and historical records under lock: `max(existing numeric IDs)+1`. Persisted counters are compatibility outputs, never allocation inputs.
4. Validate global ID uniqueness before and after mutation. Fail closed on duplicates or malformed schema.
5. Keep legacy namespaces separate and never refill historical gaps; references may exist outside the database.
6. Write to a temporary file in the same filesystem, flush and `fsync`, atomically replace, `fsync` the directory, then perform semantic readback while still locked.
7. Pass user-controlled values through argv/JSON/environment. Never interpolate them into generated Python or shell source.

## Compatibility rollout

When duplicate counters already exist in the schema, first remove their authority without changing schema: recompute and synchronize them after every mutation. Remove or consolidate fields only in a later compatibility-reviewed migration.

## Test matrix

At minimum cover: divergent counters, missing counters, gaps, legacy namespace, preexisting duplicates, many concurrent OS processes, concurrent add versus status transition, replace failure preserving original bytes, special characters/newlines, historical insert, and exact status transition/count readback. Watch a RED failure before implementation and rerun the complete matrix after every locking or write-path change.

## Production smoke safety

Prefer fixtures and a read-only validator. Never repurpose a real pending/incident ID merely to exercise the write path. Before any production state transition, read back the target's title/category and prove it is the semantic item intended by the authorization. If a wrong transition occurs, stop, restore the immediate pre-op backup atomically, regenerate derived views, and verify the original item state and uniqueness before continuing.
