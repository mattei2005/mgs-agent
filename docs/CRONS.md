# Crons MGS — Control Plane

Gerado em: `2026-08-10T08:10:01-04:00`
Fonte: `root crontab + script/log stat, read-only`
Total MGS ativo no root crontab: **42**

## Resumo executivo

```text
Frequência               | Script                                     | Owner             | Risco                                                                                                | Flock | Último log
------------------------ | ------------------------------------------ | ----------------- | ---------------------------------------------------------------------------------------------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
*/5 * * * *              | sync-souls.sh                              | Zeus/Infra        | baixo                                                                                                | sim   | 2026-08-10T08:10:01-04:00 synced zeus skills/ops
11,26,41,56 * * * *      | monitor-auto-push.sh                       | Zeus/Infra        | baixo                                                                                                | sim   | [2026-08-10T07:56:57-04:00] monitor-auto-push: Concluído. consecutive_failures=0 last_ok=f2d35827
23 10 * * *              | monitor-yoast-health-eggbev.sh             | Atena/Conteúdo    | baixo                                                                                                | sim   | [2026-08-09T10:23:08-04:00] monitor-yoast-health-eggbev: === Concluído (silencioso). SEO: 🟢216/🟡39/🔴0 / Read: 🟢212/🟡39/🔴39 ===
7,22,37,52 * * * *       | check-pending-reports.sh                   | Zeus/Infra        | baixo                                                                                                | sim   | [2026-08-10 08:07:01] check-pending-reports.sh concluído
1-56/5 * * * *           | monitor-service-restarts.sh                | Zeus/Infra        | baixo                                                                                                | sim   | 2026-08-10T08:06:01-04:00 [monitor-service-restarts] OK
54 11 * * *              | monitor-gpt55-oauth-cost.sh                | Zeus/Infra        | baixo                                                                                                | sim   | Monitor GPT-5.6 OAuth enviado: calls=30 sessions=2 input=147855 output=13028 actual_usd=0.00 hypothetical_usd=1.31 config_ok=True billing_ok=True message_id=1536039864120647802
3-58/5 * * * *           | monitor-tool-loops.sh                      | Zeus/Infra        | baixo                                                                                                | sim   | Loop detector: 0 alertas enviados
0 5 * * *                | infra-discovery.sh                         | Zeus/Infra        | médio: sobrescreve infra-inventory.json                                                              | sim   | [05:00:11] === infra-discovery.sh DONE ===
37 8,14,20 * * *         | monitor-hermes-updates.sh                  | Zeus/Infra        | baixo                                                                                                | sim   | [2026-08-09T20:37:02-04:00] OK no_changes upstream=ed3c39108b (last_notified=ed3c391)
*/15 * * * *             | track-article-cost.sh                      | Atena/Conteúdo    | baixo/médio: escreve SQLite local                                                                    | sim   | [2026-08-10T08:00:02-0400] Nothing to process. Exit.
0 * * * *                | cleanup-zombie-sessions.sh                 | Zeus/Infra        | médio: fecha sessões Hermes inativas                                                                 | sim   | [2026-08-10T08:00:02-0400] OK total closed zombie sessions: 0 (grace=180min)
44 20 * * 2,5            | housekeeping-bak-cleanup.sh                | Zeus/Infra        | alto: deleta backups antigos, preservando último por família                                         | sim   | [2026-08-07T20:44:09-04:00] housekeeping: === END (no-op) ===
0 8 * * *                | pendencia-render-md.sh                     | Zeus/Ops          | baixo: re-renderiza docs/PENDENCIAS.md                                                               | sim   | Tamanho: 16671 bytes
0 * * * *                | chat-log.sh                                | Zeus/Ops          | baixo: re-renderiza índice                                                                           | sim   | 2 sessões indexadas
10 8 * * *               | cron-control-plane.py                      | Zeus/Ops          | baixo: re-renderiza docs/CRONS.md                                                                    | sim   | OK wrote /root/mgs-agent/docs/CRONS.md jobs=42 generated_at=2026-08-09T08:10:02-04:00
*/15 * * * *             | monitor-cron-stale-logs.sh                 | Zeus/Infra        | baixo: read-only + alerta Discord                                                                    | sim   | [2026-08-10T12:00:02Z] cron-stale check: jobs=42 problems=0 resolved=0 alerts_sent=0
*/5 * * * *              | hermes-news-explainer.py                   | Zeus/Infra        | baixo/médio: consulta Discord e pode postar explicação automática                                    | sim   | 2026-08-10T12:05:02.438219Z done posted=0 skipped=0 candidates=0 last_seen_id=1536183637525925898
7 8,14,20 * * *          | monitor-webshare-status.sh                 | Zeus/Infra        | baixo: consulta status público + alerta Discord se anomalia                                          | sim   | [2026-08-10T08:07:02-04:00] monitor-webshare-status: OK completed mode=normal
41 3 * * *               | mgs-safety-backup.sh                       | Zeus/Infra        | alto: cria snapshot e remove automaticamente safety backups além dos 2 mais recentes                 | sim   | [2026-08-07T03:43:34-04:00] mgs-safety-backup: END OK archive=/root/mgs-agent/backups/safety/mgs-safety-20260807-034101.tar.gz size=3722.51MB manifest=/root/mgs-agent/backups/safety/mgs-safety-20260807-034101.manifest.tx
54 8,13,18,22 * * *      | monitor-honcho-health.sh                   | Zeus/Infra        | não classificado                                                                                     | sim   | [2026-08-09T22:54:29-04:00] monitor-honcho-health: DONE status=ok failures=0
16 9 * * *               | monitor-discord-thread-archive-warnings.py | Zeus/Infra        | baixo: consulta Discord + keepalive automático antes de auto-archive                                 | sim   | monitor-discord-thread-archive-warnings: OK candidates=2 pending_alerts=2 bumped=2 failed_bumps=0 errors=0
*/15 * * * *             | discord-archive-stale-agent-threads.py     | Zeus/Infra        | não classificado                                                                                     | não   | {"summary": {"mode": "apply", "profiles": ["zeus", "atena", "ares"], "checked": 9, "stale": 0, "archived": 0, "skipped_recent": 9, "errors": 0}}
*/5 * * * *              | monitor-vps-health.py                      | Zeus/Infra        | baixo: read-only + alerta Discord em anomalia da VPS                                                 | sim   | [2026-08-10T08:05:03-0400] monitor-vps-health: DONE status=ok issues=0 resolved=0
30 7,15 * * *            | dtr-sb-page-health-sync.sh                 | Zeus/Infra        | não classificado                                                                                     | sim   | (sem log útil ainda)
2-57/5 * * * *           | alerts-infra-failed-alert-resolver.py      | Zeus/Infra        | não classificado                                                                                     | sim   | [2026-08-10T12:07:01Z] alerts-infra-failed-alert-resolver: DONE candidates=0 handled=0 skipped=0 last_seen_id=1536277551943655515
20 6 * * *               | dtr-sb-daily-match-audit.sh                | Zeus/Infra        | não classificado                                                                                     | sim   | "op_errors": [],
39 * * * *               | monitor-op-rate-limit.py                   | Zeus/Infra        | baixo: consulta read-only + alerta Discord por transição                                             | sim   | OK level=normal transition_sent=false token:write=0.00% token:read=0.00% account:read_write=0.00%
19,49 * * * *            | monitor-drive-auth-unified.py              | Zeus/Infra        | não classificado                                                                                     | sim   | drive_auth status=ok primary=service_account sa=root_access_ok guard=legacy_runtime_clean guard_hits=0 sa_checked=0 dry_run=0
0 8 * * *                | sync-sb-sms-revenue-daily.sh               | Zeus/Revenue Tech | médio/alto: lê SB autenticada e escreve receita diária no WordPress com transação/readback           | sim   | {"status": "SYNC_OK", "target_date": "2026-08-09", "groups": 8, "source_rows": 8, "revenue_cents": 80415, "net_revenue_cents": 72372, "investment_cents": 0, "readback": {"status": "DAILY_REVENUE_IMPORT_OK", "target_date"
* * * * *                | monitor_hermes_pending_writes.py           | Zeus/Infra        | não classificado                                                                                     | sim   | {"action":"none","reason":"healthy","summary":"total=0 / >=24h=0 / mais antiga=0.0h / dead-letter=0 / memória>=90%=0","discord":"not_sent","compaction_proposals":[],"dry_run":false}
* * * * *                | finalize-hermes-structural-write.py        | Zeus/Infra        | não classificado                                                                                     | sim   | {"scanned": 259, "processed": 0, "status_counts": {"already_closed": 205, "already_quarantined": 54}, "log_rotated": false}
5 8 * * *                | dtr-sb-restricted-summary.py               | Zeus/Infra        | não classificado                                                                                     | sim   | }
14,29,44,59 * * * *      | sb-restricted-transition-monitor.py        | Zeus/Infra        | não classificado                                                                                     | sim   | "readback_ok": true
24 0,1,7-23 * * *        | monitor-sms-funnel-balance.py              | Zeus/Infra        | não classificado                                                                                     | sim   | OK level=normal credits=218809 sent=317691 notification=none message_id=none
*/5 13,14 * * 5          | monitor-sms-funnel-balance.py              | Zeus/Infra        | não classificado                                                                                     | sim   | OK level=normal credits=218809 sent=317691 notification=none message_id=none
4,14,24,34,44,54 * * * * | monitor-hermes-memory-capacity.py          | Zeus/Infra        | médio: reescreve USER/MEMORY somente após gates fail-closed e backup protegido                       | sim   | {"success":true,"dry_run":false,"profiles":["ares","atena","zeus"],"stores_checked":6,"threshold_count":0,"compacted_count":0,"failure_count":0,"delivery_failures":0,"outbox_pending":0}
* * * * *                | hermes-news-explainer-watchdog.py          | Zeus/Infra        | baixo/médio: consulta Discord a cada minuto e só posta ao recuperar explicação órfã                  | sim   | 2026-08-10T12:09:01.870377Z watchdog done dry_run=0 healthy=50 waiting=0 orphan=0 recovered=0 fallback=0 failed=0 busy=0 reconciled=0 sla_seconds=600
47 4 * * *               | hermes-context-cost-audit.py               | Zeus/Infra        | baixo: leitura local + escrita atômica de estado agregado sem conteúdo das conversas                 | sim   | 2026-08-10T08:47:01.524360+00:00 status=ok profiles=3 errors=0 max_context_percent=54.43 state=/root/mgs-agent/data/hermes-context-cost-audit-state.json
0 8 * * *                | sb-broadcast-template-repair.sh            | Zeus/Infra        | não classificado                                                                                     | não   | {"at_sp": "2026-08-10T09:00:22-03:00", "mode": "apply", "stage": "full", "templates": [{"template_id": "691bbfd5-e13c-f552-4b39-3dedf76d15bf", "template": "Eggbev - US-CC-EN/EN-SR - g006-d Nicolas", "vertical": "US-CC-EN
*/15 * * * *             | sb-broadcast-template-repair.sh            | Zeus/Infra        | não classificado                                                                                     | não   | {"at_sp": "2026-08-10T09:00:22-03:00", "mode": "apply", "stage": "full", "templates": [{"template_id": "691bbfd5-e13c-f552-4b39-3dedf76d15bf", "template": "Eggbev - US-CC-EN/EN-SR - g006-d Nicolas", "vertical": "US-CC-EN
10 23 * * *              | sb-broadcast-template-repair.sh            | Zeus/Infra        | não classificado                                                                                     | não   | {"at_sp": "2026-08-10T09:00:22-03:00", "mode": "apply", "stage": "full", "templates": [{"template_id": "691bbfd5-e13c-f552-4b39-3dedf76d15bf", "template": "Eggbev - US-CC-EN/EN-SR - g006-d Nicolas", "vertical": "US-CC-EN
17 8 * * *               | sync-sb-messenger-revenue-sheet.py         | Zeus/Revenue Tech | médio: lê SB autenticada e substitui a coluna C da planilha com backup, canário, rollback e readback | sim   | {"status":"SYNC_OK","started_at_et":"2026-08-09T08:17:01-04:00","completed_at_et":"2026-08-09T08:17:10-04:00","period_start":"2026-08-03","period_end":"2026-08-09","publishers":45,"api_rows":7137,"named_profiles":159,"da
```

