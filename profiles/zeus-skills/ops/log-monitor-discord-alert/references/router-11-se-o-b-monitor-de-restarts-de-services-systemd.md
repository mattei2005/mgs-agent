## SEÇÃO B — Monitor de Restarts de Services Systemd

### Quando usar
- Service Hermes crasha repetidamente e ninguém percebe
- Detectar padrão de instabilidade antes de virar incidente crítico

### Como funciona

Cron `*/5 * * * *` → `/root/mgs-agent/scripts/monitor-service-restarts.sh`:
1. Lê `NRestarts` de cada service via `systemctl show`
2. Calcula delta desde baseline da janela de 24h
3. Compara com thresholds e envia alerta via webhook Discord
4. Persiste estado em `/root/mgs-agent/data/service-restart-state.json`

### Services monitorados

| Service | Descrição |
|---|---|
| `zeus-gateway` | Gateway do agente Zeus (Discord) |
| `atena-gateway` | Gateway do agente Atena (Discord) |
| `mgs-autocommit` | Watcher de auto-commit git |

### Thresholds

| Nível | Delta em 24h | Ação |
|---|---|---|
| Silencioso | 0–2 | Nada |
| INFO | 3–4 | ⚠️ `[INFRA] [RESTART]` em #alerts-infra |
| WARN | 5+ | 🚨 `[INFRA] [RESTART]` + mention `<@344196393512075265>` |

Anti-spam: não reenviar mesmo nível por 12h por service.

### Schema do state file

```json
{
  "_meta": {
    "description": "Estado do monitor service-restart-watcher",
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

### Adicionar novo service

```bash
# No script monitor-service-restarts.sh
SERVICES=("zeus-gateway" "atena-gateway" "mgs-autocommit" "novo-service")
bash /root/mgs-agent/scripts/monitor-service-restarts.sh   # cria entrada no state
```

### Mensagens Discord

Usar embed + fields, **content vazio por padrão** em `#alerts-infra` — sem mention do Rodolfo, Zeus ou qualquer pessoa salvo alerta crítico com push explicitamente necessário.

Para batch de restarts, não usar tabela monoespaçada larga: no Discord mobile quebra horrível. Usar um field por serviço:

```json
{
  "content": "",
  "embeds": [{
    "title": "Restarts de serviços detectados",
    "color": 3447003,
    "fields": [
      {"name": "Serviços afetados", "value": "4", "inline": true},
      {"name": "zeus-gateway", "value": "Start: `Thu 2026-07-02 04:24:09 EDT`\nCausa: manutenção planejada/restart detectado\nAção: investigar só se repetir", "inline": false}
    ]
  }]
}
```

### Credencial

Webhook: 1Password vault `MGS Conteúdo`, item `Discord Webhook - Alerts Infra Channel`, field `webhook_url`.

---
