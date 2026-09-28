# Git Auto-Commit Secret Containment

## Trigger

Use when a credential or secret-bearing editor/backup copy may have entered an auto-committed MGS repository, especially during `.env` or token rotation.

## Full database dumps and credential-bearing backups

- Treat every full production database dump as secret-bearing until its table inventory proves otherwise. Finance dumps include password hashes/salts, encrypted MFA records, session/CSRF state and personal data even when no plaintext password is present.
- Resolve the final protected destination and require a successful `git check-ignore` **before writing any bytes**. Prefer a root/application-owned private directory outside the repository; a verified ignored `private/` subtree is acceptable for established app workflows. Never stage dumps in `work/` or assume an extension such as `.dump` is ignored.
- Check repository visibility through authenticated GitHub metadata. A repository used for internal operational versioning must not be assumed private.
- A filename-based secret scanner and a maximum-size guard do not prove a binary dump safe. Pause the watcher before an uncertain backup operation, verify destination exclusion first, and never rely on moving the file after creation: auto-commit may have already published it.
- After accidental publication, disclose the exact incident promptly, pause propagation safely, preserve a protected recovery copy, and obtain the Critical Subset confirmations for history deletion/force push and credential/session changes. Distinguish encrypted MFA and token hashes from plaintext keys; do not overclaim either compromise or safety.

## Prevention before manual secret edits

1. Pause the repository auto-commit watcher before changing a credential file.
2. Confirm the real credential file is ignored and add patterns for editor copies, including `.env.save*`, `.env.*.save*`, swap files, and backup suffixes used by the selected editor.
3. Do not place rollback copies of secret files inside the repository. If a rollback copy is indispensable, keep it root-only outside the repo and remove it after validation under the applicable deletion gate.
4. Prefer a silent prompt/atomic writer for token replacement. If Rodolfo explicitly wants direct editing, give the direct editor command, but keep auto-commit paused and verify `git status` immediately afterward before resuming.
5. Validate the replacement token without printing it, then scan tracked/untracked filenames and staged content for secret-bearing copies.

## Containment sequence after exposure

1. Stop new propagation: pause auto-commit plus dependent backup/upload jobs that would consume the exposed credential.
2. Determine exposure without printing values. Report filenames, key presence, lengths, equality/containment booleans, commit IDs, and remote reachability; never display the credential.
3. Treat credential revocation/rotation as mandatory. Git history cleanup is not a substitute because clones, caches, and exact-SHA objects may remain.
4. Remove the secret copies from the current tree, add durable ignore patterns, and commit the containment change with the live `.env` explicitly excluded from staging.
5. Before rewriting history, record the exact remote head and verify which branches/tags contain the leak.
6. Rewrite only affected refs. Prefer `git filter-repo --path <file> --invert-paths --refs refs/heads/<branch> --force`. If it is unavailable, use a narrowly scoped `git filter-branch` on the affected branch only after proving no tag/other branch contains the commit. Never use `-- --all` casually: it rewrites tags, remote-tracking refs, and `refs/replace/*`, creates collateral cleanup, and can turn a surgical purge into a repository-wide rewrite.
7. Push with an explicit lease tied to the recorded remote head, then verify `HEAD == origin/<branch>` and zero secret paths in reachable history.
8. Test whether the old commit is still fetchable by exact SHA. A clean branch and successful force push do not prove server-side purge. Prefer a disposable repository with explicit SSH/known-host configuration; fetching the old SHA into the production clone rehydrates the secret object and requires another reflog expiry/prune afterward. If the old object remains reachable, escalate to GitHub Support sensitive-data removal while keeping the credential revoked.
9. Expire local reflogs and prune unreachable objects only after the remote rewrite is validated. Do not run overlapping `git gc` processes; reconcile an existing auto-gc before retrying.
10. Rotate every derivative secret the leaked credential could read. Example: if an exposed 1Password Service Account token could retrieve a disaster-recovery private key, that encryption key and backups encrypted with it are compromised too. Pause jobs, retire the key, remove affected remote backups, create a new key only after the token is rotated, and repeat backup plus isolated restore validation.
11. After the replacement credential is edited and validated, scan the filesystem again for ignored editor copies such as `.env.save*`. Ignore rules prevent Git propagation but do not remove local plaintext duplicates. Verify absence with a real filesystem glob and delete any copies under the already-approved containment gate; `git status` or `git check-ignore` alone is not proof of absence.
12. Resume auto-commit and dependent jobs only after token, derivative key, Git history, current tree, local editor copies, and remote readbacks all pass.

## Per-file size guard for untracked content

- Generate candidate status with `git status --porcelain=v1 -z --untracked-files=all` before enforcing a per-file ceiling. The default porcelain output collapses an untracked directory into one `?? directory/` record, so a later `git add -A directory/` can stage files that were never size-checked.
- Parse the NUL-delimited records, reject or skip every regular file at/above the configured ceiling, and stage only the exact reviewed file paths. Validate the staged set again with `git diff --cached --name-only -z` plus blob sizes before commit and push.
- Prove the guard in an isolated repository containing a small file and a sparse oversized file inside the same previously untracked directory: the small file may commit, while the oversized file must remain untracked.

## Password-vault and retention validation

- Resolve each affected 1Password login by exact username/title and pass its explicit vault ID to get/edit/readback. A successful cross-vault list does not prove an unqualified item get works. Generate replacement passwords in 1Password, never argv/chat, and validate each readback before the transactional database cutover.
- Preserve roles, enabled state, financial tables and encrypted MFA records during password rotation. Verify fresh password hashes against the vault, revoke sessions/trusted devices explicitly, and exercise public authentication without enrolling another person's pending MFA merely as a smoke test.
- Test historical GitHub exposure without copying the sensitive file into tool output: a bounded Range read of the old raw URL can prove retention from HTTP200/206 and the expected file signature. A clean main, unchanged tags and a removed local blob are not complete erasure while that old URL still serves it. Keep the support/login blocker explicit; never report a support ticket as filed without its real receipt.

## Validation evidence

- auto-commit and dependent jobs are paused during remediation;
- secret copies absent from the filesystem, working tree, current remote branch, and reachable local history;
- live credential file never staged;
- explicit force-with-lease succeeded against the recorded old head;
- old exact commit fetchability was tested and honestly reported; if the production clone was used for that probe, its rehydrated unreachable objects were pruned again;
- replacement credential works without value disclosure;
- derivative keys/backups were rotated when applicable;
- auto-commit and jobs resumed only after end-to-end readback.

## Communication

Lead with impact, not Git mechanics. State whether the live token, an old token, or both were exposed; whether dependent keys/backups are invalid; what is already contained; and the one manual step Rodolfo must perform. Never imply that a force push alone revoked a credential or erased every remote cache.