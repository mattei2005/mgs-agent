### Regressão/quirk: `free_response_channels` pode desativar auto-thread

Quando Rodolfo relatar que está falando no canal principal e o agente responde ali mesmo sem abrir thread, não assumir que `auto_thread` foi desligado. Diagnóstico validado em 2026-05-22 no Zeus:

```bash
python3 - <<'PY'
import yaml
p='/root/.hermes/profiles/zeus/config.yaml'
c=yaml.safe_load(open(p)) or {}
d=c.get('discord',{}) or {}
for k in ['auto_thread','require_mention','thread_require_mention','free_response_channels','allowed_channels','no_thread_channels']:
    print(k, repr(d.get(k,'<missing>')))
PY
tr '\0' '\n' < /proc/$(systemctl show -p MainPID --value zeus-gateway.service)/environ \
  | grep -E '^DISCORD_.*(THREAD|CHANNEL|MENTION|IGNORE|AUTO)' \
  | sed -E 's/(TOKEN|KEY|SECRET)=.*/\1=[REDACTED]/'
git -C /root/.hermes/hermes-agent blame -L 4545,4558 -- gateway/platforms/discord.py
```

Causa observada: commit upstream `d55754456 fix(discord): keep free-response channels inline` alterou a condição para:

```python
skip_thread = bool(channel_ids & no_thread_channels) or is_free_channel
```

Efeito: se o canal do agente está em `free_response_channels` para aceitar mensagens sem `@bot`, o Hermes pode responder inline e não criar thread, mesmo com `DISCORD_AUTO_THREAD=true`. Para MGS, o comportamento desejado no canal Zeus é: aceitar mensagem sem mention **e ainda criar thread**.

Correção recomendada, se Rodolfo autorizar: patch local pequeno em `/root/.hermes/hermes-agent/gateway/platforms/discord.py` removendo `or is_free_channel` dessa condição, depois `py_compile`, restart controlado do gateway afetado e teste real no canal principal. Registrar patch em `/root/mgs-agent/patches/hermes/` para reaplicar após updates.

