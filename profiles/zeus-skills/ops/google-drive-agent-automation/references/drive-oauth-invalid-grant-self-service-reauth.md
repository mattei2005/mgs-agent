# Drive OAuth `invalid_grant` self-service reauthorization pattern

> Historical case study only. The Ares OAuth watchdog, helper scripts, 1Password item and local token files were retired in the `mgs-core-prod` cutover on 2026-07-17. Do not execute the legacy commands below or recreate those resources; use the canonical MGS Service Account.

Session pattern: Ares Drive OAuth watchdog detected Google token refresh failure:

```text
HTTP 400
error: invalid_grant
detail: Token has been expired or revoked.
```

## Durable lesson

A revoked/expired Google OAuth refresh token cannot be fully auto-healed by the VPS. Google requires fresh human consent. The automation goal is therefore **self-service repair**, not silent repair:

1. Detect `invalid_grant` during refresh.
2. Generate the Desktop OAuth authorization URL automatically from the stored non-secret `client_id`.
3. Include the URL and a short instruction in the watchdog alert.
4. User opens Google, approves, and pastes back the final `localhost` redirect URL or just the `code`.
5. Agent exchanges the code, stores the new `refresh_token` in the approved secret store/root-only fallback, then runs the watchdog again.
6. Watchdog emits recovery only after real refresh succeeds with HTTP 200.

This reduces the manual fix to one approval/copy-paste while respecting Google's consent boundary.

## Required implementation behavior

For script-only watchdogs that monitor Drive OAuth:

- Healthy refresh: stdout must stay empty so cron remains silent.
- `invalid_grant`: alert should include:
  - sanitized cause/impact;
  - desktop OAuth reauthorization URL;
  - instruction: “Abra o link, aprove o acesso e cole no Zeus a URL localhost final ou só o code.”
- Recovery: emit one concise recovered message only after refresh returns HTTP 200.
- Never print `client_secret`, `refresh_token`, `access_token`, raw 1Password JSON, or credential file contents.

## Smoke-test recipe

Use a temporary credential file, never damage the real one:

```bash
TMP_TOKEN=$(mktemp /tmp/ares-oauth-bad.XXXXXX.json)
TMP_STATE=$(mktemp /tmp/ares-oauth-state.XXXXXX.json)
python3 - "$TMP_TOKEN" <<'PY'
import json, sys
src='/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json'
d=json.load(open(src))
d['refresh_token']='invalid-refresh-token-for-watchdog-smoke-test'
open(sys.argv[1], 'w').write(json.dumps(d))
PY
chmod 600 "$TMP_TOKEN"
rm -f "$TMP_STATE"
ARES_DRIVE_OAUTH_CLIENT_TOKEN_FILE="$TMP_TOKEN" \
ARES_DRIVE_OAUTH_WATCHDOG_STATE="$TMP_STATE" \
ARES_DRIVE_OAUTH_WATCHDOG_REMIND_SECONDS=0 \
python3 /root/mgs-agent/scripts/ares-drive-oauth-watchdog.py > /tmp/watchdog-invalid.out
```

Validation expectations:

```text
[ARES-DRIVE-OAUTH-ALERT] present
Link de reautorização: https://accounts.google.com/o/oauth2/v2/auth?... present
client_secret / refresh_token / access_token absent
```

Then validate the real healthy path:

```bash
python3 /root/mgs-agent/scripts/ares-drive-oauth-watchdog.py > /tmp/watchdog-healthy.out
wc -c /tmp/watchdog-healthy.out   # expected 0 when healthy
```

## Reporting pattern

Tell Rodolfo directly:

- “Não dá para auto-corrigir 100%; Google exige novo consentimento humano.”
- “Dá para auto-gerar o link e reduzir a correção a aprovar + colar URL/código.”
- After implementation: report validated `invalid_grant` smoke test, healthy silent check, and secret non-exposure check.
