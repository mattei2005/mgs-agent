### Busy input no Discord: `/queue` vs `/steer`

Quando Rodolfo mandar uma segunda pergunta enquanto Zeus/Atena ainda está processando a primeira:

- `/steer texto` **não cria nova resposta**. Injeta o texto como orientação dentro do turno em andamento, após o próximo tool call. Use para corrigir/interromper direção da resposta atual.
- `/queue texto` cria **um novo turno FIFO**. O agente termina a resposta atual e depois responde o texto enfileirado como pergunta separada.
- Mensagem normal durante execução depende de `display.busy_input_mode`. Em `queue`, o caminho atual pode usar `merge_pending_message_event()` com slot único, o que pode mesclar/substituir follow-ups em vez de garantir uma resposta por mensagem.

Se o objetivo operacional for “Rodolfo pode mandar duas perguntas ao mesmo tempo e receber duas respostas em sequência”, a correção de runtime é tratar mensagem normal em `busy_input_mode: queue` como FIFO real, usando o mesmo mecanismo de `/queue` (`_enqueue_fifo`) em vez de `merge_pending_message_event()`/`_queue_or_replace_pending_event()`. Antes de patchar Hermes runtime: fazer backup, patch pequeno em `gateway/run.py`, restart do service afetado e teste real com duas mensagens rápidas.

Referência detalhada: `references/hermes-discord-busy-input-queue.md`.

