# logs-aquisicao — threaded cron delivery and permission updates

Context: Ares Meta Ads calibration uses `logs-aquisicao` for read-only/dry-run recommendations. Rodolfo expects each actionable checkpoint/recommendation to open a thread where humans answer `REC... feito`, `ignorar`, `segurar` or `não mexer`.

## Pattern: script-only cron with thread creation

For Hermes `cronjob` entries with `no_agent=True`, do not assume platform auto-threading will happen from scheduler delivery. Use a wrapper that:

1. Runs the deterministic Meta script and captures stdout into a temp file.
2. If stdout is empty, exits silently.
3. If stdout is non-empty, posts the message to `logs-aquisicao` via Discord API.
4. Creates a thread from that message using `POST /channels/{channel_id}/messages/{message_id}/threads`.
5. Keeps wrapper stdout empty so the scheduler does not deliver the same message a second time.

Minimal wrapper shape:

```bash
#!/usr/bin/env bash
set -euo pipefail
TMP=$(mktemp)
cleanup() { rm -f "$TMP"; }
trap cleanup EXIT
/root/mgs-agent/scripts/ares-meta-cron-runner.py --job intraday --operation-id OpenzedFinanzas-CC-ES --account-id 1356770869843984 --account-tz Europe/Madrid >"$TMP"
if [ -s "$TMP" ]; then
  /root/mgs-agent/scripts/ares-discord-post-with-thread.py --channel-id 1516887105543077949 --fallback-title "Intraday Meta Ares" <"$TMP"
fi
```

Validation checklist:

```text
Check                  | Expected
-----------------------|-------------------------
bash -n wrappers        | OK
py_compile poster       | OK
poster --dry-run        | extracts sane thread title
cronjob list            | no_agent=true, enabled, deliver still points logs-aquisicao
real run                | one channel message + one thread, no duplicate scheduler message
```

## Pattern: adding users to logs-aquisicao

Before handing off to Zeus/admin, check if Ares already has permission in the channel. Use the bot token internally only; never print it.

Required Discord permissions for direct update:

```text
Permission                    | Why
------------------------------|--------------------------------------
VIEW_CHANNEL                  | validate/read channel
SEND_MESSAGES                 | cron reports
READ_MESSAGE_HISTORY          | thread/channel context
MANAGE_ROLES or MANAGE_CHANNELS | apply permission overwrites
CREATE_PUBLIC_THREADS         | create report threads
SEND_MESSAGES_IN_THREADS      | participate in report threads
MANAGE_THREADS                | manage/validate threads if needed
```

If permitted, apply user overwrites on `logs-aquisicao` with at least:

```text
VIEW_CHANNEL
SEND_MESSAGES
READ_MESSAGE_HISTORY
CREATE_PUBLIC_THREADS
SEND_MESSAGES_IN_THREADS
```

Then validate with `GET /channels/{channel_id}` that each requested user has an overwrite with those allow bits. Report only IDs/status, never token or headers.

If Ares lacks permission, send the request to Zeus using the real Zeus mention `<@1496296175014252634>` in the Zeus channel, not `#alerts-infra`.

## Pitfalls

- Saying “I asked Zeus” is not the same as adding users. If the user asks whether they are added, verify channel overwrites or clearly say it is pending.
- If permissions changed mid-session, re-check before assuming Ares still cannot do it.
- Do not leave an obsolete one-shot cron active after the account already reached the target state; remove it and send `[REPORT-INFRA]`.
