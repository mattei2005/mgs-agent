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
- Issue reportada em: https://github.com/NousResearch/hermes-agent/issues/14905
- PR submetido: [se aplicável]


## discord-new-thread-ai-title-once.patch

### Problema
Threads Discord nasciam com título provisório determinístico de `adapter.py::_auto_thread_name_from_message()`, mas o callback de `agent/title_generator.py` estava desligado para Discord para evitar re-renomear threads antigas após idle/reset.

### Solução
Manter o título provisório na criação e permitir exatamente um rename por IA após a primeira resposta, com fail-closed:
- `adapter.py::_remember_auto_thread_initial_title()` salva em memória o título provisório realmente usado por thread_id.
- `run.py::_discord_thread_safe_to_autorename()` só autoriza rename se a thread é recente, pertence ao bot e o nome atual ainda iguala o provisório salvo.
- `run.py::_discord_title_message_from_gateway_text()` remove channel_context e prefixo `[Nome]` antes de enviar texto ao `title_generator.py`.
- Após rename bem-sucedido, o cache por thread é removido com `pop()`.

### Reaplicação após update
```bash
cd /root/.hermes/hermes-agent
git apply /root/mgs-agent/patches/hermes/discord-new-thread-ai-title-once.patch
python3 -m py_compile plugins/platforms/discord/adapter.py gateway/run.py
/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh
```

### Validação
1. Thread nova Discord: nasce com título provisório.
2. Após primeira resposta: log `Discord thread renamed from auto-generated title`.
3. Follow-up na mesma thread: não deve renomear novamente; se o cache já foi consumido, skip por `no_provisional_title_record` é esperado.


### Hotfix 2026-06-14 — dedupe guard
`discord-thread-title-deduplicate-safe-autorename.patch` removes a contiguous duplicate legacy block that could be left by older patch layering: duplicate `_is_discord_thread_lane`, duplicate `_sanitize_discord_thread_title`, unsafe `_rename_discord_thread_for_session_title` with reason `Hermes auto-generated session title`, and duplicate scheduler. `ensure-hermes-mgs-patches.sh` now enforces exactly one copy of each title function and zero legacy unsafe reason occurrences.
