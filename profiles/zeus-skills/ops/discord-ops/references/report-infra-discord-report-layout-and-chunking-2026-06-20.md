# REPORT-INFRA — Discord report layout/chunking validation (Ares HOA precedent)

## Context

Ares reported several infra changes around `logs-aquisicao` Meta/HOA reports:

- `ares-meta-hoa-manager.py` changed the HOA report to list all campaigns for the active focus page, not just watchlist rows.
- `ares-discord-post-with-thread.py` changed long-message splitting so Discord chunks do not cut through fenced ` ```text ` table blocks.
- Follow-up changed labels from technical `[parte 1/4]` to natural `Parte 1 de 4` and humanized the report introduction.

## Durable lesson

For REPORT-INFRA involving Discord report/poster scripts, validating syntax and hashes is not enough. The output contract is visual and must be checked with the real dry-run/preview path.

Minimum validation checklist:

1. `python3 -m py_compile` for Python scripts.
2. `sha256sum` matches report.
3. Generate representative report output (for HOA: `ares-meta-hoa-manager.py --always-output`).
4. Pipe that output through the poster in `--dry-run` mode.
5. Confirm:
   - every chunk is under 2000 chars;
   - chunker does not split inside fenced code blocks;
   - code fences are balanced per posted chunk or by complete-block grouping;
   - expected user-facing columns are present;
   - removed/undesired columns are absent;
   - part labels are user-readable, not internal/debug-looking;
   - intro text is human and concise, not cron/debug jargon.
6. Secret-scan changed scripts before commit.
7. Inventory both scripts if both are part of the output contract, even when one script’s SHA did not change but was part of validation.

## Example dry-run pattern

```bash
python3 -m py_compile \
  /root/mgs-agent/scripts/ares-meta-hoa-manager.py \
  /root/mgs-agent/scripts/ares-discord-post-with-thread.py

python3 /root/mgs-agent/scripts/ares-meta-hoa-manager.py --always-output \
  > /tmp/ares-hoa-preview.out

python3 /root/mgs-agent/scripts/ares-discord-post-with-thread.py \
  --thread-id <thread_id> --dry-run \
  < /tmp/ares-hoa-preview.out
```

Expected dry-run facts should include `chunks`, `max_chunk_len`, and every chunk length must be `< 2000`. For report tables, inspect the generated preview text for balanced fences and expected headings.

## Pitfall

A chunker that only splits by character count can produce valid JSON/API payloads while visually breaking Discord tables by cutting between ` ```text ` and closing ` ``` `. Treat this as a report-layout bug even if Discord accepts the messages.