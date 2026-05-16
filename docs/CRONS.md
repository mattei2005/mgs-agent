# Crons MGS — Control Plane

Gerado em: `2026-05-16T15:26:04-04:00`  
Fonte: `root crontab + script/log stat, read-only`  
Total MGS ativo no root crontab: **17**

## Resumo executivo

```text
Frequência   | Script                         | Owner          | Risco                                   | Flock | Último log
------------ | ------------------------------ | -------------- | --------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------
*/5 * * * *  | sync-souls.sh                  | Zeus/Infra     | baixo                                   | sim   | 2026-05-16T15:25:01-04:00 synced atena skills/devops
*/15 * * * * | monitor-auto-push.sh           | Zeus/Infra     | baixo                                   | sim   | [2026-05-16T15:15:03-04:00] monitor-auto-push: Concluído. consecutive_failures=0 last_ok=3ede918
0 10 * * *   | monitor-yoast-health-eggbev.sh | Atena/Conteúdo | baixo                                   | sim   | [2026-05-16T12:36:23-04:00] monitor-yoast-health-eggbev: === Concluído (silencioso). SEO: 🟢166/🟡39/🔴0 / Read: 🟢165/🟡36/🔴39 ===
*/15 * * * * | check-pending-reports.sh       | Zeus/Infra     | baixo                                   | sim   | [2026-05-16 15:15:01] check-pending-reports.sh concluído
*/5 * * * *  | monitor-service-restarts.sh    | Zeus/Infra     | baixo                                   | sim   | 2026-05-16T15:25:01-04:00 [monitor-service-restarts] OK
0 12 * * *   | monitor-gpt55-oauth-cost.sh    | Zeus/Infra     | baixo                                   | sim   | Zeus: 665 calls / Atena: 73 calls
*/5 * * * *  | monitor-tool-loops.sh          | Zeus/Infra     | baixo                                   | sim   | Loop detector: 0 alertas enviados
0 5 * * *    | infra-discovery.sh             | Zeus/Infra     | médio: sobrescreve infra-inventory.json | sim   | [15:26:04] === infra-discovery.sh DONE ===
0 8 * * *    | monitor-hermes-updates.sh      | Zeus/Infra     | baixo                                   | sim   | [2026-05-16T08:00:03-04:00] OK notified upstream=a91a57fa5 local=db84a78e6 behind=96 days=0 feat=19 fix=44 breaking=0
*/15 * * * * | track-article-cost.sh          | Atena/Conteúdo | baixo/médio: escreve SQLite local       | sim   | 0: syntax error in expression (error token is "0")
0 * * * *    | cleanup-zombie-sessions.sh     | Zeus/Infra     | médio: fecha sessões Hermes inativas    | sim   | (sem log útil ainda)
0 3 * * *    | housekeeping-bak-cleanup.sh    | Zeus/Infra     | alto: deleta arquivos .bak antigos      | sim   | [2026-05-16T03:00:09-04:00] housekeeping: === END — deletados 2 arquivos / 0 MB ===
0 8 * * *    | pendencia-render-md.sh         | Zeus/Ops       | baixo: re-renderiza docs/PENDENCIAS.md  | sim   | Tamanho: 16671 bytes
0 * * * *    | chat-log.sh                    | Zeus/Ops       | baixo: re-renderiza índice              | sim   | 2 sessões indexadas
*/15 * * * * | sync-codex-oauth.sh            | Zeus/Infra     | médio: atualiza auth.json dos profiles  | sim   | [2026-05-16T19:15:01Z] done: all profiles in sync, nothing to do
10 8 * * *   | cron-control-plane.py          | Zeus/Ops       | baixo: re-renderiza docs/CRONS.md       | sim   | OK wrote /root/mgs-agent/docs/CRONS.md jobs=17 generated_at=2026-05-16T08:10:01-04:00
*/15 * * * * | monitor-cron-stale-logs.sh     | Zeus/Infra     | baixo: read-only + alerta Discord       | sim   | [2026-05-16T19:15:01Z] cron-stale check: jobs=17 problems=0 resolved=0 alerts_sent=0
```

## Pontos de atenção

- Alto risco: `housekeeping-bak-cleanup.sh`
- Médio risco: `infra-discovery.sh`, `cleanup-zombie-sessions.sh`, `sync-codex-oauth.sh`
- Crons sem `flock`: nenhum

## Detalhes por cron

