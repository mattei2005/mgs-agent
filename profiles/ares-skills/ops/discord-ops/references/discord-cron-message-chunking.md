# Discord cron message chunking — Ares HOA failure 2026-06-20

## Trigger

A script-only Hermes cron posts a deterministic report to Discord via a helper script/API call, and the scheduler emits an error like:

```text
Invalid Form Body
BASE_TYPE_MAX_LENGTH: Must be 2000 or fewer in length.
Script exited with code 3
stage=post_message
```

Observed with Ares HOA manager: the generated report was 2006 characters and Discord rejected the `content` field because message content must be <= 2000 characters.

## Durable lesson

For cron/report posters that call `POST /channels/{id}/messages` directly, do not assume the report body fits in one Discord message. Implement chunking in the posting helper, not in each reporting script.

Recommended behavior:

1. Read stdin normally; exit silently on empty stdin.
2. Split content below the hard limit, preferably ~1900 chars to leave room for labels/future formatting.
3. Prefer splitting on line boundaries; fall back to fixed-size chunks for very long single lines.
4. Add small labels like `[parte 1/2]` only when there is more than one chunk.
5. For existing thread mode: post all chunks directly into that thread.
6. For channel + create-thread mode: post chunk 1 to the channel, create the thread from that message, then post remaining chunks inside the created thread.
7. Include `chunks`, `chunk_lengths`, and `max_chunk_len` in dry-run output so the fix is verifiable without sending a live Discord message.

## Validation pattern

```bash
python3 -m py_compile /root/mgs-agent/scripts/ares-discord-post-with-thread.py

/root/mgs-agent/scripts/ares-meta-hoa-manager.py \
  --operation-id OpenzedFinanzas-CC-ES \
  --account-id 1356770869843984 \
  --account-tz Europe/Madrid \
  --always-output \
| /root/mgs-agent/scripts/ares-discord-post-with-thread.py \
  --thread-id <THREAD_ID> \
  --fallback-title 'HOA Gestor Ares' \
  --dry-run

python3 - <<'PY'
import importlib.util
p='/root/mgs-agent/scripts/ares-discord-post-with-thread.py'
spec=importlib.util.spec_from_file_location('poster', p)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
for size in [1999,2000,2001,2050,5000]:
    chunks=mod.with_part_labels(mod.split_message('x'*size))
    print(size, len(chunks), max(map(len,chunks)), all(len(c)<=2000 for c in chunks))
PY
```

Expected: every chunk length <= 2000. A realistic report slightly over limit should become 2 chunks.

## Operational reporting

If the helper under `/root/mgs-agent/scripts/` is modified, send `[REPORT-INFRA]` with:

- script path;
- reason: fix Discord 2000-char report failure;
- validation evidence: `py_compile ok`, dry-run chunk count/max length, and optional sha256.

No gateway restart is needed when cron invokes the helper script directly; the next cron run uses the updated file.
