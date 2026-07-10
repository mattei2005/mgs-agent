### Reinicialização

```bash
pkill -f "hermes -p atena gateway run"
sleep 2 && ps aux | grep "atena" | grep -v grep   # confirmar morte
# Reiniciar com terminal(background=true)
sleep 5 && tail -10 /root/.hermes/profiles/atena/logs/agent.log
```

Confirmar sucesso: `Connected as Atena#2956` + `✓ discord connected` + `Gateway running with 1 platform(s)`

