# Crons MGS — Control Plane

Gerado em: `2026-07-16T19:27:57-04:00`
Fonte: `root crontab + script/log stat, read-only`
Total MGS ativo no root crontab: **35**

## Resumo executivo

```text
Frequência          | Script                                     | Owner             | Risco                                                                                      | Flock | Último log
------------------- | ------------------------------------------ | ----------------- | ------------------------------------------------------------------------------------------ | ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
*/5 * * * *         | sync-souls.sh                              | Zeus/Infra        | baixo                                                                                      | sim   | 2026-07-16T19:25:01-04:00 synced ares skills/ops/log-monitor-discord-alert
11,26,41,56 * * * * | monitor-auto-push.sh                       | Zeus/Infra        | baixo                                                                                      | sim   | [2026-07-16T19:26:44-04:00] monitor-auto-push: Concluído. consecutive_failures=0 last_ok=08f1541a
23 10 * * *         | monitor-yoast-health-eggbev.sh             | Atena/Conteúdo    | baixo                                                                                      | sim   | [2026-07-16T10:23:08-04:00] monitor-yoast-health-eggbev: === Concluído (silencioso). SEO: 🟢206/🟡39/🔴0 / Read: 🟢205/🟡36/🔴39 ===
7,22,37,52 * * * *  | check-pending-reports.sh                   | Zeus/Infra        | baixo                                                                                      | sim   | [2026-07-16 19:22:01] check-pending-reports.sh concluído
1-56/5 * * * *      | monitor-service-restarts.sh                | Zeus/Infra        | baixo                                                                                      | sim   | 2026-07-16T19:26:02-04:00 [monitor-service-restarts] OK
54 11 * * *         | monitor-gpt55-oauth-cost.sh                | Zeus/Infra        | baixo                                                                                      | sim   | Monitor GPT-5.6 OAuth enviado: calls=1155 responses=89 hypothetical_usd=28.30 config_ok=True message_id=1527342553857265890
3-58/5 * * * *      | monitor-tool-loops.sh                      | Zeus/Infra        | baixo                                                                                      | sim   | Loop detector: 0 alertas enviados
0 5 * * *           | infra-discovery.sh                         | Zeus/Infra        | médio: sobrescreve infra-inventory.json                                                    | sim   | [05:00:11] === infra-discovery.sh DONE ===
37 8,14,20 * * *    | monitor-hermes-updates.sh                  | Zeus/Infra        | baixo                                                                                      | sim   | [2026-07-16T14:37:03-04:00] OK notified upstream=f0ff8d509 local=2ccfdb2db behind=467 days=2 feat=59 fix=264 breaking=0
*/15 * * * *        | track-article-cost.sh                      | Atena/Conteúdo    | baixo/médio: escreve SQLite local                                                          | sim   | [2026-07-16T19:15:02-0400] Nothing to process. Exit.
0 * * * *           | cleanup-zombie-sessions.sh                 | Zeus/Infra        | médio: fecha sessões Hermes inativas                                                       | sim   | [2026-07-16T19:00:01-0400] OK total closed zombie sessions: 0 (grace=180min)
44 20 * * 2,5       | housekeeping-bak-cleanup.sh                | Zeus/Infra        | alto: deleta backups antigos, preservando último por família                               | sim   | [2026-07-14T20:44:03-04:00] housekeeping: === END (no-op) ===
0 8 * * *           | pendencia-render-md.sh                     | Zeus/Ops          | baixo: re-renderiza docs/PENDENCIAS.md                                                     | sim   | Tamanho: 16671 bytes
0 * * * *           | chat-log.sh                                | Zeus/Ops          | baixo: re-renderiza índice                                                                 | sim   | 2 sessões indexadas
10 8 * * *          | cron-control-plane.py                      | Zeus/Ops          | baixo: re-renderiza docs/CRONS.md                                                          | sim   | (sem log útil ainda)
*/15 * * * *        | monitor-cron-stale-logs.sh                 | Zeus/Infra        | baixo: read-only + alerta Discord                                                          | sim   | [2026-07-16T23:15:02Z] cron-stale check: jobs=35 problems=0 resolved=0 alerts_sent=0
*/5 * * * *         | hermes-news-explainer.py                   | Zeus/Infra        | baixo/médio: consulta Discord e pode postar explicação automática                          | sim   | 2026-07-16T23:25:01.940927Z done posted=0 skipped=0 candidates=0 last_seen_id=1527409549152096347
7 8,14,20 * * *     | monitor-webshare-status.sh                 | Zeus/Infra        | baixo: consulta status público + alerta Discord se anomalia                                | sim   | [2026-07-16T14:07:02-04:00] monitor-webshare-status: OK completed mode=normal
41 3 * * *          | mgs-safety-backup.sh                       | Zeus/Infra        | médio: cria tar.gz local, exclui segredos por padrão                                       | sim   | [2026-07-14T03:43:43-04:00] mgs-safety-backup: END OK archive=/root/mgs-agent/backups/safety/mgs-safety-20260714-034101.tar.gz size=3786.63MB manifest=/root/mgs-agent/backups/safety/mgs-safety-20260714-034101.manifest.tx
54 8,13,18,22 * * * | monitor-honcho-health.sh                   | Zeus/Infra        | não classificado                                                                           | sim   | [2026-07-16T18:54:34-04:00] monitor-honcho-health: DONE status=ok failures=0
16 9 * * *          | monitor-discord-thread-archive-warnings.py | Zeus/Infra        | baixo: consulta Discord + keepalive automático antes de auto-archive                       | sim   | monitor-discord-thread-archive-warnings: OK candidates=0 pending_alerts=0 bumped=0 failed_bumps=0 errors=0
*/15 * * * *        | discord-archive-stale-agent-threads.py     | Zeus/Infra        | não classificado                                                                           | não   | {"summary": {"mode": "apply", "profiles": ["zeus", "atena", "ares"], "checked": 15, "stale": 0, "archived": 0, "skipped_recent": 15, "errors": 0}}
*/5 * * * *         | monitor-vps-health.py                      | Zeus/Infra        | baixo: read-only + alerta Discord em anomalia da VPS                                       | sim   | [2026-07-16T19:25:03-0400] monitor-vps-health: DONE status=ok issues=0 resolved=0
30 7,15 * * *       | dtr-sb-page-health-sync.sh                 | Zeus/Infra        | não classificado                                                                           | sim   | (sem log útil ainda)
2-57/5 * * * *      | alerts-infra-failed-alert-resolver.py      | Zeus/Infra        | não classificado                                                                           | sim   | [2026-07-16T23:27:01Z] alerts-infra-failed-alert-resolver: DONE candidates=1 handled=0 skipped=1 last_seen_id=1527456270129434757
20 6 * * *          | dtr-sb-daily-match-audit.sh                | Zeus/Infra        | não classificado                                                                           | sim   | "op_errors": [],
39 * * * *          | monitor-op-rate-limit.py                   | Zeus/Infra        | baixo: consulta read-only + alerta Discord por transição                                   | sim   | OK level=normal transition_sent=false token:write=0.00% token:read=0.94% account:read_write=0.40%
19,49 * * * *       | monitor-drive-auth-unified.py              | Zeus/Infra        | não classificado                                                                           | sim   | drive_auth status=ok user=token_ok sa=root_access_ok sa_checked=0 dry_run=0
0 8 * * *           | sync-sb-sms-revenue-daily.sh               | Zeus/Revenue Tech | médio/alto: lê SB autenticada e escreve receita diária no WordPress com transação/readback | sim   | {"status": "SYNC_OK", "target_date": "2026-07-15", "groups": 7, "source_rows": 7, "revenue_cents": 110958, "net_revenue_cents": 99863, "investment_cents": 0, "readback": {"status": "DAILY_REVENUE_IMPORT_OK", "target_date
* * * * *           | monitor_hermes_pending_writes.py           | Zeus/Infra        | não classificado                                                                           | sim   | {"action":"none","reason":"healthy","summary":"total=0 / >=24h=0 / mais antiga=0.0h / dead-letter=0 / memória>=90%=0","discord":"not_sent","compaction_proposals":[],"dry_run":false}
* * * * *           | finalize-hermes-structural-write.py        | Zeus/Infra        | não classificado                                                                           | sim   | {"processed": 144, "results": [{"status": "already_closed", "id": "0066072b9a311acb1c47"}, {"status": "already_closed", "id": "04334cfdd2d2d15a932d"}, {"status": "blocked", "reason": "live_hash_drift", "id": "08784a43041
5 8 * * *           | dtr-sb-restricted-summary.py               | Zeus/Infra        | não classificado                                                                           | sim   | }
14,29,44,59 * * * * | sb-restricted-transition-monitor.py        | Zeus/Infra        | não classificado                                                                           | sim   | "readback_ok": true
24 0,8-22/2 * * *   | monitor-sms-funnel-balance.py              | Zeus/Infra        | não classificado                                                                           | sim   | OK level=normal credits=27329 sent=99171 notification=none message_id=none
*/5 13,14 * * 5     | monitor-sms-funnel-balance.py              | Zeus/Infra        | não classificado                                                                           | sim   | OK level=normal credits=27329 sent=99171 notification=none message_id=none
```