## Pontos de atenção

- Alto risco: `housekeeping-bak-cleanup.sh`, `mgs-safety-backup.sh`
- Médio risco: `infra-discovery.sh`, `cleanup-zombie-sessions.sh`, `sync-sb-sms-revenue-daily.sh`, `monitor-hermes-memory-capacity.py`, `sync-sb-messenger-revenue-sheet.py`
- Crons sem `flock`: `discord-archive-stale-agent-threads.py`, `sb-broadcast-template-repair.sh`, `sb-broadcast-template-repair.sh`, `sb-broadcast-template-repair.sh`

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
- **Último log:** 2026-08-10T08:10:01-04:00 (6343913 bytes)

### `monitor-auto-push.sh`
- **Frequência:** `11,26,41,56 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Monitora falhas no auto-push Git do /root/mgs-agent e alerta em #mgs-alerts.
- **Comando:** `flock -n /var/lock/monitor_auto_push.lock /root/mgs-agent/scripts/monitor-auto-push.sh >> /root/mgs-agent/logs/monitor-auto-push.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-auto-push.log`
- **Último log:** 2026-08-10T07:56:57-04:00 (1411333 bytes)

### `monitor-yoast-health-eggbev.sh`
- **Frequência:** `23 10 * * *`
- **Owner:** Atena/Conteúdo
- **Risco:** baixo
- **Função:** Monitora saúde Yoast do eggbev: SEO + Readability com baseline, semanal e alerta por degradação.
- **Comando:** `flock -n /var/lock/monitor_yoast_health_eggbev.lock /root/mgs-agent/scripts/monitor-yoast-health-eggbev.sh >> /root/mgs-agent/logs/monitor-yoast-health-eggbev.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-yoast-health-eggbev.log`
- **Último log:** 2026-08-09T10:23:08-04:00 (55121 bytes)

### `check-pending-reports.sh`
- **Frequência:** `7,22,37,52 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Detecta skills MGS sem REPORT-INFRA/inventário e cobra correção no #alerts-infra.
- **Comando:** `flock -n /var/lock/check_pending_reports.lock /root/mgs-agent/scripts/check-pending-reports.sh >> /root/mgs-agent/logs/check-pending-reports.log 2>&1`
- **Log:** `/root/mgs-agent/logs/check-pending-reports.log`
- **Último log:** 2026-08-10T08:07:03-04:00 (656777 bytes)

