# Hermes Patches — MGS Digital Corp

Patches locais aplicados ao Hermes que precisam ser reaplicados após updates.

## busy_input_mode_queue_gateway.patch

### Problema
`busy_input_mode: queue` configurado em `config.yaml > display:` não funciona
em gateway mode (Discord). Hermes interrompe agente em execução com 
"⚡ Interrupting current task" quando nova mensagem chega.

### Causa raiz
`gateway/run.py` linha 1249-1250 define `_queue_during_drain_enabled()` que
só ativa queue mode quando `_restart_requested` está True (drain de restart).

A função `_handle_active_session_busy_message` no path "Normal busy case"
(linha ~1554) ignora completamente `_busy_input_mode` e sempre interrompe.

### Solução
Adicionar early return em `_handle_active_session_busy_message` checando
`self._busy_input_mode == "queue"` ANTES de interromper. Mensagem é 
enfileirada via `merge_pending_message_event` (já existe) e usuário recebe
ack diferente: "⏳ Message queued — ..."

### Aplicação
Patch aplicado em: 24/04/2026
Hermes versão: 0.10.0 (commit ce089169)
Ponto de inserção: gateway/run.py linha ~1571 (após merge_pending_message_event)

### Validação
1. Reiniciar gateway: systemctl restart zeus-gateway
2. Mandar mensagem que demora ao Zeus
3. Imediatamente mandar segunda mensagem
4. Esperado: "⏳ Message queued..." (ao invés de "⚡ Interrupting...")
5. Após primeira tarefa terminar, segunda é processada automaticamente

### Reaplicação após update
```bash
# Após qualquer git pull do hermes-agent:
# 1. Verificar se patch ainda é necessário (pode ter sido aceito upstream)
grep -n "PATCH (MGS Digital Corp)" /root/.hermes/hermes-agent/gateway/run.py

# 2. Se NÃO encontrou, reaplicar:
cd /root/.hermes/hermes-agent
patch -p1 < /root/mgs-agent/patches/hermes/busy_input_mode_queue_gateway.patch

# 3. Restart
systemctl restart zeus-gateway atena-gateway
```

### Status upstream
- Issue reportada em: [LINK A SER ADICIONADO]
- PR submetido: [se aplicável]

