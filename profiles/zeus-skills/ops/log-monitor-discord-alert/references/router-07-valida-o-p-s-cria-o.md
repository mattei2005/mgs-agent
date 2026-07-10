## Validação pós-criação

```bash
# 1. Permissões
chmod +x /root/mgs-agent/scripts/monitor-NOME.sh
ls -la /root/mgs-agent/scripts/monitor-NOME.sh
# Esperado: -rwxr-xr-x

# 2. Dry-run manual
bash /root/mgs-agent/scripts/monitor-NOME.sh
# Esperado: "OK: zero falhas" + sem Discord enviado

# 3. State file populado
jq . /root/mgs-agent/data/NOME-monitor.json
# Esperado: last_check com timestamp, consecutive_failures=0

# 4. Cron ativo
crontab -l | grep monitor-NOME
```
