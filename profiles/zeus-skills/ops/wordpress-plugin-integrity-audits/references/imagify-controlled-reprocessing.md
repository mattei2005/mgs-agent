# Controlled Imagify reprocessing and closure

Use this for existing WordPress image-optimization failures after quota/account recovery, not for a new subscription or media redesign.

## Freeze and authorize

- Separate historical attachment errors from live entitlement: read the current API/account quota without exposing its key, then require a real one-attachment optimization. An unlimited-plan response is not evidence that old failures were reprocessed.
- Freeze attachment IDs whose native Imagify status is `error`, existing settings, media metadata, file hashes/dimensions and a retained filesystem/database recovery set before starting. Preserve backup, level, resize and Next-Gen/display settings; do not enable another format or change billing by implication.
- Resolve source/API shape from the installed plugin. On the inspected 2.2.7 implementation, `Imagify\Bulk\Bulk::get_instance()->get_bulk_instance('wp')->get_unoptimized_media_ids(2)` enumerates the native candidate set, and `run_optimize('wp',2)` queues work. Compare the complete returned ID set with the frozen authorized set before launch. The CLI `bulk-optimize` reports dispatch, not completion.

## Execute and prove completion

- Prefer native scheduling with a canary and bounded batches. Foreground status reads must enumerate WordPress image attachments and their native optimization process/data; raw `_imagify_status` row totals can include duplicate metadata and are not unique-attachment totals.
- Do not accept a successful `full` size or Action Scheduler `complete` row as full-media closure: every derived size can still be processing. Require attachment status `success` or `already_optimized`, unlocked process, valid existing image files for every native size, zero remaining media batches, inactive/unpaused native job and no pending bulk counter.
- If using a temporary foreground queue drain, first inspect the installed job implementation, pause through its supported method, require the native global process to be quiescent, prove the batches contain only frozen IDs, and test one batch. Isolate each claimed batch; preserve native task-before/size/task-after hooks, per-step queue updates and unlock. Do not race the native runner, replace vendor files, or silently enlarge concurrency/scope. Keep per-media receipts and a resumable batch on failure.
- After independent enumeration proves every target finished and the queue is empty, reconcile any stale visual bulk counter through native WordPress transient methods; never use a cleared progress indicator as the evidence of completion. Persist the raw before/after counter and do not attribute its lag to concurrency unless proven.
- Resume/complete only the now-empty owned queue, clear its native temporary health-check state, and prove no optimizer or queued worker can continue after delivery. Skip a resume already applied by a failed wrapper.
- WordPress database-backed scalar transients can read back integer marker `1` as string `"1"`. Record the observed type and accept only the exact documented marker representations; reconcile effects before retrying a mutating wrapper.

## Independent acceptance

- Compare optimized dimensions with the preserved pre-operation filesystem. A root-private restore is intentionally inaccessible to the WordPress Unix user: inspect it as the authorized root collector rather than weakening backup permissions or calling every null dimension a media regression.
- Require retained original backup for every newly processed target, valid dimensions, public image HTTP/content-type/bytes, full public HTML crawl and fixed-viewport browser/visual regression. Report source-file savings separately from page-transfer or Lighthouse performance; the CDN can retain older image bytes.
- Preserve original validation failures and receipts. A one-off third-party Google/GAM RUM error must be attributed by its actual stack, then retested without changing protected ad/tracking code; report persistent external failures separately from first-party regressions.

## Restricting root documentation without deletion

- When explicitly authorized to restrict `readme.html` and `license.txt`, preserve exact bytes, hash, mode, owner/group and private copies. A permission-only restriction can block public delivery while retaining files; prove public, cache-bypass and origin denial plus unchanged site routes.
- A WordPress-user checksum probe can fail because deliberately restricted documents are unreadable. Verify the core through an authorized privileged read collector, require every official checksum, and record the exact permission exception; do not describe that access failure as malicious drift or reopen the files to make the unprivileged validator green.
- Recheck document denial after future core updates, because an installer can reset document modes. Do not add system configuration, a cron, or a broader filesystem permission change without its separate scope/confirmation.
