# Discord tool progress cleanup and final-report delivery — 2026-06-30

## Trigger

Rodolfo reported that a Hermes/MGS update thread kept showing every tool breadcrumb/code snippet (`terminal`, `read_file`, `search_files`, command previews) instead of cleaning the workspace and delivering only the final report.

## Root cause

The global display setting was already quiet:

```yaml
display:
  tool_progress: off
```

But every MGS Discord profile had a platform-specific override that won in the resolver:

```yaml
display:
  platforms:
    discord:
      tool_progress: all
      tool_preview_length: 80
      cleanup_progress: true
```

Because `display.platforms.discord.tool_progress` has higher precedence than `display.tool_progress`, Discord still rendered the full live tool/activity stream.

## Correct MGS posture

For Zeus/Atena/Ares/agente legado Discord production channels, default to final-answer-first:

```yaml
display:
  tool_progress: off
  tool_preview_length: 0
  tool_progress_command: false
  platforms:
    discord:
      tool_progress: off
      tool_preview_length: 0
      cleanup_progress: true
      interim_assistant_messages: false
      busy_ack_detail: false
```

`cleanup_progress: true` is still useful as a safety net, but it does not replace disabling `tool_progress`; if a run crashes or a restart interrupts before cleanup, visible breadcrumbs may remain.

## Workflow for future repairs

1. Inspect both live profile configs and MGS mirrors:
   - `/root/.hermes/profiles/{zeus,atena,ares,legacy-agent}/config.yaml`
   - `/root/mgs-agent/profiles/{zeus,atena,ares,legacy-agent}-config.yaml`
2. Fix global and per-platform Discord settings; platform override wins.
3. Keep a backup in the live profile; remove temporary backup files from `/root/mgs-agent/profiles/` before committing/reporting.
4. Validate resolution, not just YAML presence:
   - import/use `gateway.display_config.resolve_display_setting(config, 'discord', 'tool_progress')`
   - expected: `off` for all four profiles.
5. Run targeted tests when touching Hermes display behavior:
   - `tests/gateway/test_display_config.py`
   - `tests/gateway/test_run_cleanup_progress.py`
6. For long update/restart operations, finalizer must deliver a clean final report after validation; do not rely on live tool progress as the operational report.

## Reporting rule

If Rodolfo asks “cadê o report?”, answer with the final validated status first, then explain the delivery failure. Do not force him to infer success from tool breadcrumbs.
