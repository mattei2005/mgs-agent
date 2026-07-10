# App Roles Alert Visual Correction — 2026-07-03

Rodolfo corrected the Meta app roles alert presentation after comparing it to the `páginas restritas` alert.

## Final accepted interpretation

When improving B001–B010 app roles alerts:

1. Keep the **first/native Discord embed** exactly as-is.
   - Real Discord card/embed, not text simulation.
   - Same green/yellow status bar, title, description, fields, and footer.
   - Do not rewrite it as plain text in previews or implementation.

2. Keep the **first code block** exactly as-is.
   - Heading remains `Usuários Atuais:`.
   - Existing table format remains unchanged.
   - No emojis or separators added to this block.

3. Change only the **third/movement code block**.
   - Sections: removed now, added now, cumulative removed.
   - Add emojis to section titles.
   - Use the heavy straight Unicode separator, not equals signs.

Accepted separator:

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Accepted movement block shape:

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
➖ USUÁRIOS REMOVIDOS AGORA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Nenhum.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🆕 USUÁRIOS ADICIONADOS AGORA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Nenhum.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 REMOVIDOS ACUMULADOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BOT EMAIL                | SEGURADOR                 | PERFIL ID
...
```

## Pitfall from session

Do not interpret "primeiro bloco igual" as "show a textual approximation of the embed". It means the actual Discord embed/card remains 100% unchanged. If Rodolfo asks to "mandar igual" and the target includes an embed, use the real bot/script delivery path to send a Discord embed test, not a normal chat response.

## Validation pattern

For a visual test, post to the specific B001–B010 channel using the same 3-message delivery path:

1. `post_webhook(<@Rodolfo>, embed, app_name=Bxxx)`
2. `post_webhook(code_block(users_block), app_name=Bxxx)`
3. `post_webhook(code_block(movement_block), app_name=Bxxx)`

Successful test posts return HTTP `200` for each message when using Discord bot channel messages.
