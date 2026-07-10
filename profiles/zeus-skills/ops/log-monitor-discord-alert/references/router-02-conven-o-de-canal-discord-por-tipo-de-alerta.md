## Convenção de canal Discord por tipo de alerta

| Tipo de alerta | Canal | Webhook 1Password |
|---|---|---|
| Saúde Yoast SEO/Readability | `#alerts-yoast` (1498193722871910550) | `Discord Webhook - Alerts Yoast Channel` |
| Infra crítica (auto-push, deploy) | `#mgs-alerts` (1498132022634483894) | `Discord Webhook - Alerts Infra Channel` |
| Updates do Hermes Agent | `#alerts-hermes-news` (1505609056771899644) | Zeus Bot API (`DISCORD_BOT_TOKEN` do profile zeus) |
| REPORT-INFRA / cobrança operacional ao Zeus | `#alerts-infra` (1498132022634483894) | `Discord Webhook - Alerts Infra Channel` |

**Layout obrigatório das mensagens:** usar Discord embed com `fields` estruturados — nunca mandar alerta como texto bruto em `content`, exceto a mention necessária para push.
- `content`: vazio para info/resolução; `<@344196393512075265> alerta curto` apenas quando precisa push.
- `embeds[0].title`: título humano curto, sem prefixo poluído.
- `embeds[0].color`: vermelho `15158332`, amarelo `15844367`, verde `3066993`, azul/info `3447003`.
- `embeds[0].fields`: dados separados por assunto (`Service`, `Estado`, `Ação`, `Detalhe técnico`, etc.).
- Detalhes longos vão em campo `Detalhe técnico` com bloco ```text, truncado se necessário.
- Resoluções usam embed verde simples.

Exemplo mínimo:
```bash
PAYLOAD=$(jq -n \
  --arg service "$SERVICE" \
  --arg detail "$DETAIL" \
  '{content:"<@344196393512075265> alerta de infra", embeds:[{title:"Service com falha", color:15158332, fields:[{name:"Service", value:("`"+$service+"`"), inline:true}, {name:"Ação", value:"Investigar log e reiniciar se necessário.", inline:false}, {name:"Detalhe técnico", value:("```text\n"+$detail[:900]+"\n```"), inline:false}]}]}')
```

**NÃO usar** o webhook `#alerts-infra` para alertas de cron/monitor automatizado. Esse canal é exclusivo para conversa operacional Rodolfo ↔ Zeus e hook git de commits interativos; `[REPORT-INFRA]` de agentes deve ir para `#alerts-infra` (1498132022634483894).

---