### `monitor-service-restarts.sh`
- **Frequência:** `1-56/5 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Detecta restarts inesperados dos services zeus-gateway, atena-gateway, ares-gateway e mgs-autocommit.
- **Comando:** `flock -n /var/lock/monitor_service_restarts.lock /root/mgs-agent/scripts/monitor-service-restarts.sh >> /root/mgs-agent/logs/monitor-service-restarts.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-service-restarts.log`
- **Último log:** 2026-08-10T08:06:01-04:00 (9190140 bytes)

### `monitor-gpt55-oauth-cost.sh`
- **Frequência:** `54 11 * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Calcula uso hipotético GPT-5.5/OAuth dos agentes; OAuth não gera custo real por token.
- **Comando:** `flock -n /var/lock/monitor_gpt55_oauth_cost.lock /root/mgs-agent/scripts/monitor-gpt55-oauth-cost.sh >> /root/mgs-agent/logs/monitor-gpt55-oauth-cost.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-gpt55-oauth-cost.log`
- **Último log:** 2026-08-09T11:54:01-04:00 (6908 bytes)

### `monitor-tool-loops.sh`
- **Frequência:** `3-58/5 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Detecta loops de tool_calls nas sessões Hermes e alerta infra.
- **Comando:** `flock -n /var/lock/monitor_tool_loops.lock /root/mgs-agent/scripts/monitor-tool-loops.sh >> /root/mgs-agent/logs/monitor-tool-loops.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-tool-loops.log`
- **Último log:** 2026-08-10T08:08:01-04:00 (522240 bytes)

### `infra-discovery.sh`
- **Frequência:** `0 5 * * *`
- **Owner:** Zeus/Infra
- **Risco:** médio: sobrescreve infra-inventory.json
- **Função:** Regenera data/infra-inventory.json a partir do estado real do sistema.
- **Comando:** `flock -n /var/lock/infra_discovery.lock /root/mgs-agent/scripts/infra-discovery.sh >> /root/mgs-agent/logs/infra-discovery.log 2>&1`
- **Log:** `/root/mgs-agent/logs/infra-discovery.log`
- **Último log:** 2026-08-10T05:00:11-04:00 (22736 bytes)

### `monitor-hermes-updates.sh`
- **Frequência:** `37 8,14,20 * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Verifica updates upstream do Hermes Agent e alerta quando há nova versão.
- **Comando:** `flock -n /var/lock/monitor_hermes_updates.lock /root/mgs-agent/scripts/monitor-hermes-updates.sh >> /root/mgs-agent/logs/monitor-hermes-updates.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-hermes-updates.log`
- **Último log:** 2026-08-09T20:37:02-04:00 (30211 bytes)