### `sync-souls.sh`
- **Frequência:** `*/5 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Sincroniza SOUL.md, config.yaml e skills MGS dos profiles Hermes para versionamento no repo.
- **Comando:** `flock -n /var/lock/sync_souls.lock /root/mgs-agent/scripts/sync-souls.sh >> /root/mgs-agent/logs/sync-souls.log 2>&1`
- **Log:** `/root/mgs-agent/logs/sync-souls.log`
- **Último log:** 2026-05-16T15:25:01-04:00 (29479 bytes)

### `monitor-auto-push.sh`
- **Frequência:** `*/15 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Monitora falhas no auto-push Git do /root/mgs-agent e alerta em #mgs-alerts.
- **Comando:** `flock -n /var/lock/monitor_auto_push.lock /root/mgs-agent/scripts/monitor-auto-push.sh >> /root/mgs-agent/logs/monitor-auto-push.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-auto-push.log`
- **Último log:** 2026-05-16T15:15:03-04:00 (11842 bytes)

### `monitor-yoast-health-eggbev.sh`
- **Frequência:** `0 10 * * *`
- **Owner:** Atena/Conteúdo
- **Risco:** baixo
- **Função:** Monitora saúde Yoast do eggbev: SEO + Readability com baseline, semanal e alerta por degradação.
- **Comando:** `flock -n /var/lock/monitor_yoast_health_eggbev.lock /root/mgs-agent/scripts/monitor-yoast-health-eggbev.sh >> /root/mgs-agent/logs/monitor-yoast-health-eggbev.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-yoast-health-eggbev.log`
- **Último log:** 2026-05-16T12:36:23-04:00 (2870 bytes)

### `check-pending-reports.sh`
- **Frequência:** `*/15 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Detecta skills MGS sem REPORT-INFRA/inventário e cobra correção no canal Zeus.
- **Comando:** `flock -n /var/lock/check_pending_reports.lock /root/mgs-agent/scripts/check-pending-reports.sh >> /root/mgs-agent/logs/check-pending-reports.log 2>&1`
- **Log:** `/root/mgs-agent/logs/check-pending-reports.log`
- **Último log:** 2026-05-16T15:15:02-04:00 (8555 bytes)

### `monitor-service-restarts.sh`
- **Frequência:** `*/5 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Detecta restarts inesperados dos services zeus-gateway, atena-gateway e mgs-autocommit.
- **Comando:** `flock -n /var/lock/monitor_service_restarts.lock /root/mgs-agent/scripts/monitor-service-restarts.sh >> /root/mgs-agent/logs/monitor-service-restarts.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-service-restarts.log`
- **Último log:** 2026-05-16T15:25:01-04:00 (64542 bytes)

### `monitor-gpt55-oauth-cost.sh`
- **Frequência:** `0 12 * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Calcula custo hipotético GPT-5.5/OAuth dos agentes; OAuth não gera custo real por token.
- **Comando:** `flock -n /var/lock/monitor_gpt55_oauth_cost.lock /root/mgs-agent/scripts/monitor-gpt55-oauth-cost.sh >> /root/mgs-agent/logs/monitor-gpt55-oauth-cost.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-gpt55-oauth-cost.log`
- **Último log:** 2026-05-16T12:00:02-04:00 (88 bytes)

### `monitor-tool-loops.sh`
- **Frequência:** `*/5 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Detecta loops de tool_calls nas sessões Hermes e alerta infra.
- **Comando:** `flock -n /var/lock/monitor_tool_loops.lock /root/mgs-agent/scripts/monitor-tool-loops.sh >> /root/mgs-agent/logs/monitor-tool-loops.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-tool-loops.log`
- **Último log:** 2026-05-16T15:25:01-04:00 (6324 bytes)

### `infra-discovery.sh`
- **Frequência:** `0 5 * * *`
- **Owner:** Zeus/Infra
- **Risco:** médio: sobrescreve infra-inventory.json
- **Função:** Regenera data/infra-inventory.json a partir do estado real do sistema.
- **Comando:** `flock -n /var/lock/infra_discovery.lock /root/mgs-agent/scripts/infra-discovery.sh >> /root/mgs-agent/logs/infra-discovery.log 2>&1`
- **Log:** `/root/mgs-agent/logs/infra-discovery.log`
- **Último log:** 2026-05-16T15:26:04-04:00 (3408 bytes)

### `monitor-hermes-updates.sh`
- **Frequência:** `0 8 * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Verifica updates upstream do Hermes Agent e alerta quando há nova versão.
- **Comando:** `flock -n /var/lock/monitor_hermes_updates.lock /root/mgs-agent/scripts/monitor-hermes-updates.sh >> /root/mgs-agent/logs/monitor-hermes-updates.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-hermes-updates.log`
- **Último log:** 2026-05-16T08:00:03-04:00 (236 bytes)

### `track-article-cost.sh`
- **Frequência:** `*/15 * * * *`
- **Owner:** Atena/Conteúdo
- **Risco:** baixo/médio: escreve SQLite local
- **Função:** Calcula custo hipotético por artigo publicado e grava data/article-tracker.db.
- **Comando:** `flock -n /var/lock/track_article_cost.lock /root/mgs-agent/scripts/track-article-cost.sh >> /root/mgs-agent/logs/track-article-cost-cron.log 2>&1`
- **Log:** `/root/mgs-agent/logs/track-article-cost-cron.log`
- **Último log:** 2026-05-16T15:25:02-04:00 (23399 bytes)

### `cleanup-zombie-sessions.sh`
- **Frequência:** `0 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** médio: fecha sessões Hermes inativas
- **Função:** Fecha sessões Hermes zumbis/inativas há mais de 30 minutos.
- **Comando:** `flock -n /var/lock/cleanup_zombie_sessions.lock /root/mgs-agent/scripts/cleanup-zombie-sessions.sh`
- **Log:** `sem redirect explícito`
- **Último log:** arquivo ausente

