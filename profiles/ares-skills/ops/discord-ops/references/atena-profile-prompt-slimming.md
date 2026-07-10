# Atena profile prompt slimming for fast Discord operations

Use this when Rodolfo/Zeus is reducing Atena latency, avoiding Discord thread overhead, or editing profile-level instructions (`SOUL.md`, `config.yaml`, channel prompts).

## Durable lesson

Do not solve Discord/thread reliability by embedding long mandatory scripts in the agent prompt. For high-volume tasks like REC publishing, those scripts become preflight overhead and can trigger repeated reading/tool calls before the actual work starts.

## Preferred pattern

For Atena channel prompts and SOUL thread rules:

```text
- Responda na thread atual; não use send_message para resposta normal.
- Se for REC direto completo, não leia AGENT.md/SKILL/template/runner antes: chame mgs-rec-runner.py uma vez e resuma o JSON.
- Se a thread precisar de rename/mention, faça apenas a menor ação necessária; falha nisso não bloqueia a tarefa.
- Em thread com Zeus/Rodolfo, não mencione outro bot salvo pedido explícito de handoff.
```

Keep the channel prompt short. A successful cleanup reduced Atena's channel prompt for `#atena-content-agent` from ~4362 chars to ~442 chars.

## What to remove from prompts

Avoid profile/channel instructions that say:
- “execute this long Python script before any other action”; 
- “always read AGENT.md now”; 
- “always mention another bot when talking about it”; 
- long examples containing live bot/user mentions;
- full workflow checklists for REC publishing.

Keep those details in skills/references or deterministic scripts, not in the always-loaded prompt.

## Safe validation after profile edits

After editing Atena `SOUL.md` or `config.yaml`:

```bash
python3 - <<'PY'
import yaml
yaml.safe_load(open('/root/.hermes/profiles/atena/config.yaml'))
print('yaml_ok')
PY
/root/mgs-agent/scripts/sync-souls.sh
sudo -n systemctl restart atena-gateway.service
sleep 3
systemctl is-active atena-gateway.service
systemctl show atena-gateway.service -p ActiveState -p SubState -p MainPID --no-pager
```

The sync step is important because profile files are versioned through `/root/mgs-agent/profiles/` by `sync-souls.sh`; direct profile edits alone may not appear in git until sync runs.

## Pitfall

A restart may log the previous gateway process exiting with status 1 during systemd replacement. Check the new `MainPID` and `ActiveState=active` after restart before reporting failure.