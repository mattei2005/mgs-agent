# Discord live progress vs. agent-loop pollution — 2026-06-16

## Context

Rodolfo corrected Zeus after a agente legado thread showed only `agente legado is typing...` while agente legado was actively generating assets. Zeus initially framed live tool/progress breadcrumbs as the same kind of “pollution” Rodolfo had complained about previously.

That was wrong.

## Durable distinction

- **Bad pollution** = agents/bots talking to each other indefinitely, ACK/status chatter, lifecycle notices, low-information bot replies, or mentions that wake another agent and create loops.
- **Useful live progress** = short Discord breadcrumbs showing what the agent is doing while it works, e.g. analyzing reference, generating image, generating video, validating output.

Do not disable useful live progress as an anti-loop measure. Anti-loop protection belongs in bot-message filtering, mention discipline, thread lifecycle discipline, and stop-after-accept behavior.

## Preferred MGS profile setting

For active MGS Discord agents when Rodolfo wants visible progress:

```yaml
display:
  platforms:
    discord:
      tool_progress: all
      tool_preview_length: 80
      cleanup_progress: true
      interim_assistant_messages: false
```

Meaning:
- `tool_progress: all` — show live progress/tool breadcrumbs.
- `tool_preview_length: 80` — keep previews short; avoid large dumps.
- `cleanup_progress: true` — remove breadcrumbs after the final answer succeeds.
- `interim_assistant_messages: false` — avoid extra assistant chatter.

## Operational sequence validated

When applying this across MGS agents:

1. Patch both active profile configs and versioned copies:
   - `/root/.hermes/profiles/{zeus,atena,ares,legacy-agent}/config.yaml`
   - `/root/mgs-agent/profiles/{zeus,atena,ares,legacy-agent}-config.yaml`
2. Validate YAML and effective values for each agent.
3. Append an audit event explaining that Rodolfo clarified “pollution” means multi-agent loops, not live progress breadcrumbs.
4. Let auto-commit capture the versioned config change, or verify that it did.
5. Restart via `/root/mgs-agent/scripts/mgs-gateway-restart-safe.sh`, detached, with Zeus last.

## Pitfall

Do not tell Rodolfo “trace/progress is off because you wanted less pollution” unless the prior complaint specifically targeted live breadcrumbs. In MGS Discord operations, assume “poluição” means loop/chat noise between agents unless Rodolfo says otherwise.
