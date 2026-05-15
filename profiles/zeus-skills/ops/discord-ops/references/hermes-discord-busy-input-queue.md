# Hermes Discord busy input: `/queue` vs `/steer`

## Contexto

Em Discord gateway, o usuário pode enviar nova mensagem enquanto o agente ainda está executando uma resposta anterior. O Hermes tem caminhos diferentes para isso:

- `/steer <texto>`: injeta orientação no turno em andamento após o próximo tool call.
- `/queue <texto>` ou `/q <texto>`: enfileira um novo turno FIFO, separado da resposta atual.
- Mensagem normal enquanto o agente está busy: comportamento controlado por `display.busy_input_mode`.

## Diagnóstico validado

Sinal visual no Discord:

```text
⏩ Steer queued — arrives after the next tool call: '...'
```

Isso significa que o texto foi entregue como orientação interna, não como nova pergunta. O agente pode incorporar ou ignorar conforme a tarefa corrente; não haverá necessariamente uma segunda resposta.

Logs úteis:

```bash
grep -E "slash '/steer|Delivered /steer|/queue|Queued follow-up|response ready" \
  /root/.hermes/profiles/<profile>/logs/agent.log \
  /root/.hermes/profiles/<profile>/logs/gateway.log
```

Exemplo observado:

```text
17:58:08 /steer "voce entendeu ?" recebido
17:58:20 Delivered /steer to agent after tool batch
18:00:00 resposta final da pergunta original enviada
```

Conclusão: não foi drop do Discord; foi semântica de `/steer`.

## Uso correto

```text
Objetivo                                      | Comando
----------------------------------------------|---------------------------
Corrigir a resposta atual enquanto roda       | /steer <orientação>
Fazer próxima pergunta separada               | /queue <pergunta>
Interromper e liberar sessão                  | /stop
Começar sessão limpa                          | /new ou /reset
```

## Correção desejada para MGS

Requisito de Rodolfo: mandar duas perguntas ao mesmo tempo e receber duas respostas em sequência, sem precisar lembrar de `/queue`.

Config atual dos agentes MGS:

```yaml
display:
  busy_input_mode: queue
```

No `gateway/run.py`, o caminho de mensagem normal com agente ativo e `busy_input_mode == "queue"` chama `_queue_or_replace_pending_event()`, que usa `merge_pending_message_event()`. Esse caminho é slot único/merge-oriented; é bom para bursts de mídia/texto, mas não garante uma resposta por mensagem.

Para o comportamento desejado, mensagem normal em `busy_input_mode: queue` deve usar FIFO real, igual `/queue`:

```python
adapter = self.adapters.get(source.platform)
if adapter:
    self._enqueue_fifo(_quick_key, event, adapter)
return None
```

Aplicar no branch:

```python
if self._busy_input_mode == "queue":
    ...
```

## Procedimento seguro antes de patchar

1. Confirmar que `/root/.hermes/hermes-agent/gateway/run.py` ainda contém `_enqueue_fifo`, `_queue_or_replace_pending_event` e o branch `self._busy_input_mode == "queue"`.
2. Backup timestamp do arquivo.
3. Patch mínimo só no branch `busy_input_mode == "queue"`.
4. Restart apenas do service afetado (`zeus-gateway.service` ou `atena-gateway.service`).
5. Validar com teste real:
   - enviar pergunta longa que usa tools;
   - durante execução, enviar mensagem normal curta;
   - confirmar duas respostas separadas em sequência;
   - conferir logs por `response ready` duas vezes e ausência de `Steer queued`.

## Pitfalls

- Não confundir `/steer` com fila. `/steer` é intra-turn guidance.
- Não registrar como “Discord dropou mensagem” quando aparece `Delivered /steer`; a mensagem chegou e foi consumida como guidance.
- Não trocar globalmente tratamento de PHOTO/bursts: mídia ainda precisa de merge para álbuns/captions. A mudança alvo é texto normal durante busy queue.
- Mudança em Hermes runtime é patch local; reportar/validar e lembrar que updates do Hermes podem sobrescrever.