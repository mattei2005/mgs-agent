# Transactional world-writable remediation

Use this reference when the live audit shows `S_IWOTH` or another overly broad mode bit on many application paths.

## Deterministic scope manifest

Store the root separately and each descendant as:

- relative path;
- `file`, `dir`, `symlink`, or other type;
- integer mode;
- uid/gid;
- size;
- `mtime_ns`.

Sort by relative path before hashing. Keep two hashes when useful:

- **logical hash:** canonical JSON before compression; this is the scope identity;
- **artifact hash:** the exact compressed file used for transport/storage.

The authorization summary must include root, descendant count, whether the root is included, transition counts, excluded parent, and action. Do not silently regenerate the manifest after authorization; live drift requires a new frozen scope or an explicit reconciliation that proves target identity did not change.

## Safe transformation

For world-write removal, calculate per entry:

`new_mode = old_mode & ~stat.S_IWOTH`

Validate these invariants before applying:

- `new_mode != old_mode` for every target;
- `(new_mode & stat.S_IWOTH) == 0`;
- `(new_mode | stat.S_IWOTH) == old_mode` when world-write is the only removed bit;
- uid, gid, file type, and path remain unchanged;
- symlinks are excluded or handled with an explicitly separate action;
- the shared parent is outside the manifest unless separately authorized.

Do not infer a single destination mode from the most common source mode. `0767 → 0765` and `0777 → 0775` preserve required group write, while blanket `0755` would change more than authorized.

## Backup and rollback invariants

A mode-only operation needs an exact metadata backup, not a copy of every file byte, provided the code never opens application files for writing. Capture it immediately before the first `chmod` and protect it with a root-only directory and file mode.

Test backup restoration in memory before mutation:

1. decompress/read;
2. verify entry count and root identity;
3. verify logical hash;
4. verify every saved path and mode can be reconstructed.

Rollback must run for failures in any later phase, not only for a failed `chmod` call. Restore descendants in reverse order and the root explicitly, then prove:

- exact original modes returned;
- original world-writable target set returned;
- public/origin smoke still passes;
- no canary or sentinel remains.

Preserve failed-attempt backups and receipts as evidence when a rollback occurred; they are not ordinary cleanup residue.

## Active-runtime timestamp drift

`chmod` changes ctime, not file content mtime. A changed mtime during the batch usually indicates the application or a cron wrote concurrently.

Use this sequence:

1. abort and rollback;
2. confirm the original writable set and HTTP health;
3. take two or more read-only snapshots over a bounded interval;
4. identify exact volatile paths;
5. require stable type and expected runtime ownership;
6. allow only the smallest proven exception, such as one cache directory mtime with unchanged size;
7. keep all other path, size, and mtime differences fatal.

Do not pre-authorize whole cache subtrees as volatile merely because their name contains `cache`. Evidence must come from the live original runtime.

## Runtime validation matrix

| Layer | Minimum acceptance |
|---|---|
| Filesystem | zero unauthorized mode bits; exact mode/uid/gid/type counts |
| Bytes | canary hash unchanged; no operation-caused content writes |
| Owner write | create/read/delete succeeds in one expected writable path; zero residue |
| Web | public and origin home/login return expected status |
| Assets | representative CSS/JS/image hashes agree between origin and public |
| Runtime identity | PHP-FPM/worker user matches the owner model |
| Scheduled work | expected cron/worker definitions use the intended user |
| Post-change traffic | fresh executions after completion return expected status |
| Logs | zero new 5xx and permission-denied errors in a bounded post-change window |
| Services | no restart unless separately authorized; named services remain healthy |
| External integrations | either run a real end-to-end test or report it as untested |

## Sheet and governance closure

When the task updates an MGS audit Sheet:

1. authenticate only with the canonical Service Account;
2. snapshot affected ranges and formula counts;
3. write/read/clear a blank canary cell;
4. update exact rows/ranges explicitly;
5. read values and `effectiveFormat` back;
6. verify formula parity and that the canary is blank.

The closure report must distinguish:

- confirmed security improvement;
- validated app/runtime functions;
- rollbacks that occurred and why;
- untested functions;
- separate parent-directory or cross-app risk;
- test/staging state versus the operational production instance.
