# Crons MGS — Control Plane

Gerado em: `2026-06-18T08:10:01-04:00`
Fonte: `root crontab + script/log stat, read-only`
Total MGS ativo no root crontab: **20**

## Resumo executivo

```text
Frequência          | Script                         | Owner          | Risco                                                             | Flock | Último log
------------------- | ------------------------------ | -------------- | ----------------------------------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------
*/5 * * * *         | sync-souls.sh                  | Zeus/Infra     | baixo                                                             | sim   | 2026-06-18T08:05:01-04:00 synced hera skills/creative/creative-brief-handoff
11,26,41,56 * * * * | monitor-auto-push.sh           | Zeus/Infra     | baixo                                                             | sim   | [2026-06-18T07:56:01-04:00] monitor-auto-push: Concluído. consecutive_failures=0 last_ok=b0caea28
23 10 * * *         | monitor-yoast-health-eggbev.sh | Atena/Conteúdo | baixo                                                             | sim   | (sem log útil ainda)
7,22,37,52 * * * *  | check-pending-reports.sh       | Zeus/Infra     | baixo                                                             | sim   | [2026-06-18 08:07:01] check-pending-reports.sh concluído
1-56/5 * * * *      | monitor-service-restarts.sh    | Zeus/Infra     | baixo                                                             | sim   | 2026-06-18T08:06:02-04:00 [monitor-service-restarts] OK
47 12 * * *         | monitor-gpt55-oauth-cost.sh    | Zeus/Infra     | baixo                                                             | sim   | (sem log útil ainda)
3-58/5 * * * *      | monitor-tool-loops.sh          | Zeus/Infra     | baixo                                                             | sim   | Loop detector: 0 alertas enviados
0 5 * * *           | infra-discovery.sh             | Zeus/Infra     | médio: sobrescreve infra-inventory.json                           | sim   | [05:00:05] === infra-discovery.sh DONE ===
37 8,14,20 * * *    | monitor-hermes-updates.sh      | Zeus/Infra     | baixo                                                             | sim   | (sem log útil ainda)
*/15 * * * *        | track-article-cost.sh          | Atena/Conteúdo | baixo/médio: escreve SQLite local                                 | sim   | [2026-06-18T08:00:01-0400] Nothing to process. Exit.
0 * * * *           | cleanup-zombie-sessions.sh     | Zeus/Infra     | médio: fecha sessões Hermes inativas                              | sim   | [2026-06-18T08:00:01-0400] OK total closed zombie sessions: 0 (grace=180min)
17 3 * * *          | housekeeping-bak-cleanup.sh    | Zeus/Infra     | alto: deleta backups antigos, preservando último por família      | sim   | [2026-06-18T03:17:06-04:00] housekeeping: === END — deletados 5 arquivos / 0.15 MB ===
0 8 * * *           | pendencia-render-md.sh         | Zeus/Ops       | baixo: re-renderiza docs/PENDENCIAS.md                            | sim   | Tamanho: 16671 bytes
0 * * * *           | chat-log.sh                    | Zeus/Ops       | baixo: re-renderiza índice                                        | sim   | 2 sessões indexadas
*/15 * * * *        | sync-codex-oauth.sh            | Zeus/Infra     | médio: atualiza auth.json dos profiles                            | sim   | [2026-06-18T12:00:01Z] done: all profiles in sync, nothing to do
10 8 * * *          | cron-control-plane.py          | Zeus/Ops       | baixo: re-renderiza docs/CRONS.md                                 | sim   | (sem log útil ainda)
*/15 * * * *        | monitor-cron-stale-logs.sh     | Zeus/Infra     | baixo: read-only + alerta Discord                                 | sim   | [2026-06-18T12:00:01Z] cron-stale check: jobs=20 problems=0 resolved=0 alerts_sent=0
*/5 * * * *         | hermes-news-explainer.py       | Zeus/Infra     | baixo/médio: consulta Discord e pode postar explicação automática | sim   | 2026-06-18T12:05:01.987415Z done posted=0 skipped=0 candidates=0 last_seen_id=1516965778895929405
7 8,14,20 * * *     | monitor-webshare-status.sh     | Zeus/Infra     | baixo: consulta status público + alerta Discord se anomalia       | sim   | [2026-06-18T08:07:01-04:00] monitor-webshare-status: OK completed mode=normal
41 3 * * *          | mgs-safety-backup.sh           | Zeus/Infra     | médio: cria tar.gz local, exclui segredos por padrão              | sim   | [2026-06-18T03:41:01-04:00] mgs-safety-backup: SKIP: último backup ainda dentro do intervalo de 3 dias: /root/mgs-agent/backups/safety/mgs-safety-20260616-034102.tar.gz
```

