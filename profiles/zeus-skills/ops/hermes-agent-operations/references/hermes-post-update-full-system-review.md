# Hermes/MGS post-update full system review

Use when Rodolfo asks for a broad post-update audit or an operational sweep: "confere tudo", "confere se tudo no sistema está funcionando", "todas as funcionalidades, crons e patches", "padrões dos agentes" and "o que veio de novo".

## Scope

Do not stop at `hermes --version` or service status. Treat the review as four parallel dimensions:

1. **Runtime health** — gateways, crons, logs, disk/memory, reboot-required, pending OS/npm updates.
2. **MGS invariants** — local Hermes patches, profile configs, current OpenAI-Codex/model policy, thread auto-add, free-response/no-thread behavior, MGS OS JSON/context files.
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
systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service mgs-autocommit.service
systemctl show zeus-gateway.service atena-gateway.service ares-gateway.service \
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

For the active Zeus/Atena/Ares profiles, summarize without secrets:

- `model.provider=openai-codex`
- `model.default` equals the current Rodolfo-approved capable GPT pin (currently `gpt-5.6-sol`; do not preserve a stale `gpt-5.5` value by rote)
- `base_url=https://chatgpt.com/backend-api/codex`
- `compression.threshold=0.85`
- channel/free-response/no-thread/thread auto-add settings
- role-required media/tool configuration only; do not treat retired-agent capabilities as an active baseline
- auth presence: active provider, auth mode, access token length, refresh token present

Compare live config to mirrored `/root/mgs-agent/profiles/*-config.yaml` when those mirrors exist. If a pre-update snapshot exists, diff it and distinguish normal Hermes config migrations/comments from MGS policy changes.

Do not treat references to Claude/Anthropic inside disabled bundled skills, model catalog caches, archived notes, or commented examples as active provider usage. Active risk is in live `config.yaml`, `auth.json`, `.env`, service units, cron/scripts, or running processes.

## Functional smoke tests

Pick small deterministic probes; do not run full production workflows unless asked.

- Web search: use the MGS Brave probe script from this skill.
- TTS: do **not** generate or send audio to Rodolfo by default. Rodolfo does not find automatic audio useful; only run a tiny MP3 file/header check when he explicitly asks to validate TTS, and do not attach/send the audio unless requested.
- Image generation: verify only for active profiles whose current MGS OS role explicitly requires image/creative generation. Zeus is GM/admin and does not need image generation. Do not use a retired agent as an active capability baseline. Run a tiny image smoke only for an active expected image profile or when Rodolfo explicitly asks; never label a role-excluded profile as failed merely because image generation is unset.
- MGS OS: parse `data/sites.json` and `data/authorized-users.json`; confirm context files exist; report pending approvals count.

## Backup inventory after cleanup

When Rodolfo asks "quais backups tem" after a cleanup/recovery, do not reuse earlier report numbers. Re-scan live state and separate **large restorable profile/backups** from small manifests/patches/crontab backups:

```bash
du -sh /root/mgs-agent/backups /root/.hermes/backups /root/backups 2>/dev/null
python3 - <<'PY'
import os, time
roots=['/root/mgs-agent','/root/.hermes','/root']
rows=[]; seen=set()
for root in roots:
    for dirpath, dirnames, filenames in os.walk(root):
        if any(skip in dirpath for skip in ['/node_modules/','/.git/','/venv/','/.cache/uv/']):
            dirnames[:] = []
            continue
        for fn in filenames:
            p=os.path.join(dirpath, fn)
            if p in seen: continue
            seen.add(p)
            if not any(tok in fn.lower() for tok in ['backup','bak','preupdate','snapshot','.tar','.tgz','.gz','.zip','.patch']):
                continue
            try: st=os.stat(p)
            except OSError: continue
            if st.st_size >= 10*1024*1024:
                rows.append((st.st_size, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime)), p))
for size, mt, p in sorted(rows, reverse=True):
    print(f'{size/1024/1024:8.1f} MB | {mt} | {p}')
print('large_backup_count=', len(rows))
PY
```

Report disk (`df -h /`) and explicitly say when `large_backup_count=0`; otherwise stale pre-cleanup numbers can mislead Rodolfo.

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