### `housekeeping-bak-cleanup.sh`
- **Frequência:** `0 3 * * *`
- **Owner:** Zeus/Infra
- **Risco:** alto: deleta arquivos .bak antigos
- **Função:** Remove arquivos .bak antigos com retenção padrão de 15 dias e reporta resumo.
- **Comando:** `flock -n /var/lock/housekeeping_bak_cleanup.lock /root/mgs-agent/scripts/housekeeping-bak-cleanup.sh >> /root/mgs-agent/logs/housekeeping-cron.log 2>&1`
- **Log:** `/root/mgs-agent/logs/housekeeping-cron.log`
- **Último log:** 2026-05-16T03:00:09-04:00 (572 bytes)

### `pendencia-render-md.sh`
- **Frequência:** `0 8 * * *`
- **Owner:** Zeus/Ops
- **Risco:** baixo: re-renderiza docs/PENDENCIAS.md
- **Função:** Renderiza docs/PENDENCIAS.md a partir de data/pendencias.db.json.
- **Comando:** `flock -n /var/lock/pendencia_render_md.lock /root/mgs-agent/scripts/pendencia-render-md.sh >> /root/mgs-agent/logs/pendencia-render.log 2>&1`
- **Log:** `/root/mgs-agent/logs/pendencia-render.log`
- **Último log:** 2026-05-16T08:00:01-04:00 (151 bytes)

### `chat-log.sh`
- **Frequência:** `0 * * * *`
- **Owner:** Zeus/Ops
- **Risco:** baixo: re-renderiza índice
- **Função:** Mantém índice Markdown de data/chat-logs/INDEX.md.
- **Comando:** `flock -n /var/lock/chat_log_rebuild.lock /root/mgs-agent/scripts/chat-log.sh --rebuild-index >> /root/mgs-agent/logs/chat-log-rebuild.log 2>&1`
- **Log:** `/root/mgs-agent/logs/chat-log-rebuild.log`
- **Último log:** 2026-05-16T15:00:01-04:00 (1290 bytes)

### `sync-codex-oauth.sh`
- **Frequência:** `*/15 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** médio: atualiza auth.json dos profiles
- **Função:** Sincroniza tokens OAuth Codex do auth global para profiles Hermes com safety check.
- **Comando:** `flock -n /var/lock/sync_codex_oauth.lock /root/mgs-agent/scripts/sync-codex-oauth.sh >> /root/mgs-agent/logs/sync-codex-oauth.log 2>&1`
- **Log:** `/root/mgs-agent/logs/sync-codex-oauth.log`
- **Último log:** 2026-05-16T15:15:01-04:00 (25410 bytes)

### `cron-control-plane.py`
- **Frequência:** `10 8 * * *`
- **Owner:** Zeus/Ops
- **Risco:** baixo: re-renderiza docs/CRONS.md
- **Função:** Regenera docs/CRONS.md com inventário/status dos crons MGS.
- **Comando:** `flock -n /var/lock/cron_control_plane.lock /root/mgs-agent/scripts/cron-control-plane.py --write-doc >> /root/mgs-agent/logs/cron-control-plane.log 2>&1`
- **Log:** `/root/mgs-agent/logs/cron-control-plane.log`
- **Último log:** 2026-05-16T08:10:01-04:00 (172 bytes)

### `monitor-cron-stale-logs.sh`
- **Frequência:** `*/15 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo: read-only + alerta Discord
- **Função:** Watchdog que alerta quando logs de crons MGS deixam de atualizar dentro da tolerância esperada.
- **Comando:** `flock -n /var/lock/monitor_cron_stale_logs.lock /root/mgs-agent/scripts/monitor-cron-stale-logs.sh >> /root/mgs-agent/logs/monitor-cron-stale-logs.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-cron-stale-logs.log`
- **Último log:** 2026-05-16T15:15:01-04:00 (4760 bytes)

## Comandos úteis

```bash
# Regenerar este documento
/root/mgs-agent/scripts/cron-control-plane.py --markdown > /root/mgs-agent/docs/CRONS.md

# Ver JSON bruto
/root/mgs-agent/scripts/cron-control-plane.py --json | jq .

# Ver root crontab atual
crontab -l
```
