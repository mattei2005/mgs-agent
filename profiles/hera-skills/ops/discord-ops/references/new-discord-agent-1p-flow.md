# New Discord agent bot token + 1Password validation

Use when creating a new MGS Discord/Hermes agent (e.g. Ares) and wiring its bot token, webhook and gateway service.

## Durable lesson

Do not assume a newly-created 1Password item contains the custom fields the user named in chat. Validate via 1Password CLI before writing `.env` or starting systemd.

## Expected 1Password shape

Vault: `MGS Conteúdo`

Bot item:

```text
Title: Discord Bot - <Agent>
Field: discord_bot_token   # concealed/string, non-empty, typical Discord bot token len ~70+
```

Webhook item:

```text
Title: Discord Webhook - <Agent> Channel
Fields:
  webhook_url              # Discord webhook URL, non-empty
  canal                    # Discord channel ID/name metadata
```

## Safe validation pattern

1. Source `/root/mgs-agent/.env` with `set -a` so `OP_SERVICE_ACCOUNT_TOKEN` is exported for `op` subprocesses:

```bash
set -a; source /root/mgs-agent/.env; set +a
```

2. Inspect item metadata without printing secrets:

```bash
op item get 'Discord Bot - Ares' --vault 'MGS Conteúdo' --format json > /tmp/item.json
python3 - /tmp/item.json <<'PY'
import json, sys
data=json.load(open(sys.argv[1]))
for f in data.get('fields', []):
    label=f.get('label') or f.get('id') or ''
    val=f.get('value') or ''
    typ=f.get('type') or ''
    print(f'- {label} type={typ} len={len(val)} has_value={bool(val)}')
PY
```

3. If direct `op://MGS Conteúdo/...` references fail because of non-ASCII vault name or spaces, resolve vault/item IDs and use ID-based refs:

```bash
op vault list --format json > /tmp/vaults.json
# find MGS Conteúdo vault id, then:
op read 'op://<vault_id>/<item_id>/discord_bot_token'
```

4. Only after `discord_bot_token` is present and non-empty, patch `/root/.hermes/profiles/<agent>/.env`.

## Pitfalls

- 1Password LOGIN items may show only built-in fields (`username`, `password`, `notesPlain`) if the custom field was not actually saved or is in a location invisible to the service account.
- A webhook URL is not a bot token. Do not use `Discord Webhook - <Agent> Channel` to populate `DISCORD_BOT_TOKEN`.
- Never print token/webhook values in chat or logs. Report only field name and length.
- `source /root/mgs-agent/.env` without `set -a` can leave `OP_SERVICE_ACCOUNT_TOKEN` unexported; `op` then reports “No accounts configured”.
- Creating `/etc/systemd/system/<agent>-gateway.service` is a Critical Subset/system-file modification in MGS; require explicit confirmation before installing/enabling it.

## Minimal success criteria before starting gateway

```text
Profile exists                          OK
/root/.hermes/profiles/<agent>/.env      DISCORD_BOT_TOKEN len>50
config.yaml allowed channel              target Discord channel only
1Password bot item                       discord_bot_token exists, non-empty
systemd unit                             user explicitly confirmed install
systemctl is-active                      active after restart
agent.log                                Discord connected / gateway running
```