## Pontos de atenção

- Alto risco: `housekeeping-bak-cleanup.sh`
- Médio risco: `infra-discovery.sh`, `cleanup-zombie-sessions.sh`, `mgs-safety-backup.sh`, `sync-sb-sms-revenue-daily.sh`
- Crons sem `flock`: `discord-archive-stale-agent-threads.py`

## Crons externos / sistema

### `/etc/cron.d/monarx-update`
- **Frequência:** `20 4 * * 2`
- **Usuário:** `root`
- **Owner:** Host/security infra
- **Risco:** médio: apt update/install externo pode acionar needrestart/systemd
- **Função:** Atualiza Monarx security scanner/protect; janela conhecida terça 04:20 EDT.
- **Comando:** `apt-get update -qq && apt-get install -y -qq monarx-agent monarx-protect monarx-protect-autodetect > /dev/null 2>&1`
- **Guardrail:** /etc/needrestart/conf.d/mgs-hermes-gateways.conf exclui Zeus/Atena/Ares de auto-restart por needrestart.

## Detalhes por cron

### `sync-souls.sh`
- **Frequência:** `*/5 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Sincroniza SOUL.md, config.yaml e skills MGS dos profiles Hermes para versionamento no repo.
- **Comando:** `flock -n /var/lock/sync_souls.lock /root/mgs-agent/scripts/sync-souls.sh >> /root/mgs-agent/logs/sync-souls.log 2>&1`
- **Log:** `/root/mgs-agent/logs/sync-souls.log`
- **Último log:** 2026-07-16T19:25:01-04:00 (3335 bytes)

### `monitor-auto-push.sh`
- **Frequência:** `11,26,41,56 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Monitora falhas no auto-push Git do /root/mgs-agent e alerta em #mgs-alerts.
- **Comando:** `flock -n /var/lock/monitor_auto_push.lock /root/mgs-agent/scripts/monitor-auto-push.sh >> /root/mgs-agent/logs/monitor-auto-push.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-auto-push.log`
- **Último log:** 2026-07-16T19:26:44-04:00 (853831 bytes)

