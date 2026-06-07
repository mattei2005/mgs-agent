# Company OS thread continuity pitfall — 2026-06-07

## Context

During a long-running MGS Company OS restructuring thread, Rodolfo replied with a short `Ok` to a prior execution report. Zeus treated it as an isolated message, renamed the already-open thread, and even inferred the wrong language/topic from the current title instead of the replied message and thread objective.

Rodolfo corrected the workflow: an already-open thread should not be renamed while it has the same objective. This is especially important for restructuring threads because the thread itself is the project context.

## Durable lesson

For Company OS / restructuring work:

1. Treat the thread objective as persistent until Rodolfo explicitly changes or closes it.
2. In Discord replies, use the quoted/replied message as the primary context anchor.
3. A short reply (`ok`, `continue`, `vamos continuar`, `proximo passo`) continues the active block/phase unless there is strong evidence otherwise.
4. Do not rename an already-open restructuring thread based on a short reply or vague message.
5. If context is ambiguous, inspect/reconstruct the active phase from the latest execution report before acting.

## Correct behavior pattern

```text
Input                         Interpretation
----------------------------- -----------------------------------------------
Ok                            Approval/acknowledgment of previous block.
Vamos continuar               Continue from the last reported next block.
Próximo passo?                State the next recommended phase/block.
Ok continue                   Execute the next recommended low-risk block.
Reply to prior execution      Anchor interpretation on the replied report.
```

## Reporting pattern after continuation

Use the same executive block style already established in the restructuring thread:

```text
Fase N — Bloco X
Arquivo principal     path/file.md
Status                file.md v0.x
Validação             OK
Secret scan diff      OK
Audit log             OK
Auto-push             OK
HEAD=origin           <sha>
Repo                  limpo
```

Then list only the operational changes and the next recommended block.