### `track-article-cost.sh`
- **Frequência:** `*/15 * * * *`
- **Owner:** Atena/Conteúdo
- **Risco:** baixo/médio: escreve SQLite local
- **Função:** Calcula custo hipotético por artigo publicado e grava data/article-tracker.db.
- **Comando:** `flock -n /var/lock/track_article_cost.lock /root/mgs-agent/scripts/track-article-cost.sh >> /root/mgs-agent/logs/track-article-cost-cron.log 2>&1`
- **Log:** `/root/mgs-agent/logs/track-article-cost-cron.log`
- **Último log:** 2026-08-10T08:00:02-04:00 (1258751 bytes)

### `cleanup-zombie-sessions.sh`
- **Frequência:** `0 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** médio: fecha sessões Hermes inativas
- **Função:** Fecha sessões Hermes zumbis/inativas usando última atividade real, com grace padrão de 180 minutos.
- **Comando:** `flock -n /var/lock/cleanup_zombie_sessions.lock /root/mgs-agent/scripts/cleanup-zombie-sessions.sh >> /root/mgs-agent/logs/cleanup-zombie-sessions.log 2>&1`
- **Log:** `/root/mgs-agent/logs/cleanup-zombie-sessions.log`
- **Último log:** 2026-08-10T08:00:02-04:00 (45390 bytes)

### `housekeeping-bak-cleanup.sh`
- **Frequência:** `44 20 * * 2,5`
- **Owner:** Zeus/Infra
- **Risco:** alto: deleta backups antigos, preservando último por família
- **Função:** Remove backups antigos (.bak/.backup/.old/.orig/~) com retenção padrão de 15 dias, preservando sempre o último por família.
- **Comando:** `flock -n /var/lock/housekeeping_bak_cleanup.lock /root/mgs-agent/scripts/housekeeping-bak-cleanup.sh >> /root/mgs-agent/logs/housekeeping-cron.log 2>&1`
- **Log:** `/root/mgs-agent/logs/housekeeping-cron.log`
- **Último log:** 2026-08-07T20:44:09-04:00 (19852 bytes)

### `pendencia-render-md.sh`
- **Frequência:** `0 8 * * *`
- **Owner:** Zeus/Ops
- **Risco:** baixo: re-renderiza docs/PENDENCIAS.md
- **Função:** Renderiza docs/PENDENCIAS.md a partir de data/pendencias.db.json.
- **Comando:** `flock -n /var/lock/pendencia_render_md.lock /root/mgs-agent/scripts/pendencia-render-md.sh >> /root/mgs-agent/logs/pendencia-render.log 2>&1`
- **Log:** `/root/mgs-agent/logs/pendencia-render.log`
- **Último log:** 2026-08-10T08:00:02-04:00 (8154 bytes)

### `chat-log.sh`
- **Frequência:** `0 * * * *`
- **Owner:** Zeus/Ops
- **Risco:** baixo: re-renderiza índice
- **Função:** Mantém índice Markdown de data/chat-logs/INDEX.md.
- **Comando:** `flock -n /var/lock/chat_log_rebuild.lock /root/mgs-agent/scripts/chat-log.sh --rebuild-index >> /root/mgs-agent/logs/chat-log-rebuild.log 2>&1`
- **Log:** `/root/mgs-agent/logs/chat-log-rebuild.log`
- **Último log:** 2026-08-10T08:00:02-04:00 (110166 bytes)

### `cron-control-plane.py`
- **Frequência:** `10 8 * * *`
- **Owner:** Zeus/Ops
- **Risco:** baixo: re-renderiza docs/CRONS.md
- **Função:** Regenera docs/CRONS.md com inventário/status dos crons MGS.
- **Comando:** `flock -n /var/lock/cron_control_plane.lock /root/mgs-agent/scripts/cron-control-plane.py --write-doc >> /root/mgs-agent/logs/cron-control-plane.log 2>&1`
- **Log:** `/root/mgs-agent/logs/cron-control-plane.log`
- **Último log:** 2026-08-09T08:10:02-04:00 (2150 bytes)

### `monitor-cron-stale-logs.sh`
- **Frequência:** `*/15 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo: read-only + alerta Discord
- **Função:** Watchdog que alerta quando logs de crons MGS deixam de atualizar dentro da tolerância esperada.
- **Comando:** `flock -n /var/lock/monitor_cron_stale_logs.lock /root/mgs-agent/scripts/monitor-cron-stale-logs.sh >> /root/mgs-agent/logs/monitor-cron-stale-logs.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-cron-stale-logs.log`
- **Último log:** 2026-08-10T08:00:03-04:00 (435285 bytes)

