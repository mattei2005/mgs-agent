## Quando usar

Qualquer situação onde um processo periódico grava em log com padrão START/OK e você quer:
- Detectar falhas silenciosas (START sem OK correspondente)
- Alertar via Discord Webhook quando threshold atingido
- Anti-spam (não repetir alerta a cada ciclo)
- Mensagem de "RESOLVIDO" quando o sistema se recupera

Também usar quando um canal Discord precisa de automação idempotente via polling, não conversa normal do gateway — por exemplo, canal de anúncios seguido externamente onde Zeus deve postar explicações abaixo de cada novo anúncio. Para o padrão específico de followed announcements, ver `discord-ops` → `references/discord-followed-announcement-explainer.md`.

Também usar para gestão de **cron reliability/control plane**: inventariar crons MGS, padronizar `flock`, criar smoke tests seguros, adicionar `--dry-run` em jobs destrutivos e monitorar logs stale. Ver referência validada: `references/cron-control-plane.md`.

Quando o pedido for auditoria/varredura operacional, checar também **erros semânticos em logs recentes** — log fresco não significa cron saudável. Ver `references/cron-semantic-error-audit.md` para o caso validado `grep -c ... || echo 0` que gerava `0\n0` e quebrava aritmética Bash sem acionar stale-log.

Quando um stale-log parece falso positivo, verificar primeiro se há **divergência entre o redirect do crontab e o `LOG=...` interno do script**. O stale monitor usa o redirect quando existe; `CUSTOM_LOG` só cobre jobs sem redirect. Ver `references/cron-log-path-canonicalization.md` para o padrão de correção e validação.

Para monitores Bash com `set -euo pipefail`, Git e pipelines truncados com `head`, ver `references/cron-pipefail-git-log-monitor.md`: cobre trap temporário de linha/rc, `git log --grep` com flags longas, SIGPIPE `141` e padrão `VAR=$( { ... | head ...; } || true )`.

Para hardening de crons + auto-commit watcher após auditoria de repo, ver `references/cron-autocommit-guardrails-2026-05-16.md`: cobre correção do bug `grep -c`, scan semântico só do bloco de execução mais recente, guardrail contra auto-commit de arquivos sensíveis, pitfall com pathspec Git e `.env` ignorado, e checklist de validação.

Para hardening de monitores que usam SSH/SCP via jump host RunCloud, ver `references/cron-ssh-hardening-2026-05-16.md`: cobre troca de `StrictHostKeyChecking` desativado por `accept-new` + `UserKnownHostsFile` dedicado, `mktemp -d` 700, cleanup trap, script remoto único por PID e validação real sem post Discord indevido.

Exemplos validados: `monitor-auto-push.sh` para o auto-push do mgs-agent; `cron-control-plane.py`, `cron-smoke-test.sh` e `monitor-cron-stale-logs.sh` para controle dos crons MGS.
Exemplos validados:
- `monitor-auto-push.sh` para o auto-push do mgs-agent.
- `cron-control-plane.py` para inventário vivo dos crons MGS em `docs/CRONS.md` — ver `references/cron-control-plane.md`.

---
## Convenção de canal Discord por tipo de alerta

| Tipo de alerta | Canal | Webhook 1Password |
|---|---|---|
| Saúde Yoast SEO/Readability | `#alerts-yoast` (1498193722871910550) | `Discord Webhook - Alerts Yoast Channel` |
| Infra crítica (auto-push, deploy) | `#mgs-alerts` (1498132022634483894) | `Discord Webhook - Alerts Infra Channel` |
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

**NÃO usar** o webhook `#zeus-admin-agent` para alertas de cron/monitor automatizado. Esse canal é exclusivo para conversa operacional Rodolfo ↔ Zeus e hook git de commits interativos; `[REPORT-INFRA]` de agentes deve ir para `#alerts-infra` (1498132022634483894).

---
## Estrutura do sistema

```
scripts/monitor-NOME.sh          — script principal
data/NOME-monitor.json           — state file (persiste entre execuções)
logs/monitor-NOME.log            — output do cron
crontab root                     — entrada cron (frequência ajustável)
```

---
## State file inicial

```json
{
  "_meta": {
    "description": "Estado do monitor de NOME. Atualizado a cada execução.",
    "created": "YYYY-MM-DD",
    "threshold": 3,
    "anti_spam_window_hours": 2
  },
  "last_check": null,
  "consecutive_failures": 0,
  "last_alert_sent": null,
  "last_failure_details": []
}
```

---
