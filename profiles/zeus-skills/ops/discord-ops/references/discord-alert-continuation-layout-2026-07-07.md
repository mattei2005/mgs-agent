# Discord alert continuation layout — 2026-07-07

## Rodolfo correction

When adding a follow-up/complement to an operational alert in Discord, do not post a casual prose addendum that visually clashes with the original alert. If a complement is ugly or unclear, delete it and repost a clean continuation block.

## Rule

For follow-up messages in operational alert channels:

1. Keep the visual style of the prior alert/report.
2. Use a compact block/section, not loose prose.
3. Make the action performed explicit for a human reader.
4. Prefer a section header such as `AÇÃO EXECUTADA NA SMART BIDDING` when the follow-up explains a dashboard write.
5. Include validation status when applicable, e.g. `readback SB OK antes do alerta`.
6. If a bad complement was already posted, delete it first, then post the replacement.

## Approved shape

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AÇÃO EXECUTADA NA SMART BIDDING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status das páginas: Broadcast
Restricted Until: data extraída do último Completed da DTR
Validação: readback SB OK antes do alerta
```

## Pitfall

Do not treat the complement as a normal chat answer. In channels like restricted-pages, humans scan alerts operationally; the continuation must read like part of the report, not like an assistant correction.