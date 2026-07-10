## Quando usar

Qualquer situação onde um processo periódico grava em log com padrão START/OK e você quer:
- Detectar falhas silenciosas (START sem OK correspondente)
- Alertar via Discord Webhook quando threshold atingido
- Anti-spam (não repetir alerta a cada ciclo)
- Mensagem de "RESOLVIDO" quando o sistema se recupera

Também usar quando um canal Discord precisa de automação idempotente via polling, não conversa normal do gateway — por exemplo, canal de anúncios seguido externamente onde Zeus deve postar explicações abaixo de cada novo anúncio. Para o padrão específico de followed announcements, ver `discord-ops` → `references/discord-followed-announcement-explainer.md`.

Também usar para gestão de **cron reliability/control plane**: inventariar crons MGS, padronizar `flock`, criar smoke tests seguros, adicionar `--dry-run` em jobs destrutivos e monitorar logs stale. Ver referência validada: `references/cron-control-plane.md`.

Quando Rodolfo perguntar se um cron/runner “já parou”, “ainda está rodando”, ou mandar print apenas como referência do assunto, **não interpretar o print como fonte de verdade**. Checar o estado real primeiro: Hermes cronjob list, root crontab, systemd units, processos (`ps`), locks e últimos logs do runner. A resposta deve dizer explicitamente `ativo/parado`, evidência mínima (`sem processo`, `sem service`, `último log`, horário atual) e separar outros crons ativos do cron específico em questão.

Quando Rodolfo pedir melhoria de crons de backup/housekeeping, especialmente limpeza de `.bak`/snapshots, separar criação de backup e cleanup, preservar sempre o último backup por família, excluir segredos por padrão e validar com dry-run + archive real. Ver `references/cron-backup-housekeeping-preserve-latest.md`. Para alertas Discord desse housekeeping, usar layout humanizado e sem ambiguidade: separar `backups pequenos preservados` de `tarballs Hermes`, mostrar risco/status, tipos deletados, amostra de paths e log completo; ver `references/backup-housekeeping-humanized-alerts.md`.

When a Hermes `cronjob` script-only (`no_agent=true`) estiver entregando log bruto em thread/canal errado, tratar como problema de roteamento + stdout bruto: mudar `deliver` para `local`, deixar sucesso silencioso, e fazer o próprio script mandar embed limpo para `#alerts-infra` via webhook com state anti-spam. Ver `references/hermes-cron-script-only-alert-routing.md`.

Quando Rodolfo reclamar que os alertas automáticos estão “poluídos” ou pedir visão mais humana/tabela, aplicar o padrão validado em `references/alerts-infra-humanized-cron-alerts-2026-06-27.md`: batch de eventos relacionados em uma única mensagem, embed com fields curtos, tabela monoespaçada para dados comparáveis, `content` só para mention necessária, e verificação ad-hoc por script temporário `/tmp/hermes-verify-*` com dry-run sem postar alerta real.

Para alertas de **Meta App Roles** nos canais B001–B010, seguir a preferência específica validada em `references/meta-app-roles-discord-layout-and-identity.md`: embed curto + dois code blocks normais, topo `Usuários Atuais:`, segundo bloco sem cabeçalho redundante `Movimentações/Ordenado`, tabela compacta `BOT EMAIL | SEGURADOR | PERFIL ID` (sem coluna `ROLE/Admin`), `BOT EMAIL` exibido sem domínio (texto antes de `@`) mas ordenado pelo email completo, e `Removidos acumulados` limpo por identidade composta (Meta ID + nome normalizado + PERFIL ID). Ao mudar layout, atualizar tanto snapshot manual quanto alerta automático de delta do cron. Não trocar para agrupamento por email/bullets sem novo pedido explícito — Rodolfo considerou poluído. Quando um app original for deletado/substituído, padronizar o replacement como chave canônica (ex.: `B005-2`, não alias `B005`) seguindo `references/meta-app-roles-replacement-app-canonicalization.md`. Para sync da planilha de migração (`Removidos acumulado`), falha de leitura/escrita nunca pode ficar só em state: alertar Rodolfo criticamente e validar o auth path real do cron (OAuth vs service account). Além disso, o sync não pode ser apenas delta desde o state: deve reconciliar a planilha inteira (`NO APP` + `USUARIO`/`Segurador`) contra a Meta API live em cada execução e marcar `X` para perfis ausentes. Ver `references/meta-app-roles-sheet-sync-auth-alerting-2026-07-02.md`, `references/meta-app-roles-sheet-reconciliation-2026-07-02.md` e `references/meta-app-roles-manager-channel-boundary-2026-07-02.md`.

