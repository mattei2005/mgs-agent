# Ares intraday — 1Password rate-limit diagnosis and recovery

## Symptom

The Ares intraday Discord thread received `runner_exit_1` every 30 minutes. The wrapper reported only that the runner exited before completion, while no new intraday audit was written.

## Confirmed boundary

A direct read-only runner smoke failed before any Meta API request or campaign write:

- failure point: `get_token_from_1password()`;
- 1Password response: `Too many requests` / client rate-limited;
- `op whoami` still returned successfully, so it was not sufficient as a credential-read health check;
- the previous helper could perform up to six `op item get` requests per execution by probing fields one by one, amplifying throttling;
- no production Meta write occurred because the operation remained dry-run/read-only.

## Durable correction

`/root/mgs-agent/scripts/ares-meta-common.py` was changed to:

1. make one `op item get --format json --reveal` request per run;
2. identify the token field from that single JSON response;
3. persist successful retrieval in `/root/.cache/mgs/ares-meta-token.json`;
4. enforce parent mode `0700` and file mode `0600`;
5. write cache atomically using a unique temporary file;
6. use the bounded cache during transient 1Password throttling;
7. return sanitized errors without exposing credential values.

The cache path is outside Git and must never be copied into tracked files or Discord output.

## Safe incident sequence

1. Pause the affected Hermes cron immediately to stop alert spam and further credential calls:
   `HERMES_HOME=/root/.hermes/profiles/ares hermes cron pause <job-id>`
2. Reproduce with the runner directly, capturing stdout/stderr in temporary files and sanitizing any displayed excerpt.
3. Fix request amplification before retrying 1Password.
4. Validate cache behavior with synthetic data: success write, rate-limit fallback, file mode `0600`, parent mode `0700`.
5. Keep the production cron paused if no valid cache exists and 1Password remains throttled.
6. Resume only after a real read-only runner smoke returns zero, creates a fresh audit with `errors=[]`, and cache permissions pass.
7. Read back the Ares `jobs.json` entry and confirm `enabled=true`, `state=scheduled`.

## Pitfalls

- Do not rely on `op whoami` as proof that `op item get` is currently allowed.
- Do not probe multiple candidate fields with separate 1Password calls in recurring jobs.
- Do not resume merely because the wrapper exits zero; this wrapper intentionally sanitizes operational errors and can return zero after reporting them.
- Do not fabricate or manually reconstruct the Meta token to seed the cache.
- Do not let a recovery action resume the cron before audit and permission readback pass.
