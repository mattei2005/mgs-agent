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