Quando Rodolfo pedir para “ficar de olho” em alertas por um período curto e só avisar se algo importante aparecer, preferir watchdog `no_agent=true` com stdout vazio no OK e stdout curto só em anomalia — não LLM cron com mensagens de OK. Ver `references/alerts-infra-script-only-watchdog.md`.

Quando Rodolfo pedir para Zeus monitorar o próprio `#alerts-infra` e **resolver alertas falhos em background**, usar o padrão de watcher Discord + Zeus oneshot + reply referenciado: baseline com `--init`, state JSON com `processing` persistido antes da ação externa, detecção conservadora de candidatos, `flock` no cron, e resposta final anexada ao alerta original via Discord Bot API. Ver `references/alerts-infra-failed-alert-background-resolver.md`; para o caso validado com limite de 50 mensagens, baseline que não processa histórico antigo, e resolução de auto-push non-fast-forward, ver também `references/alerts-infra-failed-alert-resolver-2026-07-05.md`.

Quando Rodolfo pedir monitoramento da **VPS em si** (memória, disco, CPU/load, inodes, reboot recente, tamanho de backups, services ativos), tratar como uma camada separada dos monitores operacionais Hermes/MGS. Criar/usar um `monitor-vps-health.py` silencioso em OK, com state anti-spam, `flock`, thresholds claros, alerta só em anomalia/resolução e target Discord explícito quando ele disser “crie aqui <id>”. Ver `references/vps-health-monitor-2026-07-02.md`.

Também usar quando Rodolfo pedir uma visão executiva da operação MGS antes de ativar alertas programados: criar primeiro um collector read-only + briefing manual Discord-safe, validar escopo/sinal/ruído por 1–2 dias, e só depois propor cron/entrega automática. Ver `references/ops-control-plane-briefing.md`. Runtime snapshots `data/*-latest.{md,json}` devem ficar local-only/ignorados; se auto-commit rastrear por acidente, usar `git rm --cached` para remover do Git sem apagar do disco.

Quando Rodolfo criar ou indicar um canal dedicado para auditoria operacional recorrente, separar business-monitor de infra-monitor: report diário de estado operacional vai para o canal dedicado, enquanto `#alerts-infra` fica para falha técnica/REPORT-INFRA. Começar read-only, incluir resumo + contagens de status + divergências novas/persistentes/resolvidas, manter detalhe completo em JSON/CSV local, e só autocorrigir após aprovação explícita. Ver `references/dedicated-operational-audit-channel-pattern-2026-07-09.md`.

Quando Rodolfo pedir para começar um **Ops Control Plane / dashboard / briefing executivo** amplo, começar com collector determinístico read-only e sob demanda — não cron/alerta. Se ele excluir um agente explicitamente (ex: “Atena deixa por último e me avise antes”), tratar como gate duro: não ler logs/config/profile desse agente e declarar a exclusão no relatório. Ver `references/mgs-ops-control-plane-readonly.md`.

Quando Rodolfo pedir uma checagem geral pós-update/restart (“verifica se tudo está funcionando”, “verifica todos os crons”), usar o checklist amplo em `references/full-operational-audit-after-update.md`: serviços, crons, stale-log dry-run, smoke test, recursos VPS, provider/modelo, git/autocommit e distinção entre falha histórica de restart vs problema ativo.

Quando o pedido for auditoria/varredura operacional, checar também **erros semânticos em logs recentes** — log fresco não significa cron saudável. Ver `references/cron-semantic-error-audit.md` para o caso validado `grep -c ... || echo 0` que gerava `0\n0` e quebrava aritmética Bash sem acionar stale-log.

Quando um stale-log parece falso positivo, verificar primeiro se há **divergência entre o redirect do crontab e o `LOG=...` interno do script**. O stale monitor usa o redirect quando existe; `CUSTOM_LOG` só cobre jobs sem redirect. Ver `references/cron-log-path-canonicalization.md` para o padrão de correção e validação.

Para monitores Bash com `set -euo pipefail`, Git e pipelines truncados com `head`, ver `references/cron-pipefail-git-log-monitor.md`: cobre trap temporário de linha/rc, `git log --grep` com flags longas, SIGPIPE `141` e padrão `VAR=$( { ... | head ...; } || true )`.