### `monitor-yoast-health-eggbev.sh`
- **Frequência:** `23 10 * * *`
- **Owner:** Atena/Conteúdo
- **Risco:** baixo
- **Função:** Monitora saúde Yoast do eggbev: SEO + Readability com baseline, semanal e alerta por degradação.
- **Comando:** `flock -n /var/lock/monitor_yoast_health_eggbev.lock /root/mgs-agent/scripts/monitor-yoast-health-eggbev.sh >> /root/mgs-agent/logs/monitor-yoast-health-eggbev.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-yoast-health-eggbev.log`
- **Último log:** 2026-07-16T10:23:08-04:00 (20363 bytes)

### `check-pending-reports.sh`
- **Frequência:** `7,22,37,52 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Detecta skills MGS sem REPORT-INFRA/inventário e cobra correção no #alerts-infra.
- **Comando:** `flock -n /var/lock/check_pending_reports.lock /root/mgs-agent/scripts/check-pending-reports.sh >> /root/mgs-agent/logs/check-pending-reports.log 2>&1`
- **Log:** `/root/mgs-agent/logs/check-pending-reports.log`
- **Último log:** 2026-07-16T19:22:02-04:00 (349181 bytes)

### `monitor-service-restarts.sh`
- **Frequência:** `1-56/5 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Detecta restarts inesperados dos services zeus-gateway, atena-gateway, ares-gateway e mgs-autocommit.
- **Comando:** `flock -n /var/lock/monitor_service_restarts.lock /root/mgs-agent/scripts/monitor-service-restarts.sh >> /root/mgs-agent/logs/monitor-service-restarts.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-service-restarts.log`
- **Último log:** 2026-07-16T19:26:02-04:00 (5402225 bytes)