## Pontos de atenção

- Alto risco: `housekeeping-bak-cleanup.sh`
- Médio risco: `infra-discovery.sh`, `cleanup-zombie-sessions.sh`, `sync-codex-oauth.sh`, `mgs-safety-backup.sh`
- Crons sem `flock`: nenhum

## Detalhes por cron

### `sync-souls.sh`
- **Frequência:** `*/5 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Sincroniza SOUL.md, config.yaml e skills MGS dos profiles Hermes para versionamento no repo.
- **Comando:** `flock -n /var/lock/sync_souls.lock /root/mgs-agent/scripts/sync-souls.sh >> /root/mgs-agent/logs/sync-souls.log 2>&1`
- **Log:** `/root/mgs-agent/logs/sync-souls.log`
- **Último log:** 2026-06-18T08:05:01-04:00 (28126 bytes)

### `monitor-auto-push.sh`
- **Frequência:** `11,26,41,56 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Monitora falhas no auto-push Git do /root/mgs-agent e alerta em #mgs-alerts.
- **Comando:** `flock -n /var/lock/monitor_auto_push.lock /root/mgs-agent/scripts/monitor-auto-push.sh >> /root/mgs-agent/logs/monitor-auto-push.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-auto-push.log`
- **Último log:** 2026-06-18T07:56:01-04:00 (11584 bytes)

### `monitor-yoast-health-eggbev.sh`
- **Frequência:** `23 10 * * *`
- **Owner:** Atena/Conteúdo
- **Risco:** baixo
- **Função:** Monitora saúde Yoast do eggbev: SEO + Readability com baseline, semanal e alerta por degradação.
- **Comando:** `flock -n /var/lock/monitor_yoast_health_eggbev.lock /root/mgs-agent/scripts/monitor-yoast-health-eggbev.sh >> /root/mgs-agent/logs/monitor-yoast-health-eggbev.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-yoast-health-eggbev.log`
- **Último log:** 2026-06-18T00:00:01-04:00 (0 bytes)

### `check-pending-reports.sh`
- **Frequência:** `7,22,37,52 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Detecta skills MGS sem REPORT-INFRA/inventário e cobra correção no #alerts-infra.
- **Comando:** `flock -n /var/lock/check_pending_reports.lock /root/mgs-agent/scripts/check-pending-reports.sh >> /root/mgs-agent/logs/check-pending-reports.log 2>&1`
- **Log:** `/root/mgs-agent/logs/check-pending-reports.log`
- **Último log:** 2026-06-18T08:07:02-04:00 (4158 bytes)

### `monitor-service-restarts.sh`
- **Frequência:** `1-56/5 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Detecta restarts inesperados dos services zeus-gateway, atena-gateway, ares-gateway, hera-gateway e mgs-autocommit.
- **Comando:** `flock -n /var/lock/monitor_service_restarts.lock /root/mgs-agent/scripts/monitor-service-restarts.sh >> /root/mgs-agent/logs/monitor-service-restarts.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-service-restarts.log`
- **Último log:** 2026-06-18T08:06:02-04:00 (64092 bytes)

### `monitor-gpt55-oauth-cost.sh`
- **Frequência:** `47 12 * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Calcula uso hipotético GPT-5.5/OAuth dos agentes; OAuth não gera custo real por token.
- **Comando:** `flock -n /var/lock/monitor_gpt55_oauth_cost.lock /root/mgs-agent/scripts/monitor-gpt55-oauth-cost.sh >> /root/mgs-agent/logs/monitor-gpt55-oauth-cost.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-gpt55-oauth-cost.log`
- **Último log:** 2026-06-18T00:00:01-04:00 (0 bytes)

### `monitor-tool-loops.sh`
- **Frequência:** `3-58/5 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Detecta loops de tool_calls nas sessões Hermes e alerta infra.
- **Comando:** `flock -n /var/lock/monitor_tool_loops.lock /root/mgs-agent/scripts/monitor-tool-loops.sh >> /root/mgs-agent/logs/monitor-tool-loops.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-tool-loops.log`
- **Último log:** 2026-06-18T08:08:01-04:00 (3332 bytes)