Para monitores que chamam wrappers com `uv`, Python ou ferramentas instaladas no home do root, ver `references/cron-wrapper-path-and-stdin-pitfalls.md`: validar com `env -i`, exportar PATH cron-safe no wrapper, evitar `python3 - <<'PY'` tentando ler stdin ao mesmo tempo, e resetar estado de alerta após falso positivo resolvido.

Para hardening de crons + auto-commit watcher após auditoria de repo, ver `references/cron-autocommit-guardrails-2026-05-16.md`: cobre correção do bug `grep -c`, scan semântico só do bloco de execução mais recente, guardrail contra auto-commit de arquivos sensíveis, pitfall com pathspec Git e `.env` ignorado, e checklist de validação.

Para hardening de monitores que usam SSH/SCP via jump host RunCloud, ver `references/cron-ssh-hardening-2026-05-16.md`: cobre troca de `StrictHostKeyChecking` desativado por `accept-new` + `UserKnownHostsFile` dedicado, `mktemp -d` 700, cleanup trap, script remoto único (`/tmp/name_$$.sh`) e remoção remota após execução. Validar com execução real controlada e confirmar que não houve post Discord indevido.

Para crons de backup/housekeeping e hardening em lote de crons existentes, ver `references/cron-backup-housekeeping-preserve-latest.md`: cobre split entre criação de backup e limpeza, preservação do último backup por família, snapshot seguro a cada 3 dias com exclusão de segredos, smoke-test expandido, cleanup de sessions por última mensagem, backup antes de sync de `auth.json` e escrita atômica de inventários.

- `references/autocommit-service-flapping-pathspec-2026-07-09.md`: padrão validado para alerta vermelho/verde recorrente do `mgs-autocommit` por restart loop; corrigir `auto-commit-watcher.sh` com parse NUL-safe do `git status --porcelain=v1 -z`, tratar staged deletions (`D `) sem `git add`, e não matar o service por path volátil.
- `references/cron-op-rate-limit-mitigation.md`: primeiro aplicar stagger; depois mover busca de webhook/segredo para o caminho de alerta real, mantendo execução saudável sem `op`, fallback local de alertas pendentes e `exit 2` quando `op` falhar durante alerta.
- `references/cron-enospc-recovery.md`: recuperação pós-ENOSPC/disco cheio para crons MGS — distinguir erro histórico de ativo, reconstruir state JSON corrompido, rodar monitors manualmente em modo seguro/dry-run e limpar stale-alert state.
- `references/external-status-page-maintenance-monitor.md`: padrão validado para crons que monitoram status pages externas (ex: incident.io/Webshare), detectam manutenção ativa sem falso positivo por labels estáticos, alertam `#alerts-infra` só em transição e registram resolução.
- `references/honcho-health-monitor-flapping-debounce-2026-06-22.md`: padrão validado para monitores de serviço auxiliar tipo Honcho/copilot que estavam gerando alerta vermelho/verde em loop por timeout parcial; separar falha parcial de outage crítico, debouncing por checks consecutivos, e só mandar resolução verde se `alert_active=true`.
- `references/monarx-package-update-gateway-restart-hardening-2026-06-23.md`: padrão validado para restart de gateway Hermes causado por cron externo/package update do Monarx; classificar `/etc/cron.d/monarx-update`, excluir gateways MGS de auto-restart via `needrestart` e enriquecer alerta com `Causa provável`.
- `references/cron-backup-housekeeping-preserve-latest.md`: padrão validado para separar criação de backup (`mgs-safety-backup.sh`) de limpeza (`housekeeping-bak-cleanup.sh`), preservar sempre o último backup por família, validar tar/manifest sem segredos, e endurecer crons relacionados com `--dry-run`, escrita atômica, lazy webhook, semantic log scan e smoke test sem skips fixos.

Exemplos validados: `monitor-auto-push.sh` para o auto-push do mgs-agent; `cron-control-plane.py`, `cron-smoke-test.sh` e `monitor-cron-stale-logs.sh` para controle dos crons MGS.
Exemplos validados:
- `monitor-auto-push.sh` para o auto-push do mgs-agent.
- Para alerta `START sem OK`/`push pendente` após commits concorrentes ou push non-fast-forward, reconciliar em worktree limpo e endurecer o monitor para ignorar commits já em `origin/main` ou supersedidos fora do `HEAD`; ver `references/auto-push-divergent-commit-reconciliation.md`.
- `cron-control-plane.py` para inventário vivo dos crons MGS em `docs/CRONS.md` — ver `references/cron-control-plane.md`.

---