### `hermes-news-explainer.py`
- **Frequência:** `*/5 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo/médio: consulta Discord e pode postar explicação automática
- **Função:** Lê anúncios no canal Hermes News e posta explicação executiva do Zeus em PT-BR, com estado anti-duplicata.
- **Comando:** `flock -n /var/lock/hermes_news_explainer.lock /root/mgs-agent/scripts/hermes-news-explainer.py >> /root/mgs-agent/logs/hermes-news-explainer.log 2>&1`
- **Log:** `/root/mgs-agent/logs/hermes-news-explainer.log`
- **Último log:** 2026-08-10T08:05:02-04:00 (2211452 bytes)

### `monitor-webshare-status.sh`
- **Frequência:** `7 8,14,20 * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo: consulta status público + alerta Discord se anomalia
- **Função:** Monitora status.webshare.io e alerta infra quando detectar manutenção/incidente relevante.
- **Comando:** `flock -n /var/lock/monitor_webshare_status.lock /root/mgs-agent/scripts/monitor-webshare-status.sh >> /root/mgs-agent/logs/monitor-webshare-status.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-webshare-status.log`
- **Último log:** 2026-08-10T08:07:02-04:00 (46720 bytes)

### `mgs-safety-backup.sh`
- **Frequência:** `41 3 * * *`
- **Owner:** Zeus/Infra
- **Risco:** alto: cria snapshot e remove automaticamente safety backups além dos 2 mais recentes
- **Função:** Cria snapshot operacional seguro no máximo a cada 3 dias, exclui segredos conhecidos e mantém somente os 2 snapshots validados mais recentes.
- **Comando:** `flock -n /var/lock/mgs_safety_backup.lock /root/mgs-agent/scripts/mgs-safety-backup.sh >> /root/mgs-agent/logs/mgs-safety-backup-cron.log 2>&1`
- **Log:** `/root/mgs-agent/logs/mgs-safety-backup-cron.log`
- **Último log:** 2026-08-10T03:41:01-04:00 (13857 bytes)

