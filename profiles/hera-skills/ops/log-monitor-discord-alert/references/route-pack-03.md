## Triage operacional de alertas já disparados

Quando Rodolfo pedir para "resolver um por um" alertas de Discord/cron/infra, não assumir que todos ainda estão ativos. Fazer triagem read-only primeiro e classificar cada alerta como **ativo**, **resolvido**, **histórico**, **state-corruption** ou **teste/layout** antes de mexer em scripts. Após incidente de disco cheio/ENOSPC, seguir `references/cron-enospc-recovery.md`: validar JSONs de state, reconstruir `service-restart-state.json` se zerado, rodar scripts em modo dry-run/manual seguro e limpar o estado do stale monitor com uma execução real quando `resolved=N`.

Checklist validado:

```bash
# Estado atual do monitor e últimos eventos
tail -80 /root/mgs-agent/logs/monitor-NOME.log
jq . /root/mgs-agent/data/NOME-state.json 2>/dev/null || true

# Se for script shell, validar sintaxe de todos os monitors tocados
bash -n /root/mgs-agent/scripts/monitor-NOME.sh

# Executar manualmente só quando for seguro/idempotente; usar --dry-run quando existir
/root/mgs-agent/scripts/monitor-NOME.sh --dry-run
/root/mgs-agent/scripts/monitor-NOME.sh >> /root/mgs-agent/logs/monitor-NOME.log 2>&1

# Confirmar resolução pelo log/state após a execução
tail -20 /root/mgs-agent/logs/monitor-NOME.log
```

Padrão de resposta para o CEO: tabela curta com `Item | Status agora | Decisão`. Separar claramente pendências deliberadas (ex: update Hermes em outro tópico) de problemas resolvidos. Se um erro apareceu em log mas `bash -n` e execução real passam depois, reportar como "não reproduzido no estado atual" e citar a validação feita, sem inventar causa.

---
## Atualizar infra-inventory.json

Após criar os artefatos, atualizar manualmente 3 seções do inventário:

```json
// crons: adicionar
{
  "entry": "*/15 * * * * /root/mgs-agent/scripts/monitor-NOME.sh >> /root/mgs-agent/logs/monitor-NOME.log 2>&1",
  "description": "Monitor de ..."
}

// scripts: adicionar
{
  "path": "/root/mgs-agent/scripts/monitor-NOME.sh",
  "size_bytes": N,
  "modified_at": "TIMESTAMP",
  "description": "..."
}

// data_files: adicionar
{
  "path": "/root/mgs-agent/data/NOME-monitor.json",
  "description": "Estado do monitor. Campos: last_check, consecutive_failures, last_alert_sent, last_failure_details.",
  "modified_at": "TIMESTAMP"
}
```

---