### `monitor-gpt55-oauth-cost.sh`
- **Frequência:** `54 11 * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Calcula uso hipotético GPT-5.5/OAuth dos agentes; OAuth não gera custo real por token.
- **Comando:** `flock -n /var/lock/monitor_gpt55_oauth_cost.lock /root/mgs-agent/scripts/monitor-gpt55-oauth-cost.sh >> /root/mgs-agent/logs/monitor-gpt55-oauth-cost.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-gpt55-oauth-cost.log`
- **Último log:** 2026-07-16T11:54:01-04:00 (2737 bytes)

### `monitor-tool-loops.sh`
- **Frequência:** `3-58/5 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Detecta loops de tool_calls nas sessões Hermes e alerta infra.
- **Comando:** `flock -n /var/lock/monitor_tool_loops.lock /root/mgs-agent/scripts/monitor-tool-loops.sh >> /root/mgs-agent/logs/monitor-tool-loops.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-tool-loops.log`
- **Último log:** 2026-07-16T19:23:01-04:00 (282064 bytes)

### `infra-discovery.sh`
- **Frequência:** `0 5 * * *`
- **Owner:** Zeus/Infra
- **Risco:** médio: sobrescreve infra-inventory.json
- **Função:** Regenera data/infra-inventory.json a partir do estado real do sistema.
- **Comando:** `flock -n /var/lock/infra_discovery.lock /root/mgs-agent/scripts/infra-discovery.sh >> /root/mgs-agent/logs/infra-discovery.log 2>&1`
- **Log:** `/root/mgs-agent/logs/infra-discovery.log`
- **Último log:** 2026-07-16T05:00:11-04:00 (4720 bytes)

### `monitor-hermes-updates.sh`
- **Frequência:** `37 8,14,20 * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Verifica updates upstream do Hermes Agent e alerta quando há nova versão.
- **Comando:** `flock -n /var/lock/monitor_hermes_updates.lock /root/mgs-agent/scripts/monitor-hermes-updates.sh >> /root/mgs-agent/logs/monitor-hermes-updates.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-hermes-updates.log`
- **Último log:** 2026-07-16T14:37:03-04:00 (14930 bytes)

### `track-article-cost.sh`
- **Frequência:** `*/15 * * * *`
- **Owner:** Atena/Conteúdo
- **Risco:** baixo/médio: escreve SQLite local
- **Função:** Calcula custo hipotético por artigo publicado e grava data/article-tracker.db.
- **Comando:** `flock -n /var/lock/track_article_cost.lock /root/mgs-agent/scripts/track-article-cost.sh >> /root/mgs-agent/logs/track-article-cost-cron.log 2>&1`
- **Log:** `/root/mgs-agent/logs/track-article-cost-cron.log`
- **Último log:** 2026-07-16T19:15:02-04:00 (681776 bytes)

### `cleanup-zombie-sessions.sh`
- **Frequência:** `0 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** médio: fecha sessões Hermes inativas
- **Função:** Fecha sessões Hermes zumbis/inativas usando última atividade real, com grace padrão de 180 minutos.
- **Comando:** `flock -n /var/lock/cleanup_zombie_sessions.lock /root/mgs-agent/scripts/cleanup-zombie-sessions.sh >> /root/mgs-agent/logs/cleanup-zombie-sessions.log 2>&1`
- **Log:** `/root/mgs-agent/logs/cleanup-zombie-sessions.log`
- **Último log:** 2026-07-16T19:00:01-04:00 (54550 bytes)

### `housekeeping-bak-cleanup.sh`
- **Frequência:** `44 20 * * 2,5`
- **Owner:** Zeus/Infra
- **Risco:** alto: deleta backups antigos, preservando último por família
- **Função:** Remove backups antigos (.bak/.backup/.old/.orig/~) com retenção padrão de 15 dias, preservando sempre o último por família.
- **Comando:** `flock -n /var/lock/housekeeping_bak_cleanup.lock /root/mgs-agent/scripts/housekeeping-bak-cleanup.sh >> /root/mgs-agent/logs/housekeeping-cron.log 2>&1`
- **Log:** `/root/mgs-agent/logs/housekeeping-cron.log`
- **Último log:** 2026-07-14T20:44:03-04:00 (16255 bytes)

