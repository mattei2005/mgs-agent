# Hermes Codex OAuth + Auxiliary Compression Stability Pattern

## When this applies

Use this reference when Zeus/Atena or another Hermes gateway runs the main model via `openai-codex` / ChatGPT OAuth and shows any of:

- `Codex auxiliary Responses stream exceeded 30.0s total timeout`
- `Codex auxiliary Responses stream exceeded 120.0s total timeout`
- repeated gateway restarts during `Preflight compression`
- `HTTP 401` / `Codex OAuth token was rejected`
- large Discord operational threads with logs, scripts, and audit discussion

## Root cause pattern observed

The stability issue was not simply “GPT-5.5 is bad” or “large topics are bad”. It was the combination:

| Factor | Operational effect |
|---|---|
| Very large sessions | Preflight compression triggered around 64k–181k tokens |
| Auxiliary compression on `openai-codex/gpt-5.5` | summarization used the Codex Responses stream |
| Codex OAuth/provider latency | compression timed out at 30s/120s |
| OAuth drift between global/profile auth files | occasional `HTTP 401` token rejection |
| Gateway depends on compaction to continue | failures caused restarts / TEMPFAIL / crash loops |

Example log signatures:

```text
Preflight compression: ~135,736 tokens >= 64,000 threshold
Compacting context — summarizing earlier conversation
HTTP 401: Could not parse your authentication token
Codex OAuth token was rejected

WARNING root: Failed to generate context summary: Codex auxiliary Responses stream exceeded 120.0s total timeout
WARNING root: Session summarization failed after 3 attempts: Codex auxiliary Responses stream exceeded 30.0s total timeout
```

## Durable fix pattern

Keep the main reasoning model on Codex/GPT-5.5, but move Hermes auxiliary tasks to a fast API model:

```yaml
model:
  provider: openai-codex
  default: gpt-5.5

auxiliary:
  compression:
    provider: anthropic
    model: claude-haiku-4-5-20251001
  session_search:
    provider: anthropic
    model: claude-haiku-4-5-20251001
  skills_hub:
    provider: anthropic
    model: claude-haiku-4-5-20251001
  title_generation:
    provider: anthropic
    model: claude-haiku-4-5-20251001
```

Apply consistently to all auxiliary clients used by the profile, not just compression, unless there is a deliberate exception.

## OAuth sync pattern

Use a deterministic cron script to sync the global Codex OAuth auth file to profile auth files:

- source of truth: `/root/.hermes/auth.json`
- destinations: `/root/.hermes/profiles/{profile}/auth.json`
- compare semantic `last_refresh` fields, not mtime
- validate auth with a real POST safety check
- treat HTTP 400/405 as “auth reached endpoint”; treat 401/403 as abort
- atomic writes only
- no token/secret output
- run every 15 minutes with `flock`

Known production script pattern:

```text
/root/mgs-agent/scripts/sync-codex-oauth.sh
*/15 * * * * flock -n /var/lock/sync_codex_oauth.lock /root/mgs-agent/scripts/sync-codex-oauth.sh
```

## Why not just raise `compression.threshold`?

Raising threshold reduces compression frequency but makes each compression larger, slower, and riskier. It mostly delays the failure when the auxiliary model is the bottleneck.

Recommended starting point for large operational agents:

```yaml
compression:
  enabled: true
  threshold: 0.4
  target_ratio: 0.18
  protect_last_n: 16
```

If tuning is needed after observation:

| Symptom | Safer adjustment |
|---|---|
| too many unnecessary compactions | raise threshold slightly, e.g. `0.4 → 0.5` |
| context loss after compaction | increase `protect_last_n`, e.g. `16 → 24/32` |
| summary quality too weak | test Sonnet as `auxiliary.compression` |
| timeout returns | keep fast auxiliary model; inspect payload/logs |

## Restart validation sequence

For production gateway changes, restart the lower-risk agent first, then Zeus.

Validation criteria for each service over ~2 minutes:

1. service active at T+10s/T+60s/T+120s
2. zero explicit Anthropic/Haiku 4xx/5xx
3. zero Codex `HTTP 401`
4. no crash/restart loop or repeated TEMPFAIL
5. a single `Failed with result` tied to intentional Hermes restart can be OK if the new process starts cleanly
6. verify Discord adapter reconnects; systemd active alone is not full end-to-end validation

After Zeus restart, ask Rodolfo or send a simple Discord message and confirm Zeus responds within ~60s. Do not rely on title generation/renaming as the validation signal; existing threads may not trigger title generation.

## Rollback and scope discipline

- If validation fails, show recent journal evidence, do not keep changing things.
- Roll back from timestamped config/auth backups only after deciding whether the failure is config, auth, or provider latency.
- Do not fold unrelated cleanup into the stabilization window (`hermes-agent` disabled noise, cache cleanup, old env keys, old snapshots). Stabilize first, observe, then handle P2 cleanup later.

## Shell logging pitfall

When recording chat-log entries that contain `$0`, `$5`, price ranges like `~$5-20/mês`, or other shell metacharacters, do not place the full text directly inside double quotes. Use single-quoted heredoc substitution:

```bash
./scripts/chat-log.sh --tipo evento "$(cat <<'EOF'
Text with $0 and ~$5-20/mês preserved literally.
EOF
)"
```

This prevents bash expansion from corrupting the audit text.
