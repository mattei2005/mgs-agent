## Cron entry

```bash
# Adicionar ao crontab root (sem modificar entradas existentes)
(crontab -l 2>/dev/null; echo "*/15 * * * * /root/mgs-agent/scripts/monitor-NOME.sh >> /root/mgs-agent/logs/monitor-NOME.log 2>&1") | crontab -
```

---
