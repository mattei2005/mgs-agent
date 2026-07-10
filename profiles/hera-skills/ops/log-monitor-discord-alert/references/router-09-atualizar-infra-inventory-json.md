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
