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
## SEÇÃO C — Monitor de Skills MGS sem REPORT-INFRA

### Contexto

"Opção C" do sistema defense-in-depth MGS (implementado 2026-04-27). A "Opção A" é o checklist de encerramento nos SOUL.md dos agentes. Juntos, garantem que nenhuma skill MGS seja criada sem registro no inventário.

### Arquivos do sistema

```
/root/mgs-agent/scripts/check-pending-reports.sh   — script principal
/root/mgs-agent/data/pending-reports-state.json    — state anti-spam
/root/mgs-agent/logs/check-pending-reports.log     — output do cron
crontab: */15 * * * *
```

### Diretórios monitorados

| Agente | Diretório |
|--------|-----------|
| Zeus | `/root/.hermes/profiles/zeus/skills/ops/` |
| Atena | `/root/.hermes/profiles/atena/skills/wordpress/` |
| Atena | `/root/.hermes/profiles/atena/skills/devops/` |

**NÃO monitorados** (propositalmente): skills genéricas Hermes (apple/, creative/, mlops/ etc.).

### Schema do state file (pending-reports)

```json
{
  "alerted": {
    "zeus:skill-name": {
      "alerted_at": 1745726823,
      "skill_name": "skill-name",
      "agent": "zeus",
      "path": "/root/.hermes/profiles/zeus/skills/ops/skill-name"
    }
  },
  "resolved": {}
}
```

- Anti-spam: se `now - alerted_at < 86400s (24h)`, não reaterta
- Resolução: quando skill entra no inventário, remove de `alerted` e posta `✅ RESOLVIDO`

### Adicionar novo agente/diretório ao monitor

```bash
# Em SKILL_DIRS:
SKILL_DIRS["novo_agente"]="/root/.hermes/profiles/novo_agente/skills/ops"
# Em DIR_AGENT:
DIR_AGENT["novo_agente"]="novo_agente"
```

### Formato das mensagens Discord

**Alerta:** embed vermelho com fields `Pendências`, `Ação` e `Itens`.
`content` deve conter a mention necessária para o Zeus receber o evento: `<@1496296175014252634> pending report detectado`.

**Resolução:** embed verde com fields `Skill`, `Agent` e `Inventário`; `content` vazio.

### Pitfalls específicos do pending-report monitor

1. **Source correto:** `source "/root/mgs-agent/.env"` (tem `OP_SERVICE_ACCOUNT_TOKEN`), não `/root/.hermes/profiles/zeus/.env`
2. **Separador `|` não `:`:** `agent:skill_name` usa `:` — usar `|` como separador em arrays shell; `:` causa colisão e bugs silenciosos
3. **Persistir state ANTES de `curl`:** se curl falha, state deve já ter sido salvo (idempotência evita loop infinito)
4. **Bug histórico 2026-04-27:** combinação dos bugs acima causou ~120 mensagens duplicadas em 8h. Sempre validar com dry-run após modificar lógica de state transitions
5. **Resetar state:** `echo '{"alerted": {}, "resolved": {}}' > /root/mgs-agent/data/pending-reports-state.json`

### Fluxo completo esperado

```
[t=0]   Skill nova criada no filesystem mas não no inventário
[t=15m] Cron detecta → alerta Discord → state atualizado (alerted_at=now)
[t=30m] Cron → anti-spam (< 24h) → silêncio
[t=Xh]  Zeus/Atena atualiza infra-inventory.json
[t=X+15m] Cron → skill está no inventário → ✅ RESOLVIDO → remove de alerted
```

---
