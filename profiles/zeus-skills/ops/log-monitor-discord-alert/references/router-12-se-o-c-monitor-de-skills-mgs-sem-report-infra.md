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