### `pendencia-render-md.sh`
- **Frequência:** `0 8 * * *`
- **Owner:** Zeus/Ops
- **Risco:** baixo: re-renderiza docs/PENDENCIAS.md
- **Função:** Renderiza docs/PENDENCIAS.md a partir de data/pendencias.db.json.
- **Comando:** `flock -n /var/lock/pendencia_render_md.lock /root/mgs-agent/scripts/pendencia-render-md.sh >> /root/mgs-agent/logs/pendencia-render.log 2>&1`
- **Log:** `/root/mgs-agent/logs/pendencia-render.log`
- **Último log:** 2026-07-16T08:00:02-04:00 (4379 bytes)

### `chat-log.sh`
- **Frequência:** `0 * * * *`
- **Owner:** Zeus/Ops
- **Risco:** baixo: re-renderiza índice
- **Função:** Mantém índice Markdown de data/chat-logs/INDEX.md.
- **Comando:** `flock -n /var/lock/chat_log_rebuild.lock /root/mgs-agent/scripts/chat-log.sh --rebuild-index >> /root/mgs-agent/logs/chat-log-rebuild.log 2>&1`
- **Log:** `/root/mgs-agent/logs/chat-log-rebuild.log`
- **Último log:** 2026-07-16T19:00:01-04:00 (59512 bytes)

### `cron-control-plane.py`
- **Frequência:** `10 8 * * *`
- **Owner:** Zeus/Ops
- **Risco:** baixo: re-renderiza docs/CRONS.md
- **Função:** Regenera docs/CRONS.md com inventário/status dos crons MGS.
- **Comando:** `flock -n /var/lock/cron_control_plane.lock /root/mgs-agent/scripts/cron-control-plane.py --write-doc >> /root/mgs-agent/logs/cron-control-plane.log 2>&1`
- **Log:** `/root/mgs-agent/logs/cron-control-plane.log`
- **Último log:** 2026-07-16T19:27:57-04:00 (0 bytes)

### `monitor-cron-stale-logs.sh`
- **Frequência:** `*/15 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo: read-only + alerta Discord
- **Função:** Watchdog que alerta quando logs de crons MGS deixam de atualizar dentro da tolerância esperada.
- **Comando:** `flock -n /var/lock/monitor_cron_stale_logs.lock /root/mgs-agent/scripts/monitor-cron-stale-logs.sh >> /root/mgs-agent/logs/monitor-cron-stale-logs.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-cron-stale-logs.log`
- **Último log:** 2026-07-16T19:15:02-04:00 (235110 bytes)

### `hermes-news-explainer.py`
- **Frequência:** `*/5 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo/médio: consulta Discord e pode postar explicação automática
- **Função:** Lê anúncios no canal Hermes News e posta explicação executiva do Zeus em PT-BR, com estado anti-duplicata.
- **Comando:** `flock -n /var/lock/hermes_news_explainer.lock /root/mgs-agent/scripts/hermes-news-explainer.py >> /root/mgs-agent/logs/hermes-news-explainer.log 2>&1`
- **Log:** `/root/mgs-agent/logs/hermes-news-explainer.log`
- **Último log:** 2026-07-16T19:25:01-04:00 (1000248 bytes)