### `monitor-honcho-health.sh`
- **Frequência:** `54 8,13,18,22 * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/monitor_honcho_health.lock /root/mgs-agent/scripts/monitor-honcho-health.sh >> /root/mgs-agent/logs/monitor-honcho-health.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-honcho-health.log`
- **Último log:** 2026-08-09T22:54:29-04:00 (612480 bytes)

### `monitor-discord-thread-archive-warnings.py`
- **Frequência:** `16 9 * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo: consulta Discord + keepalive automático antes de auto-archive
- **Função:** Monitora threads Discord ativas com auto-archive de 1 semana em Zeus/Atena/Ares e posta keepalive quando faltam até 24h para ficarem ocultas.
- **Comando:** `flock -n /var/lock/monitor_discord_thread_archive_warnings.lock /root/mgs-agent/scripts/monitor-discord-thread-archive-warnings.py >> /root/mgs-agent/logs/monitor-discord-thread-archive-warnings.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-discord-thread-archive-warnings.log`
- **Último log:** 2026-08-09T09:16:03-04:00 (4667 bytes)

### `discord-archive-stale-agent-threads.py`
- **Frequência:** `*/15 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `/root/mgs-agent/scripts/discord-archive-stale-agent-threads.py --apply --grace-minutes 30 --summary-only >> /root/mgs-agent/logs/discord-archive-stale-agent-threads.log 2>&1`
- **Log:** `/root/mgs-agent/logs/discord-archive-stale-agent-threads.log`
- **Último log:** 2026-08-10T08:00:04-04:00 (576916 bytes)

### `monitor-vps-health.py`
- **Frequência:** `*/5 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo: read-only + alerta Discord em anomalia da VPS
- **Função:** Monitora saúde bruta da VPS: disco, inodes, memória disponível, load, reboot recente, tamanho de backups e services MGS ativos.
- **Comando:** `flock -n /var/lock/monitor_vps_health.lock /root/mgs-agent/scripts/monitor-vps-health.py --channel-id 1522444367292268565 >> /root/mgs-agent/logs/monitor-vps-health.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-vps-health.log`
- **Último log:** 2026-08-10T08:05:03-04:00 (916945 bytes)

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
- **Último log:** 2026-08-10T08:07:01-04:00 (1358358 bytes)

### `dtr-sb-daily-match-audit.sh`
- **Frequência:** `20 6 * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/dtr_sb_daily_match_audit.lock /root/mgs-agent/scripts/dtr-sb-daily-match-audit.sh >> /root/mgs-agent/logs/dtr-sb-daily-match-audit-cron.log 2>&1`
- **Log:** `/root/mgs-agent/logs/dtr-sb-daily-match-audit-cron.log`
- **Último log:** 2026-08-10T06:56:35-04:00 (182782 bytes)

### `monitor-op-rate-limit.py`
- **Frequência:** `39 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo: consulta read-only + alerta Discord por transição
- **Função:** Monitora limites horário e diário do 1Password Business e alerta o canal dedicado em 50%/90%.
- **Comando:** `flock -n /var/lock/monitor_op_rate_limit.lock /root/mgs-agent/scripts/monitor-op-rate-limit.py >> /root/mgs-agent/logs/monitor-op-rate-limit.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-op-rate-limit.log`
- **Último log:** 2026-08-10T07:39:02-04:00 (71829 bytes)

