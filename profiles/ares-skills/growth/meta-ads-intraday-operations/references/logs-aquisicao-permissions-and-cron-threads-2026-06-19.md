# logs-aquisicao permissions and cron thread posting — 2026-06-19

Context: Rodolfo wanted managers added to `logs-aquisicao`, and confirmed the Ares Meta cron workflow should open threads so humans can reply with decisions.

## Channel

```text
Channel        | logs-aquisicao
Channel ID     | 1516887105543077949
Ares profile   | /root/.hermes/profiles/ares
```

Ares can validate channel permissions with the Discord bot token from the profile `.env` without printing it. Confirm at least:

```text
VIEW_CHANNEL
SEND_MESSAGES
READ_MESSAGE_HISTORY
CREATE_PUBLIC_THREADS
SEND_MESSAGES_IN_THREADS
MANAGE_THREADS
```

In this session Ares also had `MANAGE_CHANNELS` and `MANAGE_ROLES`, which allowed permission overwrites for individual users.

## Adding humans to logs-aquisicao

Use Discord API permission overwrites on the channel when Ares has permission. Grant:

```text
VIEW_CHANNEL
SEND_MESSAGES
READ_MESSAGE_HISTORY
CREATE_PUBLIC_THREADS
SEND_MESSAGES_IN_THREADS
```

Validate by reading `GET /channels/<channel_id>` and confirming the overwrite exists for each user. Do not report success from the PUT alone.

Users added in this session:

```text
Geizian | 321263240782807040
Isliago | 432898782188011543
Kelly   | 1291113428982693940
Icaro   | 409878085807112207
Joe     | 1214246869484576890
Nicolas | 1055570806945620030
```

## Thread-posting pattern for script-only crons

Hermes script-only cron delivery posts stdout to the target, but may not automatically create per-recommendation threads. For human decision workflows, make the wrapper post the Discord message and create the thread itself, then keep stdout empty so the scheduler does not duplicate the message.

Implemented helper:

```text
/root/mgs-agent/scripts/ares-discord-post-with-thread.py
```

Wrapper pattern:

```bash
TMP=$(mktemp)
cleanup() { rm -f "$TMP"; }
trap cleanup EXIT
/root/mgs-agent/scripts/ares-meta-cron-runner.py ... >"$TMP"
if [ -s "$TMP" ]; then
  /root/mgs-agent/scripts/ares-discord-post-with-thread.py --channel-id 1516887105543077949 --fallback-title "Intraday Meta Ares" <"$TMP"
fi
```

The helper:
1. Reads the cron message from stdin.
2. Posts it to `logs-aquisicao`.
3. Creates a thread from that message.
4. Uses the first title line inside the ```text block as thread title.
5. Exits silently when stdin is empty.

Updated wrappers:

```text
/root/.hermes/profiles/ares/scripts/ares-meta-intraday-cron.sh
/root/.hermes/profiles/ares/scripts/ares-meta-reactivate-all-cron.sh
/root/.hermes/profiles/ares/scripts/ares-meta-hoa-manager.sh
```

## Validation

Before reporting success:

```text
Check                         | Required
------------------------------|------------------------------
Channel permissions            | GET channel + computed perms
User permission overwrites      | GET channel after PUT
Wrapper syntax                  | bash -n
Python helper syntax            | py_compile
Poster title extraction         | --dry-run with sample message
Cron registration               | cronjob list
```

## Pitfalls

- If a cron wrapper posts directly to Discord, it must not also leave stdout for Hermes scheduler delivery unless duplicate messages are desired.
- Do not say the workflow opens threads just because the report text says “responda na thread”; verify the delivery layer actually creates the thread.
- If Ares lacks Discord admin permission, mention Zeus explicitly in the Zeus channel and ask him/admin to add users; do not claim completion.
