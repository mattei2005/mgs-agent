# Git Auto-Commit Secret Containment

## Trigger

Use when a credential or secret-bearing editor/backup copy may have entered an auto-committed MGS repository, especially during `.env` or token rotation.

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
8. Test whether the old commit is still fetchable by exact SHA. A clean branch and successful force push do not prove server-side purge. If the old object remains reachable, escalate to GitHub Support sensitive-data removal while keeping the credential revoked.
9. Expire local reflogs and prune unreachable objects only after the remote rewrite is validated. Do not run overlapping `git gc` processes; reconcile an existing auto-gc before retrying.
10. Rotate every derivative secret the leaked credential could read. Example: if an exposed 1Password Service Account token could retrieve a disaster-recovery private key, that encryption key and backups encrypted with it are compromised too. Pause jobs, retire the key, remove affected remote backups, create a new key only after the token is rotated, and repeat backup plus isolated restore validation.
11. Resume auto-commit and dependent jobs only after token, derivative key, Git history, current tree, and remote readbacks all pass.

## Validation evidence

- auto-commit and dependent jobs are paused during remediation;
- secret copies absent from working tree and current remote branch;
- live credential file never staged;
- explicit force-with-lease succeeded against the recorded old head;
- reachable local history contains zero named secret paths;
- old exact commit fetchability was tested and honestly reported;
- replacement credential works without value disclosure;
- derivative keys/backups were rotated when applicable;
- auto-commit and jobs resumed only after end-to-end readback.

## Communication

Lead with impact, not Git mechanics. State whether the live token, an old token, or both were exposed; whether dependent keys/backups are invalid; what is already contained; and the one manual step Rodolfo must perform. Never imply that a force push alone revoked a credential or erased every remote cache.