### `infra-discovery.sh`
- **Frequência:** `0 5 * * *`
- **Owner:** Zeus/Infra
- **Risco:** médio: sobrescreve infra-inventory.json
- **Função:** Regenera data/infra-inventory.json a partir do estado real do sistema.
- **Comando:** `flock -n /var/lock/infra_discovery.lock /root/mgs-agent/scripts/infra-discovery.sh >> /root/mgs-agent/logs/infra-discovery.log 2>&1`
- **Log:** `/root/mgs-agent/logs/infra-discovery.log`
- **Último log:** 2026-06-18T05:00:05-04:00 (589 bytes)

### `monitor-hermes-updates.sh`
- **Frequência:** `37 8,14,20 * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo
- **Função:** Verifica updates upstream do Hermes Agent e alerta quando há nova versão.
- **Comando:** `flock -n /var/lock/monitor_hermes_updates.lock /root/mgs-agent/scripts/monitor-hermes-updates.sh >> /root/mgs-agent/logs/monitor-hermes-updates.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-hermes-updates.log`
- **Último log:** 2026-06-18T00:00:01-04:00 (0 bytes)

### `track-article-cost.sh`
- **Frequência:** `*/15 * * * *`
- **Owner:** Atena/Conteúdo
- **Risco:** baixo/médio: escreve SQLite local
- **Função:** Calcula custo hipotético por artigo publicado e grava data/article-tracker.db.
- **Comando:** `flock -n /var/lock/track_article_cost.lock /root/mgs-agent/scripts/track-article-cost.sh >> /root/mgs-agent/logs/track-article-cost-cron.log 2>&1`
- **Log:** `/root/mgs-agent/logs/track-article-cost-cron.log`
- **Último log:** 2026-06-18T08:00:01-04:00 (8085 bytes)

### `cleanup-zombie-sessions.sh`
- **Frequência:** `0 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** médio: fecha sessões Hermes inativas
- **Função:** Fecha sessões Hermes zumbis/inativas usando última atividade real, com grace padrão de 180 minutos.
- **Comando:** `flock -n /var/lock/cleanup_zombie_sessions.lock /root/mgs-agent/scripts/cleanup-zombie-sessions.sh >> /root/mgs-agent/logs/cleanup-zombie-sessions.log 2>&1`
- **Log:** `/root/mgs-agent/logs/cleanup-zombie-sessions.log`
- **Último log:** 2026-06-18T08:00:01-04:00 (4546 bytes)

### `housekeeping-bak-cleanup.sh`
- **Frequência:** `17 3 * * *`
- **Owner:** Zeus/Infra
- **Risco:** alto: deleta backups antigos, preservando último por família
- **Função:** Remove backups antigos (.bak/.backup/.old/.orig/~) com retenção padrão de 15 dias, preservando sempre o último por família.
- **Comando:** `flock -n /var/lock/housekeeping_bak_cleanup.lock /root/mgs-agent/scripts/housekeeping-bak-cleanup.sh >> /root/mgs-agent/logs/housekeeping-cron.log 2>&1`
- **Log:** `/root/mgs-agent/logs/housekeeping-cron.log`
- **Último log:** 2026-06-18T03:17:06-04:00 (887 bytes)

### `pendencia-render-md.sh`
- **Frequência:** `0 8 * * *`
- **Owner:** Zeus/Ops
- **Risco:** baixo: re-renderiza docs/PENDENCIAS.md
- **Função:** Renderiza docs/PENDENCIAS.md a partir de data/pendencias.db.json.
- **Comando:** `flock -n /var/lock/pendencia_render_md.lock /root/mgs-agent/scripts/pendencia-render-md.sh >> /root/mgs-agent/logs/pendencia-render.log 2>&1`
- **Log:** `/root/mgs-agent/logs/pendencia-render.log`
- **Último log:** 2026-06-18T08:00:01-04:00 (151 bytes)

### `chat-log.sh`
- **Frequência:** `0 * * * *`
- **Owner:** Zeus/Ops
- **Risco:** baixo: re-renderiza índice
- **Função:** Mantém índice Markdown de data/chat-logs/INDEX.md.
- **Comando:** `flock -n /var/lock/chat_log_rebuild.lock /root/mgs-agent/scripts/chat-log.sh --rebuild-index >> /root/mgs-agent/logs/chat-log-rebuild.log 2>&1`
- **Log:** `/root/mgs-agent/logs/chat-log-rebuild.log`
- **Último log:** 2026-06-18T08:00:01-04:00 (774 bytes)

