# Thread rename pitfall — reply context and open-thread continuity (2026-06-07)

## Trigger

Rodolfo challenged why Zeus changed an already-open thread title and even switched the title language to Spanish after he replied `Ok`.

## What happened

- Rodolfo's `Ok` was a reply to Zeus's execution status for `Fase 4 — Bloco 2`.
- Zeus interpreted the short message as a standalone confirmation/registration instead of resolving the quoted reply context.
- Zeus applied a generic semantic title rule to a thread that was already in progress.
- Result: wrong title and wrong language.

## Durable rule

For MGS Discord ops:

1. If the message is a reply, read the quoted/replied content as primary context before interpreting short text.
2. Existing threads keep their name while the operational objective remains the same.
3. Do not rename an existing thread because of `ok`, `continua`, `executa`, `manda ver`, or similar short follow-ups.
4. Only consider rename when the subject/objective clearly changes, and never based on weak fallback interpretation.
5. Preserve the user's language; for Rodolfo in this context, PT-BR titles/content unless the live conversation is in English.

## Correct behavior

When Rodolfo says `Ok` in reply to an execution status:

```text
Action: continue/acknowledge the current block context.
Thread title: leave unchanged.
Response: concise status or next step only.
```

When Rodolfo says `Vamos continuar de onde parou`:

```text
Action: inspect current session/git/status, identify last completed block, continue with next block.
Thread title: leave unchanged.
```