### `monitor-drive-auth-unified.py`
- **Frequência:** `19,49 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/monitor_drive_auth_unified.lock /root/mgs-agent/scripts/monitor-drive-auth-unified.py >> /root/mgs-agent/logs/monitor-drive-auth-unified.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-drive-auth-unified.log`
- **Último log:** 2026-08-10T07:49:02-04:00 (171045 bytes)

### `sync-sb-sms-revenue-daily.sh`
- **Frequência:** `0 8 * * *`
- **Owner:** Zeus/Revenue Tech
- **Risco:** médio/alto: lê SB autenticada e escreve receita diária no WordPress com transação/readback
- **Função:** Às 08:00 ET, importa no WordPress a receita líquida SMS do dia anterior fechado na Smart Bidding, com upsert/readback e uma retentativa automática após 5 minutos para falhas transitórias.
- **Comando:** `flock -n /var/lock/sync_sb_sms_revenue_daily.lock /root/mgs-agent/scripts/sync-sb-sms-revenue-daily.sh >> /root/mgs-agent/logs/sync-sb-sms-revenue-daily.log 2>&1`
- **Log:** `/root/mgs-agent/logs/sync-sb-sms-revenue-daily.log`
- **Último log:** 2026-08-10T08:00:16-04:00 (20485 bytes)

### `monitor_hermes_pending_writes.py`
- **Frequência:** `* * * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/monitor_hermes_pending_writes.lock /root/mgs-agent/scripts/monitor_hermes_pending_writes.py >> /root/mgs-agent/logs/monitor-hermes-pending-writes.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-hermes-pending-writes.log`
- **Último log:** 2026-08-10T08:09:01-04:00 (7268033 bytes)

### `finalize-hermes-structural-write.py`
- **Frequência:** `* * * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/finalize-hermes-structural-write.lock /root/mgs-agent/scripts/finalize-hermes-structural-write.py >> /root/mgs-agent/logs/hermes-structural-write-finalizer.log 2>&1`
- **Log:** `/root/mgs-agent/logs/hermes-structural-write-finalizer.log`
- **Último log:** 2026-08-10T08:10:01-04:00 (1316724 bytes)

### `dtr-sb-restricted-summary.py`
- **Frequência:** `5 8 * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/dtr_sb_restricted_summary.lock xvfb-run -a /root/.local/share/mgs/sb-venv/bin/python /root/mgs-agent/scripts/dtr-sb-restricted-summary.py >> /root/mgs-agent/logs/dtr-sb-restricted-summary.log 2>&1`
- **Log:** `/root/mgs-agent/logs/dtr-sb-restricted-summary.log`
- **Último log:** 2026-08-10T08:05:15-04:00 (156976 bytes)

### `sb-restricted-transition-monitor.py`
- **Frequência:** `14,29,44,59 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/sb_restricted_transition_monitor.lock xvfb-run -a /root/.local/share/mgs/sb-venv/bin/python /root/mgs-agent/scripts/sb-restricted-transition-monitor.py --apply >> /root/mgs-agent/logs/sb-restricted-transition-monitor.log 2>&1`
- **Log:** `/root/mgs-agent/logs/sb-restricted-transition-monitor.log`
- **Último log:** 2026-08-10T07:59:17-04:00 (8249913 bytes)

### `monitor-sms-funnel-balance.py`
- **Frequência:** `24 0,1,7-23 * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/monitor_sms_funnel_balance.lock /root/mgs-agent/scripts/monitor-sms-funnel-balance.py >> /root/mgs-agent/logs/monitor-sms-funnel-balance.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-sms-funnel-balance.log`
- **Último log:** 2026-08-10T07:24:03-04:00 (42130 bytes)

### `monitor-sms-funnel-balance.py`
- **Frequência:** `*/5 13,14 * * 5`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `flock -n /var/lock/monitor_sms_funnel_balance_friday.lock /root/mgs-agent/scripts/monitor-sms-funnel-balance.py --friday-report >> /root/mgs-agent/logs/monitor-sms-funnel-balance.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-sms-funnel-balance.log`
- **Último log:** 2026-08-10T07:24:03-04:00 (42130 bytes)

