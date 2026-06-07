# Company OS thread context pitfall — 2026-06-07

## Trigger

During the MGS OS restructuring thread, Rodolfo replied with a short `Ok` to a prior execution report (`Fase 4 — Bloco 2`). Zeus treated the message as a standalone confirmation, lost the cited reply context, and changed the Discord thread title incorrectly, even switching the apparent subject/language.

## User correction

Rodolfo clarified:

- A thread already open should not be renamed automatically while it keeps the same objective.
- The thread has one objective until it is finalized.
- In long Company OS restructuring threads, short replies like `Ok`, `vamos continuar`, or `prossegue` inherit the quoted/previous block context.
- This is especially critical for enterprise restructuring threads because losing context can corrupt sequencing and governance.

## Durable rule for Company OS work

For MGS OS restructuring threads:

1. Treat the thread objective as persistent until Rodolfo explicitly finalizes or clearly changes objective.
2. Do not rename an already-open thread as part of Company OS continuation work.
3. If Rodolfo sends a short reply, anchor interpretation to the replied-to message and the current phase/block, not to the literal short text.
4. Before continuing after a short confirmation, verify the current phase/block from recent execution state or loaded plan if needed.
5. Report continuation as the next block in the existing sequence, not as a new topic.

## Bad pattern

```text
User: Ok
Agent: changes thread title / treats as isolated registration / loses phase context
```

## Good pattern

```text
User replies `Ok` to Fase 4 — Bloco 2 report
Agent continues with Fase 4 — Bloco 3, preserving thread title and Company OS sequence
```