### `monitor-webshare-status.sh`
- **Frequência:** `7 8,14,20 * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo: consulta status público + alerta Discord se anomalia
- **Função:** Monitora status.webshare.io e alerta infra quando detectar manutenção/incidente relevante.
- **Comando:** `flock -n /var/lock/monitor_webshare_status.lock /root/mgs-agent/scripts/monitor-webshare-status.sh >> /root/mgs-agent/logs/monitor-webshare-status.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-webshare-status.log`
- **Último log:** 2026-07-16T14:07:02-04:00 (25112 bytes)

### `mgs-safety-backup.sh`
- **Frequência:** `41 3 * * *`
- **Owner:** Zeus/Infra
- **Risco:** médio: cria tar.gz local, exclui segredos por padrão
- **Função:** Cria snapshot operacional seguro no máximo a cada 3 dias, excluindo segredos conhecidos e preservando o último backup.
- **Comando:** `flock -n /var/lock/mgs_safety_backup.lock /root/mgs-agent/scripts/mgs-safety-backup.sh >> /root/mgs-agent/logs/mgs-safety-backup-cron.log 2>&1`
- **Log:** `/root/mgs-agent/logs/mgs-safety-backup-cron.log`
- **Último log:** 2026-07-16T03:41:01-04:00 (6673 bytes)

### `monitor-honcho-health.sh`
- **Frequência:** `54 8,13,18,22 * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/monitor_honcho_health.lock /root/mgs-agent/scripts/monitor-honcho-health.sh >> /root/mgs-agent/logs/monitor-honcho-health.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-honcho-health.log`
- **Último log:** 2026-07-16T18:54:34-04:00 (584759 bytes)

### `monitor-discord-thread-archive-warnings.py`
- **Frequência:** `16 9 * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo: consulta Discord + keepalive automático antes de auto-archive
- **Função:** Monitora threads Discord ativas com auto-archive de 1 semana em Zeus/Atena/Ares e posta keepalive quando faltam até 24h para ficarem ocultas.
- **Comando:** `flock -n /var/lock/monitor_discord_thread_archive_warnings.lock /root/mgs-agent/scripts/monitor-discord-thread-archive-warnings.py >> /root/mgs-agent/logs/monitor-discord-thread-archive-warnings.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-discord-thread-archive-warnings.log`
- **Último log:** 2026-07-16T09:16:02-04:00 (2099 bytes)

### `discord-archive-stale-agent-threads.py`
- **Frequência:** `*/15 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `/root/mgs-agent/scripts/discord-archive-stale-agent-threads.py --apply --grace-minutes 30 --summary-only >> /root/mgs-agent/logs/discord-archive-stale-agent-threads.log 2>&1`
- **Log:** `/root/mgs-agent/logs/discord-archive-stale-agent-threads.log`
- **Último log:** 2026-07-16T19:15:03-04:00 (232813 bytes)

### `monitor-vps-health.py`
- **Frequência:** `*/5 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo: read-only + alerta Discord em anomalia da VPS
- **Função:** Monitora saúde bruta da VPS: disco, inodes, memória disponível, load, reboot recente, tamanho de backups e services MGS ativos.
- **Comando:** `flock -n /var/lock/monitor_vps_health.lock /root/mgs-agent/scripts/monitor-vps-health.py --channel-id 1522444367292268565 >> /root/mgs-agent/logs/monitor-vps-health.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-vps-health.log`
- **Último log:** 2026-07-16T19:25:03-04:00 (332118 bytes)

### `dtr-sb-page-health-sync.sh`
- **Frequência:** `30 7,15 * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/dtr_sb_page_health_sync.lock /root/mgs-agent/scripts/dtr-sb-page-health-sync.sh --apply --quiet-noop >/dev/null 2>&1`
- **Log:** `sem redirect explícito`
- **Último log:** arquivo ausente

### `alerts-infra-failed-alert-resolver.py`
- **Frequência:** `2-57/5 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/alerts_infra_failed_alert_resolver.lock /root/mgs-agent/scripts/alerts-infra-failed-alert-resolver.py >> /root/mgs-agent/logs/alerts-infra-failed-alert-resolver.log 2>&1`
- **Log:** `/root/mgs-agent/logs/alerts-infra-failed-alert-resolver.log`
- **Último log:** 2026-07-16T19:27:01-04:00 (438988 bytes)

### `dtr-sb-daily-match-audit.sh`
- **Frequência:** `20 6 * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/dtr_sb_daily_match_audit.lock /root/mgs-agent/scripts/dtr-sb-daily-match-audit.sh >> /root/mgs-agent/logs/dtr-sb-daily-match-audit-cron.log 2>&1`
- **Log:** `/root/mgs-agent/logs/dtr-sb-daily-match-audit-cron.log`
- **Último log:** 2026-07-16T06:55:07-04:00 (66276 bytes)