### `sync-codex-oauth.sh`
- **Frequência:** `*/15 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** médio: atualiza auth.json dos profiles
- **Função:** Sincroniza tokens OAuth Codex do auth global para profiles Hermes com safety check.
- **Comando:** `flock -n /var/lock/sync_codex_oauth.lock /root/mgs-agent/scripts/sync-codex-oauth.sh >> /root/mgs-agent/logs/sync-codex-oauth.log 2>&1`
- **Log:** `/root/mgs-agent/logs/sync-codex-oauth.log`
- **Último log:** 2026-06-18T08:00:01-04:00 (18645 bytes)

### `cron-control-plane.py`
- **Frequência:** `10 8 * * *`
- **Owner:** Zeus/Ops
- **Risco:** baixo: re-renderiza docs/CRONS.md
- **Função:** Regenera docs/CRONS.md com inventário/status dos crons MGS.
- **Comando:** `flock -n /var/lock/cron_control_plane.lock /root/mgs-agent/scripts/cron-control-plane.py --write-doc >> /root/mgs-agent/logs/cron-control-plane.log 2>&1`
- **Log:** `/root/mgs-agent/logs/cron-control-plane.log`
- **Último log:** 2026-06-18T00:00:00-04:00 (0 bytes)

### `monitor-cron-stale-logs.sh`
- **Frequência:** `*/15 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo: read-only + alerta Discord
- **Função:** Watchdog que alerta quando logs de crons MGS deixam de atualizar dentro da tolerância esperada.
- **Comando:** `flock -n /var/lock/monitor_cron_stale_logs.lock /root/mgs-agent/scripts/monitor-cron-stale-logs.sh >> /root/mgs-agent/logs/monitor-cron-stale-logs.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-cron-stale-logs.log`
- **Último log:** 2026-06-18T08:00:01-04:00 (2805 bytes)

### `hermes-news-explainer.py`
- **Frequência:** `*/5 * * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo/médio: consulta Discord e pode postar explicação automática
- **Função:** Lê anúncios no canal Hermes News e posta explicação executiva do Zeus em PT-BR, com estado anti-duplicata.
- **Comando:** `flock -n /var/lock/hermes_news_explainer.lock /root/mgs-agent/scripts/hermes-news-explainer.py >> /root/mgs-agent/logs/hermes-news-explainer.log 2>&1`
- **Log:** `/root/mgs-agent/logs/hermes-news-explainer.log`
- **Último log:** 2026-06-18T08:05:01-04:00 (9604 bytes)

### `monitor-webshare-status.sh`
- **Frequência:** `7 8,14,20 * * *`
- **Owner:** Zeus/Infra
- **Risco:** baixo: consulta status público + alerta Discord se anomalia
- **Função:** Monitora status.webshare.io e alerta infra quando detectar manutenção/incidente relevante.
- **Comando:** `flock -n /var/lock/monitor_webshare_status.lock /root/mgs-agent/scripts/monitor-webshare-status.sh >> /root/mgs-agent/logs/monitor-webshare-status.log 2>&1`
- **Log:** `/root/mgs-agent/logs/monitor-webshare-status.log`
- **Último log:** 2026-06-18T08:07:01-04:00 (292 bytes)

### `mgs-safety-backup.sh`
- **Frequência:** `41 3 * * *`
- **Owner:** Zeus/Infra
- **Risco:** médio: cria tar.gz local, exclui segredos por padrão
- **Função:** Cria snapshot operacional seguro no máximo a cada 3 dias, excluindo segredos conhecidos e preservando o último backup.
- **Comando:** `flock -n /var/lock/mgs_safety_backup.lock /root/mgs-agent/scripts/mgs-safety-backup.sh >> /root/mgs-agent/logs/mgs-safety-backup-cron.log 2>&1`
- **Log:** `/root/mgs-agent/logs/mgs-safety-backup-cron.log`
- **Último log:** 2026-06-18T03:41:01-04:00 (170 bytes)

## Comandos úteis

```bash
# Regenerar este documento
/root/mgs-agent/scripts/cron-control-plane.py --markdown > /root/mgs-agent/docs/CRONS.md

# Ver JSON bruto
/root/mgs-agent/scripts/cron-control-plane.py --json | jq .

# Ver root crontab atual
crontab -l
```
