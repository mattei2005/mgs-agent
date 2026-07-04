# Discord app-rate-limit channel scope — B001–B010 — 2026-07-02

## Trigger

Use when Zeus/Ares posts to or designs alerts for the 10 app-specific rate-limit channels:

```text
#b011pp-rate-limit ... #b010-app-rate-limit
```

## User correction

Rodolfo explicitly rejected a Zeus internal status/correction notice being posted in those channels.

Those channels are **manager-facing, app-specific operational alert channels**, not Zeus/infra changelog channels.

## Allowed content

Post only alerts directly actionable for the app/channel audience, such as:

- Meta App role/admin removed or added for that specific app;
- app/token/API/rate-limit health affecting that specific app;
- developer/account/app fall that managers must act on;
- concise current app-role tables when a real app-role event occurs.

## Not allowed

Do not post:

- Zeus internal correction explanations;
- broad infra/status updates;
- “monitor fixed” notices;
- generic reconciliation summaries;
- reports intended primarily for Rodolfo/Zeus ops.

Those belong in Zeus/#alerts-infra or the current Rodolfo thread unless Rodolfo explicitly asks for manager-facing broadcast content.

## Cleanup pattern if mistake happens

If an internal/broad message is mistakenly sent to B001–B010:

1. Delete the mistaken messages from all affected channels immediately via Discord API/bot token.
2. Do not replace them unless the user asks for a corrected manager-facing message.
3. Report back with deletion status per channel.

## Formatting reminder

When a real app-role alert is valid, keep the existing concise format:

```text
Meta APP - B00X
ESTADO / CONTAGEM / ADMIN / USO
Usuários Atuais
Usuários removidos/adicionados agora
Removidos acumulados
```

Avoid adding long explanations to manager channels.