### `monitor-op-rate-limit.py`
- **Frequência:** `39 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo: consulta read-only + alerta Discord por transição
- **Função:** Monitora limites horário e diário do 1Password Business e alerta o canal dedicado em 50%/90%.
- **Comando:** `flock -n /var/lock/monitor_op_rate_limit.lock /root/mgs-agent/scripts/monitor-op-rate-limit.py >> /root/mgs-agent/logs/monitor-op-rate-limit.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-op-rate-limit.log`
- **Último log:** 2026-07-16T18:39:01-04:00 (14016 bytes)

### `monitor-drive-auth-unified.py`
- **Frequência:** `19,49 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/monitor_drive_auth_unified.lock /root/mgs-agent/scripts/monitor-drive-auth-unified.py >> /root/mgs-agent/logs/monitor-drive-auth-unified.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-drive-auth-unified.log`
- **Último log:** 2026-07-16T19:19:02-04:00 (24008 bytes)

### `sync-sb-sms-revenue-daily.sh`
- **Frequência:** `0 8 * * *`
- **Owner:** Zeus/Revenue Tech
- **Risco:** médio/alto: lê SB autenticada e escreve receita diária no WordPress com transação/readback
- **Função:** Às 08:00 ET, importa no WordPress a receita líquida SMS do dia anterior fechado na Smart Bidding, com upsert/readback e uma retentativa automática após 5 minutos para falhas transitórias.
- **Comando:** `flock -n /var/lock/sync_sb_sms_revenue_daily.lock /root/mgs-agent/scripts/sync-sb-sms-revenue-daily.sh >> /root/mgs-agent/logs/sync-sb-sms-revenue-daily.log 2>&1`
- **Log:** `/root/mgs-agent/logs/sync-sb-sms-revenue-daily.log`
- **Último log:** 2026-07-16T08:00:16-04:00 (6630 bytes)

### `monitor_hermes_pending_writes.py`
- **Frequência:** `* * * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/monitor_hermes_pending_writes.lock /root/mgs-agent/scripts/monitor_hermes_pending_writes.py >> /root/mgs-agent/logs/monitor-hermes-pending-writes.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-hermes-pending-writes.log`
- **Último log:** 2026-07-16T19:27:01-04:00 (752675 bytes)

### `finalize-hermes-structural-write.py`
- **Frequência:** `* * * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/finalize-hermes-structural-write.lock /root/mgs-agent/scripts/finalize-hermes-structural-write.py >> /root/mgs-agent/logs/hermes-structural-write-finalizer.log 2>&1`
- **Log:** `/root/mgs-agent/logs/hermes-structural-write-finalizer.log`
- **Último log:** 2026-07-16T19:27:01-04:00 (20169419 bytes)

### `dtr-sb-restricted-summary.py`
- **Frequência:** `5 8 * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/dtr_sb_restricted_summary.lock xvfb-run -a /root/.local/share/mgs/sb-venv/bin/python /root/mgs-agent/scripts/dtr-sb-restricted-summary.py >> /root/mgs-agent/logs/dtr-sb-restricted-summary.log 2>&1`
- **Log:** `/root/mgs-agent/logs/dtr-sb-restricted-summary.log`
- **Último log:** 2026-07-16T08:05:13-04:00 (20176 bytes)

### `sb-restricted-transition-monitor.py`
- **Frequência:** `14,29,44,59 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/sb_restricted_transition_monitor.lock xvfb-run -a /root/.local/share/mgs/sb-venv/bin/python /root/mgs-agent/scripts/sb-restricted-transition-monitor.py --apply >> /root/mgs-agent/logs/sb-restricted-transition-monitor.log 2>&1`
- **Log:** `/root/mgs-agent/logs/sb-restricted-transition-monitor.log`
- **Último log:** 2026-07-16T19:14:15-04:00 (97774 bytes)

### `monitor-sms-funnel-balance.py`
- **Frequência:** `24 0,8-22/2 * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/monitor_sms_funnel_balance.lock /root/mgs-agent/scripts/monitor-sms-funnel-balance.py >> /root/mgs-agent/logs/monitor-sms-funnel-balance.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-sms-funnel-balance.log`
- **Último log:** 2026-07-16T19:27:41-04:00 (525 bytes)

### `monitor-sms-funnel-balance.py`
- **Frequência:** `*/5 13,14 * * 5`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/monitor_sms_funnel_balance_friday.lock /root/mgs-agent/scripts/monitor-sms-funnel-balance.py --friday-report >> /root/mgs-agent/logs/monitor-sms-funnel-balance.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-sms-funnel-balance.log`
- **Último log:** 2026-07-16T19:27:41-04:00 (525 bytes)

## Comandos úteis

```bash
# Regenerar este documento
/root/mgs-agent/scripts/cron-control-plane.py --markdown > /root/mgs-agent/docs/CRONS.md

# Ver JSON bruto
/root/mgs-agent/scripts/cron-control-plane.py --json | jq .

# Ver root crontab atual
crontab -l
```
