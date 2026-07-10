# Gateway restart recovery checkpoint

Use this reference when a Hermes Discord gateway restart/SIGTERM interrupts an active user-facing turn and the user expects the agent to return to the same thread with a closing status instead of waiting for a new prompt.

## Problem

During a controlled gateway restart, Hermes can send a shutdown notification to the active Discord thread, then terminate the process before the LLM turn produces its final response. After systemd restarts the service, the new process has Discord connectivity again but no recoverable obligation to post a final status for the interrupted turn.

Observed symptom:

```text
Gateway shutting down — Your current task will be interrupted.
[service restarts]
(no final answer until Rodolfo prompts again)
```

This is operationally wrong for MGS maintenance. Rodolfo should not have to say "continua" after a restart that Zeus initiated or coordinated.

## Correct product behavior

Implement deterministic recovery outside the LLM turn:

1. Before sending the shutdown notification, write a small checkpoint for each active chat/thread being interrupted.
2. Include platform, chat_id, thread_id/topic metadata, source message id when available, timestamp, restart reason/source, and a short operation label if known.
3. On gateway startup after platform reconnect, scan pending checkpoints with a short TTL (for example 2h).
4. Post one idempotent recovery message back to the same thread/channel.
5. Mark the checkpoint delivered before or atomically with the send result to avoid duplicate posts on crash/restart loops.
6. Keep the recovery message deterministic and cheap: do not start a cron job or new LLM task from the same restarting bot.

## Recovery message shape

```text
Voltei do restart.

O turno anterior foi interrompido durante [operação].
Status atual:
- gateway ativo
- patch/ação: aplicado|pendente|desconhecido
- validação: [última evidência disponível]

Próximo passo pendente: [ação concreta]
```

If the runtime cannot know patch/validation state, say so explicitly and provide the next safe verification command/action instead of inventing success.

## Implementation notes

Preferred location is the gateway runtime (`gateway/run.py`) around the existing shutdown notification path and startup/platform-connected path. The checkpoint must be profile-local, e.g. under the active Hermes profile state/runtime directory, not a global shared file.

The checkpoint is not a substitute for validating service health. After restart, still verify systemd state/log connectivity when responding operationally.

## Pitfalls

- Do not rely on the killed LLM process to remember the task. The process that was reasoning is gone.
- Do not schedule a self-check cron from the same bot being restarted unless explicitly accepted; it can collide with shutdown/drain and confuse the user.
- Do not duplicate recovery messages if systemd restarts repeatedly. Use TTL + delivered marker/idempotency key.
- Do not over-explain in the recovery message. Rodolfo needs status and next step, not a postmortem.
