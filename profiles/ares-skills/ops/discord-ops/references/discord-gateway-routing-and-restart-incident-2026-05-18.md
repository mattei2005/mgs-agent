# Discord gateway routing + restart incident — 2026-05-18

## Trigger

Rodolfo opened REC benchmark threads in Atena's channel. Zeus also had the Atena channel in `allowed_channels` with free-response behavior, so Zeus woke up and created a duplicate thread for an Atena editorial request.

While fixing routing, Zeus restarted `zeus-gateway` during a large active conversation and also scheduled an LLM cron healthcheck. The gateway entered normal systemd drain (`deactivating/stop-sigterm`) and sent shutdown/retry messages that looked like repeated failures to the user.

## Durable lessons

1. Cross-channel visibility is not the same as response permission.
   - Zeus may need read/audit access to Atena threads.
   - Zeus should not free-respond in Atena's editorial channel.
   - Use mention-gated behavior outside Zeus' own admin channel.

2. Restart feedback must be minimal and deterministic.
   - Avoid creating an LLM cron job just to check a gateway restart.
   - If a healthcheck is needed, prefer script-only/no-agent or direct `systemctl` checks in the active turn.
   - Do not deliver a scheduled check back into a thread already receiving follow-up user messages unless there is no alternative.

3. `deactivating/stop-sigterm` during an active turn is expected until the gateway drains.
   - Look for `Shutdown phase: drain done`, `Gateway stopped`, followed by new `Connected as <bot>` and `Gateway running`.
   - A 60s terminal timeout on `systemctl restart` can be the agent waiting on its own service shutdown, not a failed restart.

## Safe routing target

For Zeus:

```yaml
discord:
  allowed_channels: "1496267442899521627,1496267571543019653"
  require_mention: true
  thread_require_mention: true
  free_response_channels: "1496267442899521627"
```

Environment variables should mirror the same intent if used by the gateway:

```bash
DISCORD_REQUIRE_MENTION=true
DISCORD_THREAD_REQUIRE_MENTION=true
DISCORD_FREE_RESPONSE_CHANNELS=1496267442899521627
```

Result:
- Zeus admin channel: normal Zeus responses.
- Atena content channel: Zeus only responds if mentioned directly.
- Atena threads: no duplicate Zeus thread unless Rodolfo intentionally calls Zeus.

## Runtime patch caveat

If Hermes' Discord runtime treats `require_mention=true` as disabling auto-thread everywhere, preserve auto-thread for `free_response_channels` only. Patch should be small, marked `PATCH (MGS Digital Corp)`, `py_compile` validated, and revisited after Hermes updates.

## User-facing incident response

If Rodolfo reports “travando toda hora” during this class of fix:
- Stop expanding scope.
- Verify both `zeus-gateway` and `atena-gateway` are active/running.
- Remove/conclude any ad-hoc cron checks.
- State exactly what is stable now and what was patched.
- Keep final answer short and end with the next operational action.
