### Diagnóstico

```bash
# 1. Verificar processo
ps aux | grep -E "hermes.*atena|hermes.*zeus" | grep -v grep

# 2. Últimas linhas do log
tail -30 /root/.hermes/profiles/atena/logs/agent.log

# 3. Checar chegada de mensagens
grep "inbound message" /root/.hermes/profiles/atena/logs/agent.log | tail -5

# 4. Loop de rate limit?
grep -E "Retry|inbound|response ready|ERROR" /root/.hermes/profiles/atena/logs/agent.log | tail -20
```

**Sessão stale confirmada quando:** processo vivo, log mostra `Connected as Atena#2956`, mas nenhum `inbound message` novo após mensagens enviadas.

