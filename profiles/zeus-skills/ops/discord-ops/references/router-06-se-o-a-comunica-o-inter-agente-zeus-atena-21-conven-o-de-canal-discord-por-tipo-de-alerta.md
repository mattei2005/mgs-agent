### Convenção de canal Discord por tipo de alerta

| Tipo | Canal | Webhook 1Password |
|---|---|---|
| Infra crítica (auto-push, deploy) | `#mgs-alerts` (1498132022634483894) | `Discord Webhook - Alerts Infra Channel` |
| Updates do Hermes Agent | `#alerts-hermes-news` (1505609056771899644) | Zeus Bot API (`DISCORD_BOT_TOKEN` do profile zeus) |
| Saúde Yoast/Readability | `#alerts-yoast` (1498193722871910550) | `Discord Webhook - Alerts Yoast Channel` |
| REPORT-INFRA / alertas infra | `#alerts-infra` (1498132022634483894) | `Discord Webhook - Alerts Infra Channel` |

**NÃO usar** o webhook `#alerts-infra` para alertas automáticos de cron/monitor. Reservado para conversa operacional Rodolfo↔Zeus e commits interativos; `[REPORT-INFRA]` de agentes deve ir para `#alerts-infra` (1498132022634483894). Se um Hermes cron script-only já estiver preso a uma thread por `deliver=origin`, mudar o cron para `deliver=local` e fazer o script enviar embed próprio para `#alerts-infra`; não tentar “embelezar” stdout bruto na thread. Ver skill `log-monitor-discord-alert` → `references/hermes-cron-script-only-alert-routing.md`.