### `monitor-hermes-memory-capacity.py`
- **Frequência:** `4,14,24,34,44,54 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** médio: reescreve USER/MEMORY somente após gates fail-closed e backup protegido
- **Função:** Compacta USER/MEMORY automaticamente de >=90% para <=85% com backup, validação semântica, rollback/readback e alerta metadata-only em #limites-90.
- **Comando:** `flock -n /run/lock/mgs-hermes-memory-capacity.lock /root/mgs-agent/scripts/monitor-hermes-memory-capacity.py >> /root/mgs-agent/logs/monitor-hermes-memory-capacity.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-hermes-memory-capacity.log`
- **Último log:** 2026-08-10T08:04:01-04:00 (639096 bytes)

### `hermes-news-explainer-watchdog.py`
- **Frequência:** `* * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo/médio: consulta Discord a cada minuto e só posta ao recuperar explicação órfã
- **Função:** Confere diretamente no Discord se cada anúncio recebeu explicação; reconcilia state inconsistente e recupera órfãos com readback e fallback antes do SLA de 10 minutos.
- **Comando:** `flock -n /var/lock/hermes_news_explainer_watchdog.lock /root/mgs-agent/scripts/hermes-news-explainer-watchdog.py >> /root/mgs-agent/logs/hermes-news-explainer-watchdog.log 2>&1`
- **Log:** `/root/mgs-agent/logs/hermes-news-explainer-watchdog.log`
- **Último log:** 2026-08-10T08:09:02-04:00 (5791823 bytes)

### `hermes-context-cost-audit.py`
- **Frequência:** `47 4 * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo: leitura local + escrita atômica de estado agregado sem conteúdo das conversas
- **Função:** Audita diariamente o orçamento fixo, contexto estimado e uso/custo cumulativo recente dos profiles Zeus, Atena e Ares, sem chamada de modelo.
- **Comando:** `flock -n /var/lock/hermes_context_cost_audit.lock /root/mgs-agent/scripts/hermes-context-cost-audit.py >> /root/mgs-agent/logs/hermes-context-cost-audit.log 2>&1`
- **Log:** `/root/mgs-agent/logs/hermes-context-cost-audit.log`
- **Último log:** 2026-08-10T04:47:11-04:00 (2779 bytes)

### `sb-broadcast-template-repair.sh`
- **Frequência:** `0 8 * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `/root/mgs-agent/scripts/sb-broadcast-template-repair.sh dispatch >> /root/mgs-agent/logs/sb-broadcast-template-repair-cron.log 2>&1`
- **Log:** `/root/mgs-agent/logs/sb-broadcast-template-repair-cron.log`
- **Último log:** 2026-08-10T08:01:40-04:00 (111238 bytes)

### `sb-broadcast-template-repair.sh`
- **Frequência:** `*/15 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `/root/mgs-agent/scripts/sb-broadcast-template-repair.sh check >> /root/mgs-agent/logs/sb-broadcast-template-repair-cron.log 2>&1`
- **Log:** `/root/mgs-agent/logs/sb-broadcast-template-repair-cron.log`
- **Último log:** 2026-08-10T08:01:40-04:00 (111238 bytes)

### `sb-broadcast-template-repair.sh`
- **Frequência:** `10 23 * * *`
- **Owner:** Zeus/Infra
- **Risco:** não classificado
- **Função:** Sem descrição cadastrada.
- **Comando:** `/root/mgs-agent/scripts/sb-broadcast-template-repair.sh digest >> /root/mgs-agent/logs/sb-broadcast-template-repair-cron.log 2>&1`
- **Log:** `/root/mgs-agent/logs/sb-broadcast-template-repair-cron.log`
- **Último log:** 2026-08-10T08:01:40-04:00 (111238 bytes)

### `sync-sb-messenger-revenue-sheet.py`
- **Frequência:** `17 8 * * *`
- **Owner:** Zeus/Revenue Tech
- **Risco:** médio: lê SB autenticada e substitui a coluna C da planilha com backup, canário, rollback e readback
- **Função:** Atualiza diariamente a coluna RECEITA 7 DIAS da aba Migracao 22/06 com o Messenger Daily ao vivo, por Segurador, usando a Service Account canônica e readback exato.
- **Comando:** `flock -n /var/lock/sync_sb_messenger_revenue_sheet.lock xvfb-run -a /root/.local/share/mgs/sb-venv/bin/python /root/mgs-agent/scripts/sync-sb-messenger-revenue-sheet.py --apply >> /root/mgs-agent/logs/sync-sb-messenger-revenue-sheet.log 2>&1`
- **Log:** `/root/mgs-agent/logs/sync-sb-messenger-revenue-sheet.log`
- **Último log:** 2026-08-09T08:17:12-04:00 (1442 bytes)

## Comandos úteis

```bash
# Regenerar este documento
/root/mgs-agent/scripts/cron-control-plane.py --markdown > /root/mgs-agent/docs/CRONS.md

# Ver JSON bruto
/root/mgs-agent/scripts/cron-control-plane.py --json | jq .

# Ver root crontab atual
crontab -l
```
