# Hera Bootstrap Session — 2026-06-06

Session-specific detail for bootstrapping the MGS Hera creative agent.

## Inputs confirmed by Rodolfo

```text
Agent/channel name  hera-creative-agent
Discord channel ID  1513005743954198538
Initial access      Rodolfo + Zeus bot + Atena bot + Ares bot
```

Known IDs used:

```text
Rodolfo       344196393512075265
Zeus bot      1496296175014252634
Atena bot     1496306920494202950
Ares bot      1508864261504630925
```

## Safe Phase 1 result shape

- Create `/root/.hermes/profiles/hera` cloned from Zeus.
- Immediately blank `/root/.hermes/profiles/hera/.env` `DISCORD_BOT_TOKEN`.
- Scope `.env` and `config.yaml` to channel `1513005743954198538`.
- Copy OpenAI Codex OAuth from Zeus/root into Hera and validate by token length only.
- Create `SOUL.md` for Creative Operations: criativos, vídeos, Canva/Drive, handoff para Ares; no Ads campaign execution and no WordPress publishing.
- Add `agents.hera` to `/root/mgs-agent/data/authorized-users.json`.
- Append audit event to `/root/mgs-agent/logs/events-audit.jsonl`.
- Update `/root/mgs-agent/scripts/sync-souls.sh` to include Hera in SOUL/config loops only.
- Run `/root/mgs-agent/scripts/sync-souls.sh` and validate `profiles/hera-soul.md` + `profiles/hera-config.yaml` exist.
- Do **not** create or start `hera-gateway.service` until a dedicated Hera bot token exists and Rodolfo confirms the system-file write.

## Pitfall found: inherited skill sync explosion

Cloning from Zeus can leave Hera with many bundled/inherited creative skills. Do **not** add a broad `hera-skills/creative` sync block by default. In this session, doing so caused ~299 inherited creative skill files to be versioned under `/root/mgs-agent/profiles/hera-skills/creative/` before being removed.

Correct rule: for a new MGS agent, add the agent to `sync-souls.sh` SOUL/config loops first. Add selective skill sync only after the agent has truly MGS-specific custom skills that should be versioned, not for inherited bundled/hub skills.

## Validation commands/evidence shape

Use validation that prints no secrets:

```bash
hermes profile show hera
python3 - <<'PY'
from pathlib import Path
import json, yaml
profile=Path('/root/.hermes/profiles/hera')
cfg=yaml.safe_load((profile/'config.yaml').read_text())
reg=json.loads(Path('/root/mgs-agent/data/authorized-users.json').read_text())
env={}
for line in (profile/'.env').read_text().splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        k,v=line.split('=',1); env[k]=v
auth=json.loads((profile/'auth.json').read_text())
tokens=auth.get('providers',{}).get('openai-codex',{}).get('tokens',{})
print('VALIDATION_OK')
print('model_provider=', cfg['model']['provider'], sep='')
print('model_default=', cfg['model']['default'], sep='')
print('discord_channel=', cfg['discord']['allowed_channels'], sep='')
print('discord_token_len=', len(env.get('DISCORD_BOT_TOKEN','')), sep='')
print('openai_codex_access_token_len=', len(tokens.get('access_token','')), sep='')
print('openai_codex_refresh_present=', bool(tokens.get('refresh_token')), sep='')
print('authorized_ids=', ','.join(reg['agents']['hera']['authorized_user_discord_ids']), sep='')
PY
systemctl list-unit-files 'hera-gateway.service' --no-legend || true
systemctl is-active hera-gateway.service 2>/dev/null || true
git -C /root/mgs-agent status --short
```

Expected after Phase 1:

```text
discord_token_len=0
Gateway stopped
hera-gateway.service absent/inactive
/root/mgs-agent clean and pushed by auto-push
```
