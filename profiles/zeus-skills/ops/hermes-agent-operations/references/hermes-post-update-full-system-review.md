# Hermes/MGS post-update full system review

Use when Rodolfo asks for a broad post-update audit: "confere se tudo no sistema está funcionando", "todas as funcionalidades, crons e patches", "padrões dos agentes" and "o que veio de novo".

## Scope

Do not stop at `hermes --version` or service status. Treat the review as four parallel dimensions:

1. **Runtime health** — gateways, crons, logs, disk/memory, reboot-required, pending OS/npm updates.
2. **MGS invariants** — local Hermes patches, profile configs, GPT-5.5/OpenAI-Codex policy, thread auto-add, free-response/no-thread behavior, MGS OS JSON/context files.
3. **Functional smoke tests** — selected real probes for capabilities that changed or are critical to the agents.
4. **Delta vs previous version** — what changed in Hermes/Codex/Node/npm/Corepack/Ubuntu packages, with MGS relevance.

## Recommended checks

```bash
repo=/root/.hermes/hermes-agent

# versions + git
hermes --version
git -C "$repo" fetch --quiet origin main
git -C "$repo" rev-parse --short HEAD
git -C "$repo" rev-parse --short origin/main
git -C "$repo" rev-list --count HEAD..origin/main
git -C "$repo" status --short
git -C "$repo" diff --stat
node -v
npm -v
npx --yes @openai/codex --version
corepack --version

# services
systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service hera-gateway.service mgs-autocommit.service
systemctl show zeus-gateway.service atena-gateway.service ares-gateway.service hera-gateway.service \
  -p Id -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStatus -p ExecMainStartTimestamp --no-pager

# system
apt list --upgradable 2>/dev/null | sed -n '1,80p'
npm outdated -g --depth=0 2>/dev/null | sed -n '1,80p' || true
[ -f /var/run/reboot-required ] && cat /var/run/reboot-required.pkgs || true

df -h /
df -ih /
free -h
```

## Crons and monitors

Check both Hermes scheduler jobs and root crontab/system cron. Important MGS success signals:

- Hermes cron patch watchdog enabled, last status OK.
- Root crontab jobs present and `cron.service` active.
- `monitor-cron-stale-logs` reports `problems=0`.
- `sync-codex-oauth` reports profiles in sync.
- `monitor-service-restarts` reports OK.
- `monitor-tool-loops` reports zero active alerts.
- `cron-control-plane` regenerated `docs/CRONS.md` with the expected job count.

## Patch/local invariants

Always run the canonical guard, then compile and run targeted tests from the Hermes repo:

```bash
/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh
py="$repo/venv/bin/python"; [ -x "$py" ] || py=python3
"$py" -m py_compile \
  "$repo/plugins/platforms/discord/adapter.py" \
  "$repo/gateway/run.py" \
  "$repo/gateway/config.py" \
  "$repo/tools/send_message_tool.py" \
  "$repo/tools/discord_tool.py"
cd "$repo"
"$py" -m pytest -q \
  tests/gateway/test_gateway_shutdown.py \
  tests/gateway/test_restart_resume_pending.py \
  tests/gateway/test_discord_free_response.py
```

Verify MGS-specific invariants by name when reporting:

- `_auto_thread_name_from_message`
- `DISCORD_THREAD_AUTO_ADD_USERS`
- `Auto-thread member sync`
- `REPORT-INFRA`
- `resume_pending`

## Profile/policy review

For Zeus/Atena/Ares/Hera, summarize without secrets:

- `model.provider=openai-codex`
- `model.default=gpt-5.5`
- `base_url=https://chatgpt.com/backend-api/codex`
- `compression.threshold=0.85`
- channel/free-response/no-thread/thread auto-add settings
- `image_gen` config, especially Hera (`openai-codex`, `gpt-image-2-medium`)
- auth presence: active provider, auth mode, access token length, refresh token present

Compare live config to mirrored `/root/mgs-agent/profiles/*-config.yaml` when those mirrors exist. If a pre-update snapshot exists, diff it and distinguish normal Hermes config migrations/comments from MGS policy changes.

Do not treat references to Claude/Anthropic inside disabled bundled skills, model catalog caches, archived notes, or commented examples as active provider usage. Active risk is in live `config.yaml`, `auth.json`, `.env`, service units, cron/scripts, or running processes.

## Functional smoke tests

Pick small deterministic probes; do not run full production workflows unless asked.

- Web search: use the MGS Brave probe script from this skill.
- TTS: generate a tiny MP3 and verify file size/header.
- Image generation: for Hera, run a tiny `hermes -p hera -t image_gen -z ...` generation and verify PNG dimensions/size.
- MGS OS: parse `data/sites.json` and `data/authorized-users.json`; confirm context files exist; report pending approvals count.

## Delta / "what came new"

If Hermes itself is already `HEAD == origin/main`, say there was no Hermes delta. Still report deltas for system packages and global CLIs.

For OpenAI Codex CLI, use GitHub release notes by tag when possible and summarize by MGS impact, not a raw changelog dump. Example useful categories from 0.133 → 0.138:

- local conversation history search
- stronger `--profile` behavior
- MCP setup/OAuth/schema improvements
- richer diagnostics (`codex doctor`)
- TUI markdown/link/menu/vim improvements
- archive/unarchive of sessions
- hosted web/image tools in more flows
- generated/local image paths exposed to the model
- app-server/auth/token-usage improvements
- performance improvements for large streams/histories

For Ubuntu packages, prefer the top changelog reason for security-sensitive packages: systemd CVEs, CUPS CVEs, Pillow CVEs, rsync security regression fixes, AppArmor reboot requirement.

## Reporting shape

Rodolfo prefers concise executive blocks with aligned `text` tables. Start with conclusion and active risks. Separate:

1. `Resumo executivo`
2. `Validações reais que rodei`
3. `Pendências / atenção`
4. `Padrões dos agentes`
5. `Novidades comparado com antes`

Call out `reboot-required` explicitly as the normal remaining action when kernel/AppArmor changed.
