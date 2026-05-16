# RunCloud inventory hardening

Use this when maintaining `/root/mgs-agent/scripts/runcloud-inventory.sh` or any RunCloud API v3 inventory script.

## What matters

The RunCloud API shape for `/api/v3/servers/{server_id}/webapps` can differ from older examples:

```json
{
  "data": [...],
  "meta": {
    "pagination": {
      "total": 76,
      "count": 20,
      "per_page": 20,
      "current_page": 1,
      "total_pages": 4,
      "links": {"next": "...page=2"}
    }
  }
}
```

Do not rely only on `meta.lastPage`. Prefer:

```python
meta = data.get("meta", {})
pagination = meta.get("pagination", {}) if isinstance(meta, dict) else {}
total_pages = int(
    pagination.get("total_pages")
    or meta.get("lastPage", 1)
    or 1
)
```

## Secure script pattern

- Load `.env` only to make 1Password CLI work under cron/systemd.
- Fetch RunCloud token from 1Password at runtime.
- Never print token or token-derived values. Status output should be counts only.
- Pass token to Python via environment (`RUNCLOUD_TOKEN`) rather than embedding it in source or shell traces.
- Use `set -euo pipefail`.
- Add `--dry-run` and `--json` modes for safe validation.
- Write output atomically: `mktemp` then `mv`.
- Put tempfiles in `/tmp`, not repo root. If a temp pattern ever appears in the repo, add it to `.gitignore` and remove tracked temp files.

## Retry/backoff

RunCloud/API edge can return transient Cloudflare-style 403, 429, or 5xx. Treat these as retryable for a small bounded number of attempts:

```python
for attempt in range(1, 5):
    try:
        ...
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 429, 500, 502, 503, 504) and attempt < 4:
            time.sleep(2 * attempt)
            continue
        raise
```

Keep the error body short in logs (e.g. first 300 chars) and never include auth headers.

## Validation checklist

1. `bash -n scripts/runcloud-inventory.sh`
2. `scripts/runcloud-inventory.sh --dry-run`
3. `scripts/runcloud-inventory.sh --json > /tmp/runcloud-inventory.json` and parse JSON.
4. Compare new JSON against existing `inventario-webapps.json`:
   - total count
   - per-server counts
   - added/removed `webapp_id`s
5. Only run write mode after the dry-run/json output matches expectations.
6. Validate final files:
   - `inventario-webapps.json` JSON parse OK
   - `data/infra-inventory.json` regenerated if script inventory changed
   - `git ls-files '.runcloud-inventory.*'` returns 0

## Reporting

Report server totals in a compact aligned table:

```text
Servidor          | Total | WordPress
------------------|-------|----------
MatteiInc01       | 76    | 75
...
```

Do not report tokens, API headers, or 1Password field values.
