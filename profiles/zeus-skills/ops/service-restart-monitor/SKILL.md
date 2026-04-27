---
name: service-restart-monitor
description: "Monitor automático que detecta restarts inesperados de services Hermes (zeus-gateway, atena-gateway, mgs-autocommit) e alerta em #alerts-infra via webhook Discord."
tags: [monitor, systemd, restart, infra, discord, alert, cron]
related_skills: [log-monitor-discord-alert, shell-cron-env-export]
---

# Service Restart Monitor

## Quando usar
- Service Hermes crasha repetidamente e ninguém percebe
- Detectar padrão de instabilidade antes de virar incidente crítico
- Auditoria de uptime de services MGS

## Como funciona

1. Cron `*/5 * * * *` executa `/root/mgs-agent/scripts/monitor-service-restarts.sh`
2. Script lê `NRestarts` de cada service via `systemctl show`
3. Calcula delta desde o baseline da janela de 24h
4. Compara com thresholds e envia alerta via webhook Discord
5. Persiste estado em `/root/mgs-agent/data/service-restart-state.json`

## Services monitorados

| Service | Descrição |
|---|---|
| `zeus-gateway` | Gateway do agente Zeus (Discord) |
| `atena-gateway` | Gateway do agente Atena (Discord) |
| `mgs-autocommit` | Watcher de auto-commit git |

## Thresholds

| Nível | Delta em 24h | Ação |
|---|---|---|
| Silencioso | 0–2 | Nada |
| INFO | 3–4 | ⚠️ `[INFRA] [RESTART]` em #alerts-infra |
| WARN | 5+ | 🚨 `[INFRA] [RESTART]` + mention `<@344196393512075265>` |

Anti-spam: não reenviar mesmo nível por 12h por service.

## Schema do state file

```json
{
  "_meta": {
    "description": "Estado do monitor service-restart-watcher",
    "created": "ISO8601Z",
    "thresholds": {"info": 3, "warn": 5},
    "window_hours": 24,
    "anti_spam_hours": 12
  },
  "services": {
    "zeus-gateway": {
      "baseline_nrestarts": 0,
      "baseline_timestamp": "ISO8601Z",
      "window_start": "ISO8601Z",
      "last_alert_sent": null,
      "last_alert_level": null
    }
  }
}
```

- `baseline_nrestarts`: valor de NRestarts no início da janela de 24h
- `window_start`: quando a janela corrente começou (reset automático a cada 24h)
- `last_alert_sent`: ISO8601 do último alerta enviado (para anti-spam)
- `last_alert_level`: `"info"` ou `"warn"` (para anti-spam por nível)

## Adicionar novo service

1. Editar `/root/mgs-agent/scripts/monitor-service-restarts.sh`
2. Adicionar o nome do service (sem `.service`) no array:
   ```bash
   SERVICES=("zeus-gateway" "atena-gateway" "mgs-autocommit" "novo-service")
   ```
3. Rodar manualmente para criar entrada no state file:
   ```bash
   bash /root/mgs-agent/scripts/monitor-service-restarts.sh
   ```
4. Confirmar nova entrada em `service-restart-state.json`

## Convenção de mensagem

- INFO: `⚠️ [INFRA] [RESTART] \`{service}\` reiniciou {N}x nas últimas 24h. Acompanhar.`
- WARN: `🚨 [INFRA] [RESTART] \`{service}\` reiniciou {N}x nas últimas 24h. Investigar urgente. <@344196393512075265>`

## Validar funcionamento

```bash
# Dry-run manual
bash /root/mgs-agent/scripts/monitor-service-restarts.sh

# Verificar cron
crontab -l | grep monitor-service-restarts

# Ver estado atual
cat /root/mgs-agent/data/service-restart-state.json

# Ver últimas execuções
tail -20 /root/mgs-agent/logs/monitor-service-restarts.log
```

## Credencial necessária

Webhook no 1Password vault `MGS Conteúdo`, item `Discord Webhook - Alerts Infra Channel`, field `webhook_url`.

## REPORT-INFRA obrigatório

Qualquer modificação ao script ou state file deve gerar `[REPORT-INFRA]` no canal `#zeus-admin-agent` conforme padrão canônico, mencionando `<@1496296175014252634>` (bot Zeus) e `<@344196393512075265>` (Rodolfo).
