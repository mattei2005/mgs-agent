### Convenção de canal Discord por tipo de alerta

| Tipo | Canal | Webhook 1Password |
|---|---|---|
| Infra crítica (auto-push, deploy) | `#mgs-alerts` (1498132022634483894) | `Discord Webhook - Alerts Infra Channel` |
| Saúde Yoast/Readability | `#alerts-yoast` (1498193722871910550) | `Discord Webhook - Alerts Yoast Channel` |
| REPORT-INFRA / alertas infra | `#alerts-infra` (1498132022634483894) | `Discord Webhook - Alerts Infra Channel` |

**NÃO usar** o webhook `#zeus-admin-agent` para alertas automáticos de cron/monitor. Reservado para conversa operacional Rodolfo↔Zeus e commits interativos; `[REPORT-INFRA]` de agentes deve ir para `#alerts-infra` (1498132022634483894).